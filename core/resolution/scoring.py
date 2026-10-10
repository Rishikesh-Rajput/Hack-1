"""Maneuver Scoring Engine.

Evaluates simulated candidates based on configurable weights and penalizes
unsafe or infeasible maneuvers.
"""

from __future__ import annotations

from core.models.config import ScoringWeights, SeparationConfig
from core.models.resolution import ResolutionCandidate


class ManeuverScorer:
    """Scores candidate maneuvers based on simulation outcomes."""

    def __init__(self, weights: ScoringWeights, separation_config: SeparationConfig) -> None:
        """Initialize scorer with configuration.

        Args:
            weights: The relative weights for different scoring criteria.
            separation_config: Separation thresholds for margin normalization.
        """
        self.weights = weights
        self.separation_config = separation_config

    def score_candidates(self, candidates: list[ResolutionCandidate]) -> list[ResolutionCandidate]:
        """Score a list of candidates and sort them.

        Args:
            candidates: Candidates with simulation_result attached.

        Returns:
            The sorted list of scored candidates.
        """
        for cand in candidates:
            if not cand.is_valid or not cand.simulation_result:
                cand.total_score = 0.0
                cand.safety_score = 0.0
                continue

            res = cand.simulation_result

            # 1. Safety Margin Score
            # Based on how much separation we achieved over the minimum.
            # Max score if we double the required separation.
            h_margin = min(2.0, res.min_horizontal_separation_nm / self.separation_config.horizontal_nm)
            v_margin = min(2.0, res.min_vertical_separation_ft / self.separation_config.vertical_ft)
            # Combine margins (0.0 to 1.0 roughly, assuming hitting the target = 0.5)
            # We map target separation to 0.5, double separation to 1.0
            h_score = h_margin / 2.0
            v_score = v_margin / 2.0
            safety_score = max(h_score, v_score) * 100.0
            cand.safety_score = safety_score

            # 2. Downstream Conflicts Penalty
            # Severe penalty for introducing new conflicts
            downstream_penalty = len(res.new_conflicts) * 50.0

            # 3. Route Deviation & Maneuver Complexity (Heuristic proxy)
            # Larger heading/altitude changes get lower scores in this category.
            # E.g. heading: 30 deg vs 15 deg. Max deviation considered is 90 deg.
            m = cand.maneuver
            if m.type == "HEADING":
                deviation_penalty = (abs(m.heading_change) / 90.0) * 100.0
                complexity_penalty = 10.0
            elif m.type == "ALTITUDE":
                deviation_penalty = (abs(m.altitude_change) / 4000.0) * 100.0
                complexity_penalty = 20.0
            elif m.type == "SPEED":
                deviation_penalty = (abs(m.speed_change) / 100.0) * 100.0
                complexity_penalty = 5.0
            else:
                deviation_penalty = 50.0
                complexity_penalty = 30.0
                
            deviation_score = max(0.0, 100.0 - deviation_penalty)
            complexity_score = max(0.0, 100.0 - complexity_penalty)
            
            # Fuel & Delay (Placeholder heuristics based on maneuver type)
            fuel_score = 100.0 if m.type != "SPEED" else 50.0 # Speed changes waste fuel or time
            delay_score = 100.0 if m.type != "HEADING" else 60.0 # Heading changes increase track miles

            # Combine using weights
            raw_score = (
                (safety_score * self.weights.safety_margin) +
                (deviation_score * self.weights.route_deviation) +
                (delay_score * self.weights.delay) +
                (fuel_score * self.weights.fuel_cost) +
                (complexity_score * self.weights.maneuver_complexity)
            )
            
            # Apply penalties
            if downstream_penalty > 0:
                raw_score -= (downstream_penalty * self.weights.downstream_conflicts)
                
            if not res.original_conflict_resolved:
                # If we didn't resolve the original, it's effectively a failed candidate.
                cand.is_valid = False
                cand.rejection_reason = "Failed to resolve primary conflict."
                cand.total_score = 0.0
            else:
                # Floor at 0.0
                cand.total_score = max(0.0, raw_score)

        # Sort valid candidates by score descending
        valid = [c for c in candidates if c.is_valid]
        invalid = [c for c in candidates if not c.is_valid]
        
        valid.sort(key=lambda c: (c.total_score or 0.0), reverse=True)
        return valid + invalid
