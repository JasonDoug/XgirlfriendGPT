from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class VoiceCallWebhook(BaseModel):
    CallSid: str
    From: str
    To: str
    SpeechResult: Optional[str] = None
    CallStatus: Optional[str] = None

class SMSWebhook(BaseModel):
    MessageSid: str
    From: str
    To: str
    Body: str

class OutboundSMSRequest(BaseModel):
    companion_id: str
    user_id: str
    to_phone_number: str
    context_hint: Optional[str] = "Morning greeting"

class ImageGenRequest(BaseModel):
    prompt: str
    companion_id: str
    reference_face_url: Optional[str] = None
    width: int = 1024
    height: int = 1024
