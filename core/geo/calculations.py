"""Geographic calculations for aviation.

Implements great-circle (haversine) formulas for:
- Distance between two points
- Initial bearing from one point to another
- Destination point given start, bearing, and distance

All functions use canonical aviation units:
- Positions: degrees (latitude -90..90, longitude -180..180)
- Distances: nautical miles (NM)
- Altitudes: feet
- Headings/bearings: degrees true (0-360, 0=North, 90=East)

The haversine formula assumes a spherical Earth with radius 3440.065 NM.
This introduces < 0.3% error vs. WGS84 ellipsoid — acceptable for a prototype.
"""

import math

# Earth radius in nautical miles (mean radius)
EARTH_RADIUS_NM: float = 3440.065


def haversine_distance_nm(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculate great-circle distance between two points.

    Args:
        lat1: Latitude of point 1 in degrees.
        lon1: Longitude of point 1 in degrees.
        lat2: Latitude of point 2 in degrees.
        lon2: Longitude of point 2 in degrees.

    Returns:
        Distance in nautical miles.
    """
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_NM * c


def initial_bearing(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculate initial bearing (forward azimuth) from point 1 to point 2.

    Args:
        lat1: Latitude of point 1 in degrees.
        lon1: Longitude of point 1 in degrees.
        lat2: Latitude of point 2 in degrees.
        lon2: Longitude of point 2 in degrees.

    Returns:
        Initial bearing in degrees (0-360, 0=North, 90=East).
    """
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlon_r = math.radians(lon2 - lon1)

    x = math.sin(dlon_r) * math.cos(lat2_r)
    y = (
        math.cos(lat1_r) * math.sin(lat2_r)
        - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(dlon_r)
    )

    bearing = math.degrees(math.atan2(x, y))
    return normalize_heading(bearing)


def destination_point(
    lat: float, lon: float, heading: float, distance_nm: float
) -> tuple[float, float]:
    """Calculate destination point given start, heading, and distance.

    Uses the great-circle destination formula.

    Args:
        lat: Starting latitude in degrees.
        lon: Starting longitude in degrees.
        heading: Heading in degrees true (0-360).
        distance_nm: Distance to travel in nautical miles.

    Returns:
        Tuple of (latitude, longitude) in degrees.
    """
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    heading_r = math.radians(heading)
    angular_dist = distance_nm / EARTH_RADIUS_NM

    new_lat_r = math.asin(
        math.sin(lat_r) * math.cos(angular_dist)
        + math.cos(lat_r) * math.sin(angular_dist) * math.cos(heading_r)
    )

    new_lon_r = lon_r + math.atan2(
        math.sin(heading_r) * math.sin(angular_dist) * math.cos(lat_r),
        math.cos(angular_dist) - math.sin(lat_r) * math.sin(new_lat_r),
    )

    return (math.degrees(new_lat_r), normalize_longitude(math.degrees(new_lon_r)))


def normalize_heading(heading: float) -> float:
    """Normalize heading to 0-360 range.

    Args:
        heading: Heading in degrees (any value).

    Returns:
        Heading normalized to [0, 360).
    """
    return heading % 360.0


def normalize_longitude(lon: float) -> float:
    """Normalize longitude to -180 to 180 range.

    Args:
        lon: Longitude in degrees (any value).

    Returns:
        Longitude normalized to [-180, 180).
    """
    while lon > 180.0:
        lon -= 360.0
    while lon <= -180.0:
        lon += 360.0
    return lon


def knots_to_nm_per_second(speed_knots: float) -> float:
    """Convert speed from knots to nautical miles per second.

    Args:
        speed_knots: Speed in knots (NM/hour).

    Returns:
        Speed in NM/second.
    """
    return speed_knots / 3600.0


def fpm_to_fps(vertical_speed_fpm: float) -> float:
    """Convert vertical speed from feet-per-minute to feet-per-second.

    Args:
        vertical_speed_fpm: Vertical speed in feet per minute.

    Returns:
        Vertical speed in feet per second.
    """
    return vertical_speed_fpm / 60.0
