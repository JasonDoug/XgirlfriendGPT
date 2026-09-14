import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.api import clone, chat, voice, sms, settings as settings_api, rooms
from app.services.sms_service import SMSService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start proactive scheduler
    SMSService.start_proactive_scheduler()
    yield
    # Shutdown: Stop scheduler
    SMSService.stop_scheduler()

app = FastAPI(
    title=settings.APP_NAME,
    description="Full-stack AI Companion Platform Gateway & Personality Engine",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for Web / Mobile Clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory if present
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Register API Routers for the 4 Pipelines + Multi-Persona Rooms
app.include_router(clone.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(rooms.router)
app.include_router(voice.router, prefix="/api/v1")
app.include_router(sms.router, prefix="/api/v1")
app.include_router(settings_api.router, prefix="/api/v1")

@app.get("/")
def root():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "app": settings.APP_NAME,
        "status": "online",
        "pipelines": [
            "1. Text & Personality Engine (Qwen 2.5 72B / Llama 3.3 70B)",
            "2. Visual Pipeline (FLUX.1 [dev] / InstantID)",
            "3. Voice & Phone Call Pipeline (Twilio + Deepgram + Cartesia)",
            "4. SMS & Outbound Texting Pipeline (Twilio + Proactive Scheduler)"
        ]
    }
