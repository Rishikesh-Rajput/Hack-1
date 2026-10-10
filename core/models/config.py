"""Configuration models for the ATCDS system.

All simulation parameters are defined here as Pydantic models.
Values are loaded from YAML configuration files and validated at startup.

IMPORTANT: All threshold values are configurable prototype defaults,
NOT certified aviation separation standards.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator


class SimulationConfig(BaseModel):
    """Core simulation parameters."""

    time_step: float = Field(default=1.0, gt=0, description="Simulation time step in seconds")
    speed_multiplier: float = Field(default=1.0, gt=0, description="Simulation speed multiplier")
    max_aircraft: int = Field(default=50, gt=0, description="Maximum number of aircraft")


class PredictionConfig(BaseModel):
    """Trajectory prediction parameters."""

    horizon_sec: float = Field(default=900.0, gt=0, description="Prediction horizon in seconds (default: 15 min)")
    live_horizon_sec: float = Field(default=180.0, gt=0, description="Live prediction horizon in seconds (default: 3 min)")
    vertical_prediction_duration_sec: float = Field(default=60.0, ge=0, description="Duration to project vertical rate")
    step_sec: float = Field(default=5.0, gt=0, description="Prediction time step in seconds")
    max_points: int = Field(default=300, gt=0, description="Maximum number of points in predicted trajectory")


class SeparationConfig(BaseModel):
    """Separation thresholds for conflict detection.

    NOTE: These are configurable prototype values,
    NOT certified aviation separation standards.
    """

    horizontal_nm: float = Field(default=5.0, gt=0, description="Horizontal separation minimum in NM")
    vertical_ft: float = Field(default=1000.0, gt=0, description="Vertical separation minimum in feet")
    persistence_required_updates: int = Field(default=3, ge=1, description="Consecutive updates required for persistent alert")


class SeverityConfig(BaseModel):
    """Severity level thresholds based on time-to-conflict (TTC).

    TTC thresholds in seconds. A conflict with TTC below a threshold
    is classified at that severity level.
    """

    critical_sec: float = Field(default=120.0, gt=0, description="CRITICAL: TTC < this value")
    high_sec: float = Field(default=300.0, gt=0, description="HIGH: TTC < this value")
    medium_sec: float = Field(default=600.0, gt=0, description="MEDIUM: TTC < this value")
    low_sec: float = Field(default=900.0, gt=0, description="LOW: TTC <= prediction horizon")


class ManeuverConfig(BaseModel):
    """Parameters for candidate maneuver generation."""

    heading_deltas: list[float] = Field(default=[15.0, 30.0], description="Heading change options in degrees")
    altitude_deltas: list[float] = Field(default=[1000.0, 2000.0], description="Altitude change options in feet")
    speed_deltas_pct: list[float] = Field(default=[5.0, 10.0], description="Speed change options as percentage")
    hold_options_sec: list[float] = Field(default=[60.0, 120.0, 180.0, 240.0, 300.0], description="Hold durations")
    maneuver_duration_sec: float = Field(default=120.0, gt=0, description="Default maneuver duration in seconds")
    max_candidates: int = Field(default=10, gt=0, description="Maximum candidates to generate per conflict")
    turn_rate_deg_s: float = Field(default=3.0, gt=0, description="Turn rate in degrees per second")
    climb_rate_fpm: float = Field(default=1500.0, gt=0, description="Climb rate in feet per minute")
    safety_margin_nm: float = Field(default=1.0, ge=0, description="Extra horizontal safety margin")
    safety_margin_ft: float = Field(default=0.0, ge=0, description="Extra vertical safety margin")


class ScoringWeights(BaseModel):
    """Weights for multi-criteria candidate scoring.

    All weights should sum to 1.0.
    """

    safety_margin: float = Field(default=0.25, ge=0, le=1)
    route_deviation: float = Field(default=0.20, ge=0, le=1)
    delay: float = Field(default=0.15, ge=0, le=1)
    fuel_cost: float = Field(default=0.10, ge=0, le=1)
    downstream_conflicts: float = Field(default=0.20, ge=0, le=1)
    maneuver_complexity: float = Field(default=0.10, ge=0, le=1)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> ScoringWeights:
        """Validate that all weights sum to approximately 1.0."""
        total = (
            self.safety_margin
            + self.route_deviation
            + self.delay
            + self.fuel_cost
            + self.downstream_conflicts
            + self.maneuver_complexity
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total:.4f}")
        return self


class MonitoringRegionConfig(BaseModel):
    """Configuration for the airspace monitoring region.

    The region is defined as a polygon (list of lat/lon vertices)
    with an altitude band and approach buffer.
    """

    name: str = Field(default="Indian Airspace", description="Human-readable region name")
    polygon: list[tuple[float, float]] = Field(
        description="Boundary vertices as (latitude, longitude) pairs"
    )
    altitude_floor_ft: float = Field(default=0.0, ge=0, description="Altitude floor in feet")
    altitude_ceiling_ft: float = Field(default=60000.0, gt=0, description="Altitude ceiling in feet")
    approach_buffer_nm: float = Field(default=50.0, ge=0, description="Approach detection buffer in NM")


class GenAIConfig(BaseModel):
    """Configuration for GenAI explanation generation."""

    model: str = Field(default="gemini-2.0-flash", description="GenAI model identifier")
    temperature: float = Field(default=0.3, ge=0, le=2.0)
    max_tokens: int = Field(default=300, gt=0)
    timeout_sec: float = Field(default=5.0, gt=0)
    fallback_enabled: bool = Field(default=True, description="Use template fallback if GenAI fails")
    api_key: str = Field(default="", description="API key (loaded from environment)")


class AppConfig(BaseModel):
    """Root application configuration.

    Aggregates all sub-configurations. Loaded from YAML files
    and validated at startup.
    """

    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    prediction: PredictionConfig = Field(default_factory=PredictionConfig)
    separation: SeparationConfig = Field(default_factory=SeparationConfig)
    severity: SeverityConfig = Field(default_factory=SeverityConfig)
    maneuver: ManeuverConfig = Field(default_factory=ManeuverConfig)
    scoring: ScoringWeights = Field(default_factory=ScoringWeights)
    monitoring_region: MonitoringRegionConfig | None = Field(
        default=None, description="Monitoring region (loaded from region file)"
    )
    genai: GenAIConfig = Field(default_factory=GenAIConfig)


def load_config(config_path: Path | str | None = None, region_path: Path | str | None = None) -> AppConfig:
    """Load application configuration from YAML files.

    Args:
        config_path: Path to main config YAML. If None, uses defaults.
        region_path: Path to monitoring region YAML. If None, region is not loaded.

    Returns:
        Validated AppConfig instance.
    """
    config_data: dict[str, Any] = {}

    if config_path is not None:
        config_path = Path(config_path)
        if config_path.exists():
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f) or {}

    if region_path is not None:
        region_path = Path(region_path)
        if region_path.exists():
            with open(region_path, "r") as f:
                region_data = yaml.safe_load(f) or {}
            config_data["monitoring_region"] = region_data

    return AppConfig(**config_data)
