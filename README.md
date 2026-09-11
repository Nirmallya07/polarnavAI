# PolarNav AI

PolarNav AI is an AI-powered predictive navigation decision support for Antarctic research vessels.

## Problem Statement

AI-Enabled Antarctic Sea-Ice, Iceberg Trajectory, and Navigation Decision Support System.

The project aims to support vessel operators by combining environmental observations, time-aware predictions, and route-risk evaluation to recommend safer and more efficient navigation paths in Antarctic waters.

## Architecture

The intended end-to-end pipeline is:

User Input -> Environmental Data -> Preprocessing -> Sea-Ice Prediction -> Iceberg Prediction -> Time-Aware Risk -> A* Route Optimization -> Navigation Recommendation -> React Dashboard

## Tech Stack

- Backend: Python 3.11+, Flask, Flask-CORS
- Data science: NumPy, Pandas, Scikit-learn, Joblib, GeoPandas, Shapely, PyProj, Xarray, NetCDF4
- Validation: Pydantic
- Frontend: React + Vite + Leaflet / React-Leaflet
- Testing: Pytest
- Formatting: Black, Ruff

## Developer Ownership

- Developer A: data and machine learning
- Developer B: environment and risk
- Developer C: backend, routing, and frontend integration

## Project Structure

```text
polarnav-ai/
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml
├── requirements.txt
├── backend/
├── frontend/
├── data/
├── contracts/
├── notebooks/
├── tests/
├── docs/
└── .venv/
```

## Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy environment variables:
   ```bash
   cp .env.example .env
   ```

## Run Flask

```bash
export FLASK_APP=backend.app
flask run --host 127.0.0.1 --port 5000
```

## Run Tests

```bash
pytest
```

## Frontend

A Vite React application will be initialized in the frontend directory once the backend foundation is stable. It is intentionally kept minimal and will communicate with the Flask API through JSON endpoints only.

## Dataset Policy

- Do not commit large datasets.
- Do not download marine or climate data into the repository during prototype setup.
- Raw and processed data directories are included as placeholders only.
- Model artifacts should remain outside large shared data stores unless required.

## Development Rules

- Do not build unnecessary infrastructure.
- Keep model logic separate from route logic.
- Keep risk logic separate from ML prediction logic.
- Use UTC timestamps everywhere for navigation and forecasting.
- Keep API contracts stable and documented.
- Do not add authentication, database layers, or microservices in this prototype.

## Status

This is the initialization stage only. The project is intentionally structured for independent developer work without implementing the full ML, routing, or UI stack yet.
