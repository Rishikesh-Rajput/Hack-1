"""Unit tests for the Maneuver Generator."""

import pytest

from core.models.config import ManeuverConfig
from core.models.aircraft import Aircraft, Position, Velocity, FlightPlan
from core.models.conflict import Conflict, ConflictState
from core.resolution.generator import ManeuverGenerator


@pytest.fixture
def generator():
    config = ManeuverConfig(
        heading_deltas=[15.0, 30.0],
        altitude_deltas=[1000.0],
        speed_deltas_pct=[10.0],
        maneuver_duration_sec=120.0,
        max_candidates=20
    )
    return ManeuverGenerator(config)

def create_aircraft(id: str, alt: float, spd: float) -> Aircraft:
    return Aircraft(
        id=id,
        callsign=f"CS_{id}",
        position=Position(latitude=0.0, longitude=0.0, altitude=alt, timestamp=0.0),
        velocity=Velocity(ground_speed=spd, vertical_speed=0.0, heading=90.0),
        flight_plan=FlightPlan(origin="O", destination="D", cruise_altitude=alt, cruise_speed=spd)
    )

def create_conflict(id1: str, id2: str) -> Conflict:
    return Conflict(
        id=f"CONF-{id1}-{id2}",
        aircraft_1_id=id1,
        aircraft_2_id=id2,
        detection_timestamp=0.0,
        predicted_conflict_timestamp=100.0,
        time_to_conflict_sec=100.0,
        location=Position(latitude=0.0, longitude=0.0, altitude=35000.0, timestamp=100.0),
        cpa_time=100.0,
        cpa_horizontal_separation_nm=2.0,
        cpa_vertical_separation_ft=500.0,
        threshold_horizontal_nm=5.0,
        threshold_vertical_ft=1000.0,
        state=ConflictState.DETECTED,
    )

def test_generate_heading_candidates(generator):
    ac1 = create_aircraft("A1", 35000.0, 600.0)
    conflict = create_conflict("A1", "A2")
    # Provide only A1 in the dict
    cands = generator.generate_for_conflict(conflict, {"A1": ac1}, 0.0)
    
    # Heading deltas: 15, 30 -> 4 candidates (left/right)
    heading_cands = [c for c in cands if c.maneuver.type == "HEADING" and c.is_valid]
    assert len(heading_cands) == 4
    
    changes = set(c.maneuver.heading_change for c in heading_cands)
    assert changes == {15.0, -15.0, 30.0, -30.0}

def test_generate_altitude_candidates(generator):
    ac1 = create_aircraft("A1", 35000.0, 600.0)
    conflict = create_conflict("A1", "A2")
    cands = generator.generate_for_conflict(conflict, {"A1": ac1}, 0.0)
    
    # Altitude deltas: 1000 -> 2 candidates (climb/descend)
    alt_cands = [c for c in cands if c.maneuver.type == "ALTITUDE" and c.is_valid]
    assert len(alt_cands) == 2
    changes = set(c.maneuver.altitude_change for c in alt_cands)
    assert changes == {1000.0, -1000.0}

def test_altitude_rejection(generator):
    # Aircraft too low to descend 1000 ft
    ac1 = create_aircraft("A1", 500.0, 600.0)
    conflict = create_conflict("A1", "A2")
    cands = generator.generate_for_conflict(conflict, {"A1": ac1}, 0.0)
    
    # Climb is valid
    valid_alt = [c for c in cands if c.maneuver.type == "ALTITUDE" and c.is_valid]
    assert len(valid_alt) == 1
    assert valid_alt[0].maneuver.altitude_change == 1000.0
    
    # Descend is rejected
    invalid_alt = [c for c in cands if c.maneuver.type == "ALTITUDE" and not c.is_valid]
    assert len(invalid_alt) == 1
    assert invalid_alt[0].maneuver.altitude_change == -1000.0
    assert "below 0" in invalid_alt[0].rejection_reason

def test_generate_speed_candidates(generator):
    ac1 = create_aircraft("A1", 35000.0, 600.0)
    conflict = create_conflict("A1", "A2")
    cands = generator.generate_for_conflict(conflict, {"A1": ac1}, 0.0)
    
    # Speed deltas: 10% of 600 -> 60 -> +60, -60
    spd_cands = [c for c in cands if c.maneuver.type == "SPEED" and c.is_valid]
    assert len(spd_cands) == 2
    changes = set(c.maneuver.speed_change for c in spd_cands)
    assert changes == {60.0, -60.0}

def test_speed_rejection(generator):
    # Aircraft speed 100, subtracting 10% (10kt) means speed 90kt which is < 100kt
    ac1 = create_aircraft("A1", 35000.0, 105.0)
    conflict = create_conflict("A1", "A2")
    cands = generator.generate_for_conflict(conflict, {"A1": ac1}, 0.0)
    
    spd_cands = [c for c in cands if c.maneuver.type == "SPEED"]
    invalid = [c for c in spd_cands if not c.is_valid]
    
    assert len(invalid) == 1
    assert "minimum 100kt" in invalid[0].rejection_reason

def test_multiple_aircraft(generator):
    ac1 = create_aircraft("A1", 35000.0, 600.0)
    ac2 = create_aircraft("A2", 35000.0, 500.0)
    conflict = create_conflict("A1", "A2")
    cands = generator.generate_for_conflict(conflict, {"A1": ac1, "A2": ac2}, 0.0)
    
    # Each aircraft should generate 4 heading, 2 alt, 2 speed = 8 candidates -> Total 16 valid candidates
    valid_cands = [c for c in cands if c.is_valid]
    assert len(valid_cands) == 16
    
    a1_cands = [c for c in valid_cands if c.aircraft_id == "A1"]
    a2_cands = [c for c in valid_cands if c.aircraft_id == "A2"]
    assert len(a1_cands) == 8
    assert len(a2_cands) == 8

def test_deterministic_sorting(generator):
    ac1 = create_aircraft("A1", 35000.0, 600.0)
    ac2 = create_aircraft("A2", 35000.0, 500.0)
    conflict = create_conflict("A1", "A2")
    
    cands1 = generator.generate_for_conflict(conflict, {"A1": ac1, "A2": ac2}, 0.0)
    cands2 = generator.generate_for_conflict(conflict, {"A1": ac1, "A2": ac2}, 0.0)
    
    # Extract IDs to compare order
    ids1 = [c.id for c in cands1]
    ids2 = [c.id for c in cands2]
    
    assert ids1 == ids2

def test_max_candidates_truncation(generator):
    generator.config.max_candidates = 5
    ac1 = create_aircraft("A1", 35000.0, 600.0)
    ac2 = create_aircraft("A2", 35000.0, 500.0)
    conflict = create_conflict("A1", "A2")
    
    cands = generator.generate_for_conflict(conflict, {"A1": ac1, "A2": ac2}, 0.0)
    valid_cands = [c for c in cands if c.is_valid]
    
    # Should only return 5 valid candidates due to max_candidates
    assert len(valid_cands) == 5
    
    # The valid candidates shouldn't contain invalid ones
    assert all(c.is_valid for c in valid_cands)
