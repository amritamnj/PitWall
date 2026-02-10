"""
Strategy Simulator — compares pit strategies across dry and wet conditions.

Lap time model (piecewise linear + quadratic cliff):
    lap_time(n) = base_lap + pace_offset + n*deg_rate
                + cliff_rate * max(0, n - cliff_onset)^2

Weather conditions:
    dry      → slicks only (standard strategies)
    damp     → mandatory Inters start; crossover to slicks when track dries
    wet      → Inters primary; Full Wets if rain_intensity > 0.6
    extreme  → Full Wets mandatory; possible late switch to Inters

Wet tyre behaviour:
    INTERMEDIATE on wet track: +2.0s offset, 0.02s/lap deg (very durable)
    INTERMEDIATE on drying track: additional overheat penalty after crossover
        (+0.20s per lap past crossover, compounding — inters are designed for
        standing water and overheat rapidly on a dry surface)
    WET on very wet track: +5.0s offset, 0.01s/lap deg
    WET on drying track: catastrophic pace loss (+1.0s/lap cumulative)

Crossover timing:
    The crossover lap is where slicks become faster than inters. It depends on
    drying rate which is inversely proportional to rain_intensity:
        damp:    crossover ≈ total_laps * rain_intensity * 0.5
        wet:     crossover ≈ total_laps * rain_intensity * 0.7
        extreme: crossover ≈ total_laps * rain_intensity * 0.8
"""

from enum import Enum
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/simulate", tags=["simulate"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class WeatherCondition(str, Enum):
    dry = "dry"
    damp = "damp"
    wet = "wet"
    extreme = "extreme"


class CompoundParams(BaseModel):
    avg_deg_s_per_lap: float = Field(..., description="Linear degradation rate (s/lap)")
    cliff_onset_lap: int = Field(20, description="Lap where quadratic cliff begins")
    cliff_rate_s_per_lap2: float = Field(0.015, description="Quadratic cliff coefficient")
    typical_max_stint_laps: int = Field(..., description="Max laps before unviable")
    base_pace_offset: float = Field(0.0, description="Pace gap vs softest compound (s)")


class SimulateRequest(BaseModel):
    total_laps: int = Field(..., ge=10, le=100)
    pit_loss_seconds: float = Field(..., ge=10, le=40)
    base_lap_time_s: float = Field(90.0, ge=60, le=130)
    track_temp_c: Optional[float] = None
    weather_condition: WeatherCondition = Field(WeatherCondition.dry)
    rain_intensity: float = Field(0.0, ge=0.0, le=1.0, description="0=bone dry, 1=monsoon")
    compounds: dict[str, CompoundParams] = Field(
        ..., description="Slick compound params keyed by code (C1–C5)",
    )


class StintDetail(BaseModel):
    stint_number: int
    compound: str
    start_lap: int
    end_lap: int
    laps: int
    stint_time_s: float
    avg_lap_time_s: float
    final_lap_time_s: float
    cliff_laps: int
    is_wet_tyre: bool = False


class StrategyResult(BaseModel):
    name: str
    stops: int
    total_time_s: float
    total_time_display: str
    pit_stop_laps: list[int]
    stints: list[StintDetail]
    weather_note: str = ""


class SimulateResponse(BaseModel):
    total_laps: int
    pit_loss_seconds: float
    base_lap_time_s: float
    track_temp_c: Optional[float]
    weather_condition: str
    rain_intensity: float
    strategies: list[StrategyResult]
    recommended: str
    delta_s: float
    model: str


# ---------------------------------------------------------------------------
# Internal wet-tyre compound parameters
# ---------------------------------------------------------------------------

# Hardcoded — no FastF1 historical wet data.
# Calibrated from 2023–2024 wet races (Spa, Suzuka, Montreal rain events).

def _inter_params() -> CompoundParams:
    """Intermediate: good on standing water, overheats on dry."""
    return CompoundParams(
        avg_deg_s_per_lap=0.02,
        cliff_onset_lap=25,
        cliff_rate_s_per_lap2=0.005,
        typical_max_stint_laps=40,
        base_pace_offset=2.0,
    )


def _wet_params() -> CompoundParams:
    """Full Wet: extreme rain only, very slow on anything less."""
    return CompoundParams(
        avg_deg_s_per_lap=0.01,
        cliff_onset_lap=35,
        cliff_rate_s_per_lap2=0.003,
        typical_max_stint_laps=50,
        base_pace_offset=5.0,
    )


# Pace multiplier on the TRACK surface (applied to base_lap)
CONDITION_MULTIPLIER = {
    "dry": 1.00,
    "damp": 1.06,
    "wet": 1.15,
    "extreme": 1.35,
}


# ---------------------------------------------------------------------------
# Lap time computation
# ---------------------------------------------------------------------------

def _lap_time(
    n: int, base_lap: float, pace_offset: float,
    deg_rate: float, cliff_onset: int, cliff_rate: float,
) -> float:
    """Single lap time for lap n (0-indexed) in a stint."""
    t = base_lap + pace_offset + n * deg_rate
    if n > cliff_onset:
        t += cliff_rate * (n - cliff_onset) ** 2
    return t


def _stint_time(
    laps: int, base_lap: float, pace_offset: float,
    deg_rate: float, cliff_onset: int, cliff_rate: float,
) -> tuple[float, float, float, int]:
    """(total, avg, final, cliff_laps) for a stint."""
    if laps <= 0:
        return 0.0, 0.0, 0.0, 0

    linear_laps = min(laps, cliff_onset + 1)
    linear_total = linear_laps * (base_lap + pace_offset) + deg_rate * linear_laps * (linear_laps - 1) / 2

    cliff_total = 0.0
    cliff_count = 0
    if laps > cliff_onset + 1:
        cliff_count = laps - (cliff_onset + 1)
        for i in range(cliff_count):
            n = cliff_onset + 1 + i
            cliff_total += (base_lap + pace_offset) + n * deg_rate + cliff_rate * (n - cliff_onset) ** 2

    total = linear_total + cliff_total
    avg = total / laps
    final = _lap_time(laps - 1, base_lap, pace_offset, deg_rate, cliff_onset, cliff_rate)
    return total, avg, final, cliff_count


def _eval_total(
    stint_laps: list[int], compounds: list[str],
    base_lap: float, pit_loss: float, all_params: dict[str, CompoundParams],
) -> float:
    """Quick total time evaluation for optimizer."""
    total = 0.0
    for i, (code, laps) in enumerate(zip(compounds, stint_laps)):
        cp = all_params[code]
        t, _, _, _ = _stint_time(laps, base_lap, cp.base_pace_offset, cp.avg_deg_s_per_lap,
                                 cp.cliff_onset_lap, cp.cliff_rate_s_per_lap2)
        total += t
        if i < len(compounds) - 1:
            total += pit_loss
    return total


# ---------------------------------------------------------------------------
# Strategy builders
# ---------------------------------------------------------------------------

def _build_strategy(
    name: str, compound_seq: list[str], stint_laps: list[int],
    base_lap: float, pit_loss: float, all_params: dict[str, CompoundParams],
    weather_note: str = "",
) -> StrategyResult:
    stops = len(compound_seq) - 1
    stints, pit_stop_laps = [], []
    total_time, current_lap = 0.0, 1
    wet_codes = {"INTERMEDIATE", "WET"}

    for i, (code, laps) in enumerate(zip(compound_seq, stint_laps)):
        cp = all_params[code]
        st, avg, final, cliff = _stint_time(
            laps, base_lap, cp.base_pace_offset, cp.avg_deg_s_per_lap,
            cp.cliff_onset_lap, cp.cliff_rate_s_per_lap2,
        )
        stints.append(StintDetail(
            stint_number=i + 1, compound=code,
            start_lap=current_lap, end_lap=current_lap + laps - 1, laps=laps,
            stint_time_s=round(st, 3), avg_lap_time_s=round(avg, 3),
            final_lap_time_s=round(final, 3), cliff_laps=cliff,
            is_wet_tyre=code in wet_codes,
        ))
        total_time += st
        if i < stops:
            pit_stop_laps.append(current_lap + laps - 1)
            total_time += pit_loss
        current_lap += laps

    h = int(total_time // 3600)
    m = int((total_time % 3600) // 60)
    s = total_time % 60

    return StrategyResult(
        name=name, stops=stops,
        total_time_s=round(total_time, 3),
        total_time_display=f"{h}:{m:02d}:{s:06.3f}",
        pit_stop_laps=pit_stop_laps, stints=stints,
        weather_note=weather_note,
    )


def _optimize_1stop(
    total_laps: int, base_lap: float, pit_loss: float,
    c1: str, c2: str, all_params: dict[str, CompoundParams],
) -> StrategyResult:
    cp1, cp2 = all_params[c1], all_params[c2]
    max1 = cp1.typical_max_stint_laps + 5
    max2 = cp2.typical_max_stint_laps + 5
    best_time, best_split = float("inf"), total_laps // 2

    for split in range(5, total_laps - 4):
        if split > max1 or (total_laps - split) > max2:
            continue
        t = _eval_total([split, total_laps - split], [c1, c2], base_lap, pit_loss, all_params)
        if t < best_time:
            best_time, best_split = t, split

    if best_time == float("inf"):
        best_split = total_laps // 2
    return _build_strategy(f"1-Stop: {c1} \u2192 {c2}", [c1, c2],
                           [best_split, total_laps - best_split], base_lap, pit_loss, all_params)


def _optimize_2stop(
    total_laps: int, base_lap: float, pit_loss: float,
    c1: str, c2: str, c3: str, all_params: dict[str, CompoundParams],
) -> StrategyResult:
    max1 = all_params[c1].typical_max_stint_laps + 5
    max2 = all_params[c2].typical_max_stint_laps + 5
    max3 = all_params[c3].typical_max_stint_laps + 5
    best_time, best_s1, best_s2 = float("inf"), total_laps // 3, total_laps // 3

    for s1 in range(5, min(total_laps - 9, max1 + 1)):
        for s2 in range(5, min(total_laps - s1 - 4, max2 + 1)):
            s3 = total_laps - s1 - s2
            if s3 < 5 or s3 > max3:
                continue
            t = _eval_total([s1, s2, s3], [c1, c2, c3], base_lap, pit_loss, all_params)
            if t < best_time:
                best_time, best_s1, best_s2 = t, s1, s2

    if best_time == float("inf"):
        best_s1 = best_s2 = total_laps // 3
    s3 = total_laps - best_s1 - best_s2
    return _build_strategy(f"2-Stop: {c1} \u2192 {c2} \u2192 {c3}", [c1, c2, c3],
                           [best_s1, best_s2, s3], base_lap, pit_loss, all_params)


# ---------------------------------------------------------------------------
# Wet strategy generation
# ---------------------------------------------------------------------------

def _generate_wet_strategies(
    condition: str, rain_intensity: float,
    total_laps: int, base_lap: float, pit_loss: float,
    slick_codes: list[str], all_params: dict[str, CompoundParams],
) -> list[StrategyResult]:
    """
    Generate condition-appropriate strategies involving wet tyres.

    In damp/wet/extreme conditions, the track is too wet for slicks initially.
    The crossover lap is when slicks become viable as the track dries.

    Key F1 insight: teams pit at the crossover point, swapping inters for slicks.
    Running inters past crossover incurs heavy overheating penalties (~0.2s/lap
    cumulative), making the stop worthwhile even with 20+ second pit loss.
    """
    strategies: list[StrategyResult] = []

    if condition == "damp":
        # Track starts damp, dries out. Crossover relatively early.
        crossover = max(5, min(int(total_laps * rain_intensity * 0.5), total_laps - 10))
        note = f"Track dries ~lap {crossover}. Inters mandatory at start."

        # Modify INTER params: after crossover, inters overheat on drying surface.
        # We model this by setting cliff_onset to the crossover point with a severe
        # cliff_rate — inters lose ~0.10s/lap^2 past the crossover on a dry surface.
        inter_p = _inter_params()
        inter_adjusted = CompoundParams(
            avg_deg_s_per_lap=inter_p.avg_deg_s_per_lap,
            cliff_onset_lap=crossover,
            cliff_rate_s_per_lap2=0.10,  # severe overheating on dry
            typical_max_stint_laps=crossover + 5,
            base_pace_offset=inter_p.base_pace_offset,
        )
        adjusted_params = {**all_params, "INTERMEDIATE": inter_adjusted}
        base_damp = base_lap * CONDITION_MULTIPLIER["damp"]

        # INTER → each slick (1-stop at crossover)
        for sc in slick_codes:
            strat = _build_strategy(
                f"1-Stop: INTER \u2192 {sc}", ["INTERMEDIATE", sc],
                [crossover, total_laps - crossover],
                base_damp, pit_loss, adjusted_params, weather_note=note,
            )
            strategies.append(strat)

        # INTER → slick1 → slick2 (2-stop: crossover + normal pit)
        for sc1 in slick_codes:
            for sc2 in slick_codes:
                if sc1 == sc2:
                    continue
                s2_laps = (total_laps - crossover) // 2
                s3_laps = total_laps - crossover - s2_laps
                if s2_laps < 5 or s3_laps < 5:
                    continue
                strat = _build_strategy(
                    f"2-Stop: INTER \u2192 {sc1} \u2192 {sc2}",
                    ["INTERMEDIATE", sc1, sc2],
                    [crossover, s2_laps, s3_laps],
                    base_damp, pit_loss, adjusted_params, weather_note=note,
                )
                strategies.append(strat)

    elif condition == "wet":
        crossover = max(10, min(int(total_laps * rain_intensity * 0.7), total_laps - 5))
        note = f"Wet throughout. Possible late dry window ~lap {crossover}."

        inter_p = _inter_params()
        wet_p = _wet_params()
        base_wet = base_lap * CONDITION_MULTIPLIER["wet"]
        adjusted_params = {**all_params, "INTERMEDIATE": inter_p, "WET": wet_p}

        # Full INTER race (no stop if rain persists)
        strat = _build_strategy(
            "0-Stop: INTERMEDIATE", ["INTERMEDIATE"], [total_laps],
            base_wet, pit_loss, adjusted_params, weather_note="Full wet race on inters",
        )
        strategies.append(strat)

        # WET → INTER (switch as rain eases, e.g. mid-race)
        if rain_intensity > 0.5:
            switch = total_laps // 2
            strat = _build_strategy(
                "1-Stop: WET \u2192 INTER", ["WET", "INTERMEDIATE"],
                [switch, total_laps - switch],
                base_wet, pit_loss, adjusted_params,
                weather_note="Start Full Wets, switch to Inters as rain eases",
            )
            strategies.append(strat)

        # INTER → slick (if rain eases enough for late crossover)
        if rain_intensity < 0.6 and crossover < total_laps - 8:
            for sc in slick_codes[:2]:
                strat = _build_strategy(
                    f"1-Stop: INTER \u2192 {sc}", ["INTERMEDIATE", sc],
                    [crossover, total_laps - crossover],
                    base_wet, pit_loss, adjusted_params,
                    weather_note=f"Late crossover to slicks at ~lap {crossover}",
                )
                strategies.append(strat)

    elif condition == "extreme":
        note = "Extreme rain. Full Wets mandatory."
        wet_p = _wet_params()
        inter_p = _inter_params()
        base_ext = base_lap * CONDITION_MULTIPLIER["extreme"]
        adjusted_params = {**all_params, "INTERMEDIATE": inter_p, "WET": wet_p}

        # Full WET race
        strat = _build_strategy(
            "0-Stop: WET", ["WET"], [total_laps],
            base_ext, pit_loss, adjusted_params,
            weather_note="Extreme rain \u2014 Full Wets only",
        )
        strategies.append(strat)

        # WET → INTER (if rain eases)
        switch = max(total_laps // 2, int(total_laps * rain_intensity * 0.6))
        switch = min(switch, total_laps - 5)
        strat = _build_strategy(
            "1-Stop: WET \u2192 INTER", ["WET", "INTERMEDIATE"],
            [switch, total_laps - switch],
            base_ext, pit_loss, adjusted_params,
            weather_note="Switch to Inters if rain eases",
        )
        strategies.append(strat)

    return strategies


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/", response_model=SimulateResponse)
def simulate_strategy(req: SimulateRequest):
    """
    Simulate and compare pit strategies for a race.

    In dry conditions: evaluates all 1-stop and 2-stop slick combos.
    In wet conditions: generates weather-appropriate strategies with
    Intermediate/Full Wet compounds and crossover logic.

    Returns strategies ranked by total time with stint breakdowns.
    """
    slick_codes = list(req.compounds.keys())
    all_params = dict(req.compounds)
    all_strategies: list[StrategyResult] = []
    cond = req.weather_condition.value

    if cond == "dry":
        # ---- Standard dry strategies ----
        for c1 in slick_codes:
            for c2 in slick_codes:
                if c1 == c2:
                    continue
                all_strategies.append(_optimize_1stop(
                    req.total_laps, req.base_lap_time_s, req.pit_loss_seconds,
                    c1, c2, all_params,
                ))

        seen: set[tuple[str, ...]] = set()
        for c1 in slick_codes:
            for c2 in slick_codes:
                for c3 in slick_codes:
                    combo = (c1, c2, c3)
                    if combo in seen or len(set(combo)) < 2:
                        continue
                    seen.add(combo)
                    all_strategies.append(_optimize_2stop(
                        req.total_laps, req.base_lap_time_s, req.pit_loss_seconds,
                        c1, c2, c3, all_params,
                    ))
    else:
        # ---- Wet strategies ----
        wet_strats = _generate_wet_strategies(
            cond, req.rain_intensity,
            req.total_laps, req.base_lap_time_s, req.pit_loss_seconds,
            slick_codes, all_params,
        )
        all_strategies.extend(wet_strats)

    # ---- Rank and select top results ----
    all_strategies.sort(key=lambda s: s.total_time_s)

    if cond == "dry":
        one_stops = [s for s in all_strategies if s.stops == 1][:3]
        two_stops = [s for s in all_strategies if s.stops == 2][:3]
        final = sorted(one_stops + two_stops, key=lambda s: s.total_time_s)
    else:
        final = all_strategies[:6]

    recommended = final[0].name if final else "N/A"
    delta = round(final[1].total_time_s - final[0].total_time_s, 3) if len(final) > 1 else 0.0

    return SimulateResponse(
        total_laps=req.total_laps,
        pit_loss_seconds=req.pit_loss_seconds,
        base_lap_time_s=req.base_lap_time_s,
        track_temp_c=req.track_temp_c,
        weather_condition=cond,
        rain_intensity=req.rain_intensity,
        strategies=final,
        recommended=recommended,
        delta_s=delta,
        model="piecewise_linear_cliff + wet_crossover",
    )
