"""REST API route handlers for ATCDS."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from backend.api.schemas import (
    LoadScenarioRequest,
    RegionResponse,
    ScenarioSummary,
    SimulationControlRequest,
)
from core.engine.scenario_loader import load_scenario
from core.engine.simulation import SimulationEngine, SimulationSnapshot

router = APIRouter(prefix="/api", tags=["simulation"])

# Global engine and scenario registry (injected on startup)
_engine: SimulationEngine | None = None
_scenarios_dir: Path = Path("config/scenarios")


def set_engine(engine: SimulationEngine) -> None:
    """Inject the singleton simulation engine instance."""
    global _engine
    _engine = engine


def get_engine() -> SimulationEngine:
    """Get the active engine instance."""
    if _engine is None:
        raise HTTPException(status_code=500, detail="Simulation engine not initialized")
    return _engine


@router.get("/scenarios", response_model=list[ScenarioSummary])
def list_scenarios() -> list[ScenarioSummary]:
    """List all available scenario files."""
    if not _scenarios_dir.is_dir():
        return []

    summaries: list[ScenarioSummary] = []
    for file in sorted(_scenarios_dir.glob("*.yaml")):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            summaries.append(
                ScenarioSummary(
                    id=file.stem,
                    name=data.get("name", file.stem),
                    description=data.get("description", ""),
                    aircraft_count=len(data.get("aircraft", [])),
                )
            )
        except Exception:
            continue
    return summaries


@router.post("/simulation/load", response_model=SimulationSnapshot)
def load_scenario_endpoint(req: LoadScenarioRequest) -> SimulationSnapshot:
    """Load a specific scenario into the simulation engine."""
    engine = get_engine()
    # Check if direct file or ID in scenarios dir
    scenario_path = _scenarios_dir / f"{req.scenario_id}.yaml"
    if not scenario_path.is_file():
        scenario_path = Path(req.scenario_id)
        if not scenario_path.is_file():
            raise HTTPException(status_code=404, detail=f"Scenario not found: {req.scenario_id}")

    try:
        scenario = load_scenario(scenario_path)
        engine.load_scenario(scenario)
        return engine.get_snapshot()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load scenario: {e}")


@router.post("/simulation/control", response_model=SimulationSnapshot)
def control_simulation(req: SimulationControlRequest) -> SimulationSnapshot:
    """Control simulation playback (play, pause, step, reset, speed)."""
    engine = get_engine()

    if req.speed is not None:
        engine.set_speed_multiplier(req.speed)

    if req.action == "play":
        engine.play()
    elif req.action == "pause":
        engine.pause()
    elif req.action == "step":
        engine.pause()
        engine.step()
    elif req.action == "live":
        engine.toggle_live_mode(True)
    elif req.action == "sim":
        engine.toggle_live_mode(False)
    elif req.action == "reset":
        engine.reset()

    return engine.get_snapshot()


@router.get("/simulation/state", response_model=SimulationSnapshot)
def get_simulation_state() -> SimulationSnapshot:
    """Get current snapshot of the simulation."""
    engine = get_engine()
    return engine.get_snapshot()


@router.get("/provider/status")
def get_provider_status() -> dict[str, Any]:
    """Live-provider health, freshness and count; never includes credentials."""
    return get_engine().get_live_provider_status()


@router.get("/region", response_model=RegionResponse)
def get_monitoring_region() -> RegionResponse:
    """Get active monitoring region geometry (region-agnostic config)."""
    engine = get_engine()
    region = engine.config.monitoring_region
    if region is None:
        raise HTTPException(status_code=404, detail="No monitoring region configured")

    return RegionResponse(
        name=region.name,
        polygon=[[lat, lon] for lat, lon in region.polygon],
        altitude_floor_ft=region.altitude_floor_ft,
        altitude_ceiling_ft=region.altitude_ceiling_ft,
        approach_buffer_nm=region.approach_buffer_nm,
    )

@router.get("/simulation/conflicts/{conflict_id}/recommendation")
def get_conflict_recommendation(conflict_id: str) -> Any:
    """Generate and return a resolution recommendation for a specific conflict."""
    engine = get_engine()
    rec = engine.get_recommendation_for_conflict(conflict_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Conflict {conflict_id} not found or no recommendation possible.")
    return rec

class AssistantQuery(BaseModel):
    query: str
    conflict_id: str | None = None

class AssistantResponse(BaseModel):
    answer: str

@router.post("/simulation/assistant", response_model=AssistantResponse)
def ask_assistant(req: AssistantQuery) -> AssistantResponse:
    """Ask the Controller AI Assistant a question."""
    engine = get_engine()
    
    # Gather context based on what's currently active
    context = {
        "active_conflicts": [c.model_dump() for c in engine.get_snapshot().conflicts],
        "system_time": engine.clock,
    }
    
    if req.conflict_id:
        rec = engine.get_recommendation_for_conflict(req.conflict_id)
        if rec:
            context["recommendation"] = rec.model_dump()
            
    answer = engine.explainer.answer_assistant_query(req.query, context)
    return AssistantResponse(answer=answer)

class DecisionRequest(BaseModel):
    recommendation_id: str
    conflict_id: str
    candidate_id: str | None = None
    action: str  # "ACCEPT" or "REJECT"
    reason: str | None = None

# In-memory store for prototype decisions
_decisions = []

@router.post("/simulation/decisions")
def record_decision(req: DecisionRequest):
    """Record a human controller's decision."""
    import uuid
    engine = get_engine()
    
    # Avoid duplicates
    if any(d.recommendation_id == req.recommendation_id and d.action == req.action for d in _decisions):
        raise HTTPException(status_code=400, detail="Decision already recorded.")
        
    decision = {
        "id": f"DEC-{uuid.uuid4().hex[:8]}",
        "recommendation_id": req.recommendation_id,
        "conflict_id": req.conflict_id,
        "candidate_id": req.candidate_id,
        "action": req.action,
        "timestamp": engine.clock,
        "reason": req.reason
    }
    
    _decisions.append(decision)
    return decision

@router.get("/simulation/decisions")
def get_decisions():
    """Retrieve decision history."""
    return _decisions

class EvaluationRequest(BaseModel):
    scenario_id: str

@router.post("/evaluation/run")
def run_evaluation(req: EvaluationRequest):
    """Run evaluation metrics on a scenario."""
    from core.metrics.evaluator import Evaluator
    
    scenario_path = _scenarios_dir / f"{req.scenario_id}.yaml"
    if not scenario_path.is_file():
        scenario_path = Path(req.scenario_id)
        if not scenario_path.is_file():
            raise HTTPException(status_code=404, detail=f"Scenario not found: {req.scenario_id}")
            
    evaluator = Evaluator()
    try:
        metrics = evaluator.evaluate_scenario(str(scenario_path))
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
