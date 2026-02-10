"""
Tyre Degradation router — returns per-compound (C1–C5) degradation data.

Uses FastF1 historical data to compute degradation rates per absolute compound
code. Maps SOFT/MEDIUM/HARD labels to actual C-numbers using the Pirelli
nomination mapping, so C3 at Melbourne across 2023–2025 aggregates correctly.

Flow:
1. Check disk cache (keyed by circuit + years).
2. Cache miss → load FastF1 → extract stints → map to C-numbers → compute.
3. Cache result.
4. Apply temperature adjustment if track_temp is provided.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from utils.cache import read_cache, write_cache
from utils.fastf1_helpers import (
    FALLBACK_COMPOUND_DATA,
    HISTORICAL_YEARS,
    apply_temp_adjustment,
    compute_degradation,
    load_stints_for_circuit,
    normalize_circuit_name,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/degradation", tags=["degradation"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class CompoundDegradation(BaseModel):
    avg_deg_s_per_lap: float
    cliff_onset_lap: int
    cliff_rate_s_per_lap2: float
    typical_max_stint_laps: int
    avg_reference_lap_s: float
    base_pace_offset: float
    temp_multiplier: Optional[float] = None


class DegradationResponse(BaseModel):
    circuit: str
    years_used: list[int]
    track_temp_c: Optional[float] = None
    data_source: str  # "historical" | "fallback"
    compounds: dict[str, CompoundDegradation]  # keyed by "C1".."C5"
    notes: list[str]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/", response_model=DegradationResponse)
def get_degradation(
    circuit: str = Query(..., description="Circuit short name (e.g. 'melbourne', 'bahrain')"),
    track_temp: Optional[float] = Query(None, description="Track temperature °C for adjustment"),
    force_refresh: bool = Query(False, description="Bypass cache and re-fetch from FastF1"),
):
    """
    Return tyre degradation per compound code (C1–C5) for a circuit.

    Loads historical race data from FastF1 (2023-2025), maps SOFT/MEDIUM/HARD
    to actual C-numbers, and computes linear degradation + cliff parameters.
    Falls back to generic compound data when historical data is unavailable.
    """
    circuit_key = normalize_circuit_name(circuit)
    notes: list[str] = []
    cache_key_args = {"circuit": circuit_key, "years": str(HISTORICAL_YEARS)}

    degradation = dict(FALLBACK_COMPOUND_DATA)
    data_source = "fallback"
    years_used: list[int] = []

    # ---- Cache lookup ----
    cached = None
    if not force_refresh:
        cached = read_cache("degradation", **cache_key_args)

    if cached is not None:
        logger.info(f"Cache hit for degradation: {circuit_key}")
        degradation = cached["compounds"]
        data_source = cached.get("data_source", "historical")
        years_used = cached.get("years_used", HISTORICAL_YEARS)
        notes.append("Loaded from cache")
    else:
        # ---- FastF1 extraction ----
        logger.info(f"Computing degradation for {circuit_key} from FastF1...")
        try:
            stints_df = load_stints_for_circuit(circuit_key, HISTORICAL_YEARS)
            if stints_df.empty:
                logger.warning(f"No stint data for {circuit_key} — using fallback")
                notes.append(f"No historical data for '{circuit_key}'. Using generic fallback.")
            else:
                degradation = compute_degradation(stints_df)
                data_source = "historical"
                years_used = sorted(stints_df["year"].unique().tolist())
                n_stints = stints_df[["year", "driver", "stint_number"]].drop_duplicates().shape[0]
                notes.append(f"Computed from {len(stints_df)} laps across {n_stints} stints.")
        except Exception as e:
            logger.error(f"FastF1 error for {circuit_key}: {e}")
            notes.append(f"FastF1 error: {e}. Using fallback.")

        write_cache(
            "degradation",
            {"compounds": degradation, "data_source": data_source, "years_used": years_used},
            **cache_key_args,
        )

    # ---- Temperature adjustment ----
    if track_temp is not None:
        degradation = apply_temp_adjustment(degradation, track_temp)
        notes.append(f"Temp-adjusted to {track_temp}°C (heuristic: rate *= (temp/25)^1.2).")

    notes.append(
        "Model: linear + quadratic cliff. "
        "Averaged across drivers/stints. Ignores fuel, traffic, SC, 2026 reg changes."
    )

    return DegradationResponse(
        circuit=circuit_key,
        years_used=years_used,
        track_temp_c=track_temp,
        data_source=data_source,
        compounds={k: CompoundDegradation(**v) for k, v in degradation.items()},
        notes=notes,
    )
