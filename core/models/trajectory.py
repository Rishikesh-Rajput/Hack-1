"""Trajectory data models.

Represents time-indexed sequences of aircraft positions,
used for predicted, actual, and maneuver trajectories.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from core.models.aircraft import Position, Velocity


class TrajectoryType(str, Enum):
    """Type of trajectory."""

    PREDICTED = "PREDICTED"    # Extrapolated from current state
    ACTUAL = "ACTUAL"          # Recorded actual positions
    MANEUVER = "MANEUVER"      # Trajectory resulting from a candidate maneuver


class TrajectoryPoint(BaseModel):
    """A single point in a trajectory.

    Combines position, velocity, and time for a specific
    point along a trajectory.
    """

    position: Position = Field(description="Geographic position at this point")
    velocity: Velocity = Field(description="Velocity at this point")
    time: float = Field(ge=0.0, description="Simulation time in seconds")
    horizontal_uncertainty_nm: float = Field(
        default=0.0, ge=0.0, description="Positional uncertainty radius in NM"
    )
    vertical_uncertainty_ft: float = Field(
        default=0.0, ge=0.0, description="Altitude uncertainty bound in feet"
    )


class Trajectory(BaseModel):
    """A time-indexed sequence of trajectory points.

    Represents the path of an aircraft over time, whether
    predicted, actual, or resulting from a maneuver simulation.
    """

    aircraft_id: str = Field(description="ID of the aircraft this trajectory belongs to")
    points: list[TrajectoryPoint] = Field(
        default_factory=list, description="Time-ordered trajectory points"
    )
    trajectory_type: TrajectoryType = Field(
        default=TrajectoryType.PREDICTED, description="Type of this trajectory"
    )

    @property
    def start_time(self) -> float | None:
        """Time of the first point, or None if empty."""
        return self.points[0].time if self.points else None

    @property
    def end_time(self) -> float | None:
        """Time of the last point, or None if empty."""
        return self.points[-1].time if self.points else None

    @property
    def duration(self) -> float:
        """Duration of the trajectory in seconds."""
        if len(self.points) < 2:
            return 0.0
        return self.points[-1].time - self.points[0].time

    def __len__(self) -> int:
        return len(self.points)

    def __repr__(self) -> str:
        return (
            f"Trajectory(aircraft={self.aircraft_id}, "
            f"type={self.trajectory_type.value}, "
            f"points={len(self.points)}, "
            f"duration={self.duration:.1f}s)"
        )
