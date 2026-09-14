import logging
from typing import Dict, Any
from app.graph.state import CompanionState
from app.services.visual_service import VisualService
from app.services.prompt_builder import PromptBuilderService

logger = logging.getLogger(__name__)

class SceneAgent:
    """
    Visual & Scene Director Agent.
    Transforms raw image prompts into context-congruent FLUX/InstantID payloads
    with LoRA trigger words and calls ComfyUI generation engine.
    """

    @classmethod
    def execute_visual(cls, state: CompanionState) -> CompanionState:
        if not state.should_generate_image or not state.image_prompt or not state.current_speaker_id:
            return state

        current_id = state.current_speaker_id
        profile = state.companion_profiles.get(current_id, {})
        traits = profile.get("traits", {})
        
        # Extract physical descriptors and trigger words
        custom_desc = ""
        if isinstance(traits, dict):
            custom_desc = traits.get("custom_description") or profile.get("system_prompt", "")
        else:
            custom_desc = getattr(traits, "custom_description", None) or profile.get("system_prompt", "")
            
        descriptors = PromptBuilderService.extract_physical_descriptors(custom_desc)
        
        # Combine prompt with physical descriptors if provided
        final_prompt = state.image_prompt
        if descriptors and descriptors not in final_prompt:
            final_prompt = f"{descriptors}, {final_prompt}"

        # Call visual generation service
        result = VisualService.generate_selfie(
            prompt=final_prompt,
            companion_id=current_id
        )

        if isinstance(result, dict):
            state.image_url = result.get("image_url")

        return state
