"""
Unit tests for historical strategy intelligence.

Tests core computation functions with synthetic data — no FastF1 required.
Run: cd backend && python -m pytest tests/ -v
"""

import sys
from pathlib import Path

# Ensure backend root is on sys.path so `utils.*` imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.historical_analysis import (
    _compute_common_sequences,
    _compute_first_stop_stats,
    _compute_stop_count_distribution,
)


def _make_race(driver_stints: dict[str, list[dict]]) -> dict:
    """Helper: build a minimal sessions_data entry."""
    return {
        "year": 2024,
        "driver_stints": driver_stints,
        "pit_stops": [],
        "race_control": [],
        "all_laps": None,
    }


# -----------------------------------------------------------------------
# First stop statistics
# -----------------------------------------------------------------------

class TestFirstStopStats:
    def test_basic_computation(self):
        """Three drivers with first stops at laps 12, 15, 18."""
        sessions = [_make_race({
            "VER": [
                {"stint_num": 1, "compound": "MEDIUM", "start_lap": 1, "end_lap": 15, "laps": 15},
                {"stint_num": 2, "compound": "HARD", "start_lap": 16, "end_lap": 57, "laps": 42},
            ],
            "HAM": [
                {"stint_num": 1, "compound": "SOFT", "start_lap": 1, "end_lap": 12, "laps": 12},
                {"stint_num": 2, "compound": "HARD", "start_lap": 13, "end_lap": 57, "laps": 45},
            ],
            "LEC": [
                {"stint_num": 1, "compound": "MEDIUM", "start_lap": 1, "end_lap": 18, "laps": 18},
                {"stint_num": 2, "compound": "HARD", "start_lap": 19, "end_lap": 57, "laps": 39},
            ],
            "NOR": [
                {"stint_num": 1, "compound": "MEDIUM", "start_lap": 1, "end_lap": 16, "laps": 16},
                {"stint_num": 2, "compound": "HARD", "start_lap": 17, "end_lap": 57, "laps": 41},
            ],
        })]
        notes: list[str] = []
        result = _compute_first_stop_stats(sessions, notes)
        assert result is not None
        assert result["n"] == 4
        # First stops: 15, 12, 18, 16 → sorted: 12, 15, 16, 18
        assert result["median"] == 15.5  # median of [12, 15, 16, 18]
        assert result["p25"] <= result["median"] <= result["p75"]
        assert abs(result["iqr"] - (result["p75"] - result["p25"])) < 0.2

    def test_skips_lap1_stops(self):
        """Lap-1 damage stops should be excluded."""
        sessions = [_make_race({
            "D1": [
                {"stint_num": 1, "compound": "SOFT", "start_lap": 1, "end_lap": 1, "laps": 1},
                {"stint_num": 2, "compound": "HARD", "start_lap": 2, "end_lap": 57, "laps": 56},
            ],
        })]
        notes: list[str] = []
        result = _compute_first_stop_stats(sessions, notes)
        # Only 1 data point with lap-1 stop → excluded → insufficient
        assert result is None

    def test_no_stops_returns_none(self):
        """Drivers with zero stops produce no first-stop data."""
        sessions = [_make_race({
            "D1": [{"stint_num": 1, "compound": "HARD", "start_lap": 1, "end_lap": 57, "laps": 57}],
        })]
        notes: list[str] = []
        result = _compute_first_stop_stats(sessions, notes)
        assert result is None

    def test_empty_sessions_returns_none(self):
        notes: list[str] = []
        result = _compute_first_stop_stats([], notes)
        assert result is None


# -----------------------------------------------------------------------
# Stop count distribution
# -----------------------------------------------------------------------

class TestStopCountDistribution:
    def test_mixed_stops(self):
        """6 drivers: 4 one-stop, 1 two-stop, 1 three-stop."""
        driver_stints = {}
        # 1-stop drivers (2 stints each)
        for i in range(4):
            driver_stints[f"D{i}"] = [
                {"stint_num": 1, "compound": "M", "start_lap": 1, "end_lap": 20, "laps": 20},
                {"stint_num": 2, "compound": "H", "start_lap": 21, "end_lap": 57, "laps": 37},
            ]
        # 2-stop driver (3 stints)
        driver_stints["D4"] = [
            {"stint_num": 1, "compound": "S", "start_lap": 1, "end_lap": 12, "laps": 12},
            {"stint_num": 2, "compound": "M", "start_lap": 13, "end_lap": 35, "laps": 23},
            {"stint_num": 3, "compound": "H", "start_lap": 36, "end_lap": 57, "laps": 22},
        ]
        # 3-stop driver (4 stints)
        driver_stints["D5"] = [
            {"stint_num": j + 1, "compound": "S", "start_lap": 1, "end_lap": 10, "laps": 10}
            for j in range(4)
        ]
        sessions = [_make_race(driver_stints)]
        notes: list[str] = []
        result = _compute_stop_count_distribution(sessions, notes)
        assert result is not None
        assert result["n"] == 6
        total_pct = result["one_stop_pct"] + result["two_stop_pct"] + result["three_plus_pct"]
        assert abs(total_pct - 100.0) < 0.2
        assert result["one_stop_pct"] > 60  # 4/6 ≈ 66.7%

    def test_empty_returns_none(self):
        notes: list[str] = []
        result = _compute_stop_count_distribution([], notes)
        assert result is None


# -----------------------------------------------------------------------
# Common strategy sequences
# -----------------------------------------------------------------------

class TestCommonSequences:
    def test_finds_most_common(self):
        """3 drivers on M→H, 1 driver on S→H."""
        driver_stints = {}
        for i in range(3):
            driver_stints[f"D{i}"] = [
                {"stint_num": 1, "compound": "MEDIUM", "start_lap": 1, "end_lap": 20, "laps": 20},
                {"stint_num": 2, "compound": "HARD", "start_lap": 21, "end_lap": 57, "laps": 37},
            ]
        driver_stints["D3"] = [
            {"stint_num": 1, "compound": "SOFT", "start_lap": 1, "end_lap": 15, "laps": 15},
            {"stint_num": 2, "compound": "HARD", "start_lap": 16, "end_lap": 57, "laps": 42},
        ]
        sessions = [_make_race(driver_stints)]
        notes: list[str] = []
        result = _compute_common_sequences(sessions, notes)
        assert len(result) >= 1
        assert result[0]["sequence"] == ["MEDIUM", "HARD"]
        assert result[0]["frequency_pct"] == 75.0
        assert result[0]["stops"] == 1
        assert result[0]["n"] == 3

    def test_unknown_compounds_skipped(self):
        """Drivers with UNKNOWN compounds are excluded."""
        sessions = [_make_race({
            "D1": [
                {"stint_num": 1, "compound": "UNKNOWN", "start_lap": 1, "end_lap": 20, "laps": 20},
                {"stint_num": 2, "compound": "HARD", "start_lap": 21, "end_lap": 57, "laps": 37},
            ],
        })]
        notes: list[str] = []
        result = _compute_common_sequences(sessions, notes)
        assert result == []

    def test_empty_returns_empty(self):
        notes: list[str] = []
        result = _compute_common_sequences([], notes)
        assert result == []
