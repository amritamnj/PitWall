"""
Historical strategy analysis — computes CircuitHistoricalProfile data
from FastF1 race sessions.

All functions return plain dicts suitable for Pydantic model construction.
Every sub-computation returns None when data is insufficient and appends
an explanation to the shared notes list.
"""

import logging
from collections import Counter
from typing import Any, Optional

import fastf1
import numpy as np
import pandas as pd

from utils.fastf1_helpers import (
    DRY_COMPOUNDS,
    FASTF1_CACHE_DIR,
    get_circuit_info,
)

logger = logging.getLogger(__name__)

# Minimum thresholds for meaningful statistics
MIN_RACES_FOR_STATS = 1
MIN_DRIVERS_FOR_IQR = 4
UNDERCUT_GAP_THRESHOLD_S = 3.0   # max gap (seconds) for an undercut attempt
UNDERCUT_LAP_WINDOW = 3          # pitting 1-3 laps before rival


# =============================================================================
# Main entry point
# =============================================================================

def compute_historical_profile(
    circuit_key: str,
    years: list[int],
    circuit_info: dict[str, Any],
) -> dict[str, Any]:
    """
    Load FastF1 sessions for each year, extract race-level data,
    and compute all profile sub-components.

    Returns a dict ready to be unpacked into CircuitHistoricalProfile.
    """
    fastf1_name = circuit_info["fastf1_name"]
    total_laps = circuit_info.get("laps", 58)
    notes: list[str] = []

    sessions_data: list[dict] = []

    for year in years:
        try:
            logger.info(f"Loading {year} {fastf1_name} for historical analysis...")
            session = fastf1.get_session(year, fastf1_name, "R")
            session.load(
                laps=True, telemetry=False, weather=False, messages=True,
            )
            race_data = _extract_race_data(session, year)
            if race_data is not None:
                sessions_data.append(race_data)
            else:
                notes.append(f"{year}: no usable lap data.")
        except Exception as e:
            logger.warning(f"Could not load {year} {fastf1_name}: {e}")
            notes.append(f"Skipped {year}: {e}")

    seasons_used = sorted({rd["year"] for rd in sessions_data})
    races_used = len(sessions_data)

    if races_used == 0:
        notes.append("No historical races loaded. Profile is empty.")
        return {
            "seasons_used": years,
            "races_used": 0,
            "common_strategy_sequences": [],
            "notes": notes,
        }

    first_stop = _compute_first_stop_stats(sessions_data, notes)
    stop_dist = _compute_stop_count_distribution(sessions_data, notes)
    sequences = _compute_common_sequences(sessions_data, notes)
    sc_histogram = _compute_safety_car_histogram(sessions_data, total_laps, notes)
    undercut_overcut = _compute_undercut_overcut(sessions_data, notes)
    warmup = _compute_outlap_penalty(sessions_data, notes)

    notes.append(
        f"Computed from {races_used} race(s) across {len(seasons_used)} season(s)."
    )

    return {
        "seasons_used": seasons_used,
        "races_used": races_used,
        "first_stop_lap": first_stop,
        "stop_count_distribution": stop_dist,
        "common_strategy_sequences": sequences,
        "safety_car_lap_histogram": sc_histogram,
        "undercut_overcut": undercut_overcut,
        "warmup_traffic": warmup,
        "notes": notes,
    }


# =============================================================================
# Data extraction from a single FastF1 session
# =============================================================================

def _extract_race_data(session, year: int) -> Optional[dict]:
    """
    Extract per-driver stint info, pit stop laps, race control messages,
    and all laps from a single FastF1 session.
    """
    laps = session.laps
    if laps is None or laps.empty:
        return None

    # --- Driver stints ---
    driver_stints: dict[str, list[dict]] = {}
    for driver in laps["Driver"].unique():
        d_laps = laps[laps["Driver"] == driver].sort_values("LapNumber")
        stints: list[dict] = []
        for stint_num in sorted(d_laps["Stint"].dropna().unique()):
            stint_laps = d_laps[d_laps["Stint"] == stint_num]
            if stint_laps.empty:
                continue
            compound = stint_laps["Compound"].iloc[0]
            start_lap = int(stint_laps["LapNumber"].min())
            end_lap = int(stint_laps["LapNumber"].max())
            stints.append({
                "stint_num": int(stint_num),
                "compound": str(compound) if pd.notna(compound) else "UNKNOWN",
                "start_lap": start_lap,
                "end_lap": end_lap,
                "laps": end_lap - start_lap + 1,
            })
        if stints:
            driver_stints[str(driver)] = stints

    if not driver_stints:
        return None

    # --- Pit stops ---
    pit_stops: list[dict] = []
    pit_laps = laps[laps["PitInTime"].notna()]
    for _, row in pit_laps.iterrows():
        pit_stops.append({
            "driver": str(row["Driver"]),
            "lap": int(row["LapNumber"]),
        })

    # --- Race control messages (for safety car data) ---
    race_control: list[dict] = []
    try:
        rcm = session.race_control_messages
        if rcm is not None and not rcm.empty:
            for _, msg in rcm.iterrows():
                category = str(msg.get("Category", ""))
                message = str(msg.get("Message", ""))
                lap_num = msg.get("Lap", None)
                if lap_num is not None and pd.notna(lap_num):
                    race_control.append({
                        "lap": int(lap_num),
                        "category": category,
                        "message": message,
                    })
    except Exception as e:
        logger.debug(f"No race control messages for {year}: {e}")

    # --- All laps DataFrame for undercut/overcut analysis ---
    all_laps_df = None
    try:
        cols = ["Driver", "LapNumber", "LapTime", "Position", "Stint",
                "PitInTime", "PitOutTime"]
        available = [c for c in cols if c in laps.columns]
        subset = laps[available].copy()
        if "LapTime" in subset.columns:
            subset["LapTimeSec"] = subset["LapTime"].dt.total_seconds()
        all_laps_df = subset
    except Exception:
        pass

    return {
        "year": year,
        "driver_stints": driver_stints,
        "pit_stops": pit_stops,
        "race_control": race_control,
        "all_laps": all_laps_df,
    }


# =============================================================================
# First stop lap statistics
# =============================================================================

def _compute_first_stop_stats(
    sessions_data: list[dict],
    notes: list[str],
) -> Optional[dict]:
    """
    Collect first pit stop laps across all races/drivers.
    Return {median, p25, p75, iqr, n} or None.
    """
    first_stop_laps: list[int] = []

    for race in sessions_data:
        for driver, stints in race["driver_stints"].items():
            if len(stints) < 2:
                continue  # no pit stop
            first_stop_lap = stints[0]["end_lap"]
            # Skip lap-1 damage stops
            if first_stop_lap <= 1:
                continue
            first_stop_laps.append(first_stop_lap)

    if len(first_stop_laps) < MIN_DRIVERS_FOR_IQR:
        notes.append(
            f"First stop: only {len(first_stop_laps)} data points "
            f"(need {MIN_DRIVERS_FOR_IQR}). Insufficient."
        )
        return None

    arr = np.array(first_stop_laps, dtype=float)
    p25 = float(np.percentile(arr, 25))
    median = float(np.median(arr))
    p75 = float(np.percentile(arr, 75))

    return {
        "median": round(median, 1),
        "p25": round(p25, 1),
        "p75": round(p75, 1),
        "iqr": round(p75 - p25, 1),
        "n": len(first_stop_laps),
    }


# =============================================================================
# Stop count distribution
# =============================================================================

def _compute_stop_count_distribution(
    sessions_data: list[dict],
    notes: list[str],
) -> Optional[dict]:
    """
    Count 1-stop, 2-stop, 3+ per driver per race. Return distribution.
    """
    stop_counts: list[int] = []

    for race in sessions_data:
        for driver, stints in race["driver_stints"].items():
            stops = len(stints) - 1  # stints = stops + 1
            if stops < 0:
                stops = 0
            stop_counts.append(stops)

    if not stop_counts:
        notes.append("Stop count: no data available.")
        return None

    n = len(stop_counts)
    one = sum(1 for s in stop_counts if s == 1)
    two = sum(1 for s in stop_counts if s == 2)
    three_plus = sum(1 for s in stop_counts if s >= 3)

    return {
        "one_stop_pct": round(one / n * 100, 1),
        "two_stop_pct": round(two / n * 100, 1),
        "three_plus_pct": round(three_plus / n * 100, 1),
        "n": n,
    }


# =============================================================================
# Common strategy sequences
# =============================================================================

def _compute_common_sequences(
    sessions_data: list[dict],
    notes: list[str],
    top_n: int = 5,
) -> list[dict]:
    """
    Extract compound sequences per driver, find most common.
    Uses compound role names (SOFT/MEDIUM/HARD).
    """
    all_sequences: list[tuple[str, ...]] = []

    for race in sessions_data:
        for driver, stints in race["driver_stints"].items():
            compounds = [s["compound"] for s in stints]
            # Filter out UNKNOWN compounds
            if any(c == "UNKNOWN" for c in compounds):
                continue
            all_sequences.append(tuple(compounds))

    if not all_sequences:
        notes.append("Strategy sequences: no usable data.")
        return []

    counter = Counter(all_sequences)
    total = len(all_sequences)
    result: list[dict] = []

    for seq, count in counter.most_common(top_n):
        result.append({
            "stops": len(seq) - 1,
            "sequence": list(seq),
            "frequency_pct": round(count / total * 100, 1),
            "n": count,
        })

    return result


# =============================================================================
# Safety car lap histogram
# =============================================================================

def _compute_safety_car_histogram(
    sessions_data: list[dict],
    total_laps: int,
    notes: list[str],
    bucket_size: int = 5,
) -> Optional[dict[str, float]]:
    """
    From race control messages, extract SC deployment laps.
    Build histogram: probability per lap bucket across races.
    """
    sc_laps_per_race: list[list[int]] = []
    races_with_rcm = 0

    for race in sessions_data:
        rcm = race.get("race_control", [])
        if not rcm:
            continue
        races_with_rcm += 1
        sc_laps: list[int] = []
        for msg in rcm:
            cat = msg.get("category", "").upper()
            message = msg.get("message", "").upper()
            if "SAFETY CAR" in cat or "SAFETY CAR" in message:
                lap = msg.get("lap")
                if lap and lap > 0:
                    sc_laps.append(lap)
        sc_laps_per_race.append(sc_laps)

    if races_with_rcm == 0:
        notes.append("Safety car: no race control message data available.")
        return None

    # Build bucket histogram
    histogram: dict[str, float] = {}
    for bucket_start in range(1, total_laps + 1, bucket_size):
        bucket_end = min(bucket_start + bucket_size - 1, total_laps)
        key = f"{bucket_start}-{bucket_end}"
        races_with_sc_in_bucket = 0
        for sc_laps in sc_laps_per_race:
            if any(bucket_start <= lap <= bucket_end for lap in sc_laps):
                races_with_sc_in_bucket += 1
        histogram[key] = round(races_with_sc_in_bucket / races_with_rcm, 3)

    return histogram


# =============================================================================
# Undercut / overcut effectiveness
# =============================================================================

def _compute_undercut_overcut(
    sessions_data: list[dict],
    notes: list[str],
) -> Optional[dict]:
    """
    Identify undercut/overcut attempts by comparing pit stop timing
    between drivers who were within a gap threshold before the stop.

    An UNDERCUT attempt: driver A pits, driver B (who was ahead and within
    gap threshold) pits 1-3 laps later. Success: A ends up ahead of B after
    both have pitted.
    """
    undercut_attempts = 0
    undercut_successes = 0
    undercut_gains: list[float] = []
    overcut_attempts = 0
    overcut_successes = 0

    for race in sessions_data:
        all_laps = race.get("all_laps")
        if all_laps is None or all_laps.empty:
            continue
        if "LapTimeSec" not in all_laps.columns or "Position" not in all_laps.columns:
            continue

        pit_stops = race.get("pit_stops", [])
        if not pit_stops:
            continue

        # Build pit stop lookup: driver -> list of pit laps
        driver_pits: dict[str, list[int]] = {}
        for ps in pit_stops:
            driver_pits.setdefault(ps["driver"], []).append(ps["lap"])

        drivers_with_stops = list(driver_pits.keys())

        for i, d_a in enumerate(drivers_with_stops):
            for d_b in drivers_with_stops[i + 1 :]:
                _analyze_pair(
                    all_laps, d_a, d_b, driver_pits,
                    undercut_gains,
                    # Mutable counters via list trick
                    _counters := {
                        "uc_att": 0, "uc_suc": 0,
                        "oc_att": 0, "oc_suc": 0,
                    },
                )
                undercut_attempts += _counters["uc_att"]
                undercut_successes += _counters["uc_suc"]
                overcut_attempts += _counters["oc_att"]
                overcut_successes += _counters["oc_suc"]

    total_attempts = undercut_attempts + overcut_attempts
    if total_attempts == 0:
        notes.append(
            "Undercut/overcut: no qualifying driver pairs found "
            f"(gap <= {UNDERCUT_GAP_THRESHOLD_S}s, 1-{UNDERCUT_LAP_WINDOW} lap offset)."
        )
        return None

    return {
        "undercut_attempts": undercut_attempts,
        "undercut_success_rate": round(
            undercut_successes / undercut_attempts, 3
        ) if undercut_attempts > 0 else 0.0,
        "overcut_attempts": overcut_attempts,
        "overcut_success_rate": round(
            overcut_successes / overcut_attempts, 3
        ) if overcut_attempts > 0 else 0.0,
        "typical_undercut_gain_s": round(
            float(np.median(undercut_gains)), 2
        ) if undercut_gains else 0.0,
        "notes": (
            f"Computed from {total_attempts} attempt(s). "
            f"Gap threshold: {UNDERCUT_GAP_THRESHOLD_S}s, "
            f"window: 1-{UNDERCUT_LAP_WINDOW} laps."
        ),
    }


def _analyze_pair(
    all_laps: pd.DataFrame,
    d_a: str,
    d_b: str,
    driver_pits: dict[str, list[int]],
    undercut_gains: list[float],
    counters: dict,
) -> None:
    """
    Analyze a single pair of drivers for undercut/overcut attempts.
    Mutates counters dict and undercut_gains list.
    """
    pits_a = sorted(driver_pits.get(d_a, []))
    pits_b = sorted(driver_pits.get(d_b, []))

    for pit_a in pits_a:
        # Find matching pit from B within the window
        matching_b = [
            pb for pb in pits_b
            if 1 <= pb - pit_a <= UNDERCUT_LAP_WINDOW
        ]
        if not matching_b:
            continue

        pit_b = matching_b[0]

        # Check gap before A's stop
        pre_lap = pit_a - 1
        if pre_lap < 1:
            continue

        laps_a_pre = all_laps[
            (all_laps["Driver"] == d_a) & (all_laps["LapNumber"] == pre_lap)
        ]
        laps_b_pre = all_laps[
            (all_laps["Driver"] == d_b) & (all_laps["LapNumber"] == pre_lap)
        ]

        if laps_a_pre.empty or laps_b_pre.empty:
            continue
        if "Position" not in laps_a_pre.columns:
            continue

        pos_a_pre = laps_a_pre["Position"].iloc[0]
        pos_b_pre = laps_b_pre["Position"].iloc[0]

        if pd.isna(pos_a_pre) or pd.isna(pos_b_pre):
            continue

        pos_a_pre = int(pos_a_pre)
        pos_b_pre = int(pos_b_pre)

        # Check gap in seconds (need lap times around this window)
        time_a = laps_a_pre["LapTimeSec"].iloc[0] if "LapTimeSec" in laps_a_pre.columns else None
        time_b = laps_b_pre["LapTimeSec"].iloc[0] if "LapTimeSec" in laps_b_pre.columns else None
        if time_a is None or time_b is None or pd.isna(time_a) or pd.isna(time_b):
            continue

        gap = abs(time_a - time_b)
        if gap > UNDERCUT_GAP_THRESHOLD_S:
            continue

        # Check positions after both have pitted
        post_lap = pit_b + 2  # a couple laps after B pits
        laps_a_post = all_laps[
            (all_laps["Driver"] == d_a) & (all_laps["LapNumber"] == post_lap)
        ]
        laps_b_post = all_laps[
            (all_laps["Driver"] == d_b) & (all_laps["LapNumber"] == post_lap)
        ]

        if laps_a_post.empty or laps_b_post.empty:
            continue

        pos_a_post = laps_a_post["Position"].iloc[0]
        pos_b_post = laps_b_post["Position"].iloc[0]

        if pd.isna(pos_a_post) or pd.isna(pos_b_post):
            continue

        pos_a_post = int(pos_a_post)
        pos_b_post = int(pos_b_post)

        # A pitted first (undercut attempt by A)
        if pos_a_pre > pos_b_pre:
            # A was behind B before
            counters["uc_att"] += 1
            if pos_a_post < pos_b_post:
                # A is now ahead — undercut success
                counters["uc_suc"] += 1
                undercut_gains.append(gap)
        elif pos_b_pre > pos_a_pre:
            # B was behind A; A pitting first means B gets an overcut opportunity
            counters["oc_att"] += 1
            if pos_b_post < pos_a_post:
                counters["oc_suc"] += 1


# =============================================================================
# Pit outlap penalty
# =============================================================================

def _compute_outlap_penalty(
    sessions_data: list[dict],
    notes: list[str],
) -> Optional[dict]:
    """
    Compute average pit outlap penalty relative to a clean lap.
    """
    outlap_deltas: list[float] = []

    for race in sessions_data:
        all_laps = race.get("all_laps")
        if all_laps is None or all_laps.empty:
            continue
        if "LapTimeSec" not in all_laps.columns:
            continue
        if "PitOutTime" not in all_laps.columns:
            continue

        for driver in all_laps["Driver"].unique():
            d_laps = all_laps[all_laps["Driver"] == driver].sort_values("LapNumber")
            if d_laps.empty:
                continue

            # Find outlaps (laps with PitOutTime set)
            outlaps = d_laps[d_laps["PitOutTime"].notna()]
            # Clean laps: no pit in/out, valid time
            clean = d_laps[
                d_laps["PitOutTime"].isna()
                & d_laps["PitInTime"].isna()
                & d_laps["LapTimeSec"].notna()
                & d_laps["LapTimeSec"].between(60, 180)
            ]

            if clean.empty or outlaps.empty:
                continue

            median_clean = clean["LapTimeSec"].median()

            for _, ol in outlaps.iterrows():
                ol_time = ol.get("LapTimeSec")
                if ol_time is not None and pd.notna(ol_time) and 60 < ol_time < 300:
                    outlap_deltas.append(ol_time - median_clean)

    if not outlap_deltas:
        notes.append("Outlap penalty: insufficient data to compute.")
        return None

    median_penalty = float(np.median(outlap_deltas))
    return {"pit_outlap_penalty_s": round(median_penalty, 2)}
