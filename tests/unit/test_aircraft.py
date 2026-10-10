"""Unit tests for Aircraft and state models."""

import pytest
from pydantic import ValidationError

from core.models.aircraft import (
    Aircraft,
    AircraftStatus,
    FlightPlan,
    Maneuver,
    Position,
    Velocity,
)


class TestAircraftModels:
    def test_valid_aircraft_creation(self):
        ac = Aircraft(
            id="ac_01",
            callsign="AI101",
            aircraft_type="A320",
            position=Position(latitude=19.0, longitude=72.8, altitude=35000.0, timestamp=0.0),
            velocity=Velocity(ground_speed=450.0, vertical_speed=0.0, heading=90.0),
            flight_plan=FlightPlan(origin="VABB", destination="VIDP", cruise_altitude=35000.0, cruise_speed=450.0),
        )
        assert ac.callsign == "AI101"
        assert ac.status == AircraftStatus.ACTIVE
        assert ac.is_maneuvering is False

    def test_invalid_position_boundaries(self):
        with pytest.raises(ValidationError):
            Position(latitude=95.0, longitude=0.0, altitude=10000.0, timestamp=0.0)
        with pytest.raises(ValidationError):
            Position(latitude=0.0, longitude=190.0, altitude=10000.0, timestamp=0.0)
        with pytest.raises(ValidationError):
            Position(latitude=0.0, longitude=0.0, altitude=-500.0, timestamp=0.0)

    def test_invalid_velocity_boundaries(self):
        with pytest.raises(ValidationError):
            Velocity(ground_speed=-10.0, vertical_speed=0.0, heading=90.0)
        with pytest.raises(ValidationError):
            Velocity(ground_speed=400.0, vertical_speed=0.0, heading=365.0)

    def test_assign_and_clear_maneuver(self):
        ac = Aircraft(
            id="ac_01",
            callsign="AI101",
            aircraft_type="A320",
            position=Position(latitude=19.0, longitude=72.8, altitude=35000.0, timestamp=0.0),
            velocity=Velocity(ground_speed=450.0, vertical_speed=0.0, heading=90.0),
            flight_plan=FlightPlan(origin="VABB", destination="VIDP", cruise_altitude=35000.0, cruise_speed=450.0),
        )

        m = Maneuver(
            type="HEADING",
            heading_change=15.0,
            altitude_change=1000.0,
            speed_change=-20.0,
            start_time=10.0,
            duration=120.0,
        )

        ac.assign_maneuver(m)
        assert ac.status == AircraftStatus.MANEUVERING
        assert ac.is_maneuvering is True
        assert ac.velocity.heading == pytest.approx(105.0)
        assert ac.position.altitude == pytest.approx(36000.0)
        assert ac.velocity.ground_speed == pytest.approx(430.0)

        ac.clear_maneuver()
        assert ac.status == AircraftStatus.ACTIVE
        assert ac.is_maneuvering is False
        assert ac.velocity.heading == pytest.approx(90.0)
        assert ac.position.altitude == pytest.approx(35000.0)  # Restores original altitude
        assert ac.velocity.ground_speed == pytest.approx(450.0)
