import os
from pydantic import BaseModel

class Settings(BaseModel):
    APP_NAME: str = "XgirlfriendGPT"
    ENV: str = os.getenv("ENV", "development")
    
    # LLM Settings: Auto-detects local Ollama (http://localhost:11434/v1) or remote vLLM/Together/OpenAI
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto") # options: auto, ollama, vllm, together, openai, mock
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "granite4:latest")
    
    # Vector DB / Memory Settings
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", ":memory:")
    QDRANT_COLLECTION: str = os.getenv("QDRANT_COLLECTION", "companion_memories")
    
    # Media & Voice Settings
    IMAGE_GEN_API_URL: str = os.getenv("IMAGE_GEN_API_URL", "http://localhost:8001/v1/generate")
    TTS_API_URL: str = os.getenv("TTS_API_URL", "http://localhost:8002/v1/tts")
    
    # Telephony / SMS Settings
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "")

    # Security & Auth Settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "xgirlfriendgpt_secret_jwt_key_env_config")

settings = Settings()
