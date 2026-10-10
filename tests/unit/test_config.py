"""Unit tests for configuration loading and validation."""

from pathlib import Path
import pytest
from pydantic import ValidationError

from core.models.config import AppConfig, ScoringWeights, load_config


class TestConfig:
    def test_default_config_validity(self):
        cfg = AppConfig()
        assert cfg.simulation.time_step == 1.0
        assert cfg.separation.horizontal_nm == 5.0
        assert cfg.separation.vertical_ft == 1000.0

    def test_scoring_weights_sum_validation(self):
        # Valid weights summing to 1.0
        w = ScoringWeights(
            safety_margin=0.25,
            route_deviation=0.20,
            delay=0.15,
            fuel_cost=0.10,
            downstream_conflicts=0.20,
            maneuver_complexity=0.10,
        )
        assert w is not None

        # Invalid weights not summing to 1.0
        with pytest.raises(ValidationError):
            ScoringWeights(
                safety_margin=0.5,
                route_deviation=0.5,
                delay=0.5,
                fuel_cost=0.5,
                downstream_conflicts=0.5,
                maneuver_complexity=0.5,
            )

    def test_load_config_files(self):
        cfg = load_config(
            config_path="config/default.yaml",
            region_path="config/regions/india.yaml",
        )
        assert cfg.monitoring_region is not None
        assert cfg.monitoring_region.name.startswith("Indian Airspace")
        assert len(cfg.monitoring_region.polygon) >= 10
