# NexusOS Architecture

## Overview

NexusOS is a local-first AI operating environment built around a central controller (`NexusOS`) that coordinates voice, agents, automation, memory, and IoT subsystems.

## Components

### Voice Pipeline
```
Microphone → Wake Word Engine → STT (Whisper) → NexusOS Controller
NexusOS Controller → TTS Engine → Speaker
```

- **Wake Word**: Keyword detection using pvporcupine (optional) or energy-based fallback
- **STT**: OpenAI Whisper (runs locally via `openai-whisper` package)
- **TTS**: pyttsx3 with configurable voice and rate

### Agent System

Each agent handles a specific domain:

| Agent | Responsibility |
|-------|---------------|
| `ComputerAgent` | Mouse/keyboard automation via PyAutoGUI |
| `BrowserAgent` | Web browsing via Playwright |
| `FileAgent` | File system read/write/search |
| `WorkflowAgent` | Multi-step task sequencing |
| `MemoryAgent` | Long-term memory storage and retrieval |

### Memory System

Persistent memory uses SQLite with a hybrid storage approach:
- Short-term: Redis (in-session context)
- Long-term: SQLite with vector embeddings for semantic retrieval
- Episodic: Conversation history with timestamps

### Plugin System

Plugins are Python modules placed in `core/plugins/`:
```python
class MyPlugin:
    name = "my_plugin"
    triggers = ["keyword"]
    
    async def execute(self, context: dict) -> str:
        ...
```

### IoT Integration

MQTT-based integration compatible with Home Assistant:
- Subscribe to device state topics
- Publish control commands
- Event-driven automation triggers

## Data Flow

```
User Voice Input
    → STT transcription
    → Intent classification (AI)
    → Agent selection
    → Action execution
    → Result collection
    → TTS response
    → Dashboard update (WebSocket)
```

## API Server

FastAPI server on port 8000 provides:
- REST endpoints for all subsystems
- WebSocket `/ws/nexus` for real-time dashboard updates
- Swagger UI at `/docs`
