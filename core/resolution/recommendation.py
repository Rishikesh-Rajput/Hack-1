"""Recommendation Engine.

Packages scored resolution candidates into actionable recommendations
for human-in-the-loop controllers.
"""

from __future__ import annotations

import uuid

from core.models.conflict import Conflict
from core.models.resolution import ResolutionCandidate, Recommendation


class RecommendationEngine:
    """Produces controller recommendations based on scored candidates."""

    def generate_recommendation(
        self, conflict: Conflict, scored_candidates: list[ResolutionCandidate]
    ) -> Recommendation:
        """Generate a recommendation for a given conflict.

        Args:
            conflict: The conflict being addressed.
            scored_candidates: The list of candidates, sorted by score descending.

        Returns:
            A populated Recommendation object.
        """
        rec_id = f"REC-{conflict.id}-{uuid.uuid4().hex[:8]}"
        
        valid_cands = [c for c in scored_candidates if c.is_valid]
        
        if not valid_cands:
            return Recommendation(
                id=rec_id,
                conflict_id=conflict.id,
                status="NO_FEASIBLE_RECOMMENDATION",
                explanation="No candidates were found that safely resolve the conflict without violating constraints.",
                warnings=["All generated maneuvers were either infeasible or introduced new downstream conflicts."]
            )
            
        primary = valid_cands[0]
        alternatives = valid_cands[1:4] # Top 3 alternatives
        
        # Build an explanation for the primary candidate
        maneuver_desc = ""
        if primary.maneuver.type == "HEADING":
            dir = "Right" if primary.maneuver.heading_change > 0 else "Left"
            maneuver_desc = f"Turn {dir} by {abs(primary.maneuver.heading_change)} degrees."
        elif primary.maneuver.type == "ALTITUDE":
            dir = "Climb" if primary.maneuver.altitude_change > 0 else "Descend"
            maneuver_desc = f"{dir} by {abs(primary.maneuver.altitude_change)} feet."
        elif primary.maneuver.type == "SPEED":
            dir = "Increase" if primary.maneuver.speed_change > 0 else "Decrease"
            maneuver_desc = f"{dir} speed by {abs(primary.maneuver.speed_change)} knots."
            
        explanation = (
            f"Recommended action for {primary.aircraft_id}: {maneuver_desc} "
            f"This safely resolves the conflict (Score: {round(primary.total_score or 0.0, 1)}/100). "
        )
        
        res = primary.simulation_result
        if res:
            explanation += f"Achieves {round(res.min_horizontal_separation_nm, 1)} NM horizontal separation."
            
        warnings = []
        if res and res.remaining_conflicts:
            warnings.append(f"Maneuver leaves {len(res.remaining_conflicts)} other pre-existing conflicts unresolved.")
        if primary.total_score and primary.total_score < 50.0:
            warnings.append("Primary candidate has a low safety margin or high penalty. Review carefully.")
            
        return Recommendation(
            id=rec_id,
            conflict_id=conflict.id,
            status="RECOMMENDATION_AVAILABLE",
            primary_candidate=primary,
            alternative_candidates=alternatives,
            explanation=explanation,
            warnings=warnings
        )
