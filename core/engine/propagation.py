"""Aircraft state propagation.

Deterministic physics for advancing aircraft position and state
over a simulation time step.
"""

from __future__ import annotations
import math

from core.geo.calculations import (
    destination_point,
    knots_to_nm_per_second,
    fpm_to_fps,
    normalize_heading,
    initial_bearing,
)
from core.models.aircraft import Aircraft, AircraftStatus, Position, Velocity


def propagate_position(
    latitude: float,
    longitude: float,
    altitude: float,
    heading: float,
    ground_speed: float,
    vertical_speed: float,
    dt: float,
) -> tuple[float, float, float]:
    distance_nm = knots_to_nm_per_second(ground_speed) * dt
    new_lat, new_lon = destination_point(latitude, longitude, heading, distance_nm)
    altitude_change = fpm_to_fps(vertical_speed) * dt
    new_altitude = max(0.0, altitude + altitude_change)
    return (new_lat, new_lon, new_altitude)


def apply_maneuver_physics(aircraft: Aircraft, dt: float, current_time: float) -> None:
    maneuver = aircraft.assigned_maneuver
    if maneuver is None:
        return

    # Check expiration
    if current_time >= maneuver.end_time:
        aircraft.clear_maneuver()
        return

    # Constants
    TURN_RATE = 3.0 * dt
    CLIMB_RATE = 1500.0
    ACCEL_RATE = 2.0 * dt  # knots per second

    t_active = current_time - maneuver.start_time
    if t_active < 0:
        return

    # Phase: 1. Deviation/Hold (t < hold_sec)  2. Rejoin (t >= hold_sec)
    phase = "HOLD" if t_active < maneuver.hold_sec else "REJOIN"

    # Heading
    if maneuver.heading_change != 0.0:
        if phase == "HOLD":
            target_heading = normalize_heading(aircraft.original_heading + maneuver.heading_change)
        else:
            # Rejoin to original path far ahead
            rejoin_dist = knots_to_nm_per_second(aircraft.original_speed) * (maneuver.duration - t_active)
            rejoin_lat, rejoin_lon = destination_point(
                aircraft.position.latitude, aircraft.position.longitude, aircraft.original_heading, rejoin_dist
            )
            target_heading = initial_bearing(
                aircraft.position.latitude, aircraft.position.longitude, rejoin_lat, rejoin_lon
            )

        diff = normalize_heading(target_heading - aircraft.velocity.heading)
        if diff > 180:
            diff -= 360
        if abs(diff) <= TURN_RATE:
            aircraft.velocity.heading = target_heading
        else:
            aircraft.velocity.heading = normalize_heading(aircraft.velocity.heading + math.copysign(TURN_RATE, diff))

    # Altitude
    if maneuver.altitude_change != 0.0:
        target_alt = aircraft.original_altitude + maneuver.altitude_change if phase == "HOLD" else aircraft.original_altitude
        alt_diff = target_alt - aircraft.position.altitude
        
        # Determine vertical speed needed
        if abs(alt_diff) < 10.0:
            aircraft.velocity.vertical_speed = 0.0
            aircraft.position.altitude = target_alt
        else:
            aircraft.velocity.vertical_speed = math.copysign(CLIMB_RATE, alt_diff)

    # Speed
    if maneuver.speed_change != 0.0:
        target_speed = aircraft.original_speed + maneuver.speed_change if phase == "HOLD" else aircraft.original_speed
        spd_diff = target_speed - aircraft.velocity.ground_speed
        if abs(spd_diff) <= ACCEL_RATE:
            aircraft.velocity.ground_speed = target_speed
        else:
            aircraft.velocity.ground_speed += math.copysign(ACCEL_RATE, spd_diff)


def propagate_aircraft(aircraft: Aircraft, dt: float, current_time: float) -> Aircraft:
    updated = aircraft.model_copy(deep=True)
    apply_maneuver_physics(updated, dt, current_time)

    if updated.status == AircraftStatus.EXITED:
        return updated

    new_lat, new_lon, new_alt = propagate_position(
        latitude=updated.position.latitude,
        longitude=updated.position.longitude,
        altitude=updated.position.altitude,
        heading=updated.velocity.heading,
        ground_speed=updated.velocity.ground_speed,
        vertical_speed=updated.velocity.vertical_speed,
        dt=dt,
    )

    updated.position = Position(
        latitude=new_lat,
        longitude=new_lon,
        altitude=new_alt,
        timestamp=current_time + dt,
    )
    return updated
