"""Evaluation and metrics module.

Measures detection and resolution pipeline performance
using actual simulation outcomes.
"""

import time
from typing import Any
from core.engine.simulation import SimulationEngine
from core.models.config import load_config
from core.engine.scenario_loader import load_scenario
from pathlib import Path

class Evaluator:
    """Evaluates the ATCDS pipeline across scenarios."""

    def __init__(self, config_path: str | None = None):
        self.config = load_config(config_path)

    def evaluate_scenario(self, scenario_path: str) -> dict[str, Any]:
        """Runs a scenario and collects metrics."""
        engine = SimulationEngine(config=self.config)
        scenario = load_scenario(scenario_path)
        engine.load_scenario(scenario)
        
        metrics = {
            "scenario": scenario.name,
            "total_aircraft": len(scenario.initial_aircraft),
            "processing_times_ms": {},
            "conflicts": {},
            "resolutions": {}
        }
        
        # 1. Detection Evaluation
        start = time.perf_counter()
        # Propagate time to allow conflicts to form (e.g. 5 ticks)
        for _ in range(5):
            engine.tick()
        
        detect_time = (time.perf_counter() - start) * 1000
        snap = engine.get_snapshot()
        active_conflicts = snap.conflicts
        
        metrics["processing_times_ms"]["detection_and_propagation"] = round(detect_time, 2)
        metrics["conflicts"]["detected_count"] = len(active_conflicts)
        
        if not active_conflicts:
            return metrics
            
        # 2. Resolution Evaluation
        rec_start = time.perf_counter()
        
        total_candidates = 0
        valid_recommendations = 0
        infeasible_recommendations = 0
        
        for conflict in active_conflicts:
            rec = engine.get_recommendation_for_conflict(conflict.id)
            if rec:
                total_candidates += len(rec.alternative_candidates) + (1 if rec.primary_candidate else 0)
                if rec.status == "RECOMMENDATION_AVAILABLE":
                    valid_recommendations += 1
                else:
                    infeasible_recommendations += 1
                    
        rec_time = (time.perf_counter() - rec_start) * 1000
        
        metrics["processing_times_ms"]["scoring_and_recommendation"] = round(rec_time, 2)
        metrics["resolutions"]["feasible_count"] = valid_recommendations
        metrics["resolutions"]["infeasible_count"] = infeasible_recommendations
        metrics["resolutions"]["candidates_evaluated"] = total_candidates
        
        return metrics
