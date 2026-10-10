import pytest
from core.metrics.evaluator import Evaluator
from pathlib import Path

def test_evaluator():
    evaluator = Evaluator()
    # Assuming config/scenarios/head_on_conflict.yaml exists
    scenario_path = Path("config/scenarios/head_on_conflict.yaml")
    
    if not scenario_path.exists():
        pytest.skip("Scenario file not found")
        
    metrics = evaluator.evaluate_scenario(str(scenario_path))
    
    assert "scenario" in metrics
    assert "total_aircraft" in metrics
    assert "processing_times_ms" in metrics
    assert "conflicts" in metrics
