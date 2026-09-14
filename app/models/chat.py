from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class ChatMessage(BaseModel):
    role: str = Field(..., json_schema_extra={"example": "user"}) # user, assistant, system
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatRequest(BaseModel):
    companion_id: str
    user_id: str
    message: str
    history: Optional[List[Dict[str, str]]] = Field(default_factory=list, description="Recent conversation turns [{role, content}]")
    enable_memory: bool = True
    enable_vision: bool = True
    fast_mode: bool = Field(default=False, description="If True, responds immediately with text without waiting for TTS or image rendering")


class ImageGenCommand(BaseModel):
    generate_image: bool = True
    prompt: str
    negative_prompt: Optional[str] = "blurry, low quality, distorted"
    style: Optional[str] = "realistic selfie"
    image_url: Optional[str] = Field(default=None, description="Generated image static URL when available")

class MemoryItem(BaseModel):
    memory_id: str
    companion_id: str
    user_id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ChatResponse(BaseModel):
    companion_id: str
    reply: str
    image_command: Optional[ImageGenCommand] = None
    audio_url: Optional[str] = Field(default=None, description="Generated TTS voice audio MP3 URL")
    retrieved_memories: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

