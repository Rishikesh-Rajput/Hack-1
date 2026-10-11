"""Aircraft data models.

Defines the core aircraft state representation including position,
velocity, flight plan, and operational status.

Canonical units:
- Position: degrees (lat/lon), feet (altitude)
- Speed: knots (ground speed), feet per minute (vertical speed)
- Heading: degrees true (0-360)
- Time: seconds (simulation time)
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AircraftStatus(str, Enum):
    """Operational status of an aircraft in the simulation."""

    ACTIVE = "ACTIVE"          # Normal flight
    MANEUVERING = "MANEUVERING"  # Executing a resolution maneuver
    RETURNING = "RETURNING"    # Returning to original flight parameters after maneuver
    EXITED = "EXITED"          # Left the monitoring region


class Position(BaseModel):
    """Geographic position of an aircraft.

    Attributes:
        latitude: Latitude in degrees (-90 to 90).
        longitude: Longitude in degrees (-180 to 180).
        altitude: Altitude in feet above mean sea level.
        timestamp: Simulation time in seconds.
    """

    latitude: float = Field(ge=-90.0, le=90.0, description="Latitude in degrees")
    longitude: float = Field(ge=-180.0, le=180.0, description="Longitude in degrees")
    altitude: float = Field(ge=0.0, description="Altitude in feet MSL")
    timestamp: float = Field(ge=0.0, description="Simulation time in seconds")


class Velocity(BaseModel):
    """Velocity vector of an aircraft.

    Attributes:
        ground_speed: Speed over ground in knots.
        vertical_speed: Rate of climb/descent in feet per minute (positive = climb).
        heading: True heading in degrees (0-360, 0=North, 90=East).
    """

    ground_speed: float = Field(ge=0.0, description="Ground speed in knots")
    vertical_speed: float = Field(default=0.0, description="Vertical speed in fpm (positive=climb)")
    heading: float = Field(ge=0.0, lt=360.0, description="True heading in degrees")


class FlightPlan(BaseModel):
    """Flight plan for an aircraft.

    Attributes:
        origin: ICAO code of departure airport.
        destination: ICAO code of arrival airport.
        cruise_altitude: Planned cruise altitude in feet.
        cruise_speed: Planned cruise speed in knots.
        waypoints: List of planned waypoint positions (optional for MVP).
    """

    origin: str = Field(description="ICAO departure airport code")
    destination: str = Field(description="ICAO arrival airport code")
    cruise_altitude: Optional[float] = Field(default=None, ge=0.0, description="Cruise altitude in feet")
    cruise_speed: Optional[float] = Field(default=None, ge=0.0, description="Cruise speed in knots")
    waypoints: list[Position] = Field(default_factory=list, description="Planned route waypoints")


class Maneuver(BaseModel):
    """A resolution maneuver assigned to an aircraft.

    Describes a change to heading, altitude, and/or speed
    that the aircraft should execute.
    """

    type: str = Field(description="Maneuver type: HEADING, ALTITUDE, SPEED, COMBINED")
    heading_change: float = Field(default=0.0, description="Heading change in degrees (positive=right)")
    altitude_change: float = Field(default=0.0, description="Altitude change in feet (positive=climb)")
    speed_change: float = Field(default=0.0, description="Speed change in knots")
    start_time: float = Field(ge=0.0, description="Simulation time to begin maneuver")
    hold_sec: float = Field(default=120.0, gt=0.0, description="Hold duration in seconds before rejoining")
    duration: float = Field(gt=0.0, description="Total maneuver duration in seconds (hold + rejoin)")

    @property
    def end_time(self) -> float:
        """Time at which the maneuver ends."""
        return self.start_time + self.duration


class Aircraft(BaseModel):
    """Complete aircraft state in the simulation.

    Represents a single aircraft with its current position, velocity,
    flight plan, and operational status. This is the primary entity
    that flows through the entire detection and resolution pipeline.
    """

    id: str = Field(description="Unique internal aircraft ID")
    callsign: str = Field(description="ATC callsign (e.g., AI101, SQ308)")
    aircraft_type: str = Field(default="A320", description="ICAO aircraft type code")
    position: Position = Field(description="Current geographic position")
    velocity: Velocity = Field(description="Current velocity vector")
    flight_plan: FlightPlan = Field(description="Flight plan")
    status: AircraftStatus = Field(default=AircraftStatus.ACTIVE, description="Operational status")
    assigned_maneuver: Optional[Maneuver] = Field(
        default=None, description="Currently assigned resolution maneuver"
    )

    # Original flight parameters (stored when maneuver is assigned, for return)
    original_heading: Optional[float] = Field(default=None, description="Heading before maneuver")
    original_altitude: Optional[float] = Field(default=None, description="Altitude before maneuver")
    original_speed: Optional[float] = Field(default=None, description="Speed before maneuver")

    def assign_maneuver(self, maneuver: Maneuver) -> None:
        """Assign a resolution maneuver, saving original flight parameters."""
        self.original_heading = self.velocity.heading
        self.original_altitude = self.position.altitude
        self.original_speed = self.velocity.ground_speed
        self.assigned_maneuver = maneuver
        self.status = AircraftStatus.MANEUVERING

    def clear_maneuver(self) -> None:
        """Clear the assigned maneuver and restore original parameters."""
        self.assigned_maneuver = None
        self.original_heading = None
        self.original_altitude = None
        self.original_speed = None
        self.status = AircraftStatus.ACTIVE

    @property
    def is_maneuvering(self) -> bool:
        """Whether the aircraft is currently executing a maneuver."""
        return self.status == AircraftStatus.MANEUVERING

    def __repr__(self) -> str:
        return (
            f"Aircraft({self.callsign}, "
            f"pos=({self.position.latitude:.2f}, {self.position.longitude:.2f}, {self.position.altitude:.0f}ft), "
            f"hdg={self.velocity.heading:.0f}°, spd={self.velocity.ground_speed:.0f}kt, "
            f"vs={self.velocity.vertical_speed:.0f}fpm, "
            f"status={self.status.value})"
        )
