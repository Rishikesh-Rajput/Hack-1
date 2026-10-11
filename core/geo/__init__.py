"""Geographic utilities for aviation calculations.

All functions use canonical units:
- Distances: nautical miles (NM)
- Altitudes: feet
- Speeds: knots (NM/hour)
- Vertical speed: feet per minute (fpm)
- Angles: degrees (0-360 for headings, -90 to 90 for latitude, -180 to 180 for longitude)
"""

from core.geo.calculations import (
    haversine_distance_nm,
    initial_bearing,
    destination_point,
    normalize_heading,
    normalize_longitude,
)
from core.geo.regions import MonitoringRegion

__all__ = [
    "haversine_distance_nm",
    "initial_bearing",
    "destination_point",
    "normalize_heading",
    "normalize_longitude",
    "MonitoringRegion",
]
