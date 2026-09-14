from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert ("XgirlfriendGPT" in response.text or response.json().get("app") == "XgirlfriendGPT")

def test_clone_personality_with_logs():
    payload = {
        "companion_name": "Aria",
        "companion_type": "friend",
        "raw_texts": [
            "Hey! What's up? lol ngl so hyped for the weekend 🔥",
            "brb getting some boba, vibes are immaculate ✨"
        ]
    }
    
    response = client.post("/api/v1/clone/ingest", json=payload)
    assert response.status_code == 201
    data = response.json()
    
    assert data["name"] == "Aria"
    assert "companion_id" in data
    assert "system_prompt" in data

def test_clone_personality_with_description():
    payload = {
        "companion_name": "Kai",
        "companion_type": "mentor",
        "personality_description": "A calm, wise coding mentor who speaks clearly, gives detailed advice, and uses tech analogies."
    }
    
    response = client.post("/api/v1/clone/ingest", json=payload)
    assert response.status_code == 201
    data = response.json()
    
    assert data["name"] == "Kai"
    assert "CHARACTER DIRECTIVES" in data["system_prompt"]
    
    # Test Chat interaction with Kai
    chat_payload = {
        "companion_id": data["companion_id"],
        "user_id": "test_user_100",
        "message": "Hey Kai! Can you give me advice on learning Python?",
        "enable_memory": True,
        "enable_vision": False
    }
    
    chat_resp = client.post("/api/v1/chat/message", json=chat_payload)
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert chat_data["companion_id"] == data["companion_id"]
    assert "reply" in chat_data

def test_voice_webhook_endpoint():
    response = client.post(
        "/api/v1/voice/webhook",
        data={"SpeechResult": "Hello companion", "CallSid": "CA12345"}
    )
    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "<Response>" in response.text

def test_sms_webhook_endpoint():
    response = client.post(
        "/api/v1/sms/webhook",
        data={
            "MessageSid": "SM12345",
            "From": "+15550001111",
            "To": "+15559998888",
            "Body": "Hey! Are you free?"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "reply" in data

def test_fast_mode_chat_and_on_demand_synthesis():
    # 1. Test fast_mode chat turn (audio_url should be None for instant response)
    chat_payload = {
        "companion_id": "test_fast_comp",
        "user_id": "user_fast_1",
        "message": "Quick check-in!",
        "enable_memory": False,
        "fast_mode": True
    }
    resp = client.post("/api/v1/chat/message", json=chat_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert data["audio_url"] is None

    # 2. Test on-demand voice TTS synthesis endpoint
    synth_payload = {"text": data["reply"]}
    synth_resp = client.post("/api/v1/voice/synthesize", json=synth_payload)
    assert synth_resp.status_code == 200
    synth_data = synth_resp.json()
    assert "audio_url" in synth_data

