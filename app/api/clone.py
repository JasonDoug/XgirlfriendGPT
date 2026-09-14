import uuid
from typing import Dict, List, Any
from fastapi import APIRouter, HTTPException, status
from app.models.personality import PersonalityIngestionRequest, CompanionProfile
from app.services.personality_extractor import PersonalityExtractorService
from app.services.prompt_builder import PromptBuilderService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/clone", tags=["Personality Cloning & Ingestion"])

@router.post("/ingest", response_model=CompanionProfile, status_code=status.HTTP_201_CREATED)
def clone_personality(request: PersonalityIngestionRequest):
    """
    Personality Ingestion & Cloning Endpoint.
    
    Accepts EITHER:
    1. 'raw_texts': Array of text messages, chat logs, or emails.
    2. 'personality_description': Natural language text describing the companion's personality, hobbies, and style.
    
    Generates structured ExtractedTraits, constructs a system prompt, and saves the companion profile permanently.
    """
    # Step 1: Extraction Pass (Tone, Vocabulary, Slang, Emojis, Topics)
    traits = PersonalityExtractorService.extract_traits(
        raw_texts=request.raw_texts,
        personality_description=request.personality_description,
        formality_override=request.formality,
        response_length_override=request.response_length
    )

    # Step 2: Structured System Prompt Generation
    system_prompt = PromptBuilderService.build_system_prompt(
        companion_name=request.companion_name,
        companion_type=request.companion_type,
        traits=traits
    )

    companion_id = str(uuid.uuid4())

    # Step 3: Save Profile Permanently
    profile = CompanionProfile(
        companion_id=companion_id,
        name=request.companion_name,
        companion_type=request.companion_type,
        traits=traits,
        system_prompt=system_prompt
    )
    
    StorageService.save_companion(profile)

    return profile

@router.get("/list", response_model=List[CompanionProfile])
def list_companions():
    """
    Returns all permanently saved companions.
    """
    raw_list = StorageService.list_companions_raw()
    return [CompanionProfile(**c) for c in raw_list]

@router.get("/profile/{companion_id}", response_model=CompanionProfile)
def get_companion_profile(companion_id: str):
    profile_data = StorageService.get_companion_by_id(companion_id)
    if not profile_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Companion profile not found.")
    return CompanionProfile(**profile_data)

@router.delete("/{companion_id}", status_code=status.HTTP_200_OK)
def delete_companion(companion_id: str):
    success = StorageService.delete_companion(companion_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Companion not found.")
    return {"status": "deleted", "companion_id": companion_id}
