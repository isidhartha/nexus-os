export interface NexusClientOptions {
  host?: string;
  timeout?: number;
}

export interface CommandResponse {
  response: string;
  action_taken?: string;
  success: boolean;
}

export interface StatusResponse {
  listening: boolean;
  mode: string;
  uptime: number;
}

export interface Memory {
  id: string;
  content: string;
  timestamp: string;
  relevance?: number;
}

export declare class NexusClient {
  constructor(options?: NexusClientOptions);
  command(text: string, mode?: 'text' | 'voice'): Promise<CommandResponse>;
  startListening(): Promise<{ success: boolean }>;
  stopListening(): Promise<{ success: boolean }>;
  status(): Promise<StatusResponse>;
  memories(query: string): Promise<Memory[]>;
  remember(content: string): Promise<{ id: string }>;
  plugins(): Promise<string[]>;
  runWorkflow(name: string): Promise<{ success: boolean; steps_completed: number }>;
  health(): Promise<{ status: string }>;
}

export default NexusClient;
