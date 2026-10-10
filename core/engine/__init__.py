"""Simulation engine for aircraft state management and time progression."""

from core.engine.simulation import (
    SimulationEngine,
    SimulationStatus,
    SimulationSnapshot,
)

# Alias for convenience
SimulationState = SimulationStatus

__all__ = [
    "SimulationEngine",
    "SimulationStatus",
    "SimulationState",
    "SimulationSnapshot",
]
