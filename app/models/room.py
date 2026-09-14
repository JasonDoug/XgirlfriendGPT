from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class RoomParticipant(BaseModel):
    companion_id: str
    name: str
    role: Optional[str] = "participant" # host, moderator, participant

class Room(BaseModel):
    room_id: str
    name: str
    description: Optional[str] = None
    user_id: str
    participants: List[RoomParticipant]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class RoomCreateRequest(BaseModel):
    name: str = Field(..., json_schema_extra={"example": "Late Night Hangout"})
    description: Optional[str] = Field(default=None, json_schema_extra={"example": "Casual lounge with Aria and Kai"})
    user_id: str = Field(..., json_schema_extra={"example": "user_123"})
    companion_ids: List[str] = Field(..., json_schema_extra={"example": ["comp_aria", "comp_kai"]})

class RoomMessageRequest(BaseModel):
    room_id: str
    user_id: str
    message: str
    target_companion_id: Optional[str] = Field(
        default=None, 
        description="Optional explicit companion target. If None, supervisor router selects the next speaker."
    )
    enable_memory: bool = True
    enable_vision: bool = True

class RoomMessageResponse(BaseModel):
    room_id: str
    speaker_id: str
    speaker_name: str
    reply: str
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
