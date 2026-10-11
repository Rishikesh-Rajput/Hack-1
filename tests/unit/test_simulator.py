"""Unit tests for Candidate Simulation Engine."""

import pytest

from core.models.config import ManeuverConfig, PredictionConfig, SeparationConfig, SeverityConfig
from core.models.aircraft import Aircraft, Position, Velocity, FlightPlan
from core.models.conflict import Conflict, ConflictState
from core.resolution.generator import ManeuverGenerator
from core.resolution.simulator import CandidateSimulator
from core.detection.predictor import TrajectoryPredictor
from core.detection.detector import ConflictDetector


@pytest.fixture
def predictor():
    config = PredictionConfig(horizon_sec=600.0, step_sec=10.0, max_points=100)
    return TrajectoryPredictor(config)

@pytest.fixture
def detector():
    sep_config = SeparationConfig(horizontal_nm=5.0, vertical_ft=1000.0)
    sev_config = SeverityConfig(critical_sec=120.0, high_sec=300.0, medium_sec=600.0, low_sec=900.0)
    return ConflictDetector(sep_config, sev_config)

@pytest.fixture
def generator():
    config = ManeuverConfig(
        heading_deltas=[30.0], # Use large delta to ensure resolution
        altitude_deltas=[2000.0],
        speed_deltas_pct=[], # Exclude to simplify tests
        maneuver_duration_sec=120.0,
        max_candidates=20
    )
    return ManeuverGenerator(config)

@pytest.fixture
def simulator(predictor, detector):
    return CandidateSimulator(predictor, detector)

def create_aircraft(id: str, lat: float, lon: float, alt: float, hdg: float, spd: float) -> Aircraft:
    return Aircraft(
        id=id,
        callsign=f"CS_{id}",
        position=Position(latitude=lat, longitude=lon, altitude=alt, timestamp=0.0),
        velocity=Velocity(ground_speed=spd, vertical_speed=0.0, heading=hdg),
        flight_plan=FlightPlan(origin="O", destination="D", cruise_altitude=alt, cruise_speed=spd)
    )

def test_simulator_resolves_conflict(generator, simulator, predictor, detector):
    # Head-on conflict setup
    ac1 = create_aircraft("A1", 0.0, 0.0, 35000.0, 90.0, 600.0)
    ac2 = create_aircraft("A2", 0.0, 0.33, 35000.0, 270.0, 600.0)
    
    # Run baseline detection
    trajs = predictor.predict_all([ac1, ac2])
    conflicts = detector.detect_conflicts(trajs, 0.0)
    assert len(conflicts) == 1
    
    c_orig = conflicts[0]
    
    # Generate candidates
    cands = generator.generate_for_conflict(c_orig, {"A1": ac1, "A2": ac2}, 0.0)
    
    # Pick the right-turn heading candidate for A1 (+30.0)
    cand = next(c for c in cands if c.aircraft_id == "A1" and c.maneuver.heading_change == 30.0)
    
    # Simulate
    states = {"A1": ac1, "A2": ac2}
    sim_cand = simulator.simulate_candidate(cand, conflicts, states, 0.0)
    
    res = sim_cand.simulation_result
    assert res is not None
    assert res.original_conflict_resolved is True
    assert sim_cand.is_valid is True
    assert len(res.new_conflicts) == 0
    assert res.min_horizontal_separation_nm >= 5.0 # Should be safe now

def test_simulator_does_not_mutate_live_state(generator, simulator, predictor, detector):
    ac1 = create_aircraft("A1", 0.0, 0.0, 35000.0, 90.0, 600.0)
    ac2 = create_aircraft("A2", 0.0, 0.33, 35000.0, 270.0, 600.0)
    
    trajs = predictor.predict_all([ac1, ac2])
    conflicts = detector.detect_conflicts(trajs, 0.0)
    
    cands = generator.generate_for_conflict(conflicts[0], {"A1": ac1, "A2": ac2}, 0.0)
    cand = cands[0]
    
    states = {"A1": ac1, "A2": ac2}
    simulator.simulate_candidate(cand, conflicts, states, 0.0)
    
    # Verify ac1 has not been modified
    assert ac1.assigned_maneuver is None
    assert ac1.is_maneuvering is False

def test_simulator_detects_downstream_conflict(generator, simulator, predictor, detector):
    ac1 = create_aircraft("A1", 0.0, 0.0, 35000.0, 90.0, 600.0)
    ac2 = create_aircraft("A2", 0.0, 0.33, 35000.0, 270.0, 600.0)
    # A3 is flying safely north of A1, but turning A1 right might hit it
    # Let's put A3 to the South-East so A1 runs into it after turning right (heading 120).
    # A1 is at 0,0, moving at 600kt. After turning 120, lat decreases, lon increases.
    ac3 = create_aircraft("A3", -0.1, 0.17, 35000.0, 0.0, 600.0)
    
    trajs = predictor.predict_all([ac1, ac2, ac3])
    # Baseline conflicts
    conflicts = detector.detect_conflicts(trajs, 0.0)
    c_a1a2 = next(c for c in conflicts if c.aircraft_1_id in ["A1", "A2"] and c.aircraft_2_id in ["A1", "A2"])
    
    cands = generator.generate_for_conflict(c_a1a2, {"A1": ac1, "A2": ac2, "A3": ac3}, 0.0)
    cand = next(c for c in cands if c.aircraft_id == "A1" and c.maneuver.heading_change == 30.0)
    
    states = {"A1": ac1, "A2": ac2, "A3": ac3}
    sim_cand = simulator.simulate_candidate(cand, conflicts, states, 0.0)
    
    res = sim_cand.simulation_result
    assert res is not None
    # We don't care exactly if it's new or remaining for this test's success, just that
    # the simulator correctly reports conflicts involving A3
    if res.original_conflict_resolved:
        has_a3_conflict = any(
            c.aircraft_1_id == "A3" or c.aircraft_2_id == "A3"
            for c in res.new_conflicts + res.remaining_conflicts
        )
        assert has_a3_conflict

def test_simulator_invalid_candidate(simulator):
    c = Conflict(
        id="CONF-A1-A2", aircraft_1_id="A1", aircraft_2_id="A2",
        detection_timestamp=0.0, predicted_conflict_timestamp=100.0,
        time_to_conflict_sec=100.0, location=Position(latitude=0, longitude=0, altitude=0, timestamp=0),
        cpa_time=0.0, cpa_horizontal_separation_nm=0.0, cpa_vertical_separation_ft=0.0,
        threshold_horizontal_nm=5.0, threshold_vertical_ft=1000.0, state=ConflictState.DETECTED
    )
    # Missing aircraft test
    from core.models.resolution import ResolutionCandidate
    from core.models.aircraft import Maneuver
    
    cand = ResolutionCandidate(
        id="bad", conflict_id="CONF-A1-A2", aircraft_id="A1", reason="test",
        maneuver=Maneuver(type="HEADING", duration=120, start_time=0.0)
    )
    
    res = simulator.simulate_candidate(cand, [c], {}, 0.0)
    assert res.is_valid is False
    assert "not found" in res.rejection_reason
