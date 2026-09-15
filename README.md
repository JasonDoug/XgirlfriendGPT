# XgirlfriendGPT 🤖🔥 v0.1.0 (Alpha)

**XgirlfriendGPT** is a state-of-the-art, multi-modal, multi-persona AI companion platform. Built on top of **LangGraph** multi-agent orchestration, **Pydantic v2** state management, headless **ComfyUI** visual generation, **Edge-TTS** voice streaming, and **Qdrant + FastEmbed** long-term vector memory, XgirlfriendGPT delivers contextually congruent roleplay, visual selfie generation, and multi-character group interactions.

![Architecture](https://img.shields.io/badge/arch-LangGraph%20Multi--Agent-blue)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)

---

## 🌟 Key Features

### 🤖 LangGraph Multi-Agent Architecture
100% of user chat turns execute through a state graph featuring dedicated, specialized agents:

| Agent | Responsibility |
|-------|---------------|
| **RouterAgent** | Handles turn-taking and speaker selection in 1-on-1 and multi-companion room chats using name recognition, semantic topic matching, and conversation flow awareness |
| **PersonaAgent** | Blends long-term memory, conversation history, and persona directives to produce character-aligned responses and detect visual tool calls |
| **SceneAgent** | Extracts physical descriptors and triggers context-congruent visual generation payloads for ComfyUI |
| **MemoryAgent** | Asynchronously extracts long-term facts and updates vector embeddings in Qdrant |

### 📸 Visual Pipeline (Headless ComfyUI)
- Generates photorealistic selfies and scene photos aligned with the current conversation
- Supports FLUX.2, FLUX.1, SDXL checkpoints, InstantID face consistency, and custom LoRA overlays
- Inline `📸 View Photo` button embedded directly in chat response bubbles
- Async non-blocking generation with circuit breaker protection

### 🔊 Voice & Audio Pipeline
- Edge-TTS real-time synthesis for rich, natural vocal responses
- Manual inline `🔊 Listen` button with toggleable play/pause controls (no invasive autoplay)
- On-demand synthesis via `/api/v1/voice/synthesize` endpoint
- WebSocket streaming support for real-time calls

### 🧠 Vector Memory & Character Cloning
- Ingest chat logs, text exports, or natural language descriptions to auto-extract traits, formality, slang, and system prompts
- Long-term memory stored in Qdrant vector space with FastEmbed embeddings
- Dynamic memory recall during chat turns with semantic similarity search
- **Post-creation personality updates** via `PATCH /api/v1/clone/profile/{id}`

### 👥 Multi-Persona Room Group Chat
- Create multi-companion rooms where characters engage in dynamic group conversations
- Intelligent turn-taking with semantic routing and round-robin fallback
- Shared conversation history with per-speaker attribution

### 📱 Outbound Proactive Engagement
- Integrated APScheduler for automated, context-aware SMS check-ins
- Contextual message generation using recalled long-term user memories
- Twilio integration for SMS delivery

### 🛡️ Production-Ready Infrastructure
- **Health Checks**: `/health/liveness`, `/health/readiness` (Qdrant, LLM, ComfyUI), `/health/metrics` (Prometheus)
- **Observability**: Request tracing middleware with `x-request-id`, latency metrics
- **Rate Limiting**: Token bucket (chat: 60/min, media: 10/min) with thread-safe implementation
- **Circuit Breakers**: Three-state (CLOSED/OPEN/HALF_OPEN) for external service resilience
- **JWT Authentication**: HS256 tokens with configurable secret, 24hr expiry
- **Input Validation**: Path traversal prevention, strict companion_id sanitization

---

## 🛠️ System Architecture

```
                        ┌───────────────────────────────┐
                        │       FastAPI Gateway         │
                        │     (http://0.0.0.0:8005)     │
                        └───────────────┬───────────────┘
                                        │
                                        ▼
                        ┌───────────────────────────────┐
                        │   LangGraph State Orchestrator│
                        │   State: CompanionState       │
                        └───────────────┬───────────────┘
                                        │
         ┌──────────────────┬───────────┴───────────┬──────────────────┐
         │                  │                       │                  │
         ▼                  ▼                       ▼                  ▼
┌──────────────┐   ┌──────────────┐        ┌──────────────┐   ┌──────────────┐
│ Router Agent │   │Persona Agent │        │ Scene Agent  │   │ Memory Agent │
└──────────────┘   └───────┬──────┘        └───────┬──────┘   └───────┬──────┘
                           │                       │                  │
                           ▼                       ▼                  ▼
                    ┌──────────────┐        ┌──────────────┐   ┌──────────────┐
                    │    Ollama    │        │   ComfyUI    │   │    Qdrant    │
                    │ (Port 11434) │        │ (Port 8188)  │   │  (Vector DB) │
                    └──────────────┘        └──────────────┘   └──────────────┘
```

---

## 🚀 Quickstart & Setup

### Prerequisites
- **Python 3.12+**
- **Ollama** running locally on port `11434` with your preferred roleplay model (e.g., `R4C3R/qwen3-8b-heretic:q8_0`)
- **ComfyUI** running locally on port `8188` (for image generation)

### 1. Installation
```bash
git clone https://github.com/JasonDoug/XgirlfriendGPT.git
cd XgirlfriendGPT

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings:
# - LLM_BASE_URL, LLM_API_KEY, DEFAULT_MODEL
# - QDRANT_HOST, QDRANT_COLLECTION
# - JWT_SECRET_KEY (generate with: openssl rand -hex 32)
# - TWILIO credentials (optional, for SMS/Voice)
```

### 3. Launch ComfyUI Engine
```bash
bash /path/to/ComfyUI/run_comfyui.sh --port 8188
```

### 4. Launch XgirlfriendGPT Server
```bash
export PYTHONUNBUFFERED=1
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8005
```

Open your browser at `http://localhost:8005` to access the interactive web interface!

---

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `auto` | `auto`, `ollama`, `vllm`, `together`, `openai`, `mock` |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | Ollama/OpenAI-compatible endpoint |
| `LLM_API_KEY` | `` | API key for remote providers |
| `DEFAULT_MODEL` | `granite4:latest` | Model identifier for LLM inference |
| `QDRANT_HOST` | `./data/qdrant_db` | Local path or remote host:port |
| `QDRANT_COLLECTION` | `companion_memories` | Vector collection name |
| `JWT_SECRET_KEY` | *required* | HS256 signing key (generate: `openssl rand -hex 32`) |
| `TWILIO_ACCOUNT_SID` | `` | Twilio account SID for SMS/Voice |
| `TWILIO_AUTH_TOKEN` | `` | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | `` | Twilio verified phone number |

### Runtime Settings (via UI or API)
- **LLM Model**: Switch between Ollama/local models
- **Image Model**: FLUX/SDXL checkpoint selection with auto-tuned params
- **Resolution**: 512×512 to 1152×896
- **Sampling Steps**: 1–50
- **CFG Scale**: 1.0–15.0
- **LoRA Overlays**: Multi-select with auto trigger-word injection

---

## 🧪 Testing

```bash
source .venv/bin/activate

# Run all tests
pytest

# Run specific test modules
pytest tests/test_extractor.py -v
pytest tests/test_api.py -v
pytest tests/test_chat_memory.py -v

# With coverage
pytest --cov=app --cov-report=term-missing
```

**Test Suite Coverage**: 14+ test cases covering:
- Personality extraction from logs/descriptions
- API routes (chat, rooms, voice, SMS, clone, settings, health, auth)
- Vector memory storage/retrieval
- Fast mode chat + on-demand media synthesis
- Companion profile updates (formality, response length)
- WebSocket voice streaming

---

## 📁 Project Structure

```
XgirlfriendGPT/
├── app/
│   ├── api/                 # FastAPI route handlers
│   │   ├── auth.py          # JWT token issuance & validation
│   │   ├── chat.py          # 1-on-1 companion chat
│   │   ├── clone.py         # Personality ingestion & profile updates
│   │   ├── health.py        # Liveness/readiness/metrics
│   │   ├── rooms.py         # Multi-persona group chats
│   │   ├── settings.py      # Runtime model/pipeline config
│   │   ├── sms.py           # Twilio SMS webhooks
│   │   └── voice.py         # Voice webhooks & TTS
│   ├── graph/               # LangGraph multi-agent orchestration
│   │   ├── agents/          # Router, Persona, Scene, Memory agents
│   │   ├── state.py         # CompanionState (Pydantic)
│   │   └── workflow.py      # Graph compilation
│   ├── middleware/          # Observability, rate limiting
│   ├── models/              # Pydantic schemas
│   ├── services/            # Business logic (LLM, Memory, Visual, Voice, SMS, etc.)
│   ├── utils/               # Circuit breaker, helpers
│   ├── static/              # Frontend (HTML, JS, generated assets)
│   ├── config.py            # Pydantic Settings
│   └── main.py              # FastAPI app factory
├── tests/                   # Pytest test suite
├── data/                    # Persistent storage (companions, rooms, Qdrant)
├── requirements.txt         # Python dependencies
├── .env.example             # Environment template
└── README.md
```

---

## 🔌 API Reference

### Health & Observability
- `GET /health/liveness` - Process health
- `GET /health/readiness` - Dependency checks (Qdrant, Ollama, ComfyUI)
- `GET /health/metrics` - Prometheus metrics

### Authentication
- `POST /api/v1/auth/token` - Issue JWT (`{"user_id": "..."}`)
- `GET /api/v1/auth/me` - Validate token, get user info

### Personality Cloning
- `POST /api/v1/clone/ingest` - Create companion from logs/description
- `GET /api/v1/clone/list` - List all companions
- `GET /api/v1/clone/profile/{id}` - Get companion profile
- `PATCH /api/v1/clone/profile/{id}` - Update formality, response length, name, type
- `DELETE /api/v1/clone/{id}` - Delete companion

### Chat & Messaging
- `POST /api/v1/chat/message` - Send message (with rate limiting)
- `GET /api/v1/chat/history/{id}` - Get chat history
- `POST /api/v1/chat/selfie/{id}` - On-demand image generation

### Multi-Persona Rooms
- `POST /api/v1/rooms/create` - Create room
- `GET /api/v1/rooms` - List rooms
- `GET /api/v1/rooms/{id}` - Get room
- `POST /api/v1/rooms/message` - Send room message

### Voice & SMS
- `POST /api/v1/voice/webhook` - Twilio voice webhook
- `POST /api/v1/voice/synthesize` - On-demand TTS
- `WS /api/v1/voice/stream` - Real-time voice streaming
- `POST /api/v1/sms/webhook` - Twilio SMS webhook
- `POST /api/v1/sms/send` - Trigger outbound SMS

### Settings
- `GET /api/v1/settings` - Get current settings
- `POST /api/v1/settings` - Update settings
- `GET /api/v1/settings/models` - Discover available models/LoRAs

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup
```bash
git clone https://github.com/JasonDoug/XgirlfriendGPT.git
cd XgirlfriendGPT
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pre-commit install  # optional, for linting
```

### Code Style
- **Python**: Black + Ruff (line length 100)
- **Type Hints**: Required for all public functions
- **Async**: Prefer `async/await` for I/O-bound operations
- **Tests**: Add tests for new features in `tests/`

---

## 📜 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- **LangGraph** - Multi-agent orchestration framework
- **ComfyUI** - Node-based visual generation pipeline
- **Edge-TTS** - High-quality text-to-speech
- **Qdrant** - Vector database for long-term memory
- **FastEmbed** - Fast ONNX embeddings (BAAI/bge-small-en-v1.5)
- **FastAPI** - Modern, fast web framework
- **Pydantic v2** - Data validation and settings management

---

## 📞 Support & Community

- **Issues**: [GitHub Issues](https://github.com/JasonDoug/XgirlfriendGPT/issues)
- **Discussions**: [GitHub Discussions](https://github.com/JasonDoug/XgirlfriendGPT/discussions)
- **Security**: See [SECURITY.md](SECURITY.md) for vulnerability reporting

---

*Built for advanced AI companion exploration and multi-modal multi-agent orchestration.*