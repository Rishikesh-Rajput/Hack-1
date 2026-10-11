"""Pydantic schemas for REST API and WebSocket communication."""

from __future__ import annotations

from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

from core.engine.simulation import SimulationSnapshot, SimulationStatus
from core.models.aircraft import Aircraft


class ScenarioSummary(BaseModel):
    """Summary metadata of an available simulation scenario."""

    id: str = Field(description="Scenario identifier (filename without extension)")
    name: str = Field(description="Human-readable scenario title")
    description: str = Field(description="Detailed description")
    aircraft_count: int = Field(description="Number of aircraft in this scenario")


class LoadScenarioRequest(BaseModel):
    """Request payload to load a scenario."""

    scenario_id: str = Field(description="Identifier or path of scenario to load")


class SimulationControlRequest(BaseModel):
    """Request payload to control simulation playback."""

    action: Literal["play", "pause", "step", "reset", "live", "sim"] = Field(description="Playback action")
    speed: Optional[float] = Field(default=None, gt=0, description="Optional new speed multiplier")


class RegionResponse(BaseModel):
    """Active monitoring region definition sent to the frontend."""

    name: str
    polygon: list[list[float]]  # [[lat, lon], ...]
    altitude_floor_ft: float
    altitude_ceiling_ft: float
    approach_buffer_nm: float
