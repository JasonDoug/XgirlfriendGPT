import logging
from typing import Dict, Any
from app.graph.state import CompanionState
from app.services.memory_service import MemoryService

logger = logging.getLogger(__name__)

class MemoryAgent:
    """
    Summarizer & Memory Extractor Agent.
    Asynchronously extracts facts and updates long-term vector memory embeddings.
    """

    @classmethod
    def extract_and_store(cls, state: CompanionState) -> CompanionState:
        if not state.reply or not state.current_speaker_id:
            return state

        user_msg = state.user_message.strip()
        if len(user_msg) > 10:
            memory_content = f"User said: {user_msg}"
            try:
                mem_service = MemoryService()
                mem_service.add_memory(
                    companion_id=state.current_speaker_id,
                    user_id=state.user_id,
                    content=memory_content
                )
            except Exception as e:
                logger.warning(f"Memory storage deferred or failed gracefully: {e}")

        return state
