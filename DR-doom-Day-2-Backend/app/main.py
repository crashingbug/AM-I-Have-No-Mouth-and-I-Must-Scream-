from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.local_actions import router as local_actions_router
from app.api.speech import router as speech_router
from app.api.web_actions import router as web_actions_router
from app.settings import settings

app = FastAPI(title="Jarvis Backend", version="0.1.0")

# Restrict CORS strictly to local frontend origins (never use wildcard *)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(chat_router)
app.include_router(local_actions_router)
app.include_router(speech_router)
app.include_router(web_actions_router)


# ==============================================================================
# PHASE 0: THE HEARTBEAT (Health Check Endpoint)
# ==============================================================================
@app.get("/api/health")
async def health() -> dict[str, str]:
    # TODO (Phase 0): Return {"status": "ok"} so the frontend knows the backend is alive
    return {"status": "ok"}
