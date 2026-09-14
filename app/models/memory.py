from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class MemoryItem(BaseModel):
    memory_id: str
    companion_id: str
    user_id: str
    content: str
    category: str = Field(default="user_preference", description="user_preference, fact, event, emotional_state")
    importance_score: float = Field(default=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MemoryQuery(BaseModel):
    companion_id: str
    user_id: str
    query: str
    limit: int = 5
