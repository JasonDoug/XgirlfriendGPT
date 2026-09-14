from typing import Dict, Any
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["System Settings & Model Configuration"])

class SettingsUpdateRequest(BaseModel):
    llm_model: str = Field(..., json_schema_extra={"example": "R4C3R/qwen3-8b-heretic:q8_0"})
    image_model: str = Field(..., json_schema_extra={"example": "juggernautXL_ragnarok.safetensors"})
    image_width: int = Field(default=896)
    image_height: int = Field(default=1152)
    image_steps: int = Field(default=20)
    image_cfg: float = Field(default=7.0)
    selected_lora: str = Field(default="")

@router.get("", response_model=Dict[str, Any])
def get_current_settings():
    """
    Returns current active runtime settings for LLM and Visual Generation pipelines.
    """
    return SettingsService.get_settings()

@router.post("", response_model=Dict[str, Any])
def update_system_settings(request: SettingsUpdateRequest):
    """
    Updates active runtime settings for LLM and Visual Generation pipelines.
    """
    updated = SettingsService.update_settings(request.model_dump())
    return updated

@router.get("/models")
def get_available_models():
    """
    Scans /home/jason/models directory and live Ollama instance to discover all available models.
    """
    return SettingsService.discover_models()
