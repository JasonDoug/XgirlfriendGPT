import logging
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.models.chat import ChatRequest, ChatResponse, ImageGenCommand
from app.models.personality import CompanionProfile
from app.services.storage_service import StorageService
from app.services.memory_service import MemoryService
from app.services.voice_service import VoiceService
from app.graph.workflow import companion_graph
from app.graph.state import CompanionState

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Companion Chat & Text Engine"])
memory_service = MemoryService()

@router.get("/history/{companion_id}")
def get_chat_history(companion_id: str):
    """
    Returns stored chat history turns for a companion.
    """
    return StorageService.get_chat_history(companion_id)

@router.post("/message", response_model=ChatResponse)
def send_chat_message(request: ChatRequest):
    """
    Companion Interactive Chat Endpoint.
    Executes roleplay, selfie generation, vector memory, and voice synthesis
    via the LangGraph Multi-Agent Engine (companion_graph).
    """
    logger.info(f"Incoming chat request: companion_id='{request.companion_id}', message='{request.message}'")
    
    profile_data = StorageService.get_companion_by_id(request.companion_id)
    if not profile_data:
        companion_name = request.companion_id.replace("_", " ").title()
        from app.models.personality import ExtractedTraits
        from app.services.prompt_builder import PromptBuilderService
        default_traits = ExtractedTraits(
            formality="casual",
            tone="warm, friendly, immersive",
            greeting_style="Hey there! Great to chat with you."
        )
        system_prompt = PromptBuilderService.build_system_prompt(
            companion_name=companion_name,
            companion_type="friend",
            traits=default_traits
        )
        profile_data = {
            "companion_id": request.companion_id,
            "name": companion_name,
            "companion_type": "friend",
            "system_prompt": system_prompt,
            "traits": default_traits.model_dump()
        }

    # Step 1: Memory Retrieval
    retrieved_memories = []
    if request.enable_memory:
        retrieved_memories = memory_service.retrieve_memories(
            companion_id=request.companion_id,
            user_id=request.user_id,
            query=request.message,
            limit=2
        )

    # Combine existing disk chat history if frontend history is empty
    history_turns = request.history or []
    if not history_turns:
        history_turns = StorageService.get_chat_history(request.companion_id)

    # Step 2: Invoke LangGraph Multi-Agent Orchestrator
    try:
        initial_state = CompanionState(
            room_id=f"single_{request.companion_id}",
            user_id=request.user_id,
            user_message=request.message,
            active_companion_ids=[request.companion_id],
            companion_profiles={request.companion_id: profile_data},
            message_history=history_turns,
            recalled_memories=retrieved_memories,
            current_speaker_id=request.companion_id
        )

        if request.fast_mode:
            # In Fast Mode, skip pre-rendering ComfyUI visual generation during chat turn
            initial_state.should_generate_image = False

        final_state = companion_graph.invoke(initial_state)

        reply_text = final_state.get("reply") or "Hey there!"
        image_url = final_state.get("image_url") if not request.fast_mode else None
        should_gen_image = final_state.get("should_generate_image", False)
        raw_prompt = final_state.get("image_prompt", "")
        
        # Preserve or construct prompt for on-demand or pre-rendered generation
        companion_name = profile_data.get("name", "Companion")
        image_prompt = raw_prompt or f"A photorealistic selfie of {companion_name}, {reply_text[:60]}"

        image_command = ImageGenCommand(
            generate_image=should_gen_image and not request.fast_mode,
            prompt=image_prompt,
            image_url=image_url
        )

    except Exception as e:
        logger.error(f"LangGraph Chat Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LangGraph Multi-Agent Error: {str(e)}"
        )

    # Step 3: Synthesize Voice Audio MP3 (Skip in fast_mode for instant text response)
    audio_url = None
    if not request.fast_mode:
        try:
            tts_res = VoiceService.synthesize_tts_chunk(reply_text)
            audio_url = tts_res.get("audio_url")
        except Exception as e:
            logger.warning(f"Voice synthesis error: {e}")

    # Step 4: Persist Chat History to Disk
    assistant_turn = {
        "role": "assistant",
        "content": reply_text
    }
    if image_url:
        assistant_turn["image_url"] = image_url
        if image_prompt:
            assistant_turn["image_prompt"] = image_prompt
    if audio_url:
        assistant_turn["audio_url"] = audio_url

    new_history = history_turns + [
        {"role": "user", "content": request.message},
        assistant_turn
    ]
    StorageService.save_chat_history(request.companion_id, new_history[-30:])

    return ChatResponse(
        companion_id=request.companion_id,
        reply=reply_text,
        image_command=image_command,
        audio_url=audio_url,
        retrieved_memories=retrieved_memories
    )

class SelfieRequest(BaseModel):
    prompt: Optional[str] = None

@router.post("/selfie/{companion_id}")
def generate_companion_selfie(companion_id: str, req: Optional[SelfieRequest] = None):
    """
    On-Demand Visual Scene & Selfie Generator Endpoint.
    Generates a photo of the companion and returns the image URL.
    """
    profile_data = StorageService.get_companion_by_id(companion_id)
    companion_name = profile_data.get("name") if profile_data else "Companion"
    
    custom_prompt = req.prompt if (req and req.prompt) else None
    final_prompt = custom_prompt or f"A photorealistic selfie of {companion_name}"
    from app.services.prompt_builder import PromptBuilderService
    if profile_data:
        custom_desc = profile_data.get("system_prompt", "")
        descriptors = PromptBuilderService.extract_physical_descriptors(custom_desc)
        if descriptors and descriptors not in final_prompt:
            final_prompt = f"{descriptors}, {final_prompt}"

    from app.services.visual_service import VisualService
    result = VisualService.generate_selfie(prompt=final_prompt, companion_id=companion_id)
    return result


