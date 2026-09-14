from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator
from datetime import datetime

class PersonalityIngestionRequest(BaseModel):
    companion_name: str = Field(..., json_schema_extra={"example": "Aria"})
    companion_type: str = Field(default="custom", json_schema_extra={"example": "friend"}) # e.g. friend, mentor, roleplay
    formality: Optional[str] = Field(default=None, description="Optional explicit formality setting (casual, formal, witty & sarcastic, balanced, etc.)")
    response_length: Optional[str] = Field(default=None, description="Optional explicit average response length setting (short, medium, verbose, etc.)")
    raw_texts: Optional[List[str]] = Field(default=None, description="Optional array of text messages, email snippets, or chat logs.")
    personality_description: Optional[str] = Field(
        default=None, 
        description="Alternative option: Description of the desired personality traits, tone, hobbies, and speaking style."
    )
    visual_reference_urls: Optional[List[str]] = Field(default=None, description="Optional URLs of reference images.")
    voice_sample_urls: Optional[List[str]] = Field(default=None, description="Optional audio sample URLs for voice cloning.")

    @model_validator(mode="after")
    def validate_inputs(self):
        has_texts = self.raw_texts and len(self.raw_texts) > 0 and any(t.strip() for t in self.raw_texts)
        has_desc = self.personality_description and self.personality_description.strip()
        if not has_texts and not has_desc:
            raise ValueError("Must provide either 'raw_texts' or 'personality_description' to form the companion personality.")
        return self

class ExtractedTraits(BaseModel):
    formality: str = Field(default="casual", json_schema_extra={"example": "casual / formal / sarcastic"})
    slang_tokens: List[str] = Field(default_factory=list, json_schema_extra={"example": ["lol", "ngl", "brb"]})
    average_response_length: str = Field(default="short", json_schema_extra={"example": "short / medium / verbose"})
    emoji_frequency: str = Field(default="moderate", json_schema_extra={"example": "none / low / moderate / high"})
    favorite_emojis: List[str] = Field(default_factory=list, json_schema_extra={"example": ["😂", "🔥", "✨"]})
    tone: str = Field(default="friendly", json_schema_extra={"example": "warm, witty, slightly sarcastic"})
    sentiment_bias: str = Field(default="positive", json_schema_extra={"example": "positive / neutral / analytical"})
    top_topics: List[str] = Field(default_factory=list, json_schema_extra={"example": ["tech", "gaming", "music"]})
    greeting_style: str = Field(default="Hey there!", json_schema_extra={"example": "Hey! What's up?"})
    catchphrases: List[str] = Field(default_factory=list)
    custom_description: Optional[str] = None
    physical_appearance: Optional[str] = None
    trigger_words: List[str] = Field(default_factory=list)

class CompanionProfile(BaseModel):
    companion_id: str
    name: str
    companion_type: str
    traits: ExtractedTraits
    system_prompt: str
    loras: List[Dict[str, Any]] = Field(default_factory=list, description="List of dicts with name, strength, trigger_words")
    voice_id: Optional[str] = None
    voice_provider: Optional[str] = Field(default="cartesia", description="cartesia, elevenlabs, edge_tts")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
