import re
from typing import Dict, Any
from app.graph.state import CompanionState

class RouterAgent:
    """
    Supervisor Router Agent responsible for multi-persona turn-taking.
    Determines which companion persona should respond using name recognition,
    semantic topic matching, and conversation flow awareness.
    """

    @classmethod
    def _is_word_match(cls, term: str, text: str) -> bool:
        if not term or not text:
            return False
        pattern = r'\b' + re.escape(term.strip()) + r'\b'
        return bool(re.search(pattern, text, flags=re.IGNORECASE))

    @classmethod
    def select_speaker(cls, state: CompanionState) -> CompanionState:
        # If current_speaker_id is already set (e.g. 1-on-1 or target_companion_id specified), retain it
        if state.current_speaker_id and state.current_speaker_id in state.companion_profiles:
            profile = state.companion_profiles[state.current_speaker_id]
            state.current_speaker_name = profile.get("name", "Companion")
            return state

        if not state.active_companion_ids:
            return state

        msg_lower = state.user_message.lower()

        # 1. Direct Name Mention Matching (Word Boundary)
        for comp_id in state.active_companion_ids:
            profile = state.companion_profiles.get(comp_id, {})
            comp_name = profile.get("name", "")
            if comp_name and cls._is_word_match(comp_name, msg_lower):
                state.current_speaker_id = comp_id
                state.current_speaker_name = profile.get("name", "Companion")
                return state

        # 2. Semantic Topic Matching against companion traits & type (Word Boundary)
        best_match_id = None
        highest_score = 0

        for comp_id in state.active_companion_ids:
            profile = state.companion_profiles.get(comp_id, {})
            traits = profile.get("traits", {})
            top_topics = traits.get("top_topics", []) if isinstance(traits, dict) else []
            comp_type = profile.get("companion_type", "")

            score = 0
            if comp_type and cls._is_word_match(comp_type, msg_lower):
                score += 3

            for topic in top_topics:
                if topic and cls._is_word_match(topic, msg_lower):
                    score += 2

            if score > highest_score:
                highest_score = score
                best_match_id = comp_id

        if best_match_id:
            state.current_speaker_id = best_match_id
            profile = state.companion_profiles.get(best_match_id, {})
            state.current_speaker_name = profile.get("name", "Companion")
            return state

        # 3. Conversation Flow Awareness (Round-robin alternate speaker)
        last_speaker_id = None
        if state.message_history:
            for last_msg in reversed(state.message_history):
                if last_msg.get("role") == "assistant" and last_msg.get("speaker_id"):
                    last_speaker_id = last_msg.get("speaker_id")
                    break

        if last_speaker_id and len(state.active_companion_ids) > 1:
            try:
                curr_idx = state.active_companion_ids.index(last_speaker_id)
                next_idx = (curr_idx + 1) % len(state.active_companion_ids)
                selected_id = state.active_companion_ids[next_idx]
                state.current_speaker_id = selected_id
                profile = state.companion_profiles.get(selected_id, {})
                state.current_speaker_name = profile.get("name", "Companion")
                return state
            except ValueError:
                pass

        # Default to first active companion
        first_id = state.active_companion_ids[0]
        state.current_speaker_id = first_id
        profile = state.companion_profiles.get(first_id, {})
        state.current_speaker_name = profile.get("name", "Companion")
        return state
