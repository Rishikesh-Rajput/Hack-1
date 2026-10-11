"""Integration tests for Backend REST API and WebSocket endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app, engine
from core.engine.simulation import SimulationStatus


@pytest.fixture
def client():
    # Use TestClient with lifespan context
    with TestClient(app) as test_client:
        yield test_client


def test_get_scenarios(client):
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4
    ids = [item["id"] for item in data]
    assert "head_on_conflict" in ids
    assert "normal_traffic" in ids


def test_get_monitoring_region(client):
    response = client.get("/api/region")
    assert response.status_code == 200
    data = response.json()
    assert "Indian Airspace" in data["name"]
    assert len(data["polygon"]) >= 10
    assert data["altitude_ceiling_ft"] == 60000.0


def test_simulation_controls(client):
    # Reset
    resp = client.post("/api/simulation/control", json={"action": "reset"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "INITIALIZED"
    assert resp.json()["time"] == 0.0

    # Play
    resp = client.post("/api/simulation/control", json={"action": "play", "speed": 2.0})
    assert resp.status_code == 200
    assert resp.json()["status"] == "PLAYING"
    assert resp.json()["speed_multiplier"] == 2.0

    # Step
    resp = client.post("/api/simulation/control", json={"action": "step"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "PAUSED"
    assert resp.json()["time"] > 0.0

    # Pause
    resp = client.post("/api/simulation/control", json={"action": "pause"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "PAUSED"


def test_load_scenario(client):
    resp = client.post("/api/simulation/load", json={"scenario_id": "normal_traffic"})
    assert resp.status_code == 200
    snap = resp.json()
    assert snap["aircraft_count"] >= 3
    callsigns = [ac["callsign"] for ac in snap["aircraft"]]
    assert "AI101" in callsigns
    assert "6E205" in callsigns


def test_websocket_connection(client):
    with client.websocket_connect("/ws/simulation") as websocket:
        # Initial snapshot received on connect
        data = websocket.receive_json()
        assert "time" in data
        assert "aircraft" in data
        assert "trails" in data
        assert isinstance(data["aircraft"], list)
