"""
Race Calendar router — dynamic via OpenF1 API with fallback.

Primary data source: https://api.openf1.org/v1/sessions?year=2026
Enriched with CIRCUIT_INFO from fastf1_helpers for lat/lon/laps/pit_loss.

If OpenF1 is unavailable or returns no 2026 data (likely pre-season),
falls back to FALLBACK_EVENTS_2026 — a minimal hardcoded event list
derived from the official FIA-published calendar.
"""

import logging
from datetime import date, datetime
from typing import Any, Optional

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.fastf1_helpers import CIRCUIT_INFO, normalize_circuit_name

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/calendar", tags=["calendar"])

OPENF1_SESSIONS_URL = "https://api.openf1.org/v1/sessions"
CURRENT_YEAR = 2026


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------

class RaceEvent(BaseModel):
    round: str | int
    name: str
    circuit_key: str          # normalized short name (e.g. "melbourne")
    circuit_full_name: str
    country: str
    date: str                 # ISO YYYY-MM-DD
    lat: float
    lon: float
    laps: Optional[int] = None
    length_km: Optional[float] = None
    pit_loss: Optional[float] = None
    sprint: bool = False
    is_testing: bool = False


class NextRaceResponse(BaseModel):
    event: RaceEvent
    days_until: int
    season_status: str  # "pre_season", "in_season", "post_season"


# ---------------------------------------------------------------------------
# Fallback 2026 event list — used when OpenF1 has no data
# ---------------------------------------------------------------------------

FALLBACK_EVENTS_2026: list[dict[str, Any]] = [
    {"round": "TEST1", "name": "Pre-Season Testing 1",   "circuit_key": "bahrain",           "date": "2026-02-13", "session_type": "Testing"},
    {"round": "TEST2", "name": "Pre-Season Testing 2",   "circuit_key": "bahrain",           "date": "2026-02-20", "session_type": "Testing"},
    {"round": 1,  "name": "Australian Grand Prix",       "circuit_key": "melbourne",         "date": "2026-03-08", "session_type": "Race"},
    {"round": 2,  "name": "Chinese Grand Prix",          "circuit_key": "shanghai",          "date": "2026-03-15", "session_type": "Race", "sprint": True},
    {"round": 3,  "name": "Japanese Grand Prix",         "circuit_key": "suzuka",            "date": "2026-03-29", "session_type": "Race"},
    {"round": 4,  "name": "Bahrain Grand Prix",          "circuit_key": "bahrain",           "date": "2026-04-12", "session_type": "Race"},
    {"round": 5,  "name": "Miami Grand Prix",            "circuit_key": "miami",             "date": "2026-04-26", "session_type": "Race", "sprint": True},
    {"round": 6,  "name": "Canadian Grand Prix",         "circuit_key": "montreal",          "date": "2026-05-10", "session_type": "Race", "sprint": True},
    {"round": 7,  "name": "Monaco Grand Prix",           "circuit_key": "monaco",            "date": "2026-05-24", "session_type": "Race"},
    {"round": 8,  "name": "Spanish Grand Prix",          "circuit_key": "barcelona",         "date": "2026-06-07", "session_type": "Race"},
    {"round": 9,  "name": "Austrian Grand Prix",         "circuit_key": "spielberg",         "date": "2026-06-21", "session_type": "Race"},
    {"round": 10, "name": "British Grand Prix",          "circuit_key": "silverstone",       "date": "2026-07-05", "session_type": "Race"},
    {"round": 11, "name": "Belgian Grand Prix",          "circuit_key": "spa-francorchamps", "date": "2026-07-19", "session_type": "Race"},
    {"round": 12, "name": "Hungarian Grand Prix",        "circuit_key": "budapest",          "date": "2026-08-02", "session_type": "Race"},
    {"round": 13, "name": "Dutch Grand Prix",            "circuit_key": "zandvoort",         "date": "2026-08-16", "session_type": "Race"},
    {"round": 14, "name": "Italian Grand Prix",          "circuit_key": "monza",             "date": "2026-08-30", "session_type": "Race"},
    {"round": 15, "name": "Madrid Grand Prix",           "circuit_key": "madrid",            "date": "2026-09-13", "session_type": "Race"},
    {"round": 16, "name": "Azerbaijan Grand Prix",       "circuit_key": "baku",              "date": "2026-09-20", "session_type": "Race"},
    {"round": 17, "name": "Singapore Grand Prix",        "circuit_key": "singapore",         "date": "2026-10-04", "session_type": "Race", "sprint": True},
    {"round": 18, "name": "United States Grand Prix",    "circuit_key": "austin",            "date": "2026-10-18", "session_type": "Race", "sprint": True},
    {"round": 19, "name": "Mexico City Grand Prix",      "circuit_key": "mexico city",       "date": "2026-10-25", "session_type": "Race"},
    {"round": 20, "name": "São Paulo Grand Prix",        "circuit_key": "sao paulo",         "date": "2026-11-08", "session_type": "Race"},
    {"round": 21, "name": "Las Vegas Grand Prix",        "circuit_key": "las vegas",         "date": "2026-11-21", "session_type": "Race"},
    {"round": 22, "name": "Qatar Grand Prix",            "circuit_key": "lusail",            "date": "2026-11-29", "session_type": "Race", "sprint": True},
    {"round": 23, "name": "Abu Dhabi Grand Prix",        "circuit_key": "yas marina",        "date": "2026-12-06", "session_type": "Race"},
]


# ---------------------------------------------------------------------------
# OpenF1 fetch logic
# ---------------------------------------------------------------------------

def _fetch_openf1_events(year: int) -> list[dict[str, Any]] | None:
    """
    Fetch sessions from OpenF1 and group into race weekends.

    Returns a list of event dicts in our standard format, or None on failure.
    Each event represents the Race (or Sprint) session of a meeting.
    """
    try:
        resp = requests.get(OPENF1_SESSIONS_URL, params={"year": year}, timeout=8)
        resp.raise_for_status()
        sessions = resp.json()
    except Exception as e:
        logger.warning(f"OpenF1 API call failed: {e}")
        return None

    if not sessions:
        logger.info(f"OpenF1 returned no sessions for year {year}")
        return None

    # Group by meeting_key → pick one event per meeting
    meetings: dict[int, dict] = {}
    sprint_meetings: set[int] = set()

    for s in sessions:
        mk = s.get("meeting_key")
        if not mk:
            continue
        stype = s.get("session_type", "")
        if stype == "Sprint":
            sprint_meetings.add(mk)
        # Prefer "Race" session; fall back to first session seen
        if stype == "Race" or mk not in meetings:
            meetings[mk] = s

    events: list[dict[str, Any]] = []
    round_num = 0
    for mk in sorted(meetings.keys()):
        s = meetings[mk]
        stype = s.get("session_type", "Practice")
        is_testing = "test" in s.get("session_name", "").lower() or stype == "Testing"

        if not is_testing and stype in ("Race", "Sprint Qualifying", "Qualifying", "Practice"):
            round_num += 1
            r = round_num
        else:
            r = f"TEST{round_num + 1}" if is_testing else round_num

        circuit_raw = s.get("circuit_short_name", "")
        circuit_key = normalize_circuit_name(circuit_raw)
        date_str = s.get("date_start", "")[:10]
        country = s.get("country_name", "")

        events.append({
            "round": r,
            "name": s.get("session_name", f"Round {r}"),
            "circuit_key": circuit_key,
            "date": date_str,
            "session_type": stype,
            "country_override": country,
            "sprint": mk in sprint_meetings,
        })

    return events if events else None


def _enrich_event(raw: dict[str, Any]) -> RaceEvent:
    """Merge raw event data with CIRCUIT_INFO metadata."""
    ck = normalize_circuit_name(raw.get("circuit_key", ""))
    info = CIRCUIT_INFO.get(ck, {})

    return RaceEvent(
        round=raw.get("round", 0),
        name=raw.get("name", "Unknown"),
        circuit_key=ck,
        circuit_full_name=info.get("full_name", ck.title()),
        country=raw.get("country_override", "") or info.get("country", ""),
        date=raw.get("date", ""),
        lat=info.get("lat", 0.0),
        lon=info.get("lon", 0.0),
        laps=info.get("laps"),
        length_km=info.get("length_km"),
        pit_loss=info.get("pit_loss"),
        sprint=raw.get("sprint", False),
        is_testing=raw.get("session_type") == "Testing",
    )


def _get_events() -> list[dict[str, Any]]:
    """Get events from OpenF1, falling back to hardcoded list."""
    events = _fetch_openf1_events(CURRENT_YEAR)
    if events:
        return events
    logger.info("Using fallback 2026 calendar")
    return FALLBACK_EVENTS_2026


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=list[RaceEvent])
def get_full_calendar():
    """Full 2026 season calendar. Tries OpenF1 first, falls back to hardcoded list."""
    return [_enrich_event(e) for e in _get_events()]


@router.get("/next", response_model=NextRaceResponse)
def get_next_race():
    """Auto-detect next upcoming event (race, sprint, or testing) by UTC date."""
    today = date.today()
    events = _get_events()

    for e in events:
        try:
            event_date = datetime.strptime(e["date"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            continue
        if event_date >= today:
            days_until = (event_date - today).days

            # Determine season phase
            race_dates = [
                datetime.strptime(ev["date"], "%Y-%m-%d").date()
                for ev in events
                if ev.get("session_type") == "Race"
            ]
            if race_dates:
                if today < race_dates[0]:
                    status = "pre_season"
                elif today <= race_dates[-1]:
                    status = "in_season"
                else:
                    status = "post_season"
            else:
                status = "pre_season"

            return NextRaceResponse(
                event=_enrich_event(e),
                days_until=days_until,
                season_status=status,
            )

    # All events past
    last = events[-1] if events else FALLBACK_EVENTS_2026[-1]
    return NextRaceResponse(event=_enrich_event(last), days_until=0, season_status="post_season")


@router.get("/{round_id}", response_model=RaceEvent)
def get_race_by_round(round_id: str):
    """Look up a specific round by number ('1','2') or testing ID ('TEST1')."""
    events = _get_events()
    for e in events:
        if str(e.get("round")) == round_id:
            return _enrich_event(e)
    raise HTTPException(status_code=404, detail=f"Round '{round_id}' not found")
