import pytest
from unittest.mock import patch, AsyncMock
from app.graph.workflow import companion_graph
from app.graph.state import CompanionState
from app.services.memory_service import MemoryService

@pytest.mark.asyncio
async def test_langgraph_cyclical_turn_taking_and_checkpointer():
    initial_state = CompanionState(
        room_id="room_test_123",
        user_id="user_test_999",
        user_message="Hello everyone in the lounge!",
        active_companion_ids=["comp_1", "comp_2"],
        companion_profiles={
            "comp_1": {"name": "Aria", "system_prompt": "You are Aria."},
            "comp_2": {"name": "Kai", "system_prompt": "You are Kai."}
        },
        fast_mode=True
    )

    mem_service = MemoryService(host=":memory:")

    with patch("app.services.llm_service.LLMService.generate_chat_response_async", new_callable=AsyncMock) as mock_llm, \
         patch("app.graph.agents.persona_agent.MemoryService", return_value=mem_service), \
         patch("app.graph.agents.memory_agent.MemoryService", return_value=mem_service):
        
        mock_llm.return_value = ("Hey from companion!", None)
        
        config = {"configurable": {"thread_id": "room_test_123"}}
        final_state = await companion_graph.ainvoke(initial_state, config=config)

        if isinstance(final_state, dict):
            reply = final_state.get("reply")
            current_speaker = final_state.get("current_speaker_id")
            pending = final_state.get("pending_speakers")
        else:
            reply = getattr(final_state, "reply", None)
            current_speaker = getattr(final_state, "current_speaker_id", None)
            pending = getattr(final_state, "pending_speakers", [])

        assert reply is not None
        assert current_speaker in ["comp_1", "comp_2"]
        assert len(pending) == 0
