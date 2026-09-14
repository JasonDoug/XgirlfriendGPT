from fastapi.testclient import TestClient
from app.main import app
from app.services.sms_service import SMSService
from app.services.voice_service import VoiceService

client = TestClient(app)

def test_websocket_voice_stream():
    with client.websocket_connect("/api/v1/voice/stream") as websocket:
        payload = {
            "message": "Hello companion!",
            "companion_id": "comp_test_stream"
        }
        websocket.send_json(payload)
        data = websocket.receive_json()
        
        assert data["event"] == "media"
        assert "reply" in data
        assert "audio_url" in data

def test_proactive_sms_job_trigger():
    # Execute proactive outbound job pass
    SMSService._run_proactive_outbound_job()
