"""Scenario loader module.

Loads scripted and custom simulation scenarios from YAML files or dictionaries
into Aircraft and simulation state objects.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Union

import yaml
from pydantic import BaseModel, Field

from core.models.aircraft import Aircraft, AircraftStatus, FlightPlan, Position, Velocity


def parse_aircraft_dict(data: dict[str, Any], initial_time: float = 0.0) -> Aircraft:
    """Parse a single aircraft dictionary into an Aircraft instance."""
    pos_data = data.get("position", {})
    vel_data = data.get("velocity", {})
    fp_data = data.get("flight_plan", {})

    pos = Position(
        latitude=float(pos_data["lat"]),
        longitude=float(pos_data["lon"]),
        altitude=float(pos_data.get("alt", 35000.0)),
        timestamp=float(data.get("timestamp", initial_time)),
    )

    vel = Velocity(
        ground_speed=float(vel_data.get("ground_speed", vel_data.get("speed", 450.0))),
        vertical_speed=float(vel_data.get("vertical_speed", 0.0)),
        heading=float(vel_data["heading"]),
    )

    fp = FlightPlan(
        origin=fp_data.get("origin", "ZZZZ"),
        destination=fp_data.get("destination", "ZZZZ"),
        cruise_altitude=float(fp_data.get("cruise_altitude", pos.altitude)),
        cruise_speed=float(fp_data.get("cruise_speed", vel.ground_speed)),
    )

    return Aircraft(
        id=str(data.get("id", data.get("callsign", "AC_UNKNOWN"))),
        callsign=str(data.get("callsign", "UNKNOWN")),
        aircraft_type=str(data.get("type", data.get("aircraft_type", "A320"))),
        position=pos,
        velocity=vel,
        flight_plan=fp,
        status=AircraftStatus(data.get("status", "ACTIVE")),
    )


class Scenario:
    """Loaded scenario containing metadata and initial aircraft states."""

    def __init__(
        self,
        name: str,
        description: str,
        aircraft: list[Aircraft],
        initial_time: float = 0.0,
    ) -> None:
        self.name = name
        self.description = description
        self.initial_aircraft = aircraft
        self.initial_time = initial_time

    def create_aircraft_instances(self) -> list[Aircraft]:
        """Return fresh deep copies of all initial aircraft."""
        return [ac.model_copy(deep=True) for ac in self.initial_aircraft]


def load_scenario_from_dict(data: dict[str, Any]) -> Scenario:
    """Parse scenario from a raw dictionary."""
    name = str(data.get("name", "Unnamed Scenario"))
    description = str(data.get("description", ""))
    initial_time = float(data.get("initial_time", 0.0))
    raw_aircraft = data.get("aircraft", [])

    aircraft_list = [parse_aircraft_dict(item, initial_time=initial_time) for item in raw_aircraft]
    return Scenario(
        name=name,
        description=description,
        aircraft=aircraft_list,
        initial_time=initial_time,
    )


def load_scenario(scenario_path: Union[str, Path]) -> Scenario:
    """Load a scenario from a YAML file.

    Args:
        scenario_path: Path to the scenario YAML file.

    Returns:
        Loaded Scenario object.

    Raises:
        FileNotFoundError: If the scenario file does not exist.
        ValueError: If the YAML content is invalid.
    """
    path = Path(scenario_path)
    if not path.is_file():
        raise FileNotFoundError(f"Scenario file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Scenario file must contain a YAML mapping, got {type(data).__name__}")

    return load_scenario_from_dict(data)
