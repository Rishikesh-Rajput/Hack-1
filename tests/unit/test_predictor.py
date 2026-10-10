"""Unit tests for the Trajectory Predictor."""

import pytest
import math

from core.models.aircraft import Aircraft, Position, Velocity, FlightPlan
from core.models.config import PredictionConfig
from core.models.trajectory import TrajectoryType
from core.detection.predictor import TrajectoryPredictor

@pytest.fixture
def predictor():
    config = PredictionConfig(horizon_sec=600.0, step_sec=10.0, max_points=100)
    return TrajectoryPredictor(config)

@pytest.fixture
def base_aircraft():
    return Aircraft(
        id="A1",
        callsign="AI101",
        position=Position(latitude=0.0, longitude=0.0, altitude=30000.0, timestamp=0.0),
        velocity=Velocity(ground_speed=450.0, vertical_speed=0.0, heading=90.0),
        flight_plan=FlightPlan(origin="VABB", destination="VIDP", cruise_altitude=35000.0, cruise_speed=450.0)
    )

def test_straight_line_horizontal(predictor, base_aircraft):
    """Test horizontal prediction with constant speed and heading."""
    traj = predictor.predict(base_aircraft)
    assert traj.aircraft_id == "A1"
    assert traj.trajectory_type == TrajectoryType.PREDICTED
    assert len(traj.points) == 61  # 0 to 600 step 10 = 61 points

    # Heading 90 means moving east, longitude should increase, latitude should stay ~0
    start = traj.points[0]
    end = traj.points[-1]

    assert start.time == 0.0
    assert end.time == 600.0
    
    # 450 knots = 450 NM / hr = 450 / 60 NM / min = 7.5 NM / min
    # 10 mins = 75 NM. 1 degree lon at equator = 60 NM, so 75 NM = 1.25 degrees
    assert abs(start.position.latitude - end.position.latitude) < 0.01
    assert end.position.longitude > start.position.longitude
    assert abs(end.position.longitude - 1.25) < 0.05
    assert end.position.altitude == 30000.0

def test_different_headings(predictor, base_aircraft):
    """Test prediction in different cardinal directions."""
    # North
    base_aircraft.velocity.heading = 0.0
    traj = predictor.predict(base_aircraft)
    assert traj.points[-1].position.latitude > traj.points[0].position.latitude
    
    # South
    base_aircraft.velocity.heading = 180.0
    traj = predictor.predict(base_aircraft)
    assert traj.points[-1].position.latitude < traj.points[0].position.latitude

    # West
    base_aircraft.velocity.heading = 270.0
    traj = predictor.predict(base_aircraft)
    assert traj.points[-1].position.longitude < traj.points[0].position.longitude

def test_different_speeds(predictor, base_aircraft):
    """Test prediction with different speeds."""
    base_aircraft.velocity.ground_speed = 300.0
    traj_slow = predictor.predict(base_aircraft)
    
    base_aircraft.velocity.ground_speed = 600.0
    traj_fast = predictor.predict(base_aircraft)

    dist_slow = traj_slow.points[-1].position.longitude - traj_slow.points[0].position.longitude
    dist_fast = traj_fast.points[-1].position.longitude - traj_fast.points[0].position.longitude

    assert dist_fast > dist_slow
    # Roughly double the distance
    assert abs(dist_fast - (dist_slow * 2)) < 0.1

def test_vertical_movement(predictor, base_aircraft):
    """Test vertical prediction."""
    base_aircraft.velocity.vertical_speed = 1000.0 # fpm climb
    base_aircraft.velocity.ground_speed = 0.0 # isolate vertical
    base_aircraft.flight_plan.cruise_altitude = 45000.0 # avoid level off
    
    traj = predictor.predict(base_aircraft)
    # 10 mins at 1000 fpm = +10000 ft
    assert traj.points[-1].position.altitude == 40000.0
    
    base_aircraft.velocity.vertical_speed = -500.0 # fpm descent
    base_aircraft.flight_plan.cruise_altitude = 20000.0 # avoid level off going down
    traj_desc = predictor.predict(base_aircraft)
    # 10 mins at -500 fpm = -5000 ft
    assert traj_desc.points[-1].position.altitude == 25000.0

def test_combined_movement(predictor, base_aircraft):
    """Test combined horizontal and vertical movement."""
    base_aircraft.velocity.ground_speed = 450.0
    base_aircraft.velocity.vertical_speed = 1000.0
    base_aircraft.velocity.heading = 45.0 # NE
    base_aircraft.flight_plan.cruise_altitude = 45000.0 # avoid level off
    
    traj = predictor.predict(base_aircraft)
    end = traj.points[-1]
    
    assert end.position.latitude > 0.0
    assert end.position.longitude > 0.0
    assert end.position.altitude == 40000.0

def test_zero_speed(predictor, base_aircraft):
    """Test prediction with zero ground speed."""
    base_aircraft.velocity.ground_speed = 0.0
    base_aircraft.velocity.heading = 90.0
    
    traj = predictor.predict(base_aircraft)
    end = traj.points[-1]
    
    assert end.position.latitude == 0.0
    assert end.position.longitude == 0.0

def test_zero_vertical_speed(predictor, base_aircraft):
    """Test prediction with zero vertical speed."""
    base_aircraft.velocity.vertical_speed = 0.0
    
    traj = predictor.predict(base_aircraft)
    for p in traj.points:
        assert p.position.altitude == 30000.0

def test_prediction_timestep_horizon(base_aircraft):
    """Test prediction with different timestep and horizon."""
    config = PredictionConfig(horizon_sec=300.0, step_sec=30.0, max_points=100)
    p = TrajectoryPredictor(config)
    
    traj = p.predict(base_aircraft)
    assert len(traj.points) == 11 # 0, 30, ..., 300
    assert traj.points[-1].time == 300.0

def test_deterministic_repeatability(predictor, base_aircraft):
    """Test that multiple runs produce identical trajectories."""
    traj1 = predictor.predict(base_aircraft)
    traj2 = predictor.predict(base_aircraft)
    
    for p1, p2 in zip(traj1.points, traj2.points):
        assert p1.position.latitude == p2.position.latitude
        assert p1.position.longitude == p2.position.longitude
        assert p1.position.altitude == p2.position.altitude

def test_longitude_wrapping(predictor, base_aircraft):
    """Test crossing the anti-meridian."""
    base_aircraft.position.longitude = 179.5
    base_aircraft.velocity.heading = 90.0
    
    traj = predictor.predict(base_aircraft)
    end = traj.points[-1]
    
    # Starting at 179.5 and moving east by ~1.25 degrees should cross 180 and wrap to ~-179.25
    assert end.position.longitude < 0.0

def test_high_latitude(predictor, base_aircraft):
    """Test moving east near the pole (longitude changes faster)."""
    base_aircraft.position.latitude = 80.0
    base_aircraft.position.longitude = 0.0
    base_aircraft.velocity.heading = 90.0
    
    traj = predictor.predict(base_aircraft)
    end = traj.points[-1]
    
    # 75 NM at lat 80 (cos(80) approx 0.17) means a larger longitude change than at equator
    # 1 degree lon at lat 80 = 60 * 0.17 = 10 NM. So 75 NM = ~7.5 degrees
    assert end.position.longitude > 5.0

def test_invalid_input(predictor):
    """Test predictor with missing or invalid fields."""
    # This just ensures we don't crash, we might have partial data
    invalid_ac = Aircraft(
        id="A2",
        callsign="INVALID",
        position=Position(latitude=0.0, longitude=0.0, altitude=0.0, timestamp=0.0),
        velocity=Velocity(ground_speed=0.0, vertical_speed=0.0, heading=0.0),
        flight_plan=FlightPlan(origin="UNK", destination="UNK", cruise_altitude=0.0, cruise_speed=0.0)
    )
    traj = predictor.predict(invalid_ac)
    assert len(traj.points) > 0

def test_predict_all(predictor, base_aircraft):
    """Test predicting for multiple aircraft."""
    ac2 = base_aircraft.model_copy(deep=True)
    ac2.id = "A2"
    
    trajectories = predictor.predict_all([base_aircraft, ac2])
    assert len(trajectories) == 2
    assert "A1" in trajectories
    assert "A2" in trajectories
