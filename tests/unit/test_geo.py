"""Unit tests for geographic calculations and monitoring regions."""

import math
import pytest

from core.geo.calculations import (
    EARTH_RADIUS_NM,
    destination_point,
    fpm_to_fps,
    haversine_distance_nm,
    initial_bearing,
    knots_to_nm_per_second,
    normalize_heading,
    normalize_longitude,
)
from core.geo.regions import MonitoringRegion


class TestGeoCalculations:
    def test_haversine_zero_distance(self):
        d = haversine_distance_nm(20.0, 75.0, 20.0, 75.0)
        assert d == pytest.approx(0.0, abs=1e-5)

    def test_haversine_meridian_distance(self):
        # 1 degree of latitude is approximately 60 NM
        d = haversine_distance_nm(0.0, 0.0, 1.0, 0.0)
        # pi * R / 180 = 3440.065 * pi / 180 ~= 60.04 NM
        assert d == pytest.approx(60.04, abs=0.1)

    def test_haversine_symmetry(self):
        d1 = haversine_distance_nm(19.0, 72.0, 28.0, 77.0)
        d2 = haversine_distance_nm(28.0, 77.0, 19.0, 72.0)
        assert d1 == pytest.approx(d2, abs=1e-6)

    def test_initial_bearing_cardinal_directions(self):
        # Due North
        assert initial_bearing(0.0, 0.0, 10.0, 0.0) == pytest.approx(0.0, abs=0.1)
        # Due East along equator
        assert initial_bearing(0.0, 0.0, 0.0, 10.0) == pytest.approx(90.0, abs=0.1)
        # Due South
        assert initial_bearing(10.0, 0.0, 0.0, 0.0) == pytest.approx(180.0, abs=0.1)
        # Due West along equator
        assert initial_bearing(0.0, 10.0, 0.0, 0.0) == pytest.approx(270.0, abs=0.1)

    def test_destination_point_north_movement(self):
        # Move 60 NM North from (0, 0)
        lat, lon = destination_point(0.0, 0.0, 0.0, 60.04)
        assert lat == pytest.approx(1.0, abs=0.05)
        assert lon == pytest.approx(0.0, abs=0.05)

    def test_destination_point_east_movement(self):
        lat, lon = destination_point(0.0, 0.0, 90.0, 60.04)
        assert lat == pytest.approx(0.0, abs=0.05)
        assert lon == pytest.approx(1.0, abs=0.05)

    def test_normalize_heading(self):
        assert normalize_heading(0.0) == 0.0
        assert normalize_heading(360.0) == 0.0
        assert normalize_heading(450.0) == 90.0
        assert normalize_heading(-90.0) == 270.0

    def test_normalize_longitude(self):
        assert normalize_longitude(180.0) == 180.0
        assert normalize_longitude(190.0) == -170.0
        assert normalize_longitude(-190.0) == 170.0
        assert normalize_longitude(0.0) == 0.0

    def test_unit_conversions(self):
        assert knots_to_nm_per_second(360.0) == pytest.approx(0.1)
        assert fpm_to_fps(600.0) == pytest.approx(10.0)


class TestMonitoringRegion:
    @pytest.fixture
    def sample_region(self):
        return MonitoringRegion(
            name="Test Square Airspace",
            polygon=[
                (10.0, 70.0),
                (20.0, 70.0),
                (20.0, 80.0),
                (10.0, 80.0),
                (10.0, 70.0),
            ],
            altitude_floor_ft=10000.0,
            altitude_ceiling_ft=45000.0,
            approach_buffer_nm=30.0,
        )

    def test_point_in_polygon(self, sample_region):
        assert sample_region.is_point_inside(15.0, 75.0) is True
        assert sample_region.is_point_inside(5.0, 75.0) is False
        assert sample_region.is_point_inside(25.0, 75.0) is False

    def test_altitude_band(self, sample_region):
        assert sample_region.is_altitude_in_band(30000.0) is True
        assert sample_region.is_altitude_in_band(5000.0) is False
        assert sample_region.is_altitude_in_band(50000.0) is False

    def test_aircraft_relevance(self, sample_region):
        # Inside
        assert sample_region.is_aircraft_relevant(15.0, 75.0, 35000.0) is True
        # Wrong altitude
        assert sample_region.is_aircraft_relevant(15.0, 75.0, 5000.0) is False
        # Far outside
        assert sample_region.is_aircraft_relevant(30.0, 90.0, 35000.0) is False
