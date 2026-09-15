from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.memory_service import MemoryService

client = TestClient(app)

def test_room_creation_and_messaging():
    mem_service = MemoryService(host=":memory:")
    
    with patch("app.services.llm_service.LLMService.generate_chat_response_async", new_callable=AsyncMock) as mock_llm, \
         patch("app.graph.agents.persona_agent.MemoryService", return_value=mem_service), \
         patch("app.graph.agents.memory_agent.MemoryService", return_value=mem_service):
        
        mock_llm.return_value = ("Hello from Kai in the lounge!", None)

        # 1. Create two companions
        p1 = client.post("/api/v1/clone/ingest", json={
            "companion_name": "Aria",
            "companion_type": "friend",
            "personality_description": "Friendly & witty friend who loves gaming."
        }).json()

        p2 = client.post("/api/v1/clone/ingest", json={
            "companion_name": "Kai",
            "companion_type": "mentor",
            "personality_description": "Wise coding mentor."
        }).json()

        p3 = client.post("/api/v1/clone/ingest", json={
            "companion_name": "Luna",
            "companion_type": "creative",
            "personality_description": "Artist and illustrator."
        }).json()

        # 2. Create room
        room_payload = {
            "name": "Tech & Gaming Lounge",
            "description": "Room with Aria and Kai",
            "user_id": "test_user_room",
            "companion_ids": [p1["companion_id"], p2["companion_id"]]
        }
        
        room_resp = client.post("/api/v1/rooms/create", json=room_payload)
        assert room_resp.status_code == 201
        room_data = room_resp.json()
        assert room_data["name"] == "Tech & Gaming Lounge"
        assert len(room_data["participants"]) == 2

        # 3. List rooms
        list_resp = client.get("/api/v1/rooms?user_id=test_user_room")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

        # 4. Add Participant into Room
        add_p_resp = client.post(
            f"/api/v1/rooms/{room_data['room_id']}/participants", 
            json={"companion_id": p3["companion_id"]}
        )
        assert add_p_resp.status_code == 200
        assert len(add_p_resp.json()["participants"]) == 3

        # 5. Target Kai in room chat
        msg_payload = {
            "room_id": room_data["room_id"],
            "user_id": "test_user_room",
            "message": "Hey Kai, what language should I learn first?",
            "target_companion_id": p2["companion_id"]
        }
        
        msg_resp = client.post("/api/v1/rooms/message", json=msg_payload)
        assert msg_resp.status_code == 200
        msg_data = msg_resp.json()
        assert msg_data["speaker_id"] == p2["companion_id"]
        assert msg_data["speaker_name"] == "Kai"
        assert len(msg_data["reply"]) > 0

        # 6. Fetch Room History
        hist_resp = client.get(f"/api/v1/rooms/{room_data['room_id']}/history")
        assert hist_resp.status_code == 200
        assert len(hist_resp.json()) >= 2

        # 7. Delete Room
        del_resp = client.delete(f"/api/v1/rooms/{room_data['room_id']}")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "success"
