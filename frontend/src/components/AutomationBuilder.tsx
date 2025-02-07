import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Zap, Plus, Play, Trash2 } from 'lucide-react';
import axios from 'axios';

interface Step {
  id: string;
  action: string;
  params: string;
}

export default function AutomationBuilder(): React.ReactElement {
  const [name, setName] = useState('');
  const [steps, setSteps] = useState<Step[]>([]);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  const addStep = () => {
    setSteps((s) => [
      ...s,
      { id: crypto.randomUUID(), action: 'log', params: '{"message": "Step executed"}' },
    ]);
  };

  const removeStep = (id: string) => setSteps((s) => s.filter((x) => x.id !== id));

  const updateStep = (id: string, field: keyof Omit<Step, 'id'>, value: string) => {
    setSteps((s) => s.map((x) => (x.id === id ? { ...x, [field]: value } : x)));
  };

  const save = async () => {
    if (!name.trim() || steps.length === 0) return;
    const parsedSteps = steps.map((s, i) => {
      let params: Record<string, unknown> = {};
      try { params = JSON.parse(s.params); } catch { /* ignore */ }
      return { name: `step_${i + 1}`, action: s.action, params };
    });
    try {
      await axios.post('/api/v1/workflow', {
        name: name.trim(),
        description: 'User-defined workflow',
        steps: parsedSteps,
      });
      setResult(`Workflow "${name}" saved`);
    } catch {
      setResult('Error saving workflow');
    }
  };

  const runWorkflow = async () => {
    if (!name.trim()) return;
    setRunning(true);
    try {
      const { data } = await axios.post('/api/v1/workflow/run', { name: name.trim() });
      setResult(`Completed ${data.steps_completed}/${data.steps_total} steps`);
    } catch {
      setResult('Error running workflow');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="nexus-panel">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-nexus-border">
        <Zap size={14} className="text-nexus-purple" />
        <span className="font-display text-xs text-nexus-purple tracking-widest uppercase">
          Automation Builder
        </span>
      </div>

      <div className="p-4 space-y-3">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Workflow name..."
          className="nexus-input"
        />

        <div className="space-y-2 max-h-48 overflow-y-auto">
          {steps.map((step, idx) => (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="bg-nexus-bg rounded-lg border border-nexus-border p-2 space-y-2"
            >
              <div className="flex items-center gap-2">
                <span className="text-nexus-dim text-xs w-4">{idx + 1}.</span>
                <input
                  type="text"
                  value={step.action}
                  onChange={(e) => updateStep(step.id, 'action', e.target.value)}
                  placeholder="action"
                  className="nexus-input flex-1 py-1 text-xs"
                />
                <button
                  onClick={() => removeStep(step.id)}
                  className="text-nexus-dim hover:text-red-400 transition-colors"
                >
                  <Trash2 size={12} />
                </button>
              </div>
              <input
                type="text"
                value={step.params}
                onChange={(e) => updateStep(step.id, 'params', e.target.value)}
                placeholder='{"key": "value"}'
                className="nexus-input py-1 text-xs font-mono"
              />
            </motion.div>
          ))}
        </div>

        <button
          onClick={addStep}
          className="w-full py-2 border border-dashed border-nexus-border rounded-lg
                     text-nexus-dim text-xs hover:border-nexus-cyan hover:text-nexus-cyan
                     transition-all duration-200 flex items-center justify-center gap-1"
        >
          <Plus size={12} /> Add Step
        </button>

        <div className="flex gap-2">
          <button onClick={save} className="nexus-button flex-1">Save</button>
          <button
            onClick={runWorkflow}
            disabled={running}
            className="nexus-button flex-1 border-nexus-purple text-nexus-purple
                       hover:bg-nexus-purple/10 disabled:opacity-40 flex items-center justify-center gap-1"
          >
            <Play size={12} /> {running ? 'Running...' : 'Run'}
          </button>
        </div>

        {result && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-nexus-cyan text-xs text-center"
          >
            {result}
          </motion.p>
        )}
      </div>
    </div>
  );
}
