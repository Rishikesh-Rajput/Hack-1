"""Authenticated OpenSky live aircraft provider."""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Optional

import requests

from core.models.aircraft import Aircraft, AircraftStatus, FlightPlan, Position, Velocity
from core.models.config import MonitoringRegionConfig

logger = logging.getLogger(__name__)
TOKEN_URL = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
STATES_URL = "https://opensky-network.org/api/states/all"
POLL_INTERVAL_SEC = 15


class OpenSkyProvider:
    """Poll OpenSky state vectors. Credentials remain server-side."""

    def __init__(self, region: Optional[MonitoringRegionConfig] = None) -> None:
        self.region = region
        self.active = False
        self.thread: threading.Thread | None = None
        self.latest_aircraft: list[Aircraft] = []
        self._lock = threading.Lock()
        self._access_token: str | None = None
        self._token_expires_at = 0.0
        self._last_success_at: float | None = None
        self._last_error: str | None = None
        self._rate_limit_remaining: str | None = None

    def start(self) -> None:
        if self.active:
            return
        self.active = True
        self.thread = threading.Thread(target=self._poll_loop, daemon=True, name="opensky-poller")
        self.thread.start()

    def stop(self) -> None:
        self.active = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def get_latest_aircraft(self) -> list[Aircraft]:
        with self._lock:
            return list(self.latest_aircraft)

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            fresh = self._last_success_at is not None and time.time() - self._last_success_at <= POLL_INTERVAL_SEC * 2 + 5
            return {"provider": "OpenSky", "active": self.active, "connected": bool(fresh), "fresh": bool(fresh), "aircraft_count": len(self.latest_aircraft), "last_success_at": self._last_success_at, "last_error": self._last_error, "rate_limit_remaining": self._rate_limit_remaining, "poll_interval_sec": POLL_INTERVAL_SEC}

    def _get_access_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        client_id = os.getenv("OPENSKY_CLIENT_ID", "").strip()
        client_secret = os.getenv("OPENSKY_CLIENT_SECRET", "").strip()
        if not client_id or not client_secret:
            raise RuntimeError("OpenSky credentials are missing. Set OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET in .env.")
        response = requests.post(TOKEN_URL, data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}, timeout=10)
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError("OpenSky token response did not contain an access token.")
        self._access_token = token
        self._token_expires_at = time.time() + max(60, int(data.get("expires_in", 1800)) - 60)
        return token

    def _poll_loop(self) -> None:
        bounds: dict[str, float] = {"lamin": 6.0, "lomin": 68.0, "lamax": 36.0, "lomax": 98.0}
        if self.region and self.region.polygon:
            bounds = {"lamin": min(p[0] for p in self.region.polygon), "lomin": min(p[1] for p in self.region.polygon), "lamax": max(p[0] for p in self.region.polygon), "lomax": max(p[1] for p in self.region.polygon)}
        while self.active:
            try:
                response = requests.get(STATES_URL, params=bounds, headers={"Authorization": f"Bearer {self._get_access_token()}"}, timeout=15)
                if response.status_code == 401:
                    self._access_token = None
                    raise RuntimeError("OpenSky rejected the access token. Check or reset the API credential.")
                response.raise_for_status()
                self._parse_states(response.json().get("states") or [])
                with self._lock:
                    self._last_success_at, self._last_error = time.time(), None
                    self._rate_limit_remaining = response.headers.get("X-Rate-Limit-Remaining")
            except Exception as exc:
                logger.warning("OpenSky polling failed: %s", exc)
                with self._lock:
                    self._last_error = str(exc)
            time.sleep(POLL_INTERVAL_SEC)

    def _parse_states(self, states: list[list[Any]]) -> None:
        parsed: list[Aircraft] = []
        timestamp = time.time()
        for state in states:
            if not state:
                continue
            icao24, callsign, lon, lat, altitude, speed, heading, vertical_rate = state[0], state[1], state[5], state[6], state[7], state[9], state[10], state[11]
            if lat is None or lon is None or altitude is None or speed is None:
                continue
            parsed.append(Aircraft(id=str(icao24).strip(), callsign=str(callsign).strip() if callsign else str(icao24).strip(), aircraft_type="LIVE", position=Position(latitude=lat, longitude=lon, altitude=altitude * 3.28084, timestamp=timestamp), velocity=Velocity(ground_speed=speed * 1.94384, vertical_speed=(vertical_rate or 0.0) * 3.28084 * 60, heading=heading or 0.0), flight_plan=FlightPlan(origin="UNKNOWN", destination="UNKNOWN", cruise_altitude=35000, cruise_speed=400), status=AircraftStatus.ACTIVE))
        with self._lock:
            self.latest_aircraft = parsed
        logger.info("Updated %s live aircraft from OpenSky.", len(parsed))
