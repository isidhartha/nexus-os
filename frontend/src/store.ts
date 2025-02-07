import { create } from 'zustand';

export interface CommandEntry {
  id: string;
  text: string;
  timestamp: string;
  type: 'command' | 'response' | 'system';
}

export interface MemoryEntry {
  id: string;
  key: string;
  value: string;
  category: string;
  created_at: string;
}

export interface IoTDevice {
  id: string;
  name: string;
  type: string;
  state: Record<string, unknown>;
  online: boolean;
}

interface NexusState {
  isListening: boolean;
  isProcessing: boolean;
  wsConnected: boolean;
  systemStatus: string;
  commandHistory: CommandEntry[];
  memories: MemoryEntry[];
  iotDevices: IoTDevice[];
  activeApps: string[];

  setListening: (v: boolean) => void;
  setProcessing: (v: boolean) => void;
  setWsConnected: (v: boolean) => void;
  setSystemStatus: (s: string) => void;
  addCommandEntry: (e: CommandEntry) => void;
  setMemories: (m: MemoryEntry[]) => void;
  setIoTDevices: (d: IoTDevice[]) => void;
  addActiveApp: (name: string) => void;
  clearHistory: () => void;
}

export const useNexusStore = create<NexusState>((set) => ({
  isListening: false,
  isProcessing: false,
  wsConnected: false,
  systemStatus: 'idle',
  commandHistory: [],
  memories: [],
  iotDevices: [],
  activeApps: [],

  setListening: (v) => set({ isListening: v }),
  setProcessing: (v) => set({ isProcessing: v }),
  setWsConnected: (v) => set({ wsConnected: v }),
  setSystemStatus: (s) => set({ systemStatus: s }),
  addCommandEntry: (e) =>
    set((state) => ({
      commandHistory: [...state.commandHistory.slice(-99), e],
    })),
  setMemories: (m) => set({ memories: m }),
  setIoTDevices: (d) => set({ iotDevices: d }),
  addActiveApp: (name) =>
    set((state) => ({
      activeApps: state.activeApps.includes(name)
        ? state.activeApps
        : [...state.activeApps, name],
    })),
  clearHistory: () => set({ commandHistory: [] }),
}));
