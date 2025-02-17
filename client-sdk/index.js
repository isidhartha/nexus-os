'use strict';

/**
 * NexusOS Client SDK
 * Node.js client for the NexusOS AI API
 */

class NexusClient {
  constructor(options = {}) {
    this.host = options.host || 'http://localhost:8000';
    this.timeout = options.timeout || 30000;
  }

  async _request(method, path, body) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);
    try {
      const res = await fetch(`${this.host}${path}`, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`NexusOS API error ${res.status}: ${text}`);
      }
      return res.json();
    } finally {
      clearTimeout(timer);
    }
  }

  /** Send a text command to NexusOS */
  command(text, mode = 'text') {
    return this._request('POST', '/api/v1/command', { text, mode });
  }

  /** Start voice listening */
  startListening() {
    return this._request('POST', '/api/v1/voice/start', {});
  }

  /** Stop voice listening */
  stopListening() {
    return this._request('POST', '/api/v1/voice/stop', {});
  }

  /** Get current system status */
  status() {
    return this._request('GET', '/api/v1/status', null);
  }

  /** Retrieve stored memories */
  memories(query) {
    return this._request('POST', '/api/v1/memory/search', { query });
  }

  /** Store a memory */
  remember(content) {
    return this._request('POST', '/api/v1/memory', { content });
  }

  /** List available plugins */
  plugins() {
    return this._request('GET', '/api/v1/plugins', null);
  }

  /** Execute a named workflow */
  runWorkflow(name) {
    return this._request('POST', '/api/v1/workflow/run', { name });
  }

  /** Health check */
  health() {
    return this._request('GET', '/health', null);
  }
}

module.exports = NexusClient;
module.exports.default = NexusClient;
