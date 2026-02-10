"""
Historical alignment scoring — adjusts strategy total_time_s
based on how well the strategy matches historical patterns.

Called from simulate.py when a cached historical profile is available.
Adjustments are small and transparent — each one is logged in
historical_notes on the StrategyResult.
"""

import logging
from typing import Any

from utils.historical_weights import (
    FIRST_STOP_MAX_PENALTY_S,
    FIRST_STOP_OUTSIDE_IQR_PENALTY_PER_LAP,
    HISTORICAL_WEIGHT_MASTER,
    SEQUENCE_MATCH_BONUS_S,
    SEQUENCE_PARTIAL_MATCH_FACTOR,
    STOP_COUNT_ALIGNMENT_BONUS_S,
)

logger = logging.getLogger(__name__)


def apply_historical_alignment(
    strategies: list,
    profile: dict[str, Any],
    compound_to_role: dict[str, str] | None = None,
) -> list:
    """
    Apply historical alignment scoring to each strategy.

    Modifies total_time_s with small adjustments and populates
    historical_adjustment_s and historical_notes on each strategy.

    Args:
        strategies: list of StrategyResult (Pydantic models, mutated in-place)
        profile: CircuitHistoricalProfile dict (from cache)
        compound_to_role: optional mapping of C-codes to roles (e.g. {"C3": "SOFT"})
                          for sequence matching. If not provided, sequences are
                          compared using C-codes directly.

    Returns the same list (mutated).
    """
    if HISTORICAL_WEIGHT_MASTER == 0.0:
        return strategies

    first_stop = profile.get("first_stop_lap")
    stop_dist = profile.get("stop_count_distribution")
    sequences = profile.get("common_strategy_sequences", [])

    for strat in strategies:
        adjustment = 0.0
        notes: list[str] = []

        # 1. First stop IQR check
        if first_stop and strat.stops >= 1 and strat.pit_stop_laps:
            actual_first = strat.pit_stop_laps[0]
            adj, note = _score_first_stop(actual_first, first_stop)
            adjustment += adj
            if note:
                notes.append(note)

        # 2. Sequence match
        if sequences:
            strat_compounds = [s.compound for s in strat.stints]
            adj, note = _score_sequence_match(
                strat_compounds, sequences, compound_to_role,
            )
            adjustment += adj
            if note:
                notes.append(note)

        # 3. Stop count alignment
        if stop_dist:
            adj, note = _score_stop_count(strat.stops, stop_dist)
            adjustment += adj
            if note:
                notes.append(note)

        # Apply master weight
        final_adj = round(adjustment * HISTORICAL_WEIGHT_MASTER, 3)
        strat.total_time_s += final_adj
        strat.historical_adjustment_s = final_adj
        strat.historical_notes = notes

    return strategies


# ---------------------------------------------------------------------------
# Individual scoring functions
# ---------------------------------------------------------------------------

def _score_first_stop(
    actual_lap: int,
    first_stop: dict,
) -> tuple[float, str]:
    """Penalty if first stop is outside historical IQR."""
    p25 = first_stop["p25"]
    p75 = first_stop["p75"]
    median = first_stop["median"]
    n = first_stop["n"]

    if p25 <= actual_lap <= p75:
        return 0.0, (
            f"First stop L{actual_lap} within historical window "
            f"(L{p25:.0f}\u2013L{p75:.0f}, median L{median:.0f}, n={n})"
        )

    distance = max(p25 - actual_lap, actual_lap - p75, 0)
    penalty = min(
        distance * FIRST_STOP_OUTSIDE_IQR_PENALTY_PER_LAP,
        FIRST_STOP_MAX_PENALTY_S,
    )
    return penalty, (
        f"First stop L{actual_lap} is {distance:.0f} laps outside historical IQR "
        f"(L{p25:.0f}\u2013L{p75:.0f}), +{penalty:.1f}s penalty"
    )


def _score_sequence_match(
    strat_compounds: list[str],
    sequences: list[dict],
    compound_to_role: dict[str, str] | None,
) -> tuple[float, str]:
    """Bonus for matching a historically common sequence."""
    # Normalize strategy compounds to roles if mapping available
    strat_roles = strat_compounds
    if compound_to_role:
        strat_roles = [compound_to_role.get(c, c) for c in strat_compounds]

    for seq_info in sequences:
        hist_seq = seq_info["sequence"]
        freq = seq_info["frequency_pct"]

        if _sequences_match(strat_roles, hist_seq):
            bonus = -SEQUENCE_MATCH_BONUS_S * (freq / 100.0)
            seq_str = " \u2192 ".join(hist_seq)
            return bonus, (
                f"Matches historical sequence {seq_str} "
                f"({freq:.0f}% of races)"
            )

        if _sequences_partial_match(strat_roles, hist_seq):
            bonus = (
                -SEQUENCE_MATCH_BONUS_S
                * SEQUENCE_PARTIAL_MATCH_FACTOR
                * (freq / 100.0)
            )
            seq_str = " \u2192 ".join(hist_seq)
            return bonus, (
                f"Partially matches historical {seq_str} ({freq:.0f}%)"
            )

    return 0.0, ""


def _score_stop_count(
    stops: int,
    stop_dist: dict,
) -> tuple[float, str]:
    """Bonus if stop count matches the dominant historical pattern."""
    pcts = {
        1: stop_dist.get("one_stop_pct", 0),
        2: stop_dist.get("two_stop_pct", 0),
    }
    dominant = max(pcts, key=lambda k: pcts[k])
    dominant_pct = pcts[dominant]

    if stops == dominant and dominant_pct > 40:
        bonus = -STOP_COUNT_ALIGNMENT_BONUS_S * (dominant_pct / 100.0)
        return bonus, (
            f"{stops}-stop matches dominant historical pattern "
            f"({dominant_pct:.0f}% of drivers)"
        )

    return 0.0, ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sequences_match(strat_seq: list[str], hist_seq: list[str]) -> bool:
    """Exact sequence match (case-insensitive)."""
    if len(strat_seq) != len(hist_seq):
        return False
    return all(
        a.upper() == b.upper() for a, b in zip(strat_seq, hist_seq)
    )


def _sequences_partial_match(strat_seq: list[str], hist_seq: list[str]) -> bool:
    """Same set of compounds, different order."""
    if len(strat_seq) != len(hist_seq):
        return False
    return sorted(s.upper() for s in strat_seq) == sorted(
        s.upper() for s in hist_seq
    )
