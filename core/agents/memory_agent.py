"""AI memory agent — stores, retrieves, and reasons over persistent context."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..shared.logging import get_logger
from ..shared.memory import MemoryStore, get_memory_store
from ..shared.models import MemoryEntry

logger = get_logger(__name__)


class MemoryAgent:
    """Manages long-term AI memory with semantic retrieval."""

    def __init__(self, store: Optional[MemoryStore] = None) -> None:
        self._store = store or get_memory_store()
        self._embedder = None
        self._init_embedder()

    def _init_embedder(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import]
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("SentenceTransformer embedder loaded")
        except ImportError:
            logger.warning("sentence-transformers not installed — using text-only search")

    def _embed(self, text: str) -> Optional[List[float]]:
        if not self._embedder:
            return None
        try:
            return self._embedder.encode(text, normalize_embeddings=True).tolist()
        except Exception as exc:
            logger.error("Embedding error: %s", exc)
            return None

    def remember(
        self,
        key: str,
        value: str,
        category: str = "general",
        speaker_id: Optional[str] = None,
    ) -> MemoryEntry:
        """Store a fact or context in memory."""
        embedding = self._embed(f"{key} {value}")
        entry = self._store.store(
            key=key,
            value=value,
            category=category,
            speaker_id=speaker_id,
            embedding=embedding,
        )
        logger.debug("Stored memory: %s = %s", key, value[:80])
        return entry

    def recall(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        """Retrieve relevant memories by text or semantic search."""
        query_emb = self._embed(query)
        if query_emb:
            results = self._store.semantic_search(query_emb, limit=limit)
            if results:
                return results
        return self._store.search(query, limit=limit)

    def recall_by_category(self, category: str, limit: int = 20) -> List[MemoryEntry]:
        return self._store.list_all(category=category, limit=limit)

    def forget(self, entry_id: str) -> bool:
        return self._store.delete(entry_id)

    def list_recent(self, limit: int = 20) -> List[MemoryEntry]:
        return self._store.list_all(limit=limit)

    def build_context_prompt(self, query: str, max_entries: int = 5) -> str:
        """Build a context string from relevant memories for AI prompts."""
        entries = self.recall(query, limit=max_entries)
        if not entries:
            return ""
        lines = ["Relevant context from memory:"]
        for e in entries:
            lines.append(f"- [{e.category}] {e.key}: {e.value}")
        return "\n".join(lines)

    async def execute(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        handlers = {
            "remember": self._handle_remember,
            "recall": self._handle_recall,
            "forget": self._handle_forget,
            "list": self._handle_list,
            "context": self._handle_context,
        }
        handler = handlers.get(action)
        if not handler:
            return {"success": False, "error": f"Unknown memory action: {action}"}

        try:
            return await handler(params)
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _handle_remember(self, params: Dict[str, Any]) -> Dict[str, Any]:
        entry = self.remember(
            key=params["key"],
            value=params["value"],
            category=params.get("category", "general"),
            speaker_id=params.get("speaker_id"),
        )
        return {"success": True, "id": entry.id}

    async def _handle_recall(self, params: Dict[str, Any]) -> Dict[str, Any]:
        entries = self.recall(params["query"], limit=params.get("limit", 5))
        return {"success": True, "entries": [e.model_dump(mode="json") for e in entries]}

    async def _handle_forget(self, params: Dict[str, Any]) -> Dict[str, Any]:
        deleted = self.forget(params["id"])
        return {"success": deleted}

    async def _handle_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        entries = self.list_recent(limit=params.get("limit", 20))
        return {"success": True, "entries": [e.model_dump(mode="json") for e in entries]}

    async def _handle_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        ctx = self.build_context_prompt(params["query"])
        return {"success": True, "context": ctx}
