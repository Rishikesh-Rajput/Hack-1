"""Simulation engine.

Maintains the authoritative simulation clock, updates aircraft states,
advances positions, updates speed/heading where commanded, exposes state snapshots,
and supports strictly deterministic replay.

This module has NO web, UI, or transport dependencies.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import BaseModel, Field

from core.engine.propagation import propagate_aircraft
from core.engine.scenario_loader import Scenario, load_scenario, load_scenario_from_dict
from core.models.aircraft import Aircraft, AircraftStatus, Maneuver
from core.models.config import AppConfig, SimulationConfig
from core.models.trajectory import Trajectory, TrajectoryPoint, TrajectoryType
from core.models.conflict import Conflict

class SimulationStatus(str, Enum):
    """Lifecycle status of the simulation."""

    INITIALIZED = "INITIALIZED"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class SimulationSnapshot(BaseModel):
    """Immutable snapshot of the simulation state at a specific time."""

    time: float = Field(description="Current simulation time in seconds")
    status: SimulationStatus = Field(description="Current simulation status")
    speed_multiplier: float = Field(description="Active speed multiplier")
    aircraft_count: int = Field(description="Number of managed aircraft")
    aircraft: list[Aircraft] = Field(description="All current aircraft states")
    trails: dict[str, list[list[float]]] = Field(
        default_factory=dict,
        description="Recent [lat, lon] historical coordinates per aircraft ID",
    )
    predicted_trajectories: dict[str, list[list[float]]] = Field(
        default_factory=dict,
        description="Forecast [lat, lon] coordinates per aircraft, derived by the deterministic predictor",
    )
    conflicts: list[Conflict] = Field(
        default_factory=list,
        description="Currently active detected conflicts"
    )


class SimulationEngine:
    """Authoritative air traffic simulation engine.

    Guarantees deterministic execution:
    Given the same scenario, config, initial states, and timestep sequence,
    it produces identical output trajectories.
    """

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        scenario: Optional[Scenario] = None,
    ) -> None:
        self.config = config or AppConfig()
        self.sim_config: SimulationConfig = self.config.simulation

        self.clock: float = 0.0
        self.status: SimulationStatus = SimulationStatus.INITIALIZED
        self.speed_multiplier: float = self.sim_config.speed_multiplier

        self._scenario: Optional[Scenario] = None
        self._aircraft: dict[str, Aircraft] = {}
        # Records actual historical flight paths
        self._history: dict[str, list[TrajectoryPoint]] = {}
        self._conflict_persistence: dict[str, int] = {}
        self._last_processed_ingest: float = 0.0
        
        from core.detection.predictor import TrajectoryPredictor
        from core.detection.detector import ConflictDetector
        from core.resolution.generator import ManeuverGenerator
        from core.resolution.simulator import CandidateSimulator
        from core.resolution.scoring import ManeuverScorer
        from core.resolution.ml_scoring import MLScorer
        from core.resolution.recommendation import RecommendationEngine
        from core.explainer.service import ExplanationService
        
        self.predictor = TrajectoryPredictor(self.config.prediction)
        self.detector = ConflictDetector(self.config.separation, self.config.severity)
        
        self.generator = ManeuverGenerator(self.config.maneuver)
        self.simulator = CandidateSimulator(self.predictor, self.detector)
        self.scorer = ManeuverScorer(self.config.scoring, self.config.separation)
        self.ml_scorer = MLScorer(enabled=False) # Optional ML disabled by default
        self.recommender = RecommendationEngine()
        self.explainer = ExplanationService(self.config.genai)
        
        self.live_provider = None
        self.use_live_data = False
        
        self._conflicts: list[Conflict] = []

        if scenario is not None:
            self.load_scenario(scenario)

    @property
    def current_time(self) -> float:
        """Current simulation clock in seconds."""
        return self.clock

    @property
    def aircraft(self) -> list[Aircraft]:
        """List of all current aircraft states (order preserved by ID)."""
        return list(self._aircraft.values())

    def get_aircraft(self, aircraft_id: str) -> Optional[Aircraft]:
        """Retrieve an aircraft by ID."""
        return self._aircraft.get(aircraft_id)

    def load_scenario(self, scenario_or_path: Union[Scenario, str, Path, dict[str, Any]]) -> None:
        """Load or reload a scenario into the engine.

        Resets clock and history.
        """
        if isinstance(scenario_or_path, Scenario):
            scenario = scenario_or_path
        elif isinstance(scenario_or_path, (str, Path)):
            scenario = load_scenario(scenario_or_path)
        elif isinstance(scenario_or_path, dict):
            scenario = load_scenario_from_dict(scenario_or_path)
        else:
            raise TypeError(f"Unsupported scenario type: {type(scenario_or_path)}")

        self._scenario = scenario
        self.reset()

    def reset(self) -> None:
        """Reset simulation back to initial scenario state."""
        self._conflict_persistence = {}
        self._last_processed_ingest = 0.0
        
        if self._scenario is None:
            self.clock = 0.0
            self._aircraft = {}
            self._history = {}
            self.status = SimulationStatus.INITIALIZED
            return

        self.clock = self._scenario.initial_time
        self.status = SimulationStatus.INITIALIZED
        self.speed_multiplier = self.sim_config.speed_multiplier

        # Fresh deep copies of aircraft
        fresh_aircraft = self._scenario.create_aircraft_instances()
        self._aircraft = {ac.id: ac for ac in fresh_aircraft}

        # Initialize history
        self._history = {}
        for ac in fresh_aircraft:
            self._history[ac.id] = [
                TrajectoryPoint(
                    position=ac.position.model_copy(),
                    velocity=ac.velocity.model_copy(),
                    time=self.clock,
                )
            ]

    def play(self) -> None:
        """Set simulation state to PLAYING."""
        self.status = SimulationStatus.PLAYING

    def pause(self) -> None:
        """Set simulation state to PAUSED."""
        self.status = SimulationStatus.PAUSED

    def toggle_live_mode(self, enabled: bool) -> None:
        """Switch between simulated scenarios and OpenSky live data."""
        self.use_live_data = enabled
        if enabled:
            if not self.live_provider:
                from core.engine.opensky import OpenSkyProvider
                self.live_provider = OpenSkyProvider(self.config.monitoring_region)
            self.live_provider.start()
            self.status = SimulationStatus.PLAYING
            
            # Initial poll
            live_ac = self.live_provider.get_latest_aircraft()
            if live_ac:
                self._aircraft = {ac.id: ac for ac in live_ac}
        else:
            if self.live_provider:
                self.live_provider.stop()
            self.reset()

    def get_live_provider_status(self) -> dict[str, Any]:
        """Return provider connectivity/freshness without exposing credentials."""
        if not self.live_provider:
            return {
                "provider": "OpenSky",
                "active": False,
                "connected": False,
                "fresh": False,
                "aircraft_count": 0,
                "last_success_at": None,
                "last_error": "Live mode has not been started.",
                "rate_limit_remaining": None,
                "poll_interval_sec": None,
            }
        return self.live_provider.get_status()

    def set_speed_multiplier(self, multiplier: float) -> None:
        """Adjust simulation speed multiplier."""
        if multiplier <= 0.0:
            raise ValueError(f"Speed multiplier must be positive, got {multiplier}")
        self.speed_multiplier = multiplier

    def apply_conflict_persistence(self, raw_conflicts: list[Conflict]) -> list[Conflict]:
        is_new_ingest = False
        last_live = getattr(self, '_last_live_ingest', 0.0)
        last_processed = getattr(self, '_last_processed_ingest', 0.0)
        
        if last_live > last_processed:
            is_new_ingest = True
            self._last_processed_ingest = last_live
            
        persistent = []
        current_active = set()
        
        req_updates = getattr(self.config.separation, 'persistence_required_updates', 3)
        
        for c in raw_conflicts:
            current_active.add(c.id)
            
            # Fast-track critical severity (e.g. TTC < 120s) to not hide urgent alerts
            if c.time_to_conflict_sec < self.config.severity.critical_sec:
                persistent.append(c)
                continue
                
            if c.id not in self._conflict_persistence:
                self._conflict_persistence[c.id] = 1
            elif is_new_ingest:
                self._conflict_persistence[c.id] += 1
                
            if self._conflict_persistence[c.id] >= req_updates:
                persistent.append(c)
                
        # Clean up stale conflicts that are no longer predicted
        stale = [cid for cid in self._conflict_persistence if cid not in current_active]
        for cid in stale:
            del self._conflict_persistence[cid]
            
        return persistent

    def tick(self, dt: Optional[float] = None) -> SimulationSnapshot:
        """Advance the simulation by dt seconds (default: sim_config.time_step).

        Execution is completely deterministic:
        1. Advances time: clock += dt
        2. Propagates each aircraft state (position, velocity, altitude, maneuvers)
        3. Records historical point
        4. Returns immutable snapshot
        """
        step = dt if dt is not None else self.sim_config.time_step
        if step <= 0.0:
            raise ValueError(f"Timestep must be > 0, got {step}")

        # Deterministic ordering by sorted aircraft ID
        if getattr(self, 'use_live_data', False) and getattr(self, 'live_provider', None):
            status = self.live_provider.get_status()
            last_live = getattr(self, '_last_live_ingest', 0.0)
            
            # If the provider has a fresh batch we haven't processed yet
            if status['last_success_at'] and status['last_success_at'] > last_live:
                live_ac = self.live_provider.get_latest_aircraft()
                caught_up_ac = {}
                for ac in live_ac:
                    # The aircraft is at ac.position.timestamp. We need to fast-forward it to self.clock
                    catch_up_dt = max(0.0, self.clock - ac.position.timestamp)
                    if catch_up_dt > 0:
                        # Propagate it to exactly self.clock
                        ac = propagate_aircraft(ac, dt=catch_up_dt, current_time=ac.position.timestamp)
                    caught_up_ac[ac.id] = ac
                self._aircraft = caught_up_ac
                self._last_live_ingest = status['last_success_at']

        sorted_ids = sorted(self._aircraft.keys())

        updated_aircraft: dict[str, Aircraft] = {}
        for ac_id in sorted_ids:
            current_ac = self._aircraft[ac_id]
            updated_ac = propagate_aircraft(current_ac, dt=step, current_time=self.clock)
            updated_aircraft[ac_id] = updated_ac

            # Record history
            if ac_id not in self._history:
                self._history[ac_id] = []
            self._history[ac_id].append(
                TrajectoryPoint(
                    position=updated_ac.position.model_copy(),
                    velocity=updated_ac.velocity.model_copy(),
                    time=self.clock + step,
                )
            )

        self._aircraft = updated_aircraft
        self.clock += step
        
        # Predict trajectories and detect conflicts
        pred_cfg = self.config.prediction.model_copy()
        if getattr(self, 'use_live_data', False):
            pred_cfg.horizon_sec = pred_cfg.live_horizon_sec
            
        trajectories = self.predictor.predict_all(self.aircraft, config=pred_cfg)
        
        # We need to detect conflicts and then apply persistence filtering if live
        raw_conflicts = self.detector.detect_conflicts(trajectories, self.clock)
        
        if getattr(self, 'use_live_data', False):
            self._conflicts = self.apply_conflict_persistence(raw_conflicts)
        else:
            self._conflicts = raw_conflicts

        return self.get_snapshot()

    def step(self, dt: Optional[float] = None) -> SimulationSnapshot:
        """Single-step the simulation (convenience method)."""
        return self.tick(dt)

    def apply_maneuver(self, aircraft_id: str, maneuver: Maneuver) -> bool:
        """Assign a resolution maneuver to a specific aircraft.

        Args:
            aircraft_id: Target aircraft ID.
            maneuver: Maneuver definition.

        Returns:
            True if maneuver was assigned, False if aircraft was not found.
        """
        ac = self._aircraft.get(aircraft_id)
        if ac is None:
            return False

        ac.assign_maneuver(maneuver)
        return True

    def get_recommendation_for_conflict(self, conflict_id: str) -> Optional[Recommendation]:
        """Generate, simulate, score, and recommend maneuvers for a conflict.
        
        This executes the full decision-support pipeline (Parts 8-12) on demand.
        """
        # Find the active conflict
        conflict = next((c for c in self._conflicts if c.id == conflict_id), None)
        if not conflict:
            return None
            
        # 1. Generate candidate maneuvers (Part 8)
        candidates = self.generator.generate_for_conflict(conflict, self._aircraft, self.clock)
        
        # 2. Simulate candidates (Part 9)
        simulated = []
        for cand in candidates:
            sim_cand = self.simulator.simulate_candidate(cand, self._conflicts, self._aircraft, self.clock)
            simulated.append(sim_cand)
            
        # 3. Score candidates deterministically (Part 10)
        scored = self.scorer.score_candidates(simulated)
        
        # 4. Enhance scores with ML (Part 12)
        enhanced = self.ml_scorer.enhance_scores(scored)
        
        # 5. Build final recommendation (Part 11)
        recommendation = self.recommender.generate_recommendation(conflict, enhanced)
        
        # 6. Generate GenAI explanation (Part 13)
        explanation = self.explainer.explain_recommendation(conflict, recommendation)
        recommendation.explanation = explanation
        
        return recommendation

    def get_actual_trajectory(self, aircraft_id: str) -> Optional[Trajectory]:
        """Get the recorded historical trajectory for an aircraft."""
        pts = self._history.get(aircraft_id)
        if pts is None:
            return None
        return Trajectory(
            aircraft_id=aircraft_id,
            points=[p.model_copy() for p in pts],
            trajectory_type=TrajectoryType.ACTUAL,
        )

    def get_snapshot(self, max_trail_points: int = 30) -> SimulationSnapshot:
        """Capture immutable state snapshot including recent trails."""
        trails: dict[str, list[list[float]]] = {}
        for ac_id, history in self._history.items():
            recent = history[-max_trail_points:] if len(history) > max_trail_points else history
            trails[ac_id] = [[round(pt.position.latitude, 5), round(pt.position.longitude, 5)] for pt in recent]

        # This is an additive presentation field: detection continues to use the
        # same predictor output and consumers that do not need it can ignore it.
        predicted_trajectories = {
            aircraft_id: [
                [round(point.position.latitude, 5), round(point.position.longitude, 5)]
                for point in trajectory.points
            ]
            for aircraft_id, trajectory in self.predictor.predict_all(self.aircraft).items()
        }

        return SimulationSnapshot(
            time=round(self.clock, 4),
            status=self.status,
            speed_multiplier=self.speed_multiplier,
            aircraft_count=len(self._aircraft),
            aircraft=[ac.model_copy(deep=True) for ac in self._aircraft.values()],
            trails=trails,
            predicted_trajectories=predicted_trajectories,
            conflicts=[c.model_copy(deep=True) for c in self._conflicts],
        )
