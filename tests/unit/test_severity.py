"""Unit tests for the Severity Assessor."""

import pytest

from core.models.config import SeverityConfig
from core.models.aircraft import Position
from core.models.conflict import Conflict, SeverityLevel, ConflictState
from core.detection.severity import SeverityAssessor


@pytest.fixture
def severity_config():
    return SeverityConfig(
        critical_sec=120.0,
        high_sec=300.0,
        medium_sec=600.0,
        low_sec=900.0
    )

@pytest.fixture
def assessor(severity_config):
    return SeverityAssessor(severity_config)

def create_conflict(id_suffix: str, ttc: float, cpa_h: float = 2.0, cpa_v: float = 500.0) -> Conflict:
    return Conflict(
        id=f"CONF-{id_suffix}",
        aircraft_1_id="A1",
        aircraft_2_id="A2",
        detection_timestamp=0.0,
        predicted_conflict_timestamp=ttc,
        time_to_conflict_sec=ttc,
        location=Position(latitude=0.0, longitude=0.0, altitude=35000.0, timestamp=ttc),
        cpa_time=ttc,
        cpa_horizontal_separation_nm=cpa_h,
        cpa_vertical_separation_ft=cpa_v,
        threshold_horizontal_nm=5.0,
        threshold_vertical_ft=1000.0,
        state=ConflictState.DETECTED,
    )

def test_severity_levels(assessor):
    c_crit = assessor.assess(create_conflict("1", 100.0))
    assert c_crit.severity == SeverityLevel.CRITICAL
    
    c_high = assessor.assess(create_conflict("2", 200.0))
    assert c_high.severity == SeverityLevel.HIGH

    c_med = assessor.assess(create_conflict("3", 500.0))
    assert c_med.severity == SeverityLevel.MEDIUM

    c_low = assessor.assess(create_conflict("4", 800.0))
    assert c_low.severity == SeverityLevel.LOW

    c_unk = assessor.assess(create_conflict("5", 1000.0))
    assert c_unk.severity == SeverityLevel.UNKNOWN

def test_severity_scoring(assessor):
    # Imminent conflict (ttc=0), zero separation = max score (100)
    c_max = create_conflict("max", 0.0, 0.0, 0.0)
    assessor.assess(c_max)
    assert c_max.severity_score == 100.0

    # Distant conflict (ttc=900), barely touching margins (cpa_h=5.0, cpa_v=1000)
    c_min = create_conflict("min", 900.0, 5.0, 1000.0)
    assessor.assess(c_min)
    assert c_min.severity_score == 0.0

    # Something in between
    c_mid = create_conflict("mid", 450.0, 2.5, 500.0)
    assessor.assess(c_mid)
    # TTC factor: (900-450)/900 = 0.5 * 60 = 30
    # H factor: (5-2.5)/5 = 0.5 * 20 = 10
    # V factor: (1000-500)/1000 = 0.5 * 20 = 10
    # Total = 50
    assert c_mid.severity_score == 50.0

def test_different_separation_margins(assessor):
    c1 = create_conflict("1", 100.0, cpa_h=1.0, cpa_v=900.0) # Tight horizontal
    c2 = create_conflict("2", 100.0, cpa_h=4.0, cpa_v=200.0) # Tight vertical
    
    assessor.assess(c1)
    assessor.assess(c2)
    
    assert c1.severity_score > 0
    assert c2.severity_score > 0
    assert len(c1.severity_factors) > 0

def test_prioritization(assessor):
    c1 = assessor.assess(create_conflict("1", 500.0, 2.5, 500.0)) # Score 50
    c2 = assessor.assess(create_conflict("2", 0.0, 0.0, 0.0))    # Score 100
    c3 = assessor.assess(create_conflict("3", 900.0, 5.0, 1000.0)) # Score 0
    
    sorted_conflicts = assessor.prioritize([c1, c2, c3])
    
    assert sorted_conflicts[0].id == "CONF-2"
    assert sorted_conflicts[1].id == "CONF-1"
    assert sorted_conflicts[2].id == "CONF-3"

def test_stable_tie_breaking(assessor):
    c1 = assessor.assess(create_conflict("B", 100.0, 0.0, 0.0))
    c2 = assessor.assess(create_conflict("A", 100.0, 0.0, 0.0))
    
    # Identical score, identical TTC, should sort by ID lexicographically
    sorted_conflicts = assessor.prioritize([c1, c2])
    
    assert sorted_conflicts[0].id == "CONF-A"
    assert sorted_conflicts[1].id == "CONF-B"

def test_identical_inputs_identical_results(assessor):
    c1 = assessor.assess(create_conflict("1", 100.0, 2.0, 500.0))
    c2 = assessor.assess(create_conflict("2", 100.0, 2.0, 500.0))
    
    assert c1.severity == c2.severity
    assert c1.severity_score == c2.severity_score
    assert c1.severity_factors == c2.severity_factors

def test_configuration_changes(severity_config):
    # Change config to make everything critical
    severity_config.critical_sec = 1000.0
    custom_assessor = SeverityAssessor(severity_config)
    
    c = custom_assessor.assess(create_conflict("1", 900.0))
    assert c.severity == SeverityLevel.CRITICAL
