"""Conflict detection engine.

Analyzes predicted aircraft trajectories to identify potential
losses of separation within the configured horizon.
"""

from __future__ import annotations

import itertools

from core.models.config import SeparationConfig, SeverityConfig
from core.models.aircraft import Position
from core.models.trajectory import Trajectory
from core.models.conflict import Conflict, ConflictState, SeverityLevel
from core.geo.calculations import haversine_distance_nm
from core.detection.severity import SeverityAssessor


class ConflictDetector:
    """Detects predicted conflicts between aircraft."""

    def __init__(
        self,
        separation_config: SeparationConfig,
        severity_config: SeverityConfig,
    ) -> None:
        """Initialize the conflict detector.

        Args:
            separation_config: Configuration for separation thresholds.
            severity_config: Configuration for severity thresholds based on TTC.
        """
        self.separation_config = separation_config
        self.severity_config = severity_config
        self.assessor = SeverityAssessor(severity_config)

    def detect_conflicts(
        self, trajectories: dict[str, Trajectory], current_time: float
    ) -> list[Conflict]:
        """Detect all pairwise conflicts in a set of trajectories.

        Args:
            trajectories: Dictionary mapping aircraft ID to its predicted Trajectory.
            current_time: The current simulation time (detection timestamp).

        Returns:
            List of detected conflicts.
        """
        conflicts = []

        # Generate unique pairs of aircraft IDs to avoid duplicate A-B / B-A detection
        aircraft_ids = list(trajectories.keys())
        for id1, id2 in itertools.combinations(aircraft_ids, 2):
            traj1 = trajectories[id1]
            traj2 = trajectories[id2]

            conflict = self.analyze_pair(traj1, traj2, current_time)
            if conflict:
                # Assess severity deterministically
                assessed_conflict = self.assessor.assess(conflict)
                conflicts.append(assessed_conflict)

        return self.assessor.prioritize(conflicts)

    def analyze_pair(
        self, traj1: Trajectory, traj2: Trajectory, current_time: float
    ) -> Conflict | None:
        """Analyze a pair of trajectories for conflicts.

        We assume the trajectories have aligned timestamps (same step and start time).
        We iterate through the points and find the first threshold violation,
        as well as the closest point of approach (CPA).

        Args:
            traj1: First trajectory.
            traj2: Second trajectory.
            current_time: The current simulation time.

        Returns:
            A Conflict object if separation is lost, else None.
        """
        if not traj1.points or not traj2.points:
            return None

        # Create dictionaries to quickly lookup points by time for alignment
        points1_by_time = {p.time: p for p in traj1.points}
        points2_by_time = {p.time: p for p in traj2.points}

        common_times = sorted(set(points1_by_time.keys()).intersection(points2_by_time.keys()))

        if not common_times:
            return None

        initial_loss_time = None
        initial_loss_location = None
        
        min_horizontal_sep = float("inf")
        cpa_vertical_sep = float("inf")
        cpa_time = None
        
        # We track minimum 3D separation for CPA. Simple heuristic: prioritize horizontal, then vertical.
        # But closer horizontal is generally CPA.
        for t in common_times:
            p1 = points1_by_time[t]
            p2 = points2_by_time[t]

            horiz_dist_nm = haversine_distance_nm(
                p1.position.latitude,
                p1.position.longitude,
                p2.position.latitude,
                p2.position.longitude,
            )
            vert_dist_ft = abs(p1.position.altitude - p2.position.altitude)

            # Check if this point violates separation thresholds
            if (
                horiz_dist_nm < self.separation_config.horizontal_nm
                and vert_dist_ft < self.separation_config.vertical_ft
            ):
                if initial_loss_time is None:
                    initial_loss_time = t
                    # Calculate midpoint for location
                    mid_lat = (p1.position.latitude + p2.position.latitude) / 2.0
                    mid_lon = (p1.position.longitude + p2.position.longitude) / 2.0
                    mid_alt = (p1.position.altitude + p2.position.altitude) / 2.0
                    initial_loss_location = Position(
                        latitude=mid_lat,
                        longitude=mid_lon,
                        altitude=mid_alt,
                        timestamp=t,
                    )
            
            # Track CPA (Closest Point of Approach based on horizontal separation)
            if horiz_dist_nm < min_horizontal_sep:
                min_horizontal_sep = horiz_dist_nm
                cpa_vertical_sep = vert_dist_ft
                cpa_time = t

        if initial_loss_time is not None and initial_loss_location is not None and cpa_time is not None:
            ttc = max(0.0, initial_loss_time - current_time)
            
            # Generate a consistent ID for this pair and this conflict event
            # Use pair and rough TTC to identify the same conflict across ticks
            pair_id = "-".join(sorted([traj1.aircraft_id, traj2.aircraft_id]))
            conflict_id = f"CONF-{pair_id}"

            return Conflict(
                id=conflict_id,
                aircraft_1_id=traj1.aircraft_id,
                aircraft_2_id=traj2.aircraft_id,
                detection_timestamp=current_time,
                predicted_conflict_timestamp=initial_loss_time,
                time_to_conflict_sec=ttc,
                location=initial_loss_location,
                cpa_time=cpa_time,
                cpa_horizontal_separation_nm=min_horizontal_sep,
                cpa_vertical_separation_ft=cpa_vertical_sep,
                threshold_horizontal_nm=self.separation_config.horizontal_nm,
                threshold_vertical_ft=self.separation_config.vertical_ft,
                # severity is updated by assessor later
                state=ConflictState.DETECTED,
            )

        return None
