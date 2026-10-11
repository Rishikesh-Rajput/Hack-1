# AI-Based Air Traffic Conflict Resolution Decision Support (ATCDS)

An advisory decision-support prototype built to detect potential aircraft conflicts, simulate candidate resolution maneuvers, and provide GenAI-assisted recommendations to human air traffic controllers.

**Note:** This is a hackathon prototype, not a certified aviation system. OpenSky integration has *not* been implemented yet; all data relies on a deterministic internal simulation engine.

## Features

- **Trajectory Prediction & Conflict Detection**: Extrapolates paths using great-circle geophysics and checks separation minimums against configurable airspace boundaries (e.g., Indian Airspace).
- **Candidate Maneuver Simulation**: Generates heading, altitude, and speed interventions and simulates them in a sandboxed fork of the airspace to check for downstream conflict collisions.
- **Maneuver Scoring**: Deterministically ranks candidates based on CPA (Closest Point of Approach) margins, complexity, and route deviation.
- **GenAI Controller Assistant**: Uses Gemini (optional) to summarize raw metrics into natural language explanations. Fallbacks safely to hardcoded logic when an API key is missing.
- **Human-in-the-Loop Decisions**: Controllers explicitly ACCEPT or REJECT maneuvers. The system never acts autonomously.
- **Real-Time Telemetry**: Frontend dashboard runs at a simulated 4 Hz using WebSockets to smoothly render the environment.
- **Metrics Evaluator**: Headless evaluation service that benchmarks detection and resolution time against loaded scenarios.

## Project Structure

```
├── backend/
│   ├── api/        # FastAPI routes and WebSocket manager
│   └── main.py     # Application entrypoint & 4Hz background loop
├── core/
│   ├── engine/     # Deterministic simulator and state progression
│   ├── models/     # Pydantic data schemas (Aircraft, Trajectories, Config)
│   ├── geo/        # Haversine distance, bearings, and Polygon regions
│   ├── resolution/ # Candidate generation, simulation, and scoring pipeline
│   ├── explainer/  # LLM text generation fallback service
│   └── metrics/    # Scenario evaluation runner
├── frontend/       # React/Vite Dashboard (Tailwind + Lucide)
├── config/         # YAML configurations (Defaults, Regions, Scenarios)
└── tests/          # Pytest integration and unit test suite
```

## Prerequisites

- Python >= 3.11
- Node.js >= 18
- (Optional) `GEMINI_API_KEY` for LLM explanations.

## Installation & Setup

1. **Clone the repository and install Backend Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Frontend Dependencies**
   ```bash
   cd frontend
   npm install
   ```

3. **Configure GenAI (Optional)**
   Create a `.env` file in the root or export it to your terminal:
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```
   *If omitted, the system gracefully falls back to deterministic string summaries.*

## Running the Application

**Terminal 1: Start the Backend & Simulation Loop**
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2: Start the Frontend Dashboard**
```bash
cd frontend
npm run dev
```
Navigate to `http://localhost:5173`.

## API Endpoints Overview

- `GET /api/scenarios`: List available YAML scenarios.
- `GET /api/region`: Get the configured polygon airspace map.
- `GET /api/simulation/state`: Fetch a synchronous snapshot of the sky.
- `POST /api/simulation/control`: Issue PLAY, PAUSE, STEP, or RESET commands.
- `GET /api/simulation/conflicts/{id}/recommendation`: Run the AI maneuver pipeline and fetch a recommendation for a specific conflict.
- `POST /api/simulation/assistant`: Query the GenAI chat assistant with dynamic context.
- `POST /api/simulation/decisions`: Record a human controller's ACCEPT/REJECT decision.
- `POST /api/evaluation/run`: Benchmarks the core engine against a specific scenario.

*WebSocket*: `ws://localhost:8000/ws/simulation` pushes 4 Hz `SimulationSnapshot` JSON payloads.

## Testing

The project uses `pytest` for rigorous deterministic testing.
```bash
pytest -v
```
*(Currently 76 tests verifying the math, conflict resolution sandboxing, and REST APIs).*

## Known Limitations & Future Work

- **Live Data**: The system is fully simulated. Plugging in the OpenSky REST API into `backend/main.py` is the next major step.
- **ML Scoring**: `MLScorer` exists but is currently disabled natively. It requires a trained `.pkl` model to function.
- **Vertical Speeds**: The trajectory predictor calculates linear vertical profiles but does not simulate complex aerodynamic climb curves.
