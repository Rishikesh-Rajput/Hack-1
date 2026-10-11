"""Conflict data models.

Defines the structure of a detected conflict between two aircraft.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from core.models.aircraft import Position


class SeverityLevel(str, Enum):
    """Severity classification of a conflict."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class ConflictState(str, Enum):
    """Lifecycle state of a conflict."""

    DETECTED = "DETECTED"    # Newly detected
    ACTIVE = "ACTIVE"        # Still predicted
    RESOLVED = "RESOLVED"    # Was active, now resolved (maneuver applied)
    EXPIRED = "EXPIRED"      # No longer predicted (e.g. aircraft turned independently)


class Conflict(BaseModel):
    """A predicted conflict between two aircraft."""

    id: str = Field(description="Unique conflict ID (usually derived from AC IDs and time)")
    aircraft_1_id: str = Field(description="ID of first aircraft")
    aircraft_2_id: str = Field(description="ID of second aircraft")
    
    detection_timestamp: float = Field(description="Simulation time when conflict was detected")
    predicted_conflict_timestamp: float = Field(description="Simulation time of initial loss of separation")
    
    time_to_conflict_sec: float = Field(ge=0.0, description="Time until separation is lost (TTC)")
    
    location: Position = Field(description="Approximate location of the conflict (midpoint at initial loss)")
    
    # Closest Point of Approach (CPA)
    cpa_time: float = Field(description="Time of closest approach")
    cpa_horizontal_separation_nm: float = Field(ge=0.0, description="Horizontal separation at CPA")
    cpa_vertical_separation_ft: float = Field(ge=0.0, description="Vertical separation at CPA")
    
    # Thresholds applied
    threshold_horizontal_nm: float = Field(gt=0.0, description="Horizontal threshold used")
    threshold_vertical_ft: float = Field(gt=0.0, description="Vertical threshold used")
    
    severity: SeverityLevel = Field(default=SeverityLevel.UNKNOWN, description="Severity level based on TTC")
    severity_score: float = Field(default=0.0, description="Numerical severity score (0-100, higher is worse)")
    severity_factors: list[str] = Field(default_factory=list, description="List of factors contributing to severity")
    severity_explanation: str = Field(default="", description="Human-readable explanation of the severity")
    state: ConflictState = Field(default=ConflictState.DETECTED, description="Current lifecycle state")
    
    @property
    def involved_aircraft(self) -> tuple[str, str]:
        """Return a sorted tuple of involved aircraft IDs."""
        return tuple(sorted([self.aircraft_1_id, self.aircraft_2_id]))

    def __repr__(self) -> str:
        return (
            f"Conflict({self.aircraft_1_id} vs {self.aircraft_2_id}, "
            f"TTC={self.time_to_conflict_sec:.0f}s, "
            f"Sev={self.severity.value})"
        )
