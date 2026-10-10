"""Unit tests for aircraft state propagation."""

import pytest

from core.engine.propagation import propagate_aircraft, propagate_position
from core.models.aircraft import (
    Aircraft,
    AircraftStatus,
    FlightPlan,
    Maneuver,
    Position,
    Velocity,
)


class TestPropagation:
    def test_propagate_position_horizontal(self):
        # Flying East at 360 knots: 360 / 3600 = 0.1 NM/s
        # Over 60 seconds = 6 NM east along equator
        lat, lon, alt = propagate_position(
            latitude=0.0,
            longitude=0.0,
            altitude=30000.0,
            heading=90.0,
            ground_speed=360.0,
            vertical_speed=0.0,
            dt=60.0,
        )
        assert lat == pytest.approx(0.0, abs=1e-4)
        assert lon > 0.0
        assert alt == 30000.0

    def test_propagate_position_vertical_climb_and_descent(self):
        # Climb at 1200 fpm: 1200 / 60 = 20 fps
        _, _, alt_climb = propagate_position(
            latitude=10.0, longitude=70.0, altitude=30000.0,
            heading=0.0, ground_speed=400.0, vertical_speed=1200.0, dt=10.0
        )
        assert alt_climb == pytest.approx(30200.0)

        # Descent at -1200 fpm
        _, _, alt_desc = propagate_position(
            latitude=10.0, longitude=70.0, altitude=30000.0,
            heading=0.0, ground_speed=400.0, vertical_speed=-1200.0, dt=10.0
        )
        assert alt_desc == pytest.approx(29800.0)

    def test_propagate_aircraft_creates_new_instance(self):
        ac = Aircraft(
            id="ac_01",
            callsign="AI101",
            position=Position(latitude=15.0, longitude=75.0, altitude=35000.0, timestamp=0.0),
            velocity=Velocity(ground_speed=450.0, vertical_speed=0.0, heading=0.0),
            flight_plan=FlightPlan(origin="VOBL", destination="VIDP", cruise_altitude=35000.0, cruise_speed=450.0),
        )

        next_ac = propagate_aircraft(ac, dt=5.0, current_time=0.0)
        assert next_ac is not ac
        assert next_ac.position.timestamp == 5.0
        assert next_ac.position.latitude > ac.position.latitude
        assert ac.position.timestamp == 0.0  # Original not mutated
