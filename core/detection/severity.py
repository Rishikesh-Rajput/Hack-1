"""Severity assessment module.

Evaluates detected conflicts and classifies their urgency
using measurable, deterministic criteria.
"""

from __future__ import annotations

from core.models.config import SeverityConfig
from core.models.conflict import Conflict, SeverityLevel


class SeverityAssessor:
    """Evaluates and scores conflict severity."""

    def __init__(self, severity_config: SeverityConfig) -> None:
        """Initialize the assessor.

        Args:
            severity_config: Configuration containing TTC thresholds.
        """
        self.config = severity_config

    def assess(self, conflict: Conflict) -> Conflict:
        """Assess a conflict, assigning a severity level, score, and explanation.
        
        Mutates the passed conflict object and returns it.
        """
        # Determine base severity level based on time-to-conflict (TTC)
        ttc = conflict.time_to_conflict_sec
        
        if ttc < self.config.critical_sec:
            level = SeverityLevel.CRITICAL
        elif ttc < self.config.high_sec:
            level = SeverityLevel.HIGH
        elif ttc < self.config.medium_sec:
            level = SeverityLevel.MEDIUM
        elif ttc <= self.config.low_sec:
            level = SeverityLevel.LOW
        else:
            level = SeverityLevel.UNKNOWN

        conflict.severity = level

        # Calculate a deterministic severity score (0 to 100)
        # Weights: TTC (60%), Horizontal CPA margin (20%), Vertical CPA margin (20%)
        # Lower TTC = higher score
        # Smaller CPA = higher score
        
        # Max horizon is typically low_sec (e.g., 900s)
        max_ttc = self.config.low_sec
        ttc_factor = max(0.0, (max_ttc - ttc) / max_ttc)
        
        h_margin = conflict.threshold_horizontal_nm
        cpa_h = conflict.cpa_horizontal_separation_nm
        h_factor = max(0.0, (h_margin - cpa_h) / h_margin)
        
        v_margin = conflict.threshold_vertical_ft
        cpa_v = conflict.cpa_vertical_separation_ft
        v_factor = max(0.0, (v_margin - cpa_v) / v_margin)
        
        score = (ttc_factor * 60.0) + (h_factor * 20.0) + (v_factor * 20.0)
        conflict.severity_score = round(score, 2)
        
        # Generate contributing factors and explanation
        factors = []
        if ttc < self.config.critical_sec:
            factors.append(f"TTC is critical ({round(ttc)}s)")
        elif ttc < self.config.high_sec:
            factors.append(f"TTC is high urgency ({round(ttc)}s)")
            
        if cpa_h < (h_margin * 0.5):
            factors.append(f"Severe horizontal infringement ({round(cpa_h, 1)} NM)")
        if cpa_v < (v_margin * 0.5):
            factors.append(f"Severe vertical infringement ({round(cpa_v)} ft)")
            
        if not factors:
            factors.append("Separation margins violated within prediction horizon")

        conflict.severity_factors = factors
        
        explanation = (
            f"Assessed as {level.value} severity (Score: {conflict.severity_score}). "
            f"Initial loss of separation in {round(ttc)}s. "
            f"Closest approach predicted at {round(conflict.cpa_time - conflict.detection_timestamp)}s "
            f"with {round(cpa_h, 1)} NM horizontal and {round(cpa_v)} ft vertical separation."
        )
        conflict.severity_explanation = explanation

        return conflict

    def prioritize(self, conflicts: list[Conflict]) -> list[Conflict]:
        """Sort conflicts deterministically by urgency.
        
        Sorting rules (in order of precedence):
        1. Severity Score (descending)
        2. Time-to-Conflict (ascending)
        3. Lexicographical order of Conflict ID (stable tie-breaker)
        """
        return sorted(
            conflicts,
            key=lambda c: (-c.severity_score, c.time_to_conflict_sec, c.id)
        )
