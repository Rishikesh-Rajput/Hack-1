"""Unit tests verifying all scripted demo scenarios."""

from pathlib import Path
import pytest

from core.engine.scenario_loader import load_scenario
from core.engine.simulation import SimulationEngine


SCENARIO_FILES = [
    "config/scenarios/normal_traffic.yaml",
    "config/scenarios/head_on_conflict.yaml",
    "config/scenarios/crossing_conflict.yaml",
    "config/scenarios/overlapping_traffic.yaml",
]


class TestScenarioLoading:
    @pytest.mark.parametrize("scenario_path", SCENARIO_FILES)
    def test_scenario_loads_and_runs(self, scenario_path):
        path = Path(scenario_path)
        assert path.exists(), f"Scenario file missing: {scenario_path}"

        scenario = load_scenario(path)
        assert len(scenario.name) > 0
        assert len(scenario.initial_aircraft) >= 2

        # Verify engine runs for 15 steps with this scenario
        engine = SimulationEngine(scenario=scenario)
        engine.play()
        for _ in range(15):
            snap = engine.tick(dt=2.0)
            assert snap.aircraft_count == len(scenario.initial_aircraft)

        assert engine.current_time == pytest.approx(30.0)
