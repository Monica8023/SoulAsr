from fastapi.testclient import TestClient

from backend.src.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_transcribe_endpoint():
    response = client.post(
        "/api/v1/asr/transcribe",
        json={"audio_path": "samples/demo.wav", "options": {"language": "zh"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert "text" in payload["data"]


def test_system_health_endpoint():
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert "status" in payload["data"]


def test_stream_endpoint():
    with client.websocket_connect("/api/v1/asr/stream") as websocket:
        websocket.send_json(
            {
                "type": "start",
                "file_name": "demo.wav",
                "model_name": "whisper",
                "options": {"language": "zh"},
            }
        )
        websocket.send_bytes(b"\x00" * 64000)
        websocket.send_json({"type": "end"})
        first_message = websocket.receive_json()
        assert first_message["type"] in {"partial", "final"}
