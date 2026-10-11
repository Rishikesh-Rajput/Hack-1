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
        self.predictor = predictor
        self.detector = detector

    def simulate_candidate(
        self,
        candidate: ResolutionCandidate,
        current_conflicts: list[Conflict],
        aircraft_states: dict[str, Aircraft],
        current_time: float,
        pred_cfg: any = None,
    ) -> ResolutionCandidate:
        if not candidate.is_valid:
            return candidate

        if candidate.aircraft_id not in aircraft_states:
            candidate.is_valid = False
            candidate.rejection_reason = "Target aircraft not found in state."
            return candidate
            
        sim_states = aircraft_states.copy()
        
        target_ac = sim_states[candidate.aircraft_id].model_copy(deep=True)
        # We need the unmaneuvered trajectory for cross track and delay calculations
        unmaneuvered_traj = self.predictor.predict(target_ac, config=pred_cfg)
        
        target_ac.assign_maneuver(candidate.maneuver)
        sim_states[target_ac.id] = target_ac
        
        trajectories = self.predictor.predict_all(list(sim_states.values()), config=pred_cfg)
        sim_conflicts = self.detector.detect_conflicts(trajectories, current_time)
        
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
        
        is_resolved = not any(
            (c.aircraft_1_id == candidate.aircraft_id and c.aircraft_2_id == other_ac_id) or
            (c.aircraft_2_id == candidate.aircraft_id and c.aircraft_1_id == other_ac_id)
            for c in sim_conflicts
        )
        
        current_conflict_ids = {c.id for c in current_conflicts}
        new_conflicts = [c for c in sim_conflicts if c.id not in current_conflict_ids]
        remaining_conflicts = [c for c in sim_conflicts if c.id in current_conflict_ids and c.id != candidate.conflict_id]
        
        min_h, min_v, time_restored = self._calculate_cpa_stats(trajectories, candidate.aircraft_id, other_ac_id)
        max_xt, delay = self._calculate_deviation_stats(unmaneuvered_traj, trajectories[candidate.aircraft_id])
        
        # Margin checks
        req_h = self.detector.separation_config.horizontal_nm + getattr(self.detector.separation_config, 'safety_margin_nm', 1.0)
        req_v = self.detector.separation_config.vertical_ft + getattr(self.detector.separation_config, 'safety_margin_ft', 0.0)
        
        candidate.simulation_result = CandidateSimulationResult(
            original_conflict_resolved=is_resolved,
            remaining_conflicts=remaining_conflicts,
            new_conflicts=new_conflicts,
            min_horizontal_separation_nm=min_h,
            min_vertical_separation_ft=min_v,
            max_cross_track_nm=max_xt,
            delay_sec=delay,
            time_separation_restored=time_restored,
        )
        
        if not is_resolved:
            candidate.is_valid = False
            candidate.rejection_reason = "Maneuver does not resolve the conflict."
        elif new_conflicts:
            candidate.is_valid = False
            candidate.rejection_reason = "Maneuver introduces new conflicts."
            
        return candidate

    def _calculate_cpa_stats(
        self, trajectories: dict[str, any], ac1_id: str, ac2_id: str
    ) -> tuple[float, float, float | None]:
        if ac1_id not in trajectories or ac2_id not in trajectories:
            return 0.0, 0.0, None
            
        traj1 = trajectories[ac1_id]
        traj2 = trajectories[ac2_id]
        
        points1_by_time = {p.time: p for p in traj1.points}
        points2_by_time = {p.time: p for p in traj2.points}
        common_times = sorted(set(points1_by_time.keys()).intersection(points2_by_time.keys()))
        
        if not common_times:
            return 0.0, 0.0, None
            
        min_horizontal_sep = float("inf")
        cpa_vertical_sep = float("inf")
        
        req_h = self.detector.separation_config.horizontal_nm
        req_v = self.detector.separation_config.vertical_ft
        
        time_restored = None
        in_conflict = False
        
        for t in common_times:
            p1 = points1_by_time[t]
            p2 = points2_by_time[t]

            horiz_dist_nm = haversine_distance_nm(
                p1.position.latitude, p1.position.longitude,
                p2.position.latitude, p2.position.longitude,
            )
            vert_dist_ft = abs(p1.position.altitude - p2.position.altitude)
            
            # Is there a violation?
            violation = (horiz_dist_nm < req_h) and (vert_dist_ft < req_v)
            if violation:
                in_conflict = True
                time_restored = None
            elif in_conflict and not violation and time_restored is None:
                time_restored = t
            
            if horiz_dist_nm < min_horizontal_sep:
                min_horizontal_sep = horiz_dist_nm
                cpa_vertical_sep = vert_dist_ft
                
        return min_horizontal_sep, cpa_vertical_sep, time_restored

    def _calculate_deviation_stats(
        self, unmaneuvered_traj: any, maneuvered_traj: any
    ) -> tuple[float, float]:
        """Calculates max cross-track error and delay.
        
        For a simplistic prototype, we find max distance between points at same time,
        and for delay, we could see if maneuvered aircraft reaches the final unmaneuvered
        point later, but since both run to horizon_sec, we compare final distance to end.
        """
        max_xt = 0.0
        
        points_u = {p.time: p for p in unmaneuvered_traj.points}
        points_m = {p.time: p for p in maneuvered_traj.points}
        common_times = sorted(set(points_u.keys()).intersection(points_m.keys()))
        
        for t in common_times:
            pu = points_u[t]
            pm = points_m[t]
            d = haversine_distance_nm(
                pu.position.latitude, pu.position.longitude,
                pm.position.latitude, pm.position.longitude
            )
            if d > max_xt:
                max_xt = d
                
        # Delay calculation: how much longer does it take to get to the same destination?
        # Since horizon is fixed, the maneuvered aircraft might cover less ground (delay > 0)
        # Delay (sec) ~= distance_behind (NM) / speed (NM/s)
        delay = 0.0
        if common_times:
            last_t = common_times[-1]
            pu = points_u[last_t]
            pm = points_m[last_t]
            dist_behind = haversine_distance_nm(
                pu.position.latitude, pu.position.longitude,
                pm.position.latitude, pm.position.longitude
            )
            spd_nm_s = pm.velocity.ground_speed / 3600.0
            if spd_nm_s > 0:
                delay = dist_behind / spd_nm_s
                
        return max_xt, delay
