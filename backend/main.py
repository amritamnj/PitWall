"""
F1 Race Strategy Explorer — FastAPI Backend

Run with:
    cd backend
    uvicorn main:app --reload --port 8000

API docs: http://localhost:8000/docs

Requires:
    pip install -r requirements.txt
    .env file with OPENWEATHER_API_KEY (optional; weather falls back to placeholder)
"""

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import calendar, weather, degradation, simulate, tyres, historical

load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(
    title="F1 Race Strategy Explorer",
    description=(
        "Analyse tyre degradation and pit stop strategies for Formula 1 races. "
        "Uses historical data from FastF1 (2023-2025), Pirelli compound codes (C1-C5), "
        "and weather-aware simulation with wet/dry crossover logic."
    ),
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calendar.router)
app.include_router(tyres.router)
app.include_router(weather.router)
app.include_router(degradation.router)
app.include_router(simulate.router)
app.include_router(historical.router)


@app.get("/", tags=["health"])
def root():
    return {
        "app": "F1 Race Strategy Explorer",
        "version": "0.2.0",
        "docs": "/docs",
        "endpoints": [
            "/api/v1/calendar",
            "/api/v1/calendar/next",
            "/api/v1/tyres/{circuit_key}",
            "/api/v1/weather",
            "/api/v1/degradation",
            "/api/v1/simulate",
            "/api/v1/historical/profile",
        ],
    }


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
