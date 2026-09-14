from app.services.memory_service import MemoryService
from app.services.llm_service import LLMService

def test_memory_service_upsert_and_retrieve():
    mem_service = MemoryService(host=":memory:")
    
    companion_id = "comp_test_1"
    user_id = "user_test_1"
    
    mem_service.add_memory(
        companion_id=companion_id,
        user_id=user_id,
        content="User loves playing guitar and listening to indie rock."
    )
    
    retrieved = mem_service.retrieve_memories(
        companion_id=companion_id,
        user_id=user_id,
        query="music guitar",
        limit=2
    )
    
    assert len(retrieved) > 0
    assert "guitar" in retrieved[0]

def test_llm_tool_call_extraction():
    sample_llm_response = (
        "Here is a mirror selfie for you! 📸\n"
        '{"generate_image": true, "prompt": "casual selfie in cozy room"}'
    )
    
    reply, img_cmd = LLMService._extract_image_tool_call(sample_llm_response)
    
    assert "Here is a mirror selfie" in reply
    assert img_cmd is not None
    assert img_cmd.generate_image is True
    assert "cozy room" in img_cmd.prompt
