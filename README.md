# XgirlfriendGPT 🤖🔥 v0.0.1 (Alpha)

**XgirlfriendGPT** is a state-of-the-art, multi-modal, multi-persona AI companion platform. Built on top of **LangGraph** multi-agent orchestration, **Pydantic v2** state management, headless **ComfyUI** visual generation, **Edge-TTS** voice streaming, and **ChromaDB** long-term vector memory, XgirlfriendGPT delivers contextually congruent roleplay, visual selfie generation, and multi-character group interactions.

---

## 🌟 Key Features (Alpha v0.0.1)

* **🤖 LangGraph Multi-Agent Architecture**: 100% of user chat turns execute through a state graph featuring dedicated, specialized agents:
  * **RouterAgent**: Handles turn-taking and speaker selection in 1-on-1 and multi-companion room chats.
  * **PersonaAgent**: Blends long-term memory, conversation history, and persona directives to produce character-aligned responses and detect visual tool calls.
  * **SceneAgent**: Extracts physical descriptors and triggers context-congruent visual generation payloads.
  * **MemoryAgent**: Asynchronously extracts long-term facts and updates vector embeddings in ChromaDB.
* **📸 Visual Pipeline (Headless ComfyUI)**:
  * Generates photorealistic selfies and scene photos aligned with the current conversation.
  * Supports FLUX.2, FLUX.1, SDXL checkpoints, InstantID face consistency, and custom LoRA overlays.
  * Inline `📸 View Photo` button embedded directly in chat response bubbles, supporting both auto-triggered and on-demand image generation.
* **🔊 Voice & Audio Pipeline**:
  * Edge-TTS real-time synthesis for rich, natural vocal responses.
  * Manual inline `🔊 Listen` button with toggleable play/pause controls (no invasive autoplay).
* **🧠 Vector Memory & Character Cloning**:
  * Ingest chat logs, text exports, or natural language descriptions to auto-extract traits, formality, slang, and system prompts.
  * Long-term memory stored in ChromaDB vector space and recalled dynamically during chat turns.
* **👥 Multi-Persona Room Group Chat**:
  * Create multi-companion rooms where characters engage in dynamic group conversations and turn-taking.
* **📱 Outbound Proactive Engagement**:
  * Integrated scheduler for automated, context-aware SMS check-ins and proactive messages.

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
                   │    Ollama    │        │   ComfyUI    │   │   ChromaDB   │
                   │ (Port 11434) │        │ (Port 8188)  │   │ (Vector DB)  │
                   └──────────────┘        └──────────────┘   └──────────────┘
```

---

## 🚀 Quickstart & Setup

### Prerequisites
- **Python 3.12+**
- **Ollama** running locally on port `11434` with your preferred roleplay model (e.g., `L3-8B-Stheno-v3.2`).
- **ComfyUI** running locally on port `8188` (for image generation).

### 1. Installation
```bash
git clone https://github.com/JasonDoug/XgirlfriendGPT.git
cd XgirlfriendGPT

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Launch ComfyUI Engine
```bash
bash /path/to/ComfyUI/run_comfyui.sh --port 8188
```

### 3. Launch XgirlfriendGPT Server
```bash
export PYTHONUNBUFFERED=1
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8005
```

Open your browser at `http://localhost:8005` to access the interactive web interface!

---

## 🧪 Testing

Run the full automated test suite (14 test cases covering API routes, multi-persona rooms, vector memory, personality extraction, and voice synthesis):

```bash
source .venv/bin/activate
pytest
```

---

## 📄 License

MIT License. Developed for advanced AI companion exploration and multi-modal multi-agent orchestration.
