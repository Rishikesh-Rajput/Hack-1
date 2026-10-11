"""Resolution models.

Defines the structure of a resolution candidate proposed by the
maneuver generator for simulation and scoring.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from core.models.aircraft import Maneuver
from core.models.conflict import Conflict


class CandidateSimulationResult(BaseModel):
    """The simulated outcome of a candidate maneuver."""

    original_conflict_resolved: bool = Field(description="Whether the original conflict was successfully resolved")
    remaining_conflicts: list[Conflict] = Field(default_factory=list, description="List of unresolved pre-existing conflicts")
    new_conflicts: list[Conflict] = Field(default_factory=list, description="List of newly introduced downstream conflicts")
    min_horizontal_separation_nm: float = Field(description="Minimum horizontal separation achieved with the conflicting aircraft")
    min_vertical_separation_ft: float = Field(description="Minimum vertical separation achieved with the conflicting aircraft")
    max_cross_track_nm: float = Field(default=0.0, description="Max lateral deviation from original track")
    delay_sec: float = Field(default=0.0, description="Delay introduced compared to original unmaneuvered path")
    time_separation_restored: float | None = Field(default=None, description="Time at which separation is safely restored")


class ResolutionCandidate(BaseModel):
    """A proposed resolution for a detected conflict.
    
    This is a candidate action; it is not active until explicitly
    simulated, scored, and accepted.
    """

    id: str = Field(description="Unique candidate identifier")
    conflict_id: str = Field(description="ID of the conflict this attempts to resolve")
    aircraft_id: str = Field(description="ID of the aircraft to maneuver")
    maneuver: Maneuver = Field(description="The proposed maneuver details")
    reason: str = Field(description="Why this candidate was generated")
    
    # Simulation outcome
    simulation_result: CandidateSimulationResult | None = Field(default=None, description="Outcome of simulating this maneuver")
    
    # Scoring (populated in Part 10)
    safety_score: float | None = Field(default=None, description="Safety evaluation score")
    total_score: float | None = Field(default=None, description="Total aggregated score")
    is_valid: bool = Field(default=True, description="Whether this candidate is considered valid after simulation")
    rejection_reason: str | None = Field(default=None, description="Why this candidate was rejected (if invalid)")


class Recommendation(BaseModel):
    """Actionable recommendation for resolving a conflict."""

    id: str = Field(description="Unique recommendation ID")
    conflict_id: str = Field(description="ID of the conflict being resolved")
    status: str = Field(description="Status: e.g., 'RECOMMENDATION_AVAILABLE', 'NO_FEASIBLE_RECOMMENDATION'")
    primary_candidate: ResolutionCandidate | None = Field(default=None, description="The top recommended maneuver")
    alternative_candidates: list[ResolutionCandidate] = Field(default_factory=list, description="Alternative feasible maneuvers")
    explanation: str = Field(default="", description="Explanation of why this candidate is recommended and tradeoffs")
    warnings: list[str] = Field(default_factory=list, description="Any warnings, unresolved risks, or missing information")

class Decision(BaseModel):
    """A human controller's decision on a recommendation."""
    id: str = Field(description="Unique decision ID")
    recommendation_id: str = Field(description="The recommendation being reviewed")
    conflict_id: str = Field(description="The conflict being addressed")
    candidate_id: str | None = Field(default=None, description="The candidate selected, if any")
    action: str = Field(description="ACCEPT or REJECT")
    timestamp: float = Field(description="Simulation time when decided")
    reason: str | None = Field(default=None, description="Optional controller comment")
