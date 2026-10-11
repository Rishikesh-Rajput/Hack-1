import pytest
from core.engine.opensky import OpenSkyProvider
from core.models.config import MonitoringRegionConfig
from core.models.aircraft import Aircraft, Position, Velocity, FlightPlan
import time

def test_on_ground_filtered():
    provider = OpenSkyProvider()
    states = [
        # icao24, callsign, origin_country, time_position, last_contact, longitude, latitude, baro_altitude, on_ground, velocity, true_track, vertical_rate
        ["111111", "FLY1", "US", time.time(), time.time(), 0.0, 0.0, 10000.0, False, 250.0, 90.0, 0.0, None, None, None, None, None],
        ["222222", "GND1", "US", time.time(), time.time(), 0.1, 0.1, 1000.0, True, 0.0, 0.0, 0.0, None, None, None, None, None]
    ]
    provider._parse_states(states)
    parsed = provider.get_latest_aircraft()
    
    assert len(parsed) == 1
    assert parsed[0].id == "111111"

def test_low_altitude_filtered():
    provider = OpenSkyProvider()
    # 300 meters is ~984 feet
    states = [
        ["111111", "FLY1", "US", time.time(), time.time(), 0.0, 0.0, 300.0, False, 250.0, 90.0, 0.0, None, None, None, None, None],
        ["222222", "FLY2", "US", time.time(), time.time(), 0.1, 0.1, 1000.0, False, 250.0, 90.0, 0.0, None, None, None, None, None] # 3280 ft
    ]
    provider._parse_states(states)
    parsed = provider.get_latest_aircraft()
    
    assert len(parsed) == 1
    assert parsed[0].id == "222222"

def test_no_invented_cruise_altitude():
    provider = OpenSkyProvider()
    states = [
        ["111111", "FLY1", "US", time.time(), time.time(), 0.0, 0.0, 1000.0, False, 250.0, 90.0, 0.0, None, None, None, None, None]
    ]
    provider._parse_states(states)
    parsed = provider.get_latest_aircraft()
    
    assert len(parsed) == 1
    assert parsed[0].flight_plan.cruise_altitude is None
