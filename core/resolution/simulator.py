"""Candidate Maneuver Simulation Engine.

Simulates each candidate maneuver in an isolated temporary state to evaluate
its potential effects on the original conflict and downstream airspace.
"""

from __future__ import annotations

import copy

from core.models.aircraft import Aircraft
from core.models.conflict import Conflict
from core.models.resolution import ResolutionCandidate, CandidateSimulationResult
from core.detection.predictor import TrajectoryPredictor
from core.detection.detector import ConflictDetector
from core.geo.calculations import haversine_distance_nm


class CandidateSimulator:
    """Evaluates candidate maneuvers without modifying live state."""

    def __init__(
        self,
        predictor: TrajectoryPredictor,
        detector: ConflictDetector,
    ) -> None:
        """Initialize the simulator.

        Args:
            predictor: The trajectory predictor.
            detector: The conflict detector.
        """
        self.predictor = predictor
        self.detector = detector

    def simulate_candidate(
        self,
        candidate: ResolutionCandidate,
        current_conflicts: list[Conflict],
        aircraft_states: dict[str, Aircraft],
        current_time: float,
    ) -> ResolutionCandidate:
        """Simulate a candidate maneuver and populate its simulation_result.

        Args:
            candidate: The maneuver candidate to evaluate.
            current_conflicts: List of currently active conflicts (for baseline).
            aircraft_states: Dictionary of all live aircraft states.
            current_time: The current simulation time.

        Returns:
            The mutated candidate with simulation_result attached.
        """
        if not candidate.is_valid:
            # Don't simulate rejected/invalid candidates
            return candidate

        # We must NOT mutate live state. Deep copy only the aircraft we are modifying.
        # But wait, predict_all needs all aircraft. We can shallow copy the dict,
        # and deep copy the specific aircraft we modify.
        if candidate.aircraft_id not in aircraft_states:
            candidate.is_valid = False
            candidate.rejection_reason = "Target aircraft not found in state."
            return candidate
            
        sim_states = aircraft_states.copy()
        
        # Isolate the target aircraft
        target_ac = sim_states[candidate.aircraft_id].model_copy(deep=True)
        
        # Apply the maneuver
        target_ac.assign_maneuver(candidate.maneuver)
        sim_states[target_ac.id] = target_ac
        
        # Predict trajectories for the entire airspace
        trajectories = self.predictor.predict_all(list(sim_states.values()))
        
        # Detect conflicts on the new predicted trajectories
        sim_conflicts = self.detector.detect_conflicts(trajectories, current_time)
        
        # Find the original conflict we were trying to resolve
        # We identify it by matching aircraft IDs (since conflict ID contains them)
        original_conflict = next((c for c in current_conflicts if c.id == candidate.conflict_id), None)
        
        if not original_conflict:
            candidate.is_valid = False
            candidate.rejection_reason = "Original conflict not found."
            return candidate
            
        other_ac_id = (
            original_conflict.aircraft_1_id 
            if original_conflict.aircraft_2_id == candidate.aircraft_id 
            else original_conflict.aircraft_2_id
        )
        
        # Check if original conflict is still present in sim_conflicts
        # (detector normalizes pair IDs in CONF-A-B format)
        is_resolved = not any(
            (c.aircraft_1_id == candidate.aircraft_id and c.aircraft_2_id == other_ac_id) or
            (c.aircraft_2_id == candidate.aircraft_id and c.aircraft_1_id == other_ac_id)
            for c in sim_conflicts
        )
        
        # Find new downstream conflicts
        current_conflict_ids = {c.id for c in current_conflicts}
        new_conflicts = [c for c in sim_conflicts if c.id not in current_conflict_ids]
        remaining_conflicts = [c for c in sim_conflicts if c.id in current_conflict_ids and c.id != candidate.conflict_id]
        
        # Calculate minimum separation achieved with the specific conflicting aircraft
        min_h, min_v = self._calculate_cpa(trajectories, candidate.aircraft_id, other_ac_id)
        
        # Create simulation result
        candidate.simulation_result = CandidateSimulationResult(
            original_conflict_resolved=is_resolved,
            remaining_conflicts=remaining_conflicts,
            new_conflicts=new_conflicts,
            min_horizontal_separation_nm=min_h,
            min_vertical_separation_ft=min_v,
        )
        
        if not is_resolved:
            candidate.is_valid = False
            candidate.rejection_reason = "Maneuver does not resolve the conflict."
            
        return candidate

    def _calculate_cpa(
        self, trajectories: dict[str, any], ac1_id: str, ac2_id: str
    ) -> tuple[float, float]:
        """Calculate the closest point of approach (horizontal, vertical) between two trajectories."""
        if ac1_id not in trajectories or ac2_id not in trajectories:
            return 0.0, 0.0
            
        traj1 = trajectories[ac1_id]
        traj2 = trajectories[ac2_id]
        
        if not traj1.points or not traj2.points:
            return 0.0, 0.0
            
        points1_by_time = {p.time: p for p in traj1.points}
        points2_by_time = {p.time: p for p in traj2.points}
        common_times = sorted(set(points1_by_time.keys()).intersection(points2_by_time.keys()))
        
        if not common_times:
            return 0.0, 0.0
            
        min_horizontal_sep = float("inf")
        cpa_vertical_sep = float("inf")
        
        for t in common_times:
            p1 = points1_by_time[t]
            p2 = points2_by_time[t]

            horiz_dist_nm = haversine_distance_nm(
                p1.position.latitude, p1.position.longitude,
                p2.position.latitude, p2.position.longitude,
            )
            vert_dist_ft = abs(p1.position.altitude - p2.position.altitude)
            
            if horiz_dist_nm < min_horizontal_sep:
                min_horizontal_sep = horiz_dist_nm
                cpa_vertical_sep = vert_dist_ft
                
        return min_horizontal_sep, cpa_vertical_sep
