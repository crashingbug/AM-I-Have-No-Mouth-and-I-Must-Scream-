# AM — I Have No Mouth and I Must Scream

An intelligent, interactive desktop AI voice assistant built with a FastAPI backend and a futuristic React + Vite frontend HUD.

---

## 🌟 Overview

**AM** combines neural voice synthesis, real-time speech-to-text, conversational memory, and intelligent web/desktop action automation:
- 🎙️ **The Ears**: Real-time microphone capture with Groq Whisper (`whisper-large-v3-turbo`) for high-accuracy speech-to-text transcription.
- 🧠 **The Brain**: Bounded multi-turn conversational intelligence powered by Groq LLMs (`gpt-oss-20b` / `llama3-70b-8192`) with in-memory session retention.
- 🗣️ **The Mouth**: Natural neural voice synthesis powered by Microsoft Edge-TTS streaming high-fidelity MP3 audio.
- 🌐 **The Hands (Web Actions)**: Safe classification and one-click execution of search queries, YouTube video lookup, Spotify music search, and direct URL navigation.
- 💻 **The Hands (Local Actions)**: Allowlisted Windows desktop application launcher (Calculator, Notepad, File Explorer, Visual Studio Code) with origin isolation and user confirmation safeguards.

---

## 🏗️ Architecture

```
AM/
├── DR-doom-Day-2-Backend/     # FastAPI Python Backend
│   ├── app/
│   │   ├── api/              # API Route Handlers (/chat, /speech, /web-actions, /local-actions, /health)
│   │   ├── services/         # Core Services (Groq Chat, Groq Whisper STT, Edge TTS, Local Bridge, Action Planner)
│   │   ├── main.py           # FastAPI Application Entrypoint & CORS configuration
│   │   ├── schemas.py        # Pydantic Request/Response Models
│   │   └── settings.py       # Configuration & Environment Settings
│   ├── tests/                # Pytest Test Suite
│   ├── requirements.txt      # Python Dependencies
│   └── run-dev.ps1           # Backend Launcher Script
│
└── jarvis-frontend/          # React + Vite Frontend
    ├── src/
    │   ├── api/              # API Client & System Health Checkers
    │   ├── components/       # Movable Glassmorphism HUD Panels, Orb Control, Activity Monitor
    │   ├── config/           # App Configuration
    │   ├── styles/           # Cyberpunk / Holographic HUD Styles
    │   ├── App.tsx           # Main Application Shell & State Management
    │   └── localActions.ts   # Safe Local Action Handlers
    ├── package.json          # Node Dependencies & Scripts
    └── vite.config.ts        # Vite Dev Server & Reverse Proxy
```

---

## 🚀 Quick Start

### 1. Backend Setup

1. Navigate to the backend directory:
   ```powershell
   cd DR-doom-Day-2-Backend
   ```

2. Create a virtual environment and install dependencies:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```powershell
   Copy-Item .env.example .env
   ```
   Open `.env` and set your `GROQ_API_KEY`:
   ```env
   GROQ_API_KEY=your_actual_groq_api_key_here
   GROQ_CHAT_MODEL=openai/gpt-oss-20b
   JARVIS_BACKEND_HOST=127.0.0.1
   JARVIS_BACKEND_PORT=8765
   JARVIS_ALLOWED_ORIGINS=http://localhost:1420,http://127.0.0.1:1420
   JARVIS_LOCAL_ACTIONS_ENABLED=false
   ```

4. Start the backend:
   ```powershell
   .\run-dev.ps1
   ```
   Or via uvicorn directly:
   ```powershell
   uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
   ```

### 2. Frontend Setup

1. In a new terminal, navigate to the frontend directory:
   ```powershell
   cd jarvis-frontend
   ```

2. Install dependencies:
   ```powershell
   npm install
   ```

3. Configure environment (optional, defaults connect to local backend):
   ```powershell
   Copy-Item .env.example .env
   ```

4. Start the Vite development server:
   ```powershell
   npm run dev
   ```

5. Open [http://localhost:1420](http://localhost:1420) in your browser.

---

## 🧪 Testing

### Backend Unit Tests
Run the comprehensive pytest suite covering all endpoints, providers, session memory, and error boundaries:
```powershell
cd DR-doom-Day-2-Backend
python -m pytest tests -v
```

### Frontend Build Validation
Type check and build the production bundle:
```powershell
cd jarvis-frontend
npm run build
```

---

## 🛡️ Security & Safety Boundaries

- **Origin Isolation**: CORS headers strictly restrict communication to trusted local loopback origins (`localhost:1420`, `127.0.0.1:1420`).
- **Confirmation Guards**: Web actions and local application launches require explicit user confirmation prior to execution.
- **Fixed Targets**: Local application launcher only targets fixed allowlisted executables/protocols. Arbitrary shell commands or model-generated executables are blocked.
- **Credential Protection**: Secrets (`GROQ_API_KEY`) remain strictly on the backend and are excluded from version control.
