import React, { useEffect, useRef, useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Workflows from './pages/Workflows';
import Settings from './pages/Settings';
import { useNexusStore } from './store';

const WS_URL = 'ws://localhost:8000/ws/nexus';

export default function App(): React.ReactElement {
  const wsRef = useRef<WebSocket | null>(null);
  const { addCommandEntry, setSystemStatus, setWsConnected } = useNexusStore();
  const [reconnectCount, setReconnectCount] = useState(0);

  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout>;

    function connect() {
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          setWsConnected(true);
          console.log('[NexusOS] WebSocket connected');
        };

        ws.onmessage = (evt) => {
          try {
            const msg = JSON.parse(evt.data);
            handleWsMessage(msg);
          } catch {
            /* ignore malformed */
          }
        };

        ws.onclose = () => {
          setWsConnected(false);
          timeoutId = setTimeout(() => {
            setReconnectCount((c) => c + 1);
          }, 3000);
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch {
        timeoutId = setTimeout(() => setReconnectCount((c) => c + 1), 5000);
      }
    }

    function handleWsMessage(msg: { type: string; data: Record<string, unknown> }) {
      switch (msg.type) {
        case 'command_complete':
          addCommandEntry({
            id: String(msg.data.id ?? ''),
            text: String(msg.data.result ?? ''),
            timestamp: new Date().toISOString(),
            type: 'response',
          });
          break;
        case 'voice':
          setSystemStatus(String(msg.data.event ?? ''));
          break;
        default:
          break;
      }
    }

    connect();
    return () => {
      clearTimeout(timeoutId);
      wsRef.current?.close();
    };
  }, [reconnectCount]);

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard wsRef={wsRef} />} />
          <Route path="/workflows" element={<Workflows />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
