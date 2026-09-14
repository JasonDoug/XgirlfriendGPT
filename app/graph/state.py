from typing import List, Dict, Any, Optional, Annotated
from pydantic import BaseModel, Field

class CompanionState(BaseModel):
    room_id: str
    user_id: str
    user_message: str
    active_companion_ids: List[str] = Field(default_factory=list)
    companion_profiles: Dict[str, Any] = Field(default_factory=dict) # companion_id -> profile dict
    message_history: List[Dict[str, Any]] = Field(default_factory=list)
    recalled_memories: List[str] = Field(default_factory=list)
    
    current_speaker_id: Optional[str] = None
    current_speaker_name: Optional[str] = None
    reply: Optional[str] = None
    
    should_generate_image: bool = False
    image_prompt: Optional[str] = None
    image_url: Optional[str] = None
    
    audio_url: Optional[str] = None
