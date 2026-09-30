from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert ("XgirlfriendGPT" in response.text or response.json().get("app") == "XgirlfriendGPT")

def test_health_and_observability_endpoints():
    liveness_resp = client.get("/health/liveness")
    assert liveness_resp.status_code == 200
    assert liveness_resp.json()["status"] == "ok"
    assert "uptime_seconds" in liveness_resp.json()

    readiness_resp = client.get("/health/readiness")
    assert readiness_resp.status_code in [200, 503]
    readiness_data = readiness_resp.json()
    assert "dependencies" in readiness_data
    assert "qdrant" in readiness_data["dependencies"]

    metrics_resp = client.get("/health/metrics")
    assert metrics_resp.status_code == 200
    assert "http_requests_total" in metrics_resp.text
    assert "x-request-id" in liveness_resp.headers

def test_auth_jwt_token_issuance_and_verification():
    token_resp = client.post("/api/v1/auth/token", json={"user_id": "test_user_777"})
    assert token_resp.status_code == 200
    data = token_resp.json()
    assert "access_token" in data
    assert data["user_id"] == "test_user_777"

    headers = {"Authorization": f"Bearer {data['access_token']}"}
    me_resp = client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["user_id"] == "test_user_777"



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
        "enable_vision": False,
        "fast_mode": True
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

def test_update_companion_profile_formality_and_length():
    # 1. Create a companion first
    create_payload = {
        "companion_name": "Luna",
        "companion_type": "friend",
        "formality": "casual",
        "response_length": "short",
        "personality_description": "A bubbly and friendly artist who loves drawing and painting."
    }
    create_resp = client.post("/api/v1/clone/ingest", json=create_payload)
    assert create_resp.status_code == 201
    comp_id = create_resp.json()["companion_id"]

    # 2. Update formality and response length via PATCH endpoint
    update_payload = {
        "formality": "pirate & adventurous",
        "response_length": "verbose"
    }
    update_resp = client.patch(f"/api/v1/clone/profile/{comp_id}", json=update_payload)
    assert update_resp.status_code == 200
    updated_data = update_resp.json()

    assert updated_data["traits"]["formality"] == "pirate & adventurous"
    assert updated_data["traits"]["average_response_length"] == "verbose"
    assert "PIRATE & ADVENTUROUS" in updated_data["system_prompt"]
    assert "VERBOSE" in updated_data["system_prompt"]

def test_clone_personality_with_appearance_description():
    payload = {
        "companion_name": "Maya",
        "companion_type": "creative",
        "personality_description": "An adventurous traveler and photographer.",
        "appearance_description": "Short silver hair, dark brown eyes, wearing round glasses and a leather jacket."
    }
    
    response = client.post("/api/v1/clone/ingest", json=payload)
    assert response.status_code == 201
    data = response.json()
    
    assert data["name"] == "Maya"
    assert data["appearance_description"] == payload["appearance_description"]
    assert data["traits"]["physical_appearance"] == payload["appearance_description"]
    assert "Short silver hair" in data["system_prompt"]




def test_clear_companion_chat_history():
    # 1. Ingest companion
    create_payload = {
        "companion_name": "Zara",
        "companion_type": "friend",
        "personality_description": "A cheerful gamer who loves playing RPGs."
    }
    resp = client.post("/api/v1/clone/ingest", json=create_payload)
    assert resp.status_code == 201
    comp_id = resp.json()["companion_id"]

    # 2. Add fake chat history
    from app.services.storage_service import StorageService
    fake_history = [
        {"role": "user", "content": "Hey Zara!"},
        {"role": "assistant", "content": "Hey! Up for some gaming?"}
    ]
    StorageService.save_chat_history(comp_id, fake_history)

    # 3. Retrieve history and assert non-empty
    hist_resp = client.get(f"/api/v1/chat/history/{comp_id}")
    assert hist_resp.status_code == 200
    assert len(hist_resp.json()) == 2

    # 4. Clear chat history via DELETE /api/v1/chat/history/{comp_id}
    del_resp = client.delete(f"/api/v1/chat/history/{comp_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"

    # 5. Verify history is cleared while companion profile remains intact
    cleared_hist = client.get(f"/api/v1/chat/history/{comp_id}")
    assert cleared_hist.status_code == 200
    assert len(cleared_hist.json()) == 0

    profile_check = client.get(f"/api/v1/clone/profile/{comp_id}")
    assert profile_check.status_code == 200
    assert profile_check.json()["name"] == "Zara"
