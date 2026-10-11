"""Command line interface for ATCDS simulation runner.

Allows running and observing the simulation directly from the terminal
without starting any web server.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from core.engine.scenario_loader import load_scenario
from core.engine.simulation import SimulationEngine
from core.models.config import load_config


def main() -> None:
    """CLI entry point for running simulation scenarios."""
    parser = argparse.ArgumentParser(
        description="AI-Based Air Traffic Conflict Resolution Decision Support - Simulation Runner"
    )
    parser.add_argument(
        "--scenario",
        "-s",
        type=str,
        default="config/scenarios/head_on_conflict.yaml",
        help="Path to scenario YAML file",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="config/default.yaml",
        help="Path to master config YAML file",
    )
    parser.add_argument(
        "--region",
        "-r",
        type=str,
        default="config/regions/india.yaml",
        help="Path to monitoring region YAML file",
    )
    parser.add_argument(
        "--steps",
        "-n",
        type=int,
        default=30,
        help="Number of simulation steps to run (default: 30)",
    )
    parser.add_argument(
        "--dt",
        type=float,
        default=5.0,
        help="Timestep per tick in seconds (default: 5.0)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="Delay between displayed steps in seconds (default: 0.1)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("ATCDS AIR TRAFFIC SIMULATION RUNNER (PART 3 PROTOTYPE)")
    print("=" * 80)

    # 1. Load config
    cfg_path = Path(args.config) if Path(args.config).is_file() else None
    reg_path = Path(args.region) if Path(args.region).is_file() else None
    app_config = load_config(config_path=cfg_path, region_path=reg_path)
    print(f"[Config] Loaded application config (dt={app_config.simulation.time_step}s)")
    if app_config.monitoring_region:
        print(f"[Region] Active monitoring region: {app_config.monitoring_region.name}")

    # 2. Load scenario
    scenario_path = Path(args.scenario)
    if not scenario_path.is_file():
        print(f"Error: Scenario file not found: {scenario_path}", file=sys.stderr)
        sys.exit(1)

    scenario = load_scenario(scenario_path)
    print(f"[Scenario] Loaded: '{scenario.name}'")
    print(f"           Description: {scenario.description}")
    print(f"           Initial Aircraft: {len(scenario.initial_aircraft)}")
    print("=" * 80)

    # 3. Initialize engine
    engine = SimulationEngine(config=app_config, scenario=scenario)
    engine.play()

    header = f"{'Time (s)':<10} | {'Callsign':<8} | {'Lat':<8} | {'Lon':<8} | {'Alt (ft)':<9} | {'Hdg':<5} | {'Spd (kt)':<8} | {'Status':<10}"
    print(header)
    print("-" * 80)

    for step in range(args.steps):
        snapshot = engine.tick(dt=args.dt)
        for ac in snapshot.aircraft:
            print(
                f"{snapshot.time:<10.1f} | "
                f"{ac.callsign:<8} | "
                f"{ac.position.latitude:<8.3f} | "
                f"{ac.position.longitude:<8.3f} | "
                f"{ac.position.altitude:<9.0f} | "
                f"{ac.velocity.heading:<5.0f} | "
                f"{ac.velocity.ground_speed:<8.0f} | "
                f"{ac.status.value:<10}"
            )
        if args.delay > 0:
            time.sleep(args.delay)

    print("=" * 80)
    print(f"Simulation completed {args.steps} steps successfully. Clock: {engine.current_time:.1f}s")


if __name__ == "__main__":
    main()
