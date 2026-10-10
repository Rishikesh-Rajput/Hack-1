"""Aircraft state propagation.

Deterministic physics for advancing aircraft position and state
over a simulation time step.

Movement model:
1. Horizontal: Great-circle navigation using heading and ground speed.
2. Vertical: Linear interpolation using vertical speed.
3. Heading/speed: Constant unless a maneuver is being applied.

This module has NO web dependencies and can be used standalone.
"""

from __future__ import annotations

from core.geo.calculations import (
    destination_point,
    knots_to_nm_per_second,
    fpm_to_fps,
    normalize_heading,
)
from core.models.aircraft import Aircraft, AircraftStatus, Maneuver, Position, Velocity


def propagate_position(
    latitude: float,
    longitude: float,
    altitude: float,
    heading: float,
    ground_speed: float,
    vertical_speed: float,
    dt: float,
) -> tuple[float, float, float]:
    """Propagate a position forward by dt seconds.

    Args:
        latitude: Current latitude in degrees.
        longitude: Current longitude in degrees.
        altitude: Current altitude in feet.
        heading: Current heading in degrees true.
        ground_speed: Current ground speed in knots.
        vertical_speed: Current vertical speed in fpm.
        dt: Time step in seconds.

    Returns:
        Tuple of (new_latitude, new_longitude, new_altitude).
    """
    # Horizontal movement via great-circle
    distance_nm = knots_to_nm_per_second(ground_speed) * dt
    new_lat, new_lon = destination_point(latitude, longitude, heading, distance_nm)

    # Vertical movement (linear)
    altitude_change = fpm_to_fps(vertical_speed) * dt
    new_altitude = max(0.0, altitude + altitude_change)

    return (new_lat, new_lon, new_altitude)


def apply_maneuver_effects(
    aircraft: Aircraft,
    current_time: float,
) -> None:
    """Apply maneuver effects to aircraft state.

    If the aircraft has an assigned maneuver and it's within the
    maneuver's active time window, apply the heading/altitude/speed
    changes. If the maneuver has expired, clear it.

    This mutates the aircraft in place.

    Args:
        aircraft: Aircraft to apply maneuver effects to.
        current_time: Current simulation time in seconds.
    """
    maneuver = aircraft.assigned_maneuver
    if maneuver is None:
        return

    if current_time < maneuver.start_time:
        # Maneuver hasn't started yet
        return

    if current_time >= maneuver.end_time:
        # Maneuver has expired - clear it and restore original parameters
        aircraft.clear_maneuver()
        return

    # Maneuver is active - apply changes (only once, at start)
    if aircraft.status == AircraftStatus.MANEUVERING:
        # Changes are already applied via assign_maneuver
        # The heading/altitude/speed changes were applied when the maneuver was assigned
        pass


def propagate_aircraft(aircraft: Aircraft, dt: float, current_time: float) -> Aircraft:
    """Propagate an aircraft's state forward by one time step.

    This is the main entry point for aircraft state advancement.
    It handles:
    1. Maneuver effect application/expiration
    2. Position propagation using great-circle navigation
    3. Timestamp update

    This creates a new Aircraft with updated state (does not mutate the original).

    Args:
        aircraft: Current aircraft state.
        dt: Time step in seconds.
        current_time: Current simulation time before this step.

    Returns:
        New Aircraft instance with updated position and state.
    """
    # Work on a copy to maintain immutability for the caller
    updated = aircraft.model_copy(deep=True)

    # Apply or expire maneuver effects
    apply_maneuver_effects(updated, current_time + dt)

    # Skip propagation for exited aircraft
    if updated.status == AircraftStatus.EXITED:
        return updated

    # Propagate position
    new_lat, new_lon, new_alt = propagate_position(
        latitude=updated.position.latitude,
        longitude=updated.position.longitude,
        altitude=updated.position.altitude,
        heading=updated.velocity.heading,
        ground_speed=updated.velocity.ground_speed,
        vertical_speed=updated.velocity.vertical_speed,
        dt=dt,
    )

    # Update position
    updated.position = Position(
        latitude=new_lat,
        longitude=new_lon,
        altitude=new_alt,
        timestamp=current_time + dt,
    )

    return updated
