# NexusOS API Reference

Base URL: `http://localhost:8000`

## Health

### GET /health
```json
{"status": "ok", "service": "NexusOS", "version": "1.0.0"}
```

## Commands

### POST /api/v1/command
Execute an AI command.

**Request:**
```json
{
  "text": "open chrome and search for python tutorials",
  "mode": "auto"
}
```

**Response:**
```json
{
  "task_id": "uuid",
  "status": "running",
  "agent": "browser"
}
```

## Voice

### POST /api/v1/voice/start
Start voice listening.

### POST /api/v1/voice/stop
Stop voice listening.

## Memory

### GET /api/v1/memory
Returns recent memory entries.

**Response:**
```json
{
  "entries": [
    {"id": 1, "content": "...", "timestamp": "2025-01-01T00:00:00"}
  ]
}
```

## Workflows

### GET /api/v1/workflows
List all defined workflows.

### POST /api/v1/workflow/run
```json
{"name": "morning_routine"}
```

## Apps

### POST /api/v1/apps/launch
```json
{"app": "chrome"}
```

## WebSocket

### WS /ws/nexus
Real-time event stream. Messages:
```json
{"type": "transcription", "text": "open chrome"}
{"type": "agent_action", "agent": "browser", "action": "navigate"}
{"type": "response", "text": "Opened Chrome and navigated to..."}
```
