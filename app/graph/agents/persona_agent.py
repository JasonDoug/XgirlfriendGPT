from typing import Dict, Any
from app.graph.state import CompanionState
from app.services.llm_service import LLMService

class PersonaAgent:
    """
    Companion Persona Execution Agent.
    Generates personality-aligned response text and evaluates visual tool calls.
    """

    @classmethod
    async def generate_response_async(cls, state: CompanionState) -> CompanionState:
        if not state.current_speaker_id or state.current_speaker_id not in state.companion_profiles:
            state.reply = "I'm right here!"
            return state

        profile = state.companion_profiles[state.current_speaker_id]
        system_prompt = profile.get("system_prompt", "You are a friendly AI companion.")

        formatted_history = []
        for msg in state.message_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted_history.append({"role": role, "content": content})

        reply_text, image_command = await LLMService.generate_chat_response_async(
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

    @classmethod
    def generate_response(cls, state: CompanionState) -> CompanionState:
        if not state.current_speaker_id or state.current_speaker_id not in state.companion_profiles:
            state.reply = "I'm right here!"
            return state

        profile = state.companion_profiles[state.current_speaker_id]
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
