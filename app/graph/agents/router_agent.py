from typing import Dict, Any
from app.graph.state import CompanionState

class RouterAgent:
    """
    Supervisor Router Agent responsible for multi-persona turn-taking.
    Determines which companion persona should respond to the user input.
    """

    @classmethod
    def select_speaker(cls, state: CompanionState) -> CompanionState:
        # If current_speaker_id is already set (e.g. 1-on-1 or target_companion_id specified), retain it
        if state.current_speaker_id and state.current_speaker_id in state.companion_profiles:
            profile = state.companion_profiles[state.current_speaker_id]
            state.current_speaker_name = profile.get("name", "Companion")
            return state

        # If active_companion_ids has entries, pick the first or route based on message
        if state.active_companion_ids:
            # Check if any companion name is directly mentioned in user_message
            msg_lower = state.user_message.lower()
            for comp_id in state.active_companion_ids:
                profile = state.companion_profiles.get(comp_id, {})
                comp_name = profile.get("name", "").lower()
                if comp_name and comp_name in msg_lower:
                    state.current_speaker_id = comp_id
                    state.current_speaker_name = profile.get("name", "Companion")
                    return state

            # Default to first active companion
            first_id = state.active_companion_ids[0]
            state.current_speaker_id = first_id
            profile = state.companion_profiles.get(first_id, {})
            state.current_speaker_name = profile.get("name", "Companion")
        
        return state
