"""Core data models for the ATCDS system."""

from core.models.aircraft import Aircraft, Position, Velocity, FlightPlan, AircraftStatus
from core.models.trajectory import Trajectory, TrajectoryPoint, TrajectoryType
from core.models.conflict import Conflict, ConflictState, SeverityLevel
from core.models.resolution import ResolutionCandidate
from core.models.config import (
    AppConfig,
    SimulationConfig,
    PredictionConfig,
    SeparationConfig,
    SeverityConfig,
    ManeuverConfig,
    ScoringWeights,
    MonitoringRegionConfig,
    GenAIConfig,
)

__all__ = [
    "Aircraft", "Position", "Velocity", "FlightPlan", "AircraftStatus", "Maneuver",
    "Trajectory", "TrajectoryPoint", "TrajectoryType",
    "Conflict", "ConflictState", "SeverityLevel",
    "ResolutionCandidate", "Recommendation",
    "AppConfig", "SimulationConfig", "PredictionConfig", "SeparationConfig",
    "SeverityConfig", "ManeuverConfig", "ScoringWeights",
    "MonitoringRegionConfig", "GenAIConfig",
]
