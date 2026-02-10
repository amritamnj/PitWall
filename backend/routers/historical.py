"""
Historical Strategy Intelligence router.

GET /api/v1/historical/profile?circuit_key=<id>&seasons=2023,2024,2025

Returns CircuitHistoricalProfile with aggregated pit stop patterns,
strategy sequences, safety car data, and undercut/overcut effectiveness
computed from real FastF1 race data.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from utils.cache import read_cache, write_cache
from utils.fastf1_helpers import HISTORICAL_YEARS, get_circuit_info, normalize_circuit_name
from utils.historical_analysis import compute_historical_profile

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/historical", tags=["historical"])

# Cache version — bump when computation logic changes
CACHE_VERSION = "v1"


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class FirstStopLapStats(BaseModel):
    median: float
    p25: float
    p75: float
    iqr: float
    n: int


class StopCountDistribution(BaseModel):
    one_stop_pct: float
    two_stop_pct: float
    three_plus_pct: float
    n: int


class StrategySequenceInfo(BaseModel):
    stops: int
    sequence: list[str]
    frequency_pct: float
    n: int


class UndercutOvercutStats(BaseModel):
    undercut_attempts: int
    undercut_success_rate: float
    overcut_attempts: int
    overcut_success_rate: float
    typical_undercut_gain_s: float
    notes: str


class WarmupTrafficProxies(BaseModel):
    pit_outlap_penalty_s: float


class CircuitHistoricalProfile(BaseModel):
    circuit_key: str
    seasons_used: list[int]
    races_used: int
    first_stop_lap: Optional[FirstStopLapStats] = None
    stop_count_distribution: Optional[StopCountDistribution] = None
    common_strategy_sequences: list[StrategySequenceInfo] = []
    safety_car_lap_histogram: Optional[dict[str, float]] = None
    undercut_overcut: Optional[UndercutOvercutStats] = None
    warmup_traffic: Optional[WarmupTrafficProxies] = None
    notes: list[str] = []
    cache_version: str = CACHE_VERSION


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/profile", response_model=CircuitHistoricalProfile)
def get_historical_profile(
    circuit_key: str = Query(..., description="Normalized circuit key"),
    seasons: Optional[str] = Query(
        None,
        description="Comma-separated seasons (e.g. '2023,2024,2025'). Defaults to HISTORICAL_YEARS.",
    ),
    force_refresh: bool = Query(False, description="Bypass cache"),
):
    """
    Return aggregated historical strategy profile for a circuit.

    Loads FastF1 race sessions, extracts pit stop patterns, strategy sequences,
    safety car data, and undercut/overcut effectiveness. Results are cached
    to disk for fast subsequent lookups.
    """
    circuit = normalize_circuit_name(circuit_key)
    year_list = _parse_seasons(seasons)
    cache_args = {
        "circuit": circuit,
        "seasons": str(sorted(year_list)),
        "version": CACHE_VERSION,
    }

    # Cache check
    if not force_refresh:
        cached = read_cache("historical", **cache_args)
        if cached is not None:
            logger.info(f"Cache hit for historical: {circuit}")
            return CircuitHistoricalProfile(**cached)

    # Check circuit exists
    info = get_circuit_info(circuit)
    if not info:
        return _empty_profile(
            circuit, year_list,
            [f"Unknown circuit: {circuit}. No historical data available."],
        )

    # Compute from FastF1
    logger.info(f"Computing historical profile for {circuit}...")
    profile_data = compute_historical_profile(circuit, year_list, info)
    profile = CircuitHistoricalProfile(circuit_key=circuit, **profile_data)

    # Cache write
    write_cache("historical", profile.model_dump(), **cache_args)
    logger.info(f"Cached historical profile for {circuit}")

    return profile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_seasons(seasons_str: Optional[str]) -> list[int]:
    if not seasons_str:
        return list(HISTORICAL_YEARS)
    return sorted({
        int(s.strip())
        for s in seasons_str.split(",")
        if s.strip().isdigit()
    })


def _empty_profile(
    circuit: str,
    years: list[int],
    notes: list[str],
) -> CircuitHistoricalProfile:
    return CircuitHistoricalProfile(
        circuit_key=circuit,
        seasons_used=years,
        races_used=0,
        notes=notes,
    )
