"""SQLite-based persistent memory store with semantic search capability."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, List, Optional

import numpy as np

from .config import get_settings
from .logging import get_logger
from .models import MemoryEntry

logger = get_logger(__name__)


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    va, vb = np.array(a), np.array(b)
    norm_a, norm_b = np.linalg.norm(va), np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


class MemoryStore:
    """SQLite-backed memory store with optional embedding-based search."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        settings = get_settings()
        self.db_path = db_path or settings.memory_db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    speaker_id TEXT,
                    embedding TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_key ON memories(key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON memories(category)")

    def store(
        self,
        key: str,
        value: str,
        category: str = "general",
        speaker_id: Optional[str] = None,
        embedding: Optional[List[float]] = None,
    ) -> MemoryEntry:
        entry_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        embedding_json = json.dumps(embedding) if embedding else None

        with self._conn() as conn:
            existing = conn.execute(
                "SELECT id FROM memories WHERE key = ? AND category = ?",
                (key, category),
            ).fetchone()

            if existing:
                conn.execute(
                    """UPDATE memories SET value=?, updated_at=?, embedding=?
                       WHERE key=? AND category=?""",
                    (value, now, embedding_json, key, category),
                )
                entry_id = existing["id"]
            else:
                conn.execute(
                    """INSERT INTO memories
                       (id, key, value, category, speaker_id, embedding, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (entry_id, key, value, category, speaker_id, embedding_json, now, now),
                )

        return self.get(entry_id)  # type: ignore[return-value]

    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?", (entry_id,)
            ).fetchone()
        return self._row_to_entry(row) if row else None

    def search(self, query: str, limit: int = 10, category: Optional[str] = None) -> List[MemoryEntry]:
        with self._conn() as conn:
            if category:
                rows = conn.execute(
                    """SELECT * FROM memories WHERE category = ?
                       AND (key LIKE ? OR value LIKE ?)
                       ORDER BY updated_at DESC LIMIT ?""",
                    (category, f"%{query}%", f"%{query}%", limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM memories WHERE key LIKE ? OR value LIKE ?
                       ORDER BY updated_at DESC LIMIT ?""",
                    (f"%{query}%", f"%{query}%", limit),
                ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def semantic_search(
        self,
        query_embedding: List[float],
        limit: int = 10,
    ) -> List[MemoryEntry]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM memories WHERE embedding IS NOT NULL"
            ).fetchall()

        scored = []
        for row in rows:
            emb = json.loads(row["embedding"])
            score = _cosine_similarity(query_embedding, emb)
            scored.append((score, row))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [self._row_to_entry(r) for _, r in scored[:limit]]

    def list_all(self, category: Optional[str] = None, limit: int = 100) -> List[MemoryEntry]:
        with self._conn() as conn:
            if category:
                rows = conn.execute(
                    "SELECT * FROM memories WHERE category=? ORDER BY updated_at DESC LIMIT ?",
                    (category, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memories ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def delete(self, entry_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM memories WHERE id = ?", (entry_id,))
        return cur.rowcount > 0

    def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        emb = json.loads(row["embedding"]) if row["embedding"] else None
        return MemoryEntry(
            id=row["id"],
            key=row["key"],
            value=row["value"],
            category=row["category"],
            speaker_id=row["speaker_id"],
            embedding=emb,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            access_count=row["access_count"],
        )


_store: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store
