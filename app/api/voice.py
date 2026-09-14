from fastapi import APIRouter, Form, Response, status, WebSocket, WebSocketDisconnect
import json
import logging
from app.services.voice_service import VoiceService
from app.services.llm_service import LLMService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice & Phone Call Pipeline"])

@router.post("/webhook", response_class=Response)
def twilio_voice_webhook(
    SpeechResult: str = Form(default=""),
    CallSid: str = Form(default=""),
    From: str = Form(default=""),
    companion_id: str = Form(default="default")
):
    """
    Twilio Voice Webhook Endpoint.
    Receives Deepgram STT / Twilio SpeechResult, invokes fast streaming LLM response,
    and returns TwiML XML payload for real-time phone calling.
    """
    if not SpeechResult:
        speech_text = "Hey! I'm here, what did you say?"
    else:
        profile_data = StorageService.get_companion_by_id(companion_id)
        sys_prompt = profile_data.get("system_prompt") if profile_data else "You are a warm companion on a phone call. Keep responses short and conversational."
        
        reply, _ = LLMService.generate_chat_response(
            system_prompt=sys_prompt,
            user_message=SpeechResult,
            memory_context=[]
        )
        speech_text = reply

    twiml_content = VoiceService.generate_twiml_response(speech_text, continue_call=True)
    return Response(content=twiml_content, media_type="application/xml")

@router.websocket("/stream")
async def voice_websocket_stream(websocket: WebSocket):
    """
    Real-Time WebSocket Streaming Endpoint for <700ms voice calls.
    Handles continuous audio streaming, real-time STT, LLM generation, and streaming TTS.
    """
    await websocket.accept()
    logger.info("Voice WebSocket connection established.")
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                user_msg = payload.get("message", "")
                companion_id = payload.get("companion_id", "default")
                
                if not user_msg:
                    user_msg = "Hello!"

                profile_data = StorageService.get_companion_by_id(companion_id)
                sys_prompt = profile_data.get("system_prompt") if profile_data else "You are an AI companion on a voice stream. Keep replies brief."

                reply, _ = LLMService.generate_chat_response(
                    system_prompt=sys_prompt,
                    user_message=user_msg,
                    memory_context=[]
                )

                tts_info = VoiceService.synthesize_tts_chunk(reply)
                
                response_payload = {
                    "event": "media",
                    "companion_id": companion_id,
                    "reply": reply,
                    "audio_url": tts_info.get("audio_url"),
                    "latency_ms": tts_info.get("latency_ms")
                }
                await websocket.send_text(json.dumps(response_payload))

            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"event": "error", "message": "Invalid JSON format"}))
                
    except WebSocketDisconnect:
        logger.info("Voice WebSocket stream disconnected.")

from pydantic import BaseModel
from typing import Optional
from fastapi import HTTPException

class SynthesizeRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None

@router.post("/synthesize")
def synthesize_speech(req: SynthesizeRequest):
    """
    On-Demand Voice TTS Synthesis Endpoint.
    Synthesizes TTS audio MP3 for a given text payload.
    """
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text payload is required")
    
    tts_res = VoiceService.synthesize_tts_chunk(req.text.strip())
    return tts_res

