from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_room_creation_and_messaging():
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

    # 4. Target Kai in room chat
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
