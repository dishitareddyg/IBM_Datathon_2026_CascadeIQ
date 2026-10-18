# CascadeIQ Backend

> **Predict the Cascade. Prevent the Crisis.**

A decision-support simulator for predicting cascading urban emergency consequences caused by flooding in **Bengaluru Urban district, Karnataka, India**.

> ⚠️ **Disclaimer**: All simulation results are computer-generated estimates for **research and educational purposes only**. They do not represent actual emergency-response data and must **not** be used for real-world disaster management decisions.

---

## Architecture

```
Heavy Rainfall
     │
     ▼
Flood Risk Estimation (rule-based, configurable)
     │
     ▼
Road Degradation / Closure  ←─ OSM road network (bundled or live)
     │
     ▼
Ambulance Route Delays  ←─ Dijkstra on passable subgraph
     │
     ▼
Hospital Capacity Stress  ←─ capacity-weighted assignment
     │
     ▼
Isolated Facilities / Unreachable Requests
     │
     ▼
Cascade Timeline  →  Recommendations  →  Baseline vs CascadeIQ Comparison
```

```
backend/
├── app/
│   ├── main.py              # FastAPI app, lifespan, middleware
│   ├── core/                # config, logging, errors
│   ├── api/routes/          # route handlers (city, weather, scenarios, simulations, …)
│   ├── schemas/             # Pydantic v2 request/response models
│   ├── models/              # Python dataclasses (graph, scenario, entities)
│   ├── services/            # business logic (graph, routing, cascade, …)
│   ├── data_sources/        # OSM, IMD, synthetic weather adapters
│   ├── repositories/        # in-memory stores (Phase 1)
│   ├── db/                  # SQLAlchemy stubs (Phase 3)
│   └── utils/               # geo, time helpers
├── tests/                   # pytest test suite
├── scripts/                 # seed_data.py smoke test
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Quickstart — Local Development

### Prerequisites
- Python 3.11+
- pip

### 1. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment (optional)

```bash
cp .env.example .env
# Edit .env – all defaults work without changes
```

### 3. Start the server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server starts without a database or external API credentials. The bundled synthetic road graph loads automatically.

### 4. Explore the API

- **OpenAPI docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health check**: http://localhost:8000/health

---

## Quickstart — Docker

```bash
cd backend
docker build -t cascadeiq-backend .
docker run -p 8000:8000 cascadeiq-backend
```

Compatible with Red Hat OpenShift on IBM LinuxONE (runs as non-root UID 1001, group-writable `/app`).

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `CascadeIQ` | Service name |
| `APP_VERSION` | `0.1.0` | Semantic version |
| `DEBUG` | `false` | Enable debug mode |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8000` | Bind port |
| `LOG_LEVEL` | `INFO` | Root log level |
| `STUDY_AREA` | `Bengaluru Urban` | OSM district name |
| `STUDY_AREA_STATE` | `Karnataka` | State |
| `STUDY_AREA_COUNTRY` | `India` | Country |
| `COORDINATE_SYSTEM` | `EPSG:4326` | Storage CRS |
| `LOCAL_CRS` | `EPSG:32643` | UTM Zone 43N for distance calc |
| `USE_BUNDLED_GRAPH` | `true` | Load bundled graph (no OSM download) |
| `OSM_NETWORK_TYPE` | `drive` | OSMnx network type |
| `MAX_SCENARIO_STEPS` | `50` | Maximum simulation steps |
| `FLOOD_RISK_RAINFALL_MM_HIGH` | `50.0` | High-risk rainfall threshold (mm/24h) |
| `FLOOD_RISK_RAINFALL_MM_CRITICAL` | `100.0` | Critical-risk rainfall threshold |
| `FLOOD_RISK_WARNING_WEIGHT` | `0.4` | Weight of warning in risk score |
| `FLOOD_RISK_RAINFALL_WEIGHT` | `0.6` | Weight of rainfall in risk score |
| `OBJECTIVE_LAMBDA` | `0.3` | λ weight for hospital overload |
| `OBJECTIVE_MU` | `0.1` | μ weight for intervention cost |
| `IMD_API_KEY` | _(empty)_ | IMD API key (optional; synthetic used if absent) |
| `DATABASE_URL` | _(empty)_ | SQLAlchemy URL (optional; in-memory if absent) |

---

## API Endpoints

### Health

```bash
GET /health
# → {"status":"ok","version":"0.1.0","graph_loaded":true,"study_area":"Bengaluru Urban","timestamp":"..."}
```

### City Graph

```bash
GET /api/v1/city/metadata
GET /api/v1/city/graph
```

### Weather

```bash
GET /api/v1/weather/current      # rainfall observations
GET /api/v1/weather/warnings     # active weather warnings
GET /api/v1/weather/status       # summary + disclaimer
```

### Scenarios

```bash
GET /api/v1/scenarios            # list bundled scenarios
GET /api/v1/scenarios/{id}       # single scenario config
```

### Simulations

```bash
# Run a simulation
POST /api/v1/simulations/run
Content-Type: application/json

{
  "scenario_id": "my_scenario",
  "seed": 42,
  "hospitals": [
    {"hospital_id": "H1", "name": "Victoria Hospital",
     "lat": 12.9612, "lon": 77.5726,
     "total_beds": 200, "available_beds": 80, "icu_beds": 20}
  ],
  "ambulances": [
    {"ambulance_id": "A1", "lat": 12.9767, "lon": 77.5713, "is_available": true}
  ],
  "emergency_requests": [
    {"request_id": "R1", "origin_lat": 12.95, "origin_lon": 77.59, "priority": "HIGH"}
  ],
  "road_disruptions": [],
  "simulation_steps": 5,
  "weather_mode": "synthetic"
}

# Retrieve result
GET /api/v1/simulations/{simulation_id}

# List all simulation IDs
GET /api/v1/simulations/
```

### Recommendations

```bash
POST /api/v1/recommendations
Content-Type: application/json

{
  "simulation_id": "<id from simulation>",
  "objective_lambda": 0.3,
  "objective_mu": 0.1,
  "max_recommendations": 5
}
```

### Evaluation

```bash
POST /api/v1/evaluations/compare
Content-Type: application/json

{
  "scenario_input": { ...same as POST /api/v1/simulations/run... },
  "objective_lambda": 0.3,
  "objective_mu": 0.1
}
```

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

Expected: all tests pass without network access or API credentials.

---

## Seed Script

```bash
cd backend
python scripts/seed_data.py
```

Runs all 3 bundled scenarios and prints a summary table.

---

## Data Provenance

| Source | Data | Licence | Notes |
|---|---|---|---|
| OpenStreetMap contributors | Road network | ODbL 1.0 | Retrieved via OSMnx; bundled graph is synthetic approximation |
| Survey of India / Bhuvan | District boundary bbox | Government of India open data | Approximate bounds only |
| IMD (India Meteorological Dept) | Rainfall / warnings | Conditional | API not publicly available; synthetic fallback used |
| Synthetic generator | All weather in Phase 1 | N/A | numpy-seeded, deterministic |

**Bengaluru Urban District bbox**: (12.75°N, 77.35°E) to (13.18°N, 77.85°E), WGS84.
**Population**: ~11.8M (approx. 2011 Census, Bengaluru Urban district).

---

## Objective Function

```
score = −response_time_improvement_s
        + λ · (−hospital_overload_reduction)
        + μ · intervention_cost
```

Lower score = better intervention. λ and μ are configurable per request. **Global optimality is not guaranteed** — a greedy heuristic is used.

---

## Phase Roadmap

| Phase | Scope |
|---|---|
| **Phase 1** (current) | Backend, bundled graph, simulation engine, REST API, tests |
| **Phase 2** | React frontend, map visualisation, scenario editor |
| **Phase 3** | PostgreSQL/PostGIS persistence, live OSM graph, IMD integration |
| **Phase 4** | OpenShift deployment on IBM LinuxONE, monitoring |
