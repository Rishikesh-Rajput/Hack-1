"""Maneuver Generation module.

Deterministically generates resolution candidates (heading, altitude, speed)
for detected conflicts, based on configurable maneuver constraints.
"""

from __future__ import annotations

import uuid

from core.models.config import ManeuverConfig
from core.models.aircraft import Aircraft, Maneuver
from core.models.conflict import Conflict
from core.models.resolution import ResolutionCandidate


class ManeuverGenerator:
    """Generates candidate maneuvers to resolve conflicts."""

    def __init__(self, config: ManeuverConfig) -> None:
        """Initialize the generator.

        Args:
            config: Maneuver configuration defining deltas and limits.
        """
        self.config = config

    def generate_for_conflict(
        self, conflict: Conflict, aircraft_states: dict[str, Aircraft], current_time: float
    ) -> list[ResolutionCandidate]:
        """Generate resolution candidates for a specific conflict.

        Args:
            conflict: The detected conflict to resolve.
            aircraft_states: Dictionary of all current aircraft states.
            current_time: The simulation time when the maneuver would start.

        Returns:
            A list of ResolutionCandidate objects.
        """
        candidates: list[ResolutionCandidate] = []
        
        # Determine involved aircraft
        involved_ids = [conflict.aircraft_1_id, conflict.aircraft_2_id]
        
        for ac_id in involved_ids:
            if ac_id not in aircraft_states:
                continue
                
            ac = aircraft_states[ac_id]
            
            # Generate Heading Candidates
            for delta in self.config.heading_deltas:
                # Right turn (positive)
                candidates.append(
                    self._create_candidate(
                        conflict, ac, "HEADING", heading_change=delta, reason=f"Turn right {delta} deg"
                    )
                )
                # Left turn (negative)
                candidates.append(
                    self._create_candidate(
                        conflict, ac, "HEADING", heading_change=-delta, reason=f"Turn left {delta} deg"
                    )
                )
                
            # Generate Altitude Candidates
            for delta in self.config.altitude_deltas:
                # Climb (positive)
                candidates.append(
                    self._create_candidate(
                        conflict, ac, "ALTITUDE", altitude_change=delta, reason=f"Climb {delta} ft"
                    )
                )
                
                # Descend (negative)
                # Check minimum altitude constraint (e.g., must stay above 0, or some floor)
                if ac.position.altitude - delta >= 0:
                    candidates.append(
                        self._create_candidate(
                            conflict, ac, "ALTITUDE", altitude_change=-delta, reason=f"Descend {delta} ft"
                        )
                    )
                else:
                    rej = self._create_rejected_candidate(
                        conflict, ac, "ALTITUDE", altitude_change=-delta, reason=f"Descend {delta} ft",
                        rejection_reason="Altitude would fall below 0 ft"
                    )
                    candidates.append(rej)
                    
            # Generate Speed Candidates
            for pct in self.config.speed_deltas_pct:
                speed_delta = ac.velocity.ground_speed * (pct / 100.0)
                
                # Speed up
                candidates.append(
                    self._create_candidate(
                        conflict, ac, "SPEED", speed_change=speed_delta, reason=f"Increase speed by {pct}%"
                    )
                )
                
                # Slow down
                if ac.velocity.ground_speed - speed_delta >= 100.0: # Arbitrary prototype minimum speed (e.g. 100kt stall)
                    candidates.append(
                        self._create_candidate(
                            conflict, ac, "SPEED", speed_change=-speed_delta, reason=f"Decrease speed by {pct}%"
                        )
                    )
                else:
                    rej = self._create_rejected_candidate(
                        conflict, ac, "SPEED", speed_change=-speed_delta, reason=f"Decrease speed by {pct}%",
                        rejection_reason="Speed would fall below minimum 100kt"
                    )
                    candidates.append(rej)

        # Truncate to max candidates if needed (for now, return all valid + invalid so they can be inspected)
        # Sort deterministically by aircraft ID, then maneuver type, then value
        candidates.sort(key=lambda c: (
            c.aircraft_id,
            c.maneuver.type,
            c.maneuver.heading_change,
            c.maneuver.altitude_change,
            c.maneuver.speed_change
        ))
        
        # Only cap the valid ones, keep all invalid for transparency? The config says max_candidates
        # We will apply max_candidates limit to the valid ones to avoid combinatorial explosion in scoring.
        valid_cands = [c for c in candidates if c.is_valid]
        invalid_cands = [c for c in candidates if not c.is_valid]
        
        final_valid = valid_cands[:self.config.max_candidates]
        
        return final_valid + invalid_cands

    def _create_candidate(
        self,
        conflict: Conflict,
        ac: Aircraft,
        type_name: str,
        reason: str,
        heading_change: float = 0.0,
        altitude_change: float = 0.0,
        speed_change: float = 0.0,
    ) -> ResolutionCandidate:
        """Create a valid resolution candidate."""
        # Use deterministic ID based on properties
        m_id = f"CAND-{conflict.id}-{ac.id}-{type_name}-{heading_change}-{altitude_change}-{speed_change}"
        
        maneuver = Maneuver(
            type=type_name,
            heading_change=heading_change,
            altitude_change=altitude_change,
            speed_change=speed_change,
            start_time=conflict.detection_timestamp,
            duration=self.config.maneuver_duration_sec,
        )
        
        return ResolutionCandidate(
            id=m_id,
            conflict_id=conflict.id,
            aircraft_id=ac.id,
            maneuver=maneuver,
            reason=reason,
            is_valid=True
        )

    def _create_rejected_candidate(
        self,
        conflict: Conflict,
        ac: Aircraft,
        type_name: str,
        reason: str,
        rejection_reason: str,
        heading_change: float = 0.0,
        altitude_change: float = 0.0,
        speed_change: float = 0.0,
    ) -> ResolutionCandidate:
        """Create a rejected resolution candidate."""
        c = self._create_candidate(conflict, ac, type_name, reason, heading_change, altitude_change, speed_change)
        c.is_valid = False
        c.rejection_reason = rejection_reason
        return c
