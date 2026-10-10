"""Monitoring region implementation.

Defines configurable airspace monitoring regions as polygons
with altitude bands and approach buffers.

The core algorithms are geographically region-agnostic.
Indian airspace (or any other region) is injected as configuration.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, Field

from core.geo.calculations import haversine_distance_nm


class MonitoringRegion(BaseModel):
    """A configurable airspace monitoring region.

    Defined by a polygon boundary, altitude band, and approach buffer.
    Used to filter which aircraft are relevant for conflict detection.
    """

    name: str = Field(description="Human-readable region name")
    polygon: list[tuple[float, float]] = Field(
        description="Boundary vertices as (latitude, longitude) pairs. Must form a closed polygon."
    )
    altitude_floor_ft: float = Field(default=0.0, ge=0, description="Altitude floor in feet")
    altitude_ceiling_ft: float = Field(default=60000.0, gt=0, description="Altitude ceiling in feet")
    approach_buffer_nm: float = Field(default=50.0, ge=0, description="Approach detection buffer in NM")

    def is_point_inside(
        self, latitude: float, longitude: float
    ) -> bool:
        """Check if a lat/lon point is inside the polygon.

        Uses the ray-casting algorithm for point-in-polygon test.

        Args:
            latitude: Point latitude in degrees.
            longitude: Point longitude in degrees.

        Returns:
            True if the point is inside the polygon.
        """
        n = len(self.polygon)
        inside = False

        j = n - 1
        for i in range(n):
            yi, xi = self.polygon[i]
            yj, xj = self.polygon[j]

            if ((yi > latitude) != (yj > latitude)) and (
                longitude < (xj - xi) * (latitude - yi) / (yj - yi) + xi
            ):
                inside = not inside
            j = i

        return inside

    def is_altitude_in_band(self, altitude_ft: float) -> bool:
        """Check if an altitude is within the monitoring altitude band.

        Args:
            altitude_ft: Altitude in feet.

        Returns:
            True if altitude is within [floor, ceiling].
        """
        return self.altitude_floor_ft <= altitude_ft <= self.altitude_ceiling_ft

    def distance_to_boundary_nm(
        self, latitude: float, longitude: float
    ) -> float:
        """Calculate approximate distance from a point to the nearest polygon edge.

        Uses point-to-vertex minimum distance as an approximation.
        For a prototype, this is sufficient for approach detection.

        Args:
            latitude: Point latitude in degrees.
            longitude: Point longitude in degrees.

        Returns:
            Approximate distance to nearest boundary point in NM.
        """
        min_dist = float("inf")
        for vlat, vlon in self.polygon:
            dist = haversine_distance_nm(latitude, longitude, vlat, vlon)
            if dist < min_dist:
                min_dist = dist
        return min_dist

    def is_aircraft_relevant(
        self,
        latitude: float,
        longitude: float,
        altitude_ft: float,
    ) -> bool:
        """Determine if an aircraft is relevant to this monitoring region.

        An aircraft is relevant if it is:
        - Inside the polygon and within the altitude band, OR
        - Within the approach buffer distance of the polygon boundary
          and within the altitude band.

        Args:
            latitude: Aircraft latitude in degrees.
            longitude: Aircraft longitude in degrees.
            altitude_ft: Aircraft altitude in feet.

        Returns:
            True if the aircraft should be monitored.
        """
        if not self.is_altitude_in_band(altitude_ft):
            return False

        if self.is_point_inside(latitude, longitude):
            return True

        # Check approach buffer
        if self.approach_buffer_nm > 0:
            dist = self.distance_to_boundary_nm(latitude, longitude)
            return dist <= self.approach_buffer_nm

        return False
