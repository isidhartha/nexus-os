# NexusOS

[![Discussions](https://img.shields.io/github/discussions/isidhartha/nexus-os)](https://github.com/isidhartha/nexus-os/discussions)

I built NexusOS because I wanted a Jarvis — not a toy demo, but something that actually controls my computer, understands what I'm asking, and takes action. This is that project.

It's an AI operating environment that runs locally. You say "Hey Nexus", it wakes up, listens, figures out what you want, and does it. Open Chrome, search for something, move files around, run a script, control your smart home devices — all through voice or text, without touching the keyboard.

---

## What it does

**Voice pipeline** — NexusOS listens for a wake word using your microphone. When it hears "Hey Nexus", it captures your command, transcribes it with OpenAI Whisper (which runs locally), and passes it to the AI brain. When it responds, it speaks back using text-to-speech. The whole loop takes about 2-3 seconds.

**Computer control** — It can move your mouse, click buttons, type text, and interact with any application on your desktop using PyAutoGUI. You tell it what you want to do in plain English, and it figures out the clicks.

**Browser automation** — Built on Playwright, so it can open browsers, navigate to pages, fill forms, click links, and read page content back to you. I use it to look things up without touching the keyboard.

**File management** — Create, move, rename, search, and delete files through voice commands. It operates within safe boundaries and won't touch system directories.

**Autonomous workflows** — You can define multi-step routines — "morning routine", "end of day", whatever you want — and it runs through each step in sequence. Open Slack, check email, pull up your calendar, read you the headlines. Define it once, run it anytime.

**AI memory** — This is the part I'm most proud of. NexusOS remembers things across sessions. Tell it something and it stores it with a vector embedding. Next time you ask something related, it retrieves the right memory. It actually knows context from previous conversations.

**Smart home** — Connects to MQTT, which means it works with Home Assistant and most IoT devices. Turn lights on and off, read sensor data, trigger automations.

**Plugin system** — Drop a Python file into the plugins folder and NexusOS loads it automatically. No configuration needed. Build your own integrations without touching the core.

---

## Tech stack

The backend is Python — FastAPI serving a REST API and WebSocket connections, Whisper for speech recognition, pyttsx3 for text-to-speech, PyAutoGUI for computer control, Playwright for browser automation, SQLite with vector embeddings for memory, and Paho MQTT for IoT.

The frontend is React with Tailwind CSS — a dashboard that shows real-time transcriptions, command history, your memory entries, and smart home controls.

Everything runs in Docker, so you don't have to install audio libraries on your host machine unless you want to use the actual microphone.

---

## How to run it

You'll need Docker and Docker Compose installed. That's the only real prerequisite.

**1. Clone the repo**

```bash
git clone https://github.com/isidhartha/nexus-os.git
cd nexus-os
```

**2. Set up your environment**

```bash
cp .env.example .env
```

Open `.env` and add your OpenAI API key. Everything else can stay as the default values to start.

```
OPENAI_API_KEY=sk-your-key-here
WAKE_WORD=nexus
```

**3. Start everything**

```bash
docker-compose up --build
```

This builds the backend, starts Postgres, Redis, and the MQTT broker, and serves the frontend. First build takes a few minutes because it installs the Playwright browser.

**4. Open the dashboard**

Go to `http://localhost:3000`. You'll see the NexusOS dashboard — the voice orb in the center shows whether it's listening or idle.

**5. Use it**

Click "Start Listening" in the dashboard, or hit the endpoint directly:

```bash
curl -X POST http://localhost:8000/api/v1/voice/start
```

Then talk. Or just use the text command box if you're not set up for audio yet.

---

## Free local LLM option (no API key needed)

If you don't have OpenAI API credits, you can run NexusOS entirely for free using [Ollama](https://ollama.com) — a local LLM runner that works on Mac, Linux, and Windows.

**1. Install Ollama**

Download and install from https://ollama.com. It takes about 2 minutes.

**2. Pull the model**

```bash
ollama pull llama3.2
```

This downloads a ~2GB model to your machine. You only do this once.

**3. Set the provider in your `.env`**

```
LLM_PROVIDER=ollama
```

Leave `OPENAI_API_KEY` blank — it won't be used.

**4. Start NexusOS as normal**

```bash
docker-compose up --build
```

Ollama needs to be running on your host machine (not inside Docker). If you want to run it inside Docker too, uncomment the `ollama` service in `docker-compose.yml`.

> **Switching back to OpenAI**: set `LLM_PROVIDER=openai` and add your `OPENAI_API_KEY`.

---

## Without a microphone

If you just want to explore the system without voice, use the text command API:

```bash
curl -X POST http://localhost:8000/api/v1/command \
  -H "Content-Type: application/json" \
  -d '{"text": "open chrome and go to github.com", "mode": "text"}'
```

---

## API

The full API reference is in [docs/API.md](docs/API.md). The backend exposes Swagger UI at `http://localhost:8000/docs`.

---

## Architecture

Detailed breakdown of how the voice pipeline, agent system, and memory layer fit together in [docs/architecture.md](docs/architecture.md).

---

## Contributing

If you're building on top of this or want to add a new integration, read [CONTRIBUTING.md](CONTRIBUTING.md) first. The plugin system makes it pretty easy to add new capabilities without modifying core code.

---

## License

MIT. Use it however you want.
