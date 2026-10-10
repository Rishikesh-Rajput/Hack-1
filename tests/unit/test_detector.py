"""Unit tests for the Conflict Detector."""

import pytest

from core.models.config import SeparationConfig, SeverityConfig, PredictionConfig
from core.models.aircraft import Aircraft, Position, Velocity, FlightPlan
from core.models.trajectory import TrajectoryType
from core.detection.predictor import TrajectoryPredictor
from core.detection.detector import ConflictDetector, SeverityLevel


@pytest.fixture
def predictor():
    config = PredictionConfig(horizon_sec=600.0, step_sec=10.0, max_points=100)
    return TrajectoryPredictor(config)

@pytest.fixture
def detector():
    sep_config = SeparationConfig(horizontal_nm=5.0, vertical_ft=1000.0)
    sev_config = SeverityConfig(critical_sec=120.0, high_sec=300.0, medium_sec=600.0, low_sec=900.0)
    return ConflictDetector(sep_config, sev_config)

def create_aircraft(id, lat, lon, alt, hdg, spd, vs=0.0):
    return Aircraft(
        id=id,
        callsign=f"CS_{id}",
        position=Position(latitude=lat, longitude=lon, altitude=alt, timestamp=0.0),
        velocity=Velocity(ground_speed=spd, vertical_speed=vs, heading=hdg),
        flight_plan=FlightPlan(origin="O", destination="D", cruise_altitude=alt, cruise_speed=spd)
    )

def test_head_on_conflict(predictor, detector):
    # Two aircraft facing each other 20 NM apart (about 0.33 degrees at equator)
    ac1 = create_aircraft("A1", 0.0, 0.0, 35000.0, 90.0, 600.0)
    ac2 = create_aircraft("A2", 0.0, 0.33, 35000.0, 270.0, 600.0)
    
    trajectories = predictor.predict_all([ac1, ac2])
    conflicts = detector.detect_conflicts(trajectories, 0.0)
    
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.aircraft_1_id == "A1" or c.aircraft_2_id == "A1"
    assert c.cpa_vertical_separation_ft == 0.0
    assert c.time_to_conflict_sec > 0.0

def test_crossing_conflict(predictor, detector):
    ac1 = create_aircraft("A1", 0.0, 0.0, 35000.0, 90.0, 600.0)
    ac2 = create_aircraft("A2", -0.165, 0.165, 35000.0, 0.0, 600.0)
    
    trajectories = predictor.predict_all([ac1, ac2])
    conflicts = detector.detect_conflicts(trajectories, 0.0)
    
    assert len(conflicts) == 1
    assert conflicts[0].severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]

def test_altitude_separation_no_conflict(predictor, detector):
    # Same horizontal path, but 2000 ft apart
    ac1 = create_aircraft("A1", 0.0, 0.0, 35000.0, 90.0, 600.0)
    ac2 = create_aircraft("A2", 0.0, 0.33, 37000.0, 270.0, 600.0)
    
    trajectories = predictor.predict_all([ac1, ac2])
    conflicts = detector.detect_conflicts(trajectories, 0.0)
    
    assert len(conflicts) == 0

def test_climbing_conflict(predictor, detector):
    # ac1 cruising, ac2 climbing into its path
    ac1 = create_aircraft("A1", 0.0, 0.0, 35000.0, 90.0, 600.0)
    ac2 = create_aircraft("A2", 0.0, 0.33, 34000.0, 270.0, 600.0, vs=1000.0)
    # Give ac2 a high cruise altitude so it keeps climbing
    ac2.flight_plan.cruise_altitude = 40000.0
    
    trajectories = predictor.predict_all([ac1, ac2])
    conflicts = detector.detect_conflicts(trajectories, 0.0)
    
    assert len(conflicts) == 1

def test_parallel_safe(predictor, detector):
    # Flying same direction, separated by 10 NM
    ac1 = create_aircraft("A1", 0.0, 0.0, 35000.0, 90.0, 600.0)
    ac2 = create_aircraft("A2", 0.165, 0.0, 35000.0, 90.0, 600.0)
    
    trajectories = predictor.predict_all([ac1, ac2])
    conflicts = detector.detect_conflicts(trajectories, 0.0)
    
    assert len(conflicts) == 0

def test_temporally_separated(predictor, detector):
    # Crossing same point but at different times
    ac1 = create_aircraft("A1", 0.0, 0.0, 35000.0, 90.0, 600.0)
    # A2 starts further south, same speed, crosses the equator way later
    ac2 = create_aircraft("A2", -1.0, 0.165, 35000.0, 0.0, 600.0)
    
    trajectories = predictor.predict_all([ac1, ac2])
    conflicts = detector.detect_conflicts(trajectories, 0.0)
    
    assert len(conflicts) == 0

def test_multiple_aircraft(predictor, detector):
    ac1 = create_aircraft("A1", 0.0, 0.0, 35000.0, 90.0, 600.0)
    ac2 = create_aircraft("A2", 0.0, 0.33, 35000.0, 270.0, 600.0)
    ac3 = create_aircraft("A3", -0.165, 0.165, 35000.0, 0.0, 600.0)
    
    trajectories = predictor.predict_all([ac1, ac2, ac3])
    conflicts = detector.detect_conflicts(trajectories, 0.0)
    
    # 3 aircraft meeting at the center: A1-A2, A1-A3, A2-A3
    assert len(conflicts) == 3

def test_duplicate_pair_prevention(predictor, detector):
    ac1 = create_aircraft("A1", 0.0, 0.0, 35000.0, 90.0, 600.0)
    ac2 = create_aircraft("A2", 0.0, 0.33, 35000.0, 270.0, 600.0)
    
    trajectories = predictor.predict_all([ac1, ac2])
    # Detector combinations guarantees A-B only checked once
    conflicts = detector.detect_conflicts(trajectories, 0.0)
    
    assert len(conflicts) == 1
    
    involved = conflicts[0].involved_aircraft
    assert involved == ("A1", "A2")

def test_invalid_input(detector):
    # Empty trajectories
    assert detector.detect_conflicts({}, 0.0) == []
