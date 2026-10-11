"""Trajectory prediction engine.

Provides deterministic kinematic trajectory prediction over a configurable horizon.
Answers the question:
    "If this aircraft continues according to its current flight state/intent,
     where is it likely to be at future times?"

NOTE: This is an advisory decision-support prototype module,
NOT certified aviation-grade trajectory prediction.
"""

from __future__ import annotations
import math

from typing import Optional, Sequence

from core.engine.propagation import propagate_aircraft
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
        """Predict future trajectory for a single aircraft."""
        cfg = config or self.default_config

        if cfg.horizon_sec <= 0.0:
            raise ValueError(f"Prediction horizon must be > 0, got {cfg.horizon_sec}")
        if cfg.step_sec <= 0.0:
            raise ValueError(f"Prediction step must be > 0, got {cfg.step_sec}")

        points: list[TrajectoryPoint] = []
        
        # We simulate this aircraft forward using the unified physics engine.
        sim_ac = aircraft.model_copy(deep=True)
        current_time = sim_ac.position.timestamp

        points.append(
            TrajectoryPoint(
                position=sim_ac.position.model_copy(),
                velocity=sim_ac.velocity.model_copy(),
                time=current_time,
                horizontal_uncertainty_nm=0.0,
                vertical_uncertainty_ft=0.0,
            )
        )

        num_intervals = int(cfg.horizon_sec / cfg.step_sec)
        max_intervals = min(num_intervals, cfg.max_points - 1)
        sim_time = current_time
        
        for i in range(1, max_intervals + 1):
            dt = cfg.step_sec
            
            # Predictor logic specific (like cruise alt leveling or live vertical limit)
            # must be injected before propagation if we want it.
            # But wait, propagation now handles maneuvers. What about normal waypoint steering?
            # Waypoint steering can just modify heading before propagate.
            
            if sim_ac.flight_plan and sim_ac.flight_plan.waypoints and not sim_ac.assigned_maneuver:
                target_wp = sim_ac.flight_plan.waypoints[0]
                dist_to_wp = haversine_distance_nm(sim_ac.position.latitude, sim_ac.position.longitude, target_wp.latitude, target_wp.longitude)
                if dist_to_wp > 2.0:
                    sim_ac.velocity.heading = initial_bearing(sim_ac.position.latitude, sim_ac.position.longitude, target_wp.latitude, target_wp.longitude)

            if sim_ac.aircraft_type == "LIVE" and (sim_time - current_time) > cfg.vertical_prediction_duration_sec:
                sim_ac.velocity.vertical_speed = 0.0
                
            cruise_alt = sim_ac.flight_plan.cruise_altitude if sim_ac.flight_plan else None
            if cruise_alt is not None and sim_ac.velocity.vertical_speed != 0.0 and not sim_ac.assigned_maneuver:
                if (sim_ac.velocity.vertical_speed > 0.0 and sim_ac.position.altitude >= cruise_alt) or (sim_ac.velocity.vertical_speed < 0.0 and sim_ac.position.altitude <= cruise_alt):
                    sim_ac.position.altitude = cruise_alt
                    sim_ac.velocity.vertical_speed = 0.0

            # Advance physics
            sim_ac = propagate_aircraft(sim_ac, dt, sim_time)
            sim_time += dt
            
            # Level-off check after propagation
            if cruise_alt is not None and sim_ac.velocity.vertical_speed != 0.0 and not sim_ac.assigned_maneuver:
                if (sim_ac.velocity.vertical_speed > 0.0 and sim_ac.position.altitude >= cruise_alt) or (sim_ac.velocity.vertical_speed < 0.0 and sim_ac.position.altitude <= cruise_alt):
                    sim_ac.position.altitude = cruise_alt
                    sim_ac.velocity.vertical_speed = 0.0

            elapsed_min = (i * dt) / 60.0
            h_uncertainty = round(0.05 * elapsed_min, 4)
            v_uncertainty = round(10.0 * elapsed_min, 1)

            points.append(
                TrajectoryPoint(
                    position=Position(
                        latitude=round(sim_ac.position.latitude, 5),
                        longitude=round(sim_ac.position.longitude, 5),
                        altitude=round(sim_ac.position.altitude, 1),
                        timestamp=round(sim_time, 2),
                    ),
                    velocity=Velocity(
                        ground_speed=round(sim_ac.velocity.ground_speed, 1),
                        vertical_speed=round(sim_ac.velocity.vertical_speed, 1),
                        heading=round(sim_ac.velocity.heading, 1),
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
        """Predict trajectories for a batch of aircraft."""
        return {ac.id: self.predict(ac, config) for ac in aircraft_list}


default_predictor = TrajectoryPredictor()


def predict_trajectory(aircraft: Aircraft, config: Optional[PredictionConfig] = None) -> Trajectory:
    return default_predictor.predict(aircraft, config)


def predict_all_trajectories(
    aircraft_list: Sequence[Aircraft], config: Optional[PredictionConfig] = None
) -> dict[str, Trajectory]:
    return default_predictor.predict_all(aircraft_list, config)
