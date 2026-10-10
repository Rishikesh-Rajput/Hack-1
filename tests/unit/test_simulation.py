"""Unit tests for SimulationEngine and deterministic replay."""

import pytest

from core.engine.simulation import SimulationEngine, SimulationStatus
from core.models.aircraft import Aircraft, FlightPlan, Position, Velocity
from core.models.config import AppConfig


class TestSimulationEngine:
    @pytest.fixture
    def test_aircraft(self):
        return [
            Aircraft(
                id="ac_01",
                callsign="AI101",
                position=Position(latitude=20.0, longitude=75.0, altitude=35000.0, timestamp=0.0),
                velocity=Velocity(ground_speed=450.0, vertical_speed=0.0, heading=90.0),
                flight_plan=FlightPlan(origin="VABB", destination="VECC", cruise_altitude=35000.0, cruise_speed=450.0),
            ),
            Aircraft(
                id="ac_02",
                callsign="UK802",
                position=Position(latitude=20.0, longitude=80.0, altitude=35000.0, timestamp=0.0),
                velocity=Velocity(ground_speed=450.0, vertical_speed=0.0, heading=270.0),
                flight_plan=FlightPlan(origin="VECC", destination="VABB", cruise_altitude=35000.0, cruise_speed=450.0),
            ),
        ]

    def test_engine_lifecycle(self, test_aircraft):
        engine = SimulationEngine()
        engine.load_scenario({
            "name": "Test Scenario",
            "aircraft": [
                {
                    "id": "ac_01", "callsign": "AI101",
                    "position": {"lat": 20.0, "lon": 75.0, "alt": 35000},
                    "velocity": {"heading": 90.0, "speed": 450.0},
                }
            ]
        })

        assert engine.status == SimulationStatus.INITIALIZED
        engine.play()
        assert engine.status == SimulationStatus.PLAYING
        engine.pause()
        assert engine.status == SimulationStatus.PAUSED

    def test_engine_tick_progression(self, test_aircraft):
        engine = SimulationEngine()
        engine.load_scenario({
            "name": "Test",
            "aircraft": [
                {
                    "id": "ac_01", "callsign": "AI101",
                    "position": {"lat": 20.0, "lon": 75.0, "alt": 35000},
                    "velocity": {"heading": 90.0, "speed": 450.0},
                }
            ]
        })

        snap1 = engine.tick(dt=1.0)
        assert snap1.time == 1.0
        assert engine.current_time == 1.0

        snap2 = engine.tick(dt=2.0)
        assert snap2.time == 3.0
        assert engine.current_time == 3.0

    def test_strictly_deterministic_replay(self, test_aircraft):
        # Run 1
        engine1 = SimulationEngine()
        engine1.load_scenario({
            "name": "Deterministic Test",
            "aircraft": [
                {
                    "id": "ac_01", "callsign": "AI101",
                    "position": {"lat": 20.0, "lon": 75.0, "alt": 35000},
                    "velocity": {"heading": 90.0, "speed": 450.0},
                },
                {
                    "id": "ac_02", "callsign": "UK802",
                    "position": {"lat": 20.0, "lon": 80.0, "alt": 35000},
                    "velocity": {"heading": 270.0, "speed": 450.0},
                }
            ]
        })
        history1 = []
        for _ in range(20):
            snap = engine1.tick(dt=1.0)
            history1.append([(ac.position.latitude, ac.position.longitude) for ac in snap.aircraft])

        # Run 2 with identical inputs
        engine2 = SimulationEngine()
        engine2.load_scenario({
            "name": "Deterministic Test",
            "aircraft": [
                {
                    "id": "ac_01", "callsign": "AI101",
                    "position": {"lat": 20.0, "lon": 75.0, "alt": 35000},
                    "velocity": {"heading": 90.0, "speed": 450.0},
                },
                {
                    "id": "ac_02", "callsign": "UK802",
                    "position": {"lat": 20.0, "lon": 80.0, "alt": 35000},
                    "velocity": {"heading": 270.0, "speed": 450.0},
                }
            ]
        })
        history2 = []
        for _ in range(20):
            snap = engine2.tick(dt=1.0)
            history2.append([(ac.position.latitude, ac.position.longitude) for ac in snap.aircraft])

        # Exact match
        assert history1 == history2
