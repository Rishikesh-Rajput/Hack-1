"""FastAPI application entry point with background simulation loop."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from backend.api.routes import router as api_router, set_engine
from backend.api.websocket import ws_manager
from core.engine.scenario_loader import load_scenario
from core.engine.simulation import SimulationEngine, SimulationStatus
from core.models.config import load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("atcds.main")

# Local credentials are loaded only by the backend process.
load_dotenv()

# Global engine instance
config = load_config(
    config_path="config/default.yaml",
    region_path="config/regions/india.yaml",
)
engine = SimulationEngine(config=config)
set_engine(engine)

# Load primary demo scenario by default
default_scenario_path = Path("config/scenarios/head_on_conflict.yaml")
if default_scenario_path.is_file():
    engine.load_scenario(load_scenario(default_scenario_path))
    logger.info("Loaded default scenario: head_on_conflict.yaml")

# 4 Hz tick interval (0.25 seconds per push)
TICK_INTERVAL_SEC: float = 0.25


async def simulation_background_loop() -> None:
    """Authoritative background loop running at 4 Hz.

    Ticks the engine when PLAYING and broadcasts the latest snapshot over WebSocket.
    """
    logger.info("Starting simulation background loop at 4 Hz (250ms cadence)...")
    try:
        while True:
            # Advance simulation when in PLAYING state
            if engine.status == SimulationStatus.PLAYING:
                # dt scaled by speed multiplier and real-time 4 Hz interval
                dt = TICK_INTERVAL_SEC * engine.speed_multiplier
                engine.tick(dt=dt)

            # Broadcast latest snapshot to all connected dashboards
            if ws_manager.active_connections:
                snapshot = engine.get_snapshot()
                await ws_manager.broadcast_json(snapshot.model_dump())

            await asyncio.sleep(TICK_INTERVAL_SEC)
    except asyncio.CancelledError:
        logger.info("Simulation background loop stopped.")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan managing background simulation task."""
    task = asyncio.create_task(simulation_background_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="ATCDS - Air Traffic Conflict Resolution Decision Support",
    version="0.1.0",
    description="Backend API and WebSocket service for ATCDS prototype",
    lifespan=lifespan,
)

# Enable CORS for frontend Vite development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.websocket("/ws/simulation")
async def websocket_simulation_endpoint(websocket: WebSocket) -> None:
    """Real-time simulation state push endpoint."""
    await ws_manager.connect(websocket)
    # Immediately push the current snapshot upon connection
    try:
        await websocket.send_text(engine.get_snapshot().model_dump_json())
        while True:
            # Keep alive and receive any client ping messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
        await ws_manager.disconnect(websocket)
