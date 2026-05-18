import React, { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Trash2 } from 'lucide-react';
import { CommandEntry, useNexusStore } from '../store';

interface CommandConsoleProps {
  onCommand: (text: string) => void;
  isProcessing: boolean;
}

function EntryRow({ entry }: { entry: CommandEntry }): React.ReactElement {
  const colors: Record<CommandEntry['type'], string> = {
    command: '#00d4ff',
    response: '#c8e6ff',
    system: '#7b2fff',
  };

  const prefixes: Record<CommandEntry['type'], string> = {
    command: '>>> ',
    response: '    ',
    system: '[SYS] ',
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex gap-2 py-0.5 font-mono text-sm leading-relaxed"
    >
      <span className="text-nexus-dim text-xs mt-0.5 shrink-0">
        {new Date(entry.timestamp).toLocaleTimeString()}
      </span>
      <span style={{ color: colors[entry.type] }}>
        {prefixes[entry.type]}
        {entry.text}
      </span>
    </motion.div>
  );
}

export default function CommandConsole({
  onCommand,
  isProcessing,
}: CommandConsoleProps): React.ReactElement {
  const { commandHistory, clearHistory } = useNexusStore();
  const [input, setInput] = React.useState('');
  const [historyIdx, setHistoryIdx] = React.useState(-1);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo(0, scrollRef.current.scrollHeight);
  }, [commandHistory]);

  const commands = commandHistory.filter((e) => e.type === 'command');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || isProcessing) return;
    onCommand(text);
    setInput('');
    setHistoryIdx(-1);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      const idx = Math.min(historyIdx + 1, commands.length - 1);
      setHistoryIdx(idx);
      setInput(commands[commands.length - 1 - idx]?.text ?? '');
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIdx <= 0) {
        setHistoryIdx(-1);
        setInput('');
      } else {
        const idx = historyIdx - 1;
        setHistoryIdx(idx);
        setInput(commands[commands.length - 1 - idx]?.text ?? '');
      }
    }
  }

  return (
    <div className="nexus-panel flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-nexus-border">
        <div className="flex items-center gap-2">
          <Terminal size={14} className="text-nexus-cyan" />
          <span className="font-display text-xs text-nexus-cyan tracking-widest uppercase">
            Command Console
          </span>
        </div>
        <button
          onClick={clearHistory}
          className="text-nexus-dim hover:text-nexus-cyan transition-colors"
          title="Clear console"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {/* Output */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-0.5 scan-overlay"
      >
        {commandHistory.length === 0 && (
          <p className="text-nexus-dim text-sm font-mono">
            NexusOS v1.0.0 — AI Operating System ready.
            <br />
            Type a command or say "Hey Nexus" to begin.
          </p>
        )}
        <AnimatePresence initial={false}>
          {commandHistory.map((entry) => (
            <EntryRow key={entry.id} entry={entry} />
          ))}
        </AnimatePresence>
        {isProcessing && (
          <div className="flex gap-1 mt-2">
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-nexus-cyan"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="flex gap-2 px-4 py-3 border-t border-nexus-border"
      >
        <span className="text-nexus-cyan font-mono text-sm mt-2">{'>'}</span>
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          className="nexus-input"
          placeholder="Enter command or ask NexusOS anything..."
          disabled={isProcessing}
          autoFocus
        />
        <button
          type="submit"
          disabled={isProcessing || !input.trim()}
          className="nexus-button shrink-0 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </form>
    </div>
  );
}
