"""Trajectory prediction engine.

Provides deterministic kinematic trajectory prediction over a configurable horizon.
Answers the question:
    "If this aircraft continues according to its current flight state/intent,
     where is it likely to be at future times?"

Features:
- Great-circle geodesic forward extrapolation
- Constant velocity & heading continuation
- Optional flight-plan waypoint steering & altitude level-off
- Configurable prediction horizon, step size, and point limit
- Future-ready uncertainty bounds representation
- Strictly deterministic output for identical inputs

NOTE: This is an advisory decision-support prototype module,
NOT certified aviation-grade trajectory prediction.
"""

from __future__ import annotations

from typing import Optional, Sequence

from core.engine.propagation import propagate_position
from core.geo.calculations import haversine_distance_nm, initial_bearing
from core.models.aircraft import Aircraft, Position, Velocity
from core.models.config import PredictionConfig
from core.models.trajectory import Trajectory, TrajectoryPoint, TrajectoryType


class TrajectoryPredictor:
    """Deterministic trajectory predictor for aircraft state extrapolation."""

    def __init__(self, default_config: Optional[PredictionConfig] = None) -> None:
        self.default_config = default_config or PredictionConfig()

    def predict(
        self,
        aircraft: Aircraft,
        config: Optional[PredictionConfig] = None,
    ) -> Trajectory:
        """Predict future trajectory for a single aircraft.

        Args:
            aircraft: Current aircraft state.
            config: Optional override of prediction configuration.

        Returns:
            Trajectory containing time-indexed sequence of future points.
        """
        cfg = config or self.default_config

        if cfg.horizon_sec <= 0.0:
            raise ValueError(f"Prediction horizon must be > 0, got {cfg.horizon_sec}")
        if cfg.step_sec <= 0.0:
            raise ValueError(f"Prediction step must be > 0, got {cfg.step_sec}")

        points: list[TrajectoryPoint] = []

        # Current state
        current_time = aircraft.position.timestamp
        lat = aircraft.position.latitude
        lon = aircraft.position.longitude
        alt = aircraft.position.altitude

        spd = aircraft.velocity.ground_speed
        vs = aircraft.velocity.vertical_speed
        hdg = aircraft.velocity.heading

        # Point 0: Current state (t = 0 from start of prediction)
        points.append(
            TrajectoryPoint(
                position=Position(latitude=lat, longitude=lon, altitude=alt, timestamp=current_time),
                velocity=Velocity(ground_speed=spd, vertical_speed=vs, heading=hdg),
                time=current_time,
                horizontal_uncertainty_nm=0.0,
                vertical_uncertainty_ft=0.0,
            )
        )

        # Check for flight plan waypoints
        waypoints = list(aircraft.flight_plan.waypoints) if aircraft.flight_plan else []
        current_wp_idx = 0
        waypoint_capture_dist_nm = 2.0  # Distance threshold to sequence to next waypoint
        cruise_alt = aircraft.flight_plan.cruise_altitude if aircraft.flight_plan else None

        # Number of forecast intervals
        num_intervals = int(cfg.horizon_sec / cfg.step_sec)
        max_intervals = min(num_intervals, cfg.max_points - 1)

        sim_time = current_time
        for i in range(1, max_intervals + 1):
            dt = cfg.step_sec
            sim_time += dt

            # 1. Waypoint steering (if active waypoints exist)
            if current_wp_idx < len(waypoints):
                target_wp = waypoints[current_wp_idx]
                dist_to_wp = haversine_distance_nm(lat, lon, target_wp.latitude, target_wp.longitude)

                if dist_to_wp <= waypoint_capture_dist_nm:
                    # Captured waypoint, advance to next
                    current_wp_idx += 1
                    if current_wp_idx < len(waypoints):
                        target_wp = waypoints[current_wp_idx]
                        hdg = initial_bearing(lat, lon, target_wp.latitude, target_wp.longitude)
                else:
                    hdg = initial_bearing(lat, lon, target_wp.latitude, target_wp.longitude)

            # 2. Cruise altitude level-off constraint
            if cruise_alt is not None and vs != 0.0:
                if (vs > 0.0 and alt >= cruise_alt) or (vs < 0.0 and alt <= cruise_alt):
                    alt = cruise_alt
                    vs = 0.0

            # 3. Propagate forward by dt
            new_lat, new_lon, new_alt = propagate_position(
                latitude=lat,
                longitude=lon,
                altitude=alt,
                heading=hdg,
                ground_speed=spd,
                vertical_speed=vs,
                dt=dt,
            )

            # If climbing/descending towards cruise alt, check if crossed during step
            if cruise_alt is not None and vs != 0.0:
                if (vs > 0.0 and new_alt >= cruise_alt) or (vs < 0.0 and new_alt <= cruise_alt):
                    new_alt = cruise_alt
                    vs = 0.0

            lat, lon, alt = new_lat, new_lon, new_alt

            # 4. Uncertainty representation: linear expansion proxy (e.g. 0.05 NM per minute)
            elapsed_min = (i * dt) / 60.0
            h_uncertainty = round(0.05 * elapsed_min, 4)
            v_uncertainty = round(10.0 * elapsed_min, 1)

            points.append(
                TrajectoryPoint(
                    position=Position(
                        latitude=round(lat, 5),
                        longitude=round(lon, 5),
                        altitude=round(alt, 1),
                        timestamp=round(sim_time, 2),
                    ),
                    velocity=Velocity(
                        ground_speed=round(spd, 1),
                        vertical_speed=round(vs, 1),
                        heading=round(hdg, 1),
                    ),
                    time=round(sim_time, 2),
                    horizontal_uncertainty_nm=h_uncertainty,
                    vertical_uncertainty_ft=v_uncertainty,
                )
            )

        return Trajectory(
            aircraft_id=aircraft.id,
            points=points,
            trajectory_type=TrajectoryType.PREDICTED,
        )

    def predict_all(
        self,
        aircraft_list: Sequence[Aircraft],
        config: Optional[PredictionConfig] = None,
    ) -> dict[str, Trajectory]:
        """Predict trajectories for a batch of aircraft.

        Returns:
            Dictionary mapping aircraft ID -> predicted Trajectory.
        """
        return {ac.id: self.predict(ac, config) for ac in aircraft_list}


# Convenience module-level instances & functions
default_predictor = TrajectoryPredictor()


def predict_trajectory(aircraft: Aircraft, config: Optional[PredictionConfig] = None) -> Trajectory:
    """Predict trajectory for a single aircraft using the default predictor."""
    return default_predictor.predict(aircraft, config)


def predict_all_trajectories(
    aircraft_list: Sequence[Aircraft], config: Optional[PredictionConfig] = None
) -> dict[str, Trajectory]:
    """Predict trajectories for all aircraft using the default predictor."""
    return default_predictor.predict_all(aircraft_list, config)
