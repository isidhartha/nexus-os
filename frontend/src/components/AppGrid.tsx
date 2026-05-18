import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Grid3X3, Play, Terminal, Globe, FileText, Music, Code, Calculator } from 'lucide-react';
import axios from 'axios';
import { useNexusStore } from '../store';

interface AppDef {
  name: string;
  label: string;
  icon: React.ReactNode;
  color: string;
}

const APPS: AppDef[] = [
  { name: 'browser', label: 'Browser', icon: <Globe size={20} />, color: '#00d4ff' },
  { name: 'terminal', label: 'Terminal', icon: <Terminal size={20} />, color: '#00ff88' },
  { name: 'notepad', label: 'Notes', icon: <FileText size={20} />, color: '#ffaa00' },
  { name: 'calculator', label: 'Calc', icon: <Calculator size={20} />, color: '#ff6b6b' },
  { name: 'vscode', label: 'VS Code', icon: <Code size={20} />, color: '#007acc' },
  { name: 'spotify', label: 'Music', icon: <Music size={20} />, color: '#1db954' },
];

export default function AppGrid(): React.ReactElement {
  const { addActiveApp } = useNexusStore();
  const [launching, setLaunching] = useState<string | null>(null);

  const launch = async (app: AppDef) => {
    setLaunching(app.name);
    try {
      await axios.post('/api/v1/apps/launch', { app_name: app.name });
      addActiveApp(app.name);
    } catch {
      /* offline mode */
    } finally {
      setTimeout(() => setLaunching(null), 1000);
    }
  };

  return (
    <div className="nexus-panel">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-nexus-border">
        <Grid3X3 size={14} className="text-nexus-cyan" />
        <span className="font-display text-xs text-nexus-cyan tracking-widest uppercase">
          App Launcher
        </span>
      </div>

      <div className="p-3 grid grid-cols-3 gap-2">
        {APPS.map((app) => (
          <motion.button
            key={app.name}
            onClick={() => launch(app)}
            disabled={launching === app.name}
            className="flex flex-col items-center gap-2 p-3 rounded-lg border border-nexus-border
                       hover:border-nexus-cyan/50 hover:bg-nexus-glow/20 transition-all duration-200
                       disabled:opacity-50"
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
          >
            <motion.div
              style={{ color: app.color }}
              animate={
                launching === app.name
                  ? { rotate: [0, 10, -10, 0], scale: [1, 1.2, 1] }
                  : {}
              }
              transition={{ duration: 0.5 }}
            >
              {app.icon}
            </motion.div>
            <span className="text-nexus-text text-xs font-mono">{app.label}</span>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
