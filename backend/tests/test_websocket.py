"""Test suite for full-duplex WebSocket real-time communication."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_ws_info_endpoint(client: TestClient):
    """Verify metadata discovery endpoint for WebSockets."""
    response = client.get("/api/v1/ws/info")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert data["protocol"] == "airops-nexus-ws-v1"
    assert "/api/v1/ws" in data["endpoints"]
    assert "/ws" in data["endpoints"]
    assert "jobs:progress" in data["channels"]
    assert "duplex_messaging" in data["capabilities"]


def test_websocket_handshake_and_ping_pong(client: TestClient):
    """Verify WebSocket connection handshake and duplex ping/pong."""
    with client.websocket_connect("/api/v1/ws") as websocket:
        # Step 1: Initial connection handshake
        handshake = websocket.receive_json()
        assert handshake["type"] == "connected"
        assert handshake["protocol"] == "airops-nexus-ws-v1"
        assert "as_of" in handshake

        # Step 2: Client sends ping action
        websocket.send_json({"action": "ping"})
        response = websocket.receive_json()
        assert response["type"] == "pong"
        assert "timestamp" in response


def test_top_level_ws_endpoint(client: TestClient):
    """Verify top-level /ws endpoint connects and sends handshake."""
    with client.websocket_connect("/ws") as websocket:
        handshake = websocket.receive_json()
        assert handshake["type"] == "connected"
        assert handshake["protocol"] == "airops-nexus-ws-v1"


def test_websocket_echo_and_subscribe(client: TestClient):
    """Verify client action dispatching including echo and channel subscription."""
    with client.websocket_connect("/api/v1/ws") as websocket:
        _ = websocket.receive_json()  # Consume handshake

        # Test echo
        websocket.send_json({"action": "echo", "payload": {"test_key": "test_val"}})
        echo_resp = websocket.receive_json()
        assert echo_resp["type"] == "echo"
        assert echo_resp["payload"] == {"test_key": "test_val"}

        # Test subscription
        websocket.send_json({"action": "subscribe", "channel": "jobs:progress"})
        sub_resp = websocket.receive_json()
        assert sub_resp["type"] == "subscribed"
        assert sub_resp["channel"] == "jobs:progress"
