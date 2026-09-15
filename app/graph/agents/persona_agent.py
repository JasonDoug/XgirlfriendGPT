from typing import Dict, Any, List
from app.graph.state import CompanionState
from app.services.llm_service import LLMService
from app.services.storage_service import StorageService
from app.services.memory_service import MemoryService

class PersonaAgent:
    """
    Companion Persona Execution Agent.
    Generates personality-aligned response text, dynamically hydratable with DB persona traits,
    memories, and multi-speaker turn prefixes.
    """

    @classmethod
    async def generate_response_async(cls, state: CompanionState) -> CompanionState:
        # Determine persona ID from pending queue or current speaker
        persona_id = None
        if state.pending_speakers:
            persona_id = state.pending_speakers.pop(0)
        else:
            persona_id = state.current_speaker_id or (state.active_companion_ids[0] if state.active_companion_ids else None)

        if not persona_id:
            state.reply = "I'm right here!"
            return state

        state.current_speaker_id = persona_id
        state.active_persona_id = persona_id

        # Hydrate persona profile
        profile = state.companion_profiles.get(persona_id)
        if not profile:
            profile = StorageService.get_companion_by_id(persona_id) or {}
            state.companion_profiles[persona_id] = profile

        persona_name = profile.get("name", "Companion")
        state.current_speaker_name = persona_name
        system_prompt = profile.get("system_prompt", "You are a friendly AI companion.")
        style_attrs = profile.get("traits", {})

        # Dynamically retrieve memories if not present
        memories = list(state.recalled_memories)
        if not memories and state.user_message:
            try:
                mem_service = MemoryService()
                retrieved = mem_service.retrieve_memories(
                    companion_id=persona_id,
                    user_id=state.user_id,
                    query=state.user_message,
                    limit=2
                )
                memories.extend(retrieved)
            except Exception:
                pass

        # In multi-persona group rooms, instruct model on strict character boundaries
        is_multi_persona = len(state.active_companion_ids) > 1 or (state.room_id and state.room_id.startswith("room_"))
        if is_multi_persona:
            system_prompt = (
                f"{system_prompt}\n\n"
                f"CRITICAL DIRECTIVE: You are speaking as '{persona_name}'. "
                f"Prefix your response with [{persona_name}]: and speak ONLY as {persona_name}. "
                f"Never write dialogue or actions for other characters or participants."
            )

        formatted_history = []
        for msg in state.message_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_history.append({"role": role, "content": content})

        reply_text, image_command = await LLMService.generate_chat_response_async(
            system_prompt=system_prompt,
            user_message=state.user_message,
            memory_context=memories,
            history=formatted_history
        )

        # Prefix with speaker name if multi-persona room and not already prefixed
        if is_multi_persona and not reply_text.strip().startswith(f"[{persona_name}]"):
            reply_text = f"[{persona_name}]: {reply_text}"

        state.reply = reply_text

        # Append response turn to message_history
        state.message_history.append({
            "role": "assistant",
            "speaker_id": persona_id,
            "speaker_name": persona_name,
            "content": reply_text
        })

        if image_command and image_command.generate_image:
            state.should_generate_image = True
            state.image_prompt = image_command.prompt

        return state

    @classmethod
    def generate_response(cls, state: CompanionState) -> CompanionState:
        persona_id = None
        if state.pending_speakers:
            persona_id = state.pending_speakers.pop(0)
        else:
            persona_id = state.current_speaker_id or (state.active_companion_ids[0] if state.active_companion_ids else None)

        if not persona_id:
            state.reply = "I'm right here!"
            return state

        state.current_speaker_id = persona_id
        state.active_persona_id = persona_id

        profile = state.companion_profiles.get(persona_id)
        if not profile:
            profile = StorageService.get_companion_by_id(persona_id) or {}
            state.companion_profiles[persona_id] = profile

        persona_name = profile.get("name", "Companion")
        state.current_speaker_name = persona_name
        system_prompt = profile.get("system_prompt", "You are a friendly AI companion.")

        formatted_history = []
        for msg in state.message_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_history.append({"role": role, "content": content})

        reply_text, image_command = LLMService.generate_chat_response(
            system_prompt=system_prompt,
            user_message=state.user_message,
            memory_context=state.recalled_memories,
            history=formatted_history
        )

        state.reply = reply_text

        if image_command and image_command.generate_image:
            state.should_generate_image = True
            state.image_prompt = image_command.prompt

        return state
