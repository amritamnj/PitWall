"""
FastF1 data extraction + circuit/compound reference data.

This module is the foundation of the degradation engine. It contains:

1. CIRCUIT_INFO — metadata for all circuits (lat/lon, laps, pit loss, FastF1 event name)
2. COMPOUND_NOMINATIONS — Pirelli's per-race compound selection (C1–C5)
3. FastF1 stint extraction — loads historical sessions, maps SOFT/MEDIUM/HARD → actual C-number
4. Degradation computation — per C-number, with piecewise linear + quadratic cliff model

Degradation model (piecewise linear + quadratic cliff):
    For lap n in stint (0-indexed):
        delta(n) = n * deg_rate                                  [linear phase]
                 + cliff_rate * max(0, n - cliff_onset)^2        [cliff phase]

    The cliff term penalises running beyond the tyre's thermal/mechanical limit.
    This is what makes 2-stop strategies competitive: accumulated cliff penalty
    on a long stint can exceed the ~22s pit-lane time loss.

Compound system:
    Pirelli nominates 3 dry slick compounds per race from C1 (hardest) to C5 (softest).
    The SAME C-number has the SAME chemistry everywhere — C3 at Bahrain has the same
    construction as C3 at Monaco. What changes is the ROLE: C3 is the "soft" at Bahrain
    but the "hard" at Monaco. Degradation is tied to the compound chemistry + track surface,
    so we compute and cache degradation per C-number per circuit.

Limitations:
    - Degradation averaged across drivers/stints; ignores traffic, SC, fuel load
    - 2026 regs change tyre construction → 2023-2025 data is a proxy only
    - Cliff detection is heuristic (quadratic fit to pooled stint residuals)
"""

import logging
import unicodedata
from pathlib import Path
from typing import Any

import fastf1
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# FastF1 built-in cache for raw session data
FASTF1_CACHE_DIR = Path(__file__).resolve().parent.parent / "cache" / "fastf1"
FASTF1_CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(FASTF1_CACHE_DIR))

HISTORICAL_YEARS = [2023, 2024, 2025]
DRY_COMPOUNDS = {"SOFT", "MEDIUM", "HARD"}


# =============================================================================
# Circuit metadata — keyed by normalized circuit_short_name (lowercase, no accents)
# =============================================================================

CIRCUIT_INFO: dict[str, dict[str, Any]] = {
    "bahrain": {
        "full_name": "Bahrain International Circuit",
        "country": "Bahrain",
        "fastf1_name": "Bahrain Grand Prix",
        "lat": 26.0325, "lon": 50.5106,
        "laps": 57, "length_km": 5.412, "pit_loss": 20,
    },
    "jeddah": {
        "full_name": "Jeddah Corniche Circuit",
        "country": "Saudi Arabia",
        "fastf1_name": "Saudi Arabian Grand Prix",
        "lat": 21.6319, "lon": 39.1044,
        "laps": 50, "length_km": 6.174, "pit_loss": 23,
    },
    "melbourne": {
        "full_name": "Albert Park Circuit",
        "country": "Australia",
        "fastf1_name": "Australian Grand Prix",
        "lat": -37.8497, "lon": 144.9683,
        "laps": 58, "length_km": 5.278, "pit_loss": 22,
    },
    "suzuka": {
        "full_name": "Suzuka Circuit",
        "country": "Japan",
        "fastf1_name": "Japanese Grand Prix",
        "lat": 34.8431, "lon": 136.5410,
        "laps": 53, "length_km": 5.807, "pit_loss": 24,
    },
    "shanghai": {
        "full_name": "Shanghai International Circuit",
        "country": "China",
        "fastf1_name": "Chinese Grand Prix",
        "lat": 31.3389, "lon": 121.2200,
        "laps": 56, "length_km": 5.451, "pit_loss": 23,
    },
    "miami": {
        "full_name": "Miami International Autodrome",
        "country": "United States",
        "fastf1_name": "Miami Grand Prix",
        "lat": 25.9581, "lon": -80.2389,
        "laps": 57, "length_km": 5.412, "pit_loss": 21,
    },
    "imola": {
        "full_name": "Autodromo Enzo e Dino Ferrari",
        "country": "Italy",
        "fastf1_name": "Emilia Romagna Grand Prix",
        "lat": 44.3439, "lon": 11.7167,
        "laps": 63, "length_km": 4.909, "pit_loss": 22,
    },
    "monaco": {
        "full_name": "Circuit de Monaco",
        "country": "Monaco",
        "fastf1_name": "Monaco Grand Prix",
        "lat": 43.7347, "lon": 7.4206,
        "laps": 78, "length_km": 3.337, "pit_loss": 18,
    },
    "montreal": {
        "full_name": "Circuit Gilles Villeneuve",
        "country": "Canada",
        "fastf1_name": "Canadian Grand Prix",
        "lat": 45.5017, "lon": -73.5228,
        "laps": 70, "length_km": 4.361, "pit_loss": 20,
    },
    "barcelona": {
        "full_name": "Circuit de Barcelona-Catalunya",
        "country": "Spain",
        "fastf1_name": "Spanish Grand Prix",
        "lat": 41.5700, "lon": 2.2611,
        "laps": 66, "length_km": 4.675, "pit_loss": 22,
    },
    "spielberg": {
        "full_name": "Red Bull Ring",
        "country": "Austria",
        "fastf1_name": "Austrian Grand Prix",
        "lat": 47.2197, "lon": 14.7647,
        "laps": 71, "length_km": 4.318, "pit_loss": 19,
    },
    "silverstone": {
        "full_name": "Silverstone Circuit",
        "country": "United Kingdom",
        "fastf1_name": "British Grand Prix",
        "lat": 52.0786, "lon": -1.0169,
        "laps": 52, "length_km": 5.891, "pit_loss": 22,
    },
    "budapest": {
        "full_name": "Hungaroring",
        "country": "Hungary",
        "fastf1_name": "Hungarian Grand Prix",
        "lat": 47.5789, "lon": 19.2486,
        "laps": 70, "length_km": 4.381, "pit_loss": 21,
    },
    "spa-francorchamps": {
        "full_name": "Circuit de Spa-Francorchamps",
        "country": "Belgium",
        "fastf1_name": "Belgian Grand Prix",
        "lat": 50.4372, "lon": 5.9714,
        "laps": 44, "length_km": 7.004, "pit_loss": 23,
    },
    "zandvoort": {
        "full_name": "Circuit Zandvoort",
        "country": "Netherlands",
        "fastf1_name": "Dutch Grand Prix",
        "lat": 52.3888, "lon": 4.5409,
        "laps": 72, "length_km": 4.259, "pit_loss": 20,
    },
    "monza": {
        "full_name": "Autodromo Nazionale Monza",
        "country": "Italy",
        "fastf1_name": "Italian Grand Prix",
        "lat": 45.6156, "lon": 9.2811,
        "laps": 53, "length_km": 5.793, "pit_loss": 24,
    },
    "baku": {
        "full_name": "Baku City Circuit",
        "country": "Azerbaijan",
        "fastf1_name": "Azerbaijan Grand Prix",
        "lat": 40.3725, "lon": 49.8533,
        "laps": 51, "length_km": 6.003, "pit_loss": 23,
    },
    "singapore": {
        "full_name": "Marina Bay Street Circuit",
        "country": "Singapore",
        "fastf1_name": "Singapore Grand Prix",
        "lat": 1.2914, "lon": 103.8644,
        "laps": 62, "length_km": 4.940, "pit_loss": 22,
    },
    "austin": {
        "full_name": "Circuit of the Americas",
        "country": "United States",
        "fastf1_name": "United States Grand Prix",
        "lat": 30.1328, "lon": -97.6411,
        "laps": 56, "length_km": 5.513, "pit_loss": 22,
    },
    "mexico city": {
        "full_name": "Autódromo Hermanos Rodríguez",
        "country": "Mexico",
        "fastf1_name": "Mexico City Grand Prix",
        "lat": 19.4042, "lon": -99.0907,
        "laps": 71, "length_km": 4.304, "pit_loss": 21,
    },
    "sao paulo": {
        "full_name": "Autódromo José Carlos Pace",
        "country": "Brazil",
        "fastf1_name": "São Paulo Grand Prix",
        "lat": -23.7036, "lon": -46.6997,
        "laps": 71, "length_km": 4.309, "pit_loss": 21,
    },
    "las vegas": {
        "full_name": "Las Vegas Strip Street Circuit",
        "country": "United States",
        "fastf1_name": "Las Vegas Grand Prix",
        "lat": 36.1699, "lon": -115.1398,
        "laps": 50, "length_km": 6.201, "pit_loss": 23,
    },
    "lusail": {
        "full_name": "Lusail International Circuit",
        "country": "Qatar",
        "fastf1_name": "Qatar Grand Prix",
        "lat": 25.4900, "lon": 51.4543,
        "laps": 57, "length_km": 5.419, "pit_loss": 21,
    },
    "yas marina": {
        "full_name": "Yas Marina Circuit",
        "country": "United Arab Emirates",
        "fastf1_name": "Abu Dhabi Grand Prix",
        "lat": 24.4672, "lon": 54.6031,
        "laps": 58, "length_km": 5.281, "pit_loss": 22,
    },
    "madrid": {
        "full_name": "Madrid Street Circuit",
        "country": "Spain",
        "fastf1_name": "Madrid Grand Prix",
        "lat": 40.4168, "lon": -3.7038,
        "laps": 66, "length_km": 5.470, "pit_loss": 22,
    },
}


# =============================================================================
# Pirelli compound nominations per race (year, circuit_key) → {role: Cx}
#
# Source: Pirelli pre-race announcements. 2024 is verified; 2025/2026 use
# 2024 as template (update manually as Pirelli announces each race).
# =============================================================================

COMPOUND_NOMINATIONS: dict[tuple[int, str], dict[str, str]] = {
    # ---- 2024 season ----
    (2024, "bahrain"):           {"hard": "C1", "medium": "C2", "soft": "C3"},
    (2024, "jeddah"):            {"hard": "C2", "medium": "C3", "soft": "C4"},
    (2024, "melbourne"):         {"hard": "C2", "medium": "C3", "soft": "C4"},
    (2024, "suzuka"):            {"hard": "C1", "medium": "C2", "soft": "C3"},
    (2024, "shanghai"):          {"hard": "C2", "medium": "C3", "soft": "C4"},
    (2024, "miami"):             {"hard": "C2", "medium": "C3", "soft": "C4"},
    (2024, "imola"):             {"hard": "C2", "medium": "C3", "soft": "C4"},
    (2024, "monaco"):            {"hard": "C3", "medium": "C4", "soft": "C5"},
    (2024, "montreal"):          {"hard": "C3", "medium": "C4", "soft": "C5"},
    (2024, "barcelona"):         {"hard": "C1", "medium": "C2", "soft": "C3"},
    (2024, "spielberg"):         {"hard": "C2", "medium": "C3", "soft": "C4"},
    (2024, "silverstone"):       {"hard": "C1", "medium": "C2", "soft": "C3"},
    (2024, "budapest"):          {"hard": "C2", "medium": "C3", "soft": "C4"},
    (2024, "spa-francorchamps"): {"hard": "C1", "medium": "C2", "soft": "C3"},
    (2024, "zandvoort"):         {"hard": "C1", "medium": "C2", "soft": "C3"},
    (2024, "monza"):             {"hard": "C2", "medium": "C3", "soft": "C4"},
    (2024, "baku"):              {"hard": "C2", "medium": "C3", "soft": "C4"},
    (2024, "singapore"):         {"hard": "C3", "medium": "C4", "soft": "C5"},
    (2024, "austin"):            {"hard": "C2", "medium": "C3", "soft": "C4"},
    (2024, "mexico city"):       {"hard": "C2", "medium": "C3", "soft": "C4"},
    (2024, "sao paulo"):         {"hard": "C2", "medium": "C3", "soft": "C4"},
    (2024, "las vegas"):         {"hard": "C2", "medium": "C3", "soft": "C4"},
    (2024, "lusail"):            {"hard": "C1", "medium": "C2", "soft": "C3"},
    (2024, "yas marina"):        {"hard": "C2", "medium": "C3", "soft": "C4"},
    # ---- 2025 uses 2024 as baseline (update from Pirelli press releases) ----
    # Lookup function falls back to 2024 if (2025, circuit) is not found.
    # ---- 2026: new tyre regs — populate from Pirelli once announced ----
    # Lookup function falls back to most recent year.
}


# =============================================================================
# Fallback degradation per absolute compound (C1–C5)
#
# These represent the INHERENT characteristics of each compound's chemistry,
# independent of which circuit it runs at. Circuit-specific effects (surface
# roughness, corner load, temperature) are captured by the FastF1 historical
# extraction. These are generic fallbacks for when no historical data exists.
#
# Calibrated to approximate 2023–2024 Pirelli behaviour:
#   C5 (softest): peak grip, highest deg, short stints (~12–18 laps)
#   C1 (hardest): lowest grip, lowest deg, marathon stints (~40+ laps)
# =============================================================================

FALLBACK_COMPOUND_DATA: dict[str, dict[str, Any]] = {
    "C1": {
        "avg_deg_s_per_lap": 0.030,
        "cliff_onset_lap": 35,
        "cliff_rate_s_per_lap2": 0.006,
        "typical_max_stint_laps": 45,
        "avg_reference_lap_s": 84.0,
        "base_pace_offset": 2.0,
    },
    "C2": {
        "avg_deg_s_per_lap": 0.045,
        "cliff_onset_lap": 30,
        "cliff_rate_s_per_lap2": 0.008,
        "typical_max_stint_laps": 40,
        "avg_reference_lap_s": 83.3,
        "base_pace_offset": 1.3,
    },
    "C3": {
        "avg_deg_s_per_lap": 0.065,
        "cliff_onset_lap": 24,
        "cliff_rate_s_per_lap2": 0.012,
        "typical_max_stint_laps": 32,
        "avg_reference_lap_s": 82.7,
        "base_pace_offset": 0.7,
    },
    "C4": {
        "avg_deg_s_per_lap": 0.095,
        "cliff_onset_lap": 18,
        "cliff_rate_s_per_lap2": 0.025,
        "typical_max_stint_laps": 25,
        "avg_reference_lap_s": 82.2,
        "base_pace_offset": 0.2,
    },
    "C5": {
        "avg_deg_s_per_lap": 0.140,
        "cliff_onset_lap": 12,
        "cliff_rate_s_per_lap2": 0.035,
        "typical_max_stint_laps": 18,
        "avg_reference_lap_s": 82.0,
        "base_pace_offset": 0.0,
    },
}


# =============================================================================
# Utility functions
# =============================================================================

def normalize_circuit_name(name: str) -> str:
    """Lowercase + strip Unicode accents: 'Montréal' → 'montreal', 'São Paulo' → 'sao paulo'."""
    nfkd = unicodedata.normalize("NFKD", name)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def get_circuit_info(circuit_key: str) -> dict[str, Any] | None:
    """Look up circuit metadata by normalized key."""
    return CIRCUIT_INFO.get(normalize_circuit_name(circuit_key))


def get_compound_nominations(year: int, circuit_key: str) -> dict[str, str]:
    """
    Get Pirelli compound nominations for a race.

    Returns {"hard": "Cx", "medium": "Cy", "soft": "Cz"}.
    Falls back to most recent year if exact year not found,
    then to generic C2/C3/C4 as ultimate fallback.
    """
    key = normalize_circuit_name(circuit_key)
    for y in range(year, 2022, -1):
        if (y, key) in COMPOUND_NOMINATIONS:
            return COMPOUND_NOMINATIONS[(y, key)]
    return {"hard": "C2", "medium": "C3", "soft": "C4"}


def _role_to_code(year: int, circuit_key: str, role: str) -> str:
    """Map FastF1 compound role (SOFT/MEDIUM/HARD) → Pirelli code (C1–C5)."""
    noms = get_compound_nominations(year, circuit_key)
    mapping = {"SOFT": noms["soft"], "MEDIUM": noms["medium"], "HARD": noms["hard"]}
    return mapping.get(role, role)


# =============================================================================
# FastF1 data loading
# =============================================================================

def load_stints_for_circuit(circuit_key: str, years: list[int] | None = None) -> pd.DataFrame:
    """
    Load historical stint data from FastF1 and map compounds to C-numbers.

    Returns DataFrame: year, driver, stint_number, compound_code, lap_in_stint, lap_time_seconds
    """
    years = years or HISTORICAL_YEARS
    info = get_circuit_info(circuit_key)
    if not info or "fastf1_name" not in info:
        logger.warning(f"No FastF1 mapping for circuit: {circuit_key}")
        return pd.DataFrame()

    fastf1_name = info["fastf1_name"]
    all_stints: list[pd.DataFrame] = []

    for year in years:
        try:
            logger.info(f"Loading {year} {fastf1_name} from FastF1...")
            session = fastf1.get_session(year, fastf1_name, "R")
            session.load(laps=True, telemetry=False, weather=False, messages=False)
        except Exception as e:
            logger.warning(f"Could not load {year} {fastf1_name}: {e}")
            continue

        laps = session.laps
        mask = (
            laps["IsAccurate"]
            & ~laps["PitInTime"].notna()
            & ~laps["PitOutTime"].notna()
        )
        clean_laps = laps[mask].copy()
        if clean_laps.empty:
            continue

        clean_laps["LapTimeSec"] = clean_laps["LapTime"].dt.total_seconds()
        clean_laps = clean_laps[clean_laps["LapTimeSec"].between(60, 180)]

        for (driver, stint_num), group in clean_laps.groupby(["Driver", "Stint"]):
            role = group["Compound"].iloc[0]
            if role not in DRY_COMPOUNDS:
                continue

            # Map SOFT/MEDIUM/HARD → actual C-number for this year & circuit
            compound_code = _role_to_code(year, circuit_key, role)

            sorted_group = group.sort_values("LapNumber")
            lap_times = sorted_group["LapTimeSec"].values
            if len(lap_times) < 3:
                continue

            stint_df = pd.DataFrame({
                "year": year,
                "driver": driver,
                "stint_number": stint_num,
                "compound_code": compound_code,
                "lap_in_stint": range(1, len(lap_times) + 1),
                "lap_time_seconds": lap_times,
            })
            all_stints.append(stint_df)

    if not all_stints:
        return pd.DataFrame()
    return pd.concat(all_stints, ignore_index=True)


# =============================================================================
# Degradation computation
# =============================================================================

def compute_degradation(stints_df: pd.DataFrame) -> dict[str, Any]:
    """
    Compute per-compound-code degradation with cliff detection.

    Returns dict keyed by compound code ("C2", "C3", etc.) with:
        avg_deg_s_per_lap, cliff_onset_lap, cliff_rate_s_per_lap2,
        typical_max_stint_laps, avg_reference_lap_s, base_pace_offset
    """
    if stints_df.empty:
        return dict(FALLBACK_COMPOUND_DATA)

    results: dict[str, Any] = {}
    codes_found = stints_df["compound_code"].unique()

    for code in codes_found:
        code_data = stints_df[stints_df["compound_code"] == code]
        if code_data.empty:
            continue

        slopes: list[float] = []
        max_laps_list: list[int] = []
        reference_times: list[float] = []
        all_curves: list[tuple[np.ndarray, np.ndarray]] = []

        for _, stint in code_data.groupby(["year", "driver", "stint_number"]):
            stint_clean = stint[stint["lap_in_stint"] > 1].copy()
            if len(stint_clean) < 2:
                continue

            ref_time = stint_clean["lap_time_seconds"].iloc[0]
            reference_times.append(ref_time)

            laps_from_ref = stint_clean["lap_in_stint"].values - stint_clean["lap_in_stint"].values[0]
            deltas = stint_clean["lap_time_seconds"].values - ref_time

            if len(laps_from_ref) >= 2:
                slope, _ = np.polyfit(laps_from_ref, deltas, 1)
                slopes.append(max(slope, 0.0))

            all_curves.append((laps_from_ref, deltas))
            max_laps_list.append(stint_clean["lap_in_stint"].max())

        if not slopes:
            continue

        avg_deg = float(np.mean(slopes))
        typical_max = int(np.percentile(max_laps_list, 75)) if max_laps_list else 30
        avg_ref = float(np.mean(reference_times)) if reference_times else 85.0

        cliff_onset, cliff_rate = _detect_cliff(all_curves, avg_deg, typical_max, code)

        results[code] = {
            "avg_deg_s_per_lap": round(avg_deg, 4),
            "cliff_onset_lap": cliff_onset,
            "cliff_rate_s_per_lap2": round(cliff_rate, 5),
            "typical_max_stint_laps": typical_max,
            "avg_reference_lap_s": round(avg_ref, 3),
        }

    if not results:
        return dict(FALLBACK_COMPOUND_DATA)

    # Compute base_pace_offset relative to the softest compound found
    softest_code = max(results.keys(), key=lambda c: int(c[1]))
    softest_ref = results[softest_code]["avg_reference_lap_s"]
    for code in results:
        offset = results[code]["avg_reference_lap_s"] - softest_ref
        results[code]["base_pace_offset"] = round(max(offset, 0.0), 3)

    # Fill missing C-numbers with fallback data
    for code, fallback in FALLBACK_COMPOUND_DATA.items():
        if code not in results:
            results[code] = dict(fallback)

    return results


def _detect_cliff(
    stint_curves: list[tuple[np.ndarray, np.ndarray]],
    linear_deg: float,
    typical_max: int,
    compound_code: str,
) -> tuple[int, float]:
    """
    Detect cliff onset and quadratic rate from pooled stint data.

    Pools all stints into lap bins, computes mean delta, subtracts linear model,
    finds where residuals exceed threshold, then fits quadratic to the tail.
    Falls back to compound-specific heuristics when data is sparse.
    """
    # Heuristic defaults tied to compound softness
    code_num = int(compound_code[1]) if compound_code.startswith("C") and compound_code[1:].isdigit() else 3
    heuristic_onset = max(8, 40 - code_num * 6)  # C1→34, C3→22, C5→10
    heuristic_rate = 0.005 + code_num * 0.006     # C1→0.011, C3→0.023, C5→0.035

    if not stint_curves or typical_max < 6:
        return heuristic_onset, round(heuristic_rate, 5)

    max_lap = max(c[0].max() for c in stint_curves if len(c[0]) > 0)
    if max_lap < 4:
        return heuristic_onset, round(heuristic_rate, 5)

    # Pool into bins
    bin_deltas: dict[int, list[float]] = {}
    for laps, deltas in stint_curves:
        for lap, delta in zip(laps, deltas):
            bin_deltas.setdefault(int(lap), []).append(delta)

    bins_sorted = sorted(bin_deltas.keys())
    mean_deltas = np.array([np.mean(bin_deltas[b]) for b in bins_sorted])
    bins_arr = np.array(bins_sorted, dtype=float)

    if len(bins_arr) < 4:
        return heuristic_onset, round(heuristic_rate, 5)

    # Residuals from linear model
    residuals = mean_deltas - linear_deg * bins_arr

    cliff_onset = None
    for i, (b, r) in enumerate(zip(bins_sorted, residuals)):
        if r > 0.15 and i >= len(bins_sorted) // 3:
            cliff_onset = int(b)
            break

    if cliff_onset is None:
        return heuristic_onset, round(heuristic_rate, 5)

    # Fit quadratic to post-cliff residuals
    post_mask = bins_arr >= cliff_onset
    post_bins = bins_arr[post_mask] - cliff_onset
    post_residuals = residuals[post_mask]

    if len(post_bins) < 2:
        return cliff_onset + 2, round(heuristic_rate, 5)

    try:
        coeffs = np.polyfit(post_bins, post_residuals, 2)
        cliff_rate = max(float(coeffs[0]), 0.005)
    except Exception:
        cliff_rate = heuristic_rate

    return cliff_onset + 2, round(cliff_rate, 5)


def apply_temp_adjustment(degradation: dict[str, Any], track_temp_c: float) -> dict[str, Any]:
    """
    Adjust degradation rates for track temperature.

    Heuristic: multiplier = (track_temp / 25.0) ** 1.2
    Softer compounds (higher C-number) are MORE sensitive to heat:
      effective_multiplier = multiplier * (1 + 0.05 * (code_num - 3))
    So C5 gets a larger temp effect than C1, which matches Pirelli data.

    At 25°C (baseline): multiplier = 1.0
    At 45°C: multiplier ≈ 2.0 (double degradation)
    At 15°C: multiplier ≈ 0.5 (half degradation)
    """
    base_mult = (track_temp_c / 25.0) ** 1.2

    adjusted = {}
    for code, data in degradation.items():
        # Softer compounds get extra sensitivity
        code_num = int(code[1]) if code.startswith("C") and code[1:].isdigit() else 3
        sensitivity = 1.0 + 0.05 * (code_num - 3)
        mult = base_mult * sensitivity

        cliff_onset = data.get("cliff_onset_lap", 20)
        cliff_rate = data.get("cliff_rate_s_per_lap2", 0.015)

        adjusted[code] = {
            **data,
            "avg_deg_s_per_lap": round(data["avg_deg_s_per_lap"] * mult, 4),
            "cliff_onset_lap": max(5, int(cliff_onset / max(mult ** 0.5, 0.5))),
            "cliff_rate_s_per_lap2": round(cliff_rate * mult, 5),
            "typical_max_stint_laps": max(5, int(data["typical_max_stint_laps"] / max(mult, 0.5))),
            "temp_multiplier": round(mult, 3),
        }
    return adjusted
