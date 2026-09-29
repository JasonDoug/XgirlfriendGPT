from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator
from datetime import datetime

class PersonalityIngestionRequest(BaseModel):
    companion_name: str = Field(..., json_schema_extra={"example": "Aria"})
    companion_type: str = Field(default="custom", json_schema_extra={"example": "friend"}) # e.g. friend, mentor, roleplay
    formality: Optional[str] = Field(default=None, description="Optional explicit formality setting (casual, formal, witty & sarcastic, balanced, etc.)")
    response_length: Optional[str] = Field(default=None, description="Optional explicit average response length setting (short, medium, verbose, etc.)")
    messaging_style: Optional[str] = Field(default="sms", description="Messaging style ('sms' for casual text messaging without asterisk actions, or 'roleplay')")
    raw_texts: Optional[List[str]] = Field(default=None, description="Optional array of text messages, email snippets, or chat logs.")
    personality_description: Optional[str] = Field(
        default=None, 
        description="Description of the desired personality traits, tone, hobbies, and speaking style."
    )
    appearance_description: Optional[str] = Field(
        default=None,
        description="Detailed physical appearance description (e.g. hair color/style, eye color, facial features, outfit, height, skin tone)."
    )
    visual_reference_urls: Optional[List[str]] = Field(default=None, description="Optional URLs of reference images.")
    voice_sample_urls: Optional[List[str]] = Field(default=None, description="Optional audio sample URLs for voice cloning.")

    @model_validator(mode="after")
    def validate_inputs(self):
        has_texts = self.raw_texts and len(self.raw_texts) > 0 and any(t.strip() for t in self.raw_texts)
        has_desc = self.personality_description and self.personality_description.strip()
        has_app = self.appearance_description and self.appearance_description.strip()
        if not has_texts and not has_desc and not has_app:
            raise ValueError("Must provide at least one of 'personality_description', 'appearance_description', or 'raw_texts' to form the companion character.")
        return self

class ExtractedTraits(BaseModel):
    formality: str = Field(default="casual", json_schema_extra={"example": "casual / formal / sarcastic"})
    slang_tokens: List[str] = Field(default_factory=list, json_schema_extra={"example": ["lol", "ngl", "brb"]})
    average_response_length: str = Field(default="short", json_schema_extra={"example": "short / medium / verbose"})
    messaging_style: str = Field(default="sms", description="Messaging style: 'sms' (casual short text messages without asterisk actions) or 'roleplay'")
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

class CompanionUpdateRequest(BaseModel):
    formality: Optional[str] = Field(default=None, description="Updated formality setting (casual, formal, witty & sarcastic, etc.)")
    response_length: Optional[str] = Field(default=None, description="Updated average response length (short, medium, verbose)")
    messaging_style: Optional[str] = Field(default=None, description="Updated messaging style (sms, roleplay)")
    name: Optional[str] = Field(default=None, description="Optional updated companion name")
    companion_type: Optional[str] = Field(default=None, description="Optional updated companion type")
    appearance_description: Optional[str] = Field(default=None, description="Optional updated physical appearance description")

class CompanionProfile(BaseModel):
    companion_id: str
    name: str
    companion_type: str
    traits: ExtractedTraits
    system_prompt: str
    appearance_description: Optional[str] = None
    avatar_image_url: Optional[str] = None
    loras: List[Dict[str, Any]] = Field(default_factory=list, description="List of dicts with name, strength, trigger_words")
    voice_id: Optional[str] = None
    voice_provider: Optional[str] = Field(default="cartesia", description="cartesia, elevenlabs, edge_tts")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
