import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Brain, Search, RefreshCw } from 'lucide-react';
import { useNexusStore, MemoryEntry } from '../store';
import axios from 'axios';

export default function MemoryPanel(): React.ReactElement {
  const { memories, setMemories } = useNexusStore();
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchMemories = async () => {
    setLoading(true);
    try {
      const url = search
        ? `/api/v1/memory/search?query=${encodeURIComponent(search)}`
        : '/api/v1/memory?limit=30';
      const { data } = await axios.get<MemoryEntry[]>(url);
      setMemories(data);
    } catch {
      /* server may be offline */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMemories();
    const id = setInterval(fetchMemories, 15000);
    return () => clearInterval(id);
  }, []);

  const filtered = memories.filter(
    (m) =>
      !search ||
      m.key.toLowerCase().includes(search.toLowerCase()) ||
      m.value.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="nexus-panel flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-nexus-border">
        <div className="flex items-center gap-2">
          <Brain size={14} className="text-nexus-purple" />
          <span className="font-display text-xs text-nexus-purple tracking-widest uppercase">
            AI Memory
          </span>
          <span className="text-nexus-dim text-xs">({memories.length})</span>
        </div>
        <button
          onClick={fetchMemories}
          className="text-nexus-dim hover:text-nexus-cyan transition-colors"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="px-4 py-2 border-b border-nexus-border">
        <div className="relative">
          <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-nexus-dim" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchMemories()}
            placeholder="Search memories..."
            className="nexus-input pl-8 text-xs py-1.5"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {filtered.length === 0 && (
          <p className="text-nexus-dim text-xs text-center mt-4">
            No memories yet. Start interacting with NexusOS!
          </p>
        )}
        {filtered.map((entry) => (
          <motion.div
            key={entry.id}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-nexus-bg/50 border border-nexus-border/50 rounded-lg p-3 group"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <p className="text-nexus-cyan text-xs font-mono truncate">{entry.key}</p>
                <p className="text-nexus-text text-xs mt-1 line-clamp-2">{entry.value}</p>
              </div>
              <span className="text-nexus-dim text-xs shrink-0 bg-nexus-border/30 px-1.5 py-0.5 rounded">
                {entry.category}
              </span>
            </div>
            <p className="text-nexus-dim text-xs mt-2">
              {new Date(entry.created_at).toLocaleDateString()}
            </p>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
