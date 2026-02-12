"""
Grid router — Calendar overview, Drivers, and Teams data.

Primary driver/team source: Jolpica F1 API (Ergast successor)
  https://api.jolpi.ca/ergast/f1

Strategy:
  1. Try /current/driverStandings.json (one call, includes constructor linkage)
  2. If empty (pre-season), fetch constructors then per-constructor drivers
  3. If all fails, fall back to hardcoded static list

All responses are disk-cached with a 6-hour TTL.
"""

import logging
from typing import Optional

import requests
from fastapi import APIRouter
from pydantic import BaseModel

from routers.calendar import _get_events, _enrich_event, RaceEvent
from utils.cache import read_cache, write_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/grid", tags=["grid"])

JOLPICA_BASE = "https://api.jolpi.ca/ergast/f1"
CACHE_TTL = 21600  # 6 hours
REQUEST_TIMEOUT = 10


# ---------------------------------------------------------------------------
# Nationality string → ISO 3-letter country code
# ---------------------------------------------------------------------------

NATIONALITY_TO_CODE: dict[str, str] = {
    "Dutch": "NED",
    "British": "GBR",
    "Monegasque": "MON",
    "Australian": "AUS",
    "Spanish": "ESP",
    "Canadian": "CAN",
    "French": "FRA",
    "German": "GER",
    "Mexican": "MEX",
    "Japanese": "JPN",
    "Thai": "THA",
    "Finnish": "FIN",
    "Chinese": "CHN",
    "Danish": "DEN",
    "Italian": "ITA",
    "Brazilian": "BRA",
    "American": "USA",
    "New Zealander": "NZL",
    "Argentine": "ARG",
    "Swiss": "SUI",
    "Indian": "IND",
    "Polish": "POL",
    "Russian": "RUS",
    "Austrian": "AUT",
    "Belgian": "BEL",
    "Swedish": "SWE",
    "South Korean": "KOR",
    "Indonesian": "IDN",
    "Colombian": "COL",
    "Israeli": "ISR",
    "Portuguese": "POR",
    "South African": "RSA",
}


# ---------------------------------------------------------------------------
# Constructor ID → team colour hex (no '#' prefix)
# Jolpica does not provide colours; this is the single source of truth.
# ---------------------------------------------------------------------------

CONSTRUCTOR_COLOURS: dict[str, str] = {
    "red_bull": "3671C6",
    "ferrari": "E80020",
    "mclaren": "FF8000",
    "mercedes": "27F4D2",
    "aston_martin": "229971",
    "alpine": "0093CC",
    "audi": "52E252",
    "williams": "1868DB",
    "haas": "B6BABD",
    "rb": "6692FF",
    "cadillac": "C0C0C0",
    # legacy IDs that may appear in older data
    "sauber": "52E252",
    "alphatauri": "6692FF",
    "alfa": "A50F2D",
    "racing_point": "F596C8",
    "toro_rosso": "469BFF",
}


# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------

class GridCalendarResponse(BaseModel):
    events: list[RaceEvent]
    next_event: Optional[RaceEvent] = None
    days_until_next: int = 0
    season_status: str = "pre_season"
    note: str = ""


class Driver(BaseModel):
    driver_number: int
    broadcast_name: str
    full_name: str
    name_acronym: str
    team_name: str
    team_colour: str
    country_code: Optional[str] = None
    headshot_url: Optional[str] = None


class GridDriversResponse(BaseModel):
    drivers: list[Driver]
    note: str = ""


class TeamEntry(BaseModel):
    team_name: str
    team_colour: str
    drivers: list[Driver]


class GridTeamsResponse(BaseModel):
    teams: list[TeamEntry]
    note: str = ""


# ---------------------------------------------------------------------------
# Fallback driver data (2025 grid — used only when API is unreachable)
# ---------------------------------------------------------------------------

FALLBACK_DRIVERS: list[dict] = [
    {"driver_number": 1,  "broadcast_name": "M VERSTAPPEN", "full_name": "Max Verstappen",       "name_acronym": "VER", "team_name": "Red Bull",          "team_colour": "3671C6", "country_code": "NED"},
    {"driver_number": 22, "broadcast_name": "Y TSUNODA",    "full_name": "Yuki Tsunoda",         "name_acronym": "TSU", "team_name": "Red Bull",          "team_colour": "3671C6", "country_code": "JPN"},
    {"driver_number": 44, "broadcast_name": "L HAMILTON",   "full_name": "Lewis Hamilton",        "name_acronym": "HAM", "team_name": "Ferrari",           "team_colour": "E80020", "country_code": "GBR"},
    {"driver_number": 16, "broadcast_name": "C LECLERC",    "full_name": "Charles Leclerc",       "name_acronym": "LEC", "team_name": "Ferrari",           "team_colour": "E80020", "country_code": "MON"},
    {"driver_number": 4,  "broadcast_name": "L NORRIS",     "full_name": "Lando Norris",          "name_acronym": "NOR", "team_name": "McLaren",           "team_colour": "FF8000", "country_code": "GBR"},
    {"driver_number": 81, "broadcast_name": "O PIASTRI",    "full_name": "Oscar Piastri",         "name_acronym": "PIA", "team_name": "McLaren",           "team_colour": "FF8000", "country_code": "AUS"},
    {"driver_number": 63, "broadcast_name": "G RUSSELL",    "full_name": "George Russell",        "name_acronym": "RUS", "team_name": "Mercedes",          "team_colour": "27F4D2", "country_code": "GBR"},
    {"driver_number": 12, "broadcast_name": "A ANTONELLI",  "full_name": "Andrea Kimi Antonelli", "name_acronym": "ANT", "team_name": "Mercedes",          "team_colour": "27F4D2", "country_code": "ITA"},
    {"driver_number": 14, "broadcast_name": "F ALONSO",     "full_name": "Fernando Alonso",       "name_acronym": "ALO", "team_name": "Aston Martin",      "team_colour": "229971", "country_code": "ESP"},
    {"driver_number": 18, "broadcast_name": "L STROLL",     "full_name": "Lance Stroll",          "name_acronym": "STR", "team_name": "Aston Martin",      "team_colour": "229971", "country_code": "CAN"},
    {"driver_number": 10, "broadcast_name": "P GASLY",      "full_name": "Pierre Gasly",          "name_acronym": "GAS", "team_name": "Alpine F1 Team",    "team_colour": "0093CC", "country_code": "FRA"},
    {"driver_number": 7,  "broadcast_name": "J DOOHAN",     "full_name": "Jack Doohan",           "name_acronym": "DOO", "team_name": "Alpine F1 Team",    "team_colour": "0093CC", "country_code": "AUS"},
    {"driver_number": 27, "broadcast_name": "N HULKENBERG", "full_name": "Nico Hulkenberg",       "name_acronym": "HUL", "team_name": "Audi",              "team_colour": "52E252", "country_code": "GER"},
    {"driver_number": 5,  "broadcast_name": "G BORTOLETO",  "full_name": "Gabriel Bortoleto",     "name_acronym": "BOR", "team_name": "Audi",              "team_colour": "52E252", "country_code": "BRA"},
    {"driver_number": 23, "broadcast_name": "A ALBON",      "full_name": "Alexander Albon",       "name_acronym": "ALB", "team_name": "Williams",          "team_colour": "1868DB", "country_code": "THA"},
    {"driver_number": 55, "broadcast_name": "C SAINZ",      "full_name": "Carlos Sainz",          "name_acronym": "SAI", "team_name": "Williams",          "team_colour": "1868DB", "country_code": "ESP"},
    {"driver_number": 87, "broadcast_name": "O BEARMAN",    "full_name": "Oliver Bearman",        "name_acronym": "BEA", "team_name": "Haas F1 Team",      "team_colour": "B6BABD", "country_code": "GBR"},
    {"driver_number": 31, "broadcast_name": "E OCON",       "full_name": "Esteban Ocon",          "name_acronym": "OCO", "team_name": "Haas F1 Team",      "team_colour": "B6BABD", "country_code": "FRA"},
    {"driver_number": 30, "broadcast_name": "L LAWSON",     "full_name": "Liam Lawson",           "name_acronym": "LAW", "team_name": "RB F1 Team",        "team_colour": "6692FF", "country_code": "NZL"},
    {"driver_number": 6,  "broadcast_name": "I HADJAR",     "full_name": "Isack Hadjar",          "name_acronym": "HAD", "team_name": "RB F1 Team",        "team_colour": "6692FF", "country_code": "FRA"},
]


# ---------------------------------------------------------------------------
# Jolpica API helpers
# ---------------------------------------------------------------------------

def _jolpica_get(path: str) -> dict | None:
    """GET a Jolpica endpoint and return parsed JSON, or None on failure."""
    url = f"{JOLPICA_BASE}{path}"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("Jolpica request failed [%s]: %s", path, exc)
        return None


def _parse_driver(d: dict, constructor: dict | None = None) -> Driver:
    """Convert a Jolpica Driver dict (+ optional Constructor) into our Driver model."""
    given = d.get("givenName", "")
    family = d.get("familyName", "")
    num_str = d.get("permanentNumber", "0")
    num = int(num_str) if num_str.isdigit() else 0

    team_name = ""
    team_colour = "555555"
    if constructor:
        team_name = constructor.get("name", "")
        team_colour = CONSTRUCTOR_COLOURS.get(
            constructor.get("constructorId", ""), "555555"
        )

    nationality = d.get("nationality", "")
    country_code = NATIONALITY_TO_CODE.get(nationality, nationality[:3].upper() if nationality else None)

    return Driver(
        driver_number=num,
        broadcast_name=f"{given[0]} {family.upper()}" if given and family else family.upper(),
        full_name=f"{given} {family}".strip(),
        name_acronym=d.get("code", family[:3].upper() if family else ""),
        team_name=team_name,
        team_colour=team_colour,
        country_code=country_code,
        headshot_url=None,
    )


def _fetch_via_standings() -> list[Driver] | None:
    """
    Strategy 1: /current/driverStandings.json
    One call, includes constructor linkage. Only works once the season has races.
    """
    data = _jolpica_get("/current/driverStandings.json")
    if not data:
        return None

    standings_lists = (
        data.get("MRData", {})
        .get("StandingsTable", {})
        .get("StandingsLists", [])
    )
    if not standings_lists:
        return None

    entries = standings_lists[0].get("DriverStandings", [])
    if not entries:
        return None

    drivers: list[Driver] = []
    for entry in entries:
        d = entry.get("Driver", {})
        constructors = entry.get("Constructors", [])
        constructor = constructors[0] if constructors else None
        drivers.append(_parse_driver(d, constructor))

    return drivers if drivers else None


def _fetch_via_constructors() -> list[Driver] | None:
    """
    Strategy 2: Fetch /current/constructors.json, then for each constructor
    fetch /current/constructors/{id}/drivers.json to establish linkage.
    Used pre-season when standings are empty.
    """
    data = _jolpica_get("/current/constructors.json")
    if not data:
        return None

    constructors = (
        data.get("MRData", {})
        .get("ConstructorTable", {})
        .get("Constructors", [])
    )
    if not constructors:
        return None

    drivers: list[Driver] = []
    for constructor in constructors:
        cid = constructor.get("constructorId", "")
        cdata = _jolpica_get(f"/current/constructors/{cid}/drivers.json")
        if not cdata:
            continue

        c_drivers = (
            cdata.get("MRData", {})
            .get("DriverTable", {})
            .get("Drivers", [])
        )
        for d in c_drivers:
            drivers.append(_parse_driver(d, constructor))

    return drivers if drivers else None


# ---------------------------------------------------------------------------
# Internal driver fetch with cache + fallback chain
# ---------------------------------------------------------------------------

def _get_grid_drivers() -> tuple[list[Driver], str]:
    """
    Return (drivers, note).
    Checks cache first, then tries Jolpica strategies, then fallback.
    """
    cache_args = {"scope": "grid_drivers", "version": "v2"}
    cached = read_cache("grid_drivers", ttl_seconds=CACHE_TTL, **cache_args)
    if cached:
        return [Driver(**d) for d in cached["drivers"]], cached.get("note", "")

    # Strategy 1: driverStandings (preferred, 1 call)
    drivers = _fetch_via_standings()
    note = "Jolpica driverStandings"

    # Strategy 2: constructors + per-constructor drivers
    if not drivers:
        logger.info("Standings empty — trying constructor-based driver fetch")
        drivers = _fetch_via_constructors()
        note = "Jolpica constructors"

    # Strategy 3: static fallback
    if not drivers:
        logger.info("Jolpica unavailable — using fallback driver list")
        drivers = [Driver(**d) for d in FALLBACK_DRIVERS]
        note = "Fallback data (static grid)"

    # Sort by driver number
    drivers.sort(key=lambda d: d.driver_number)

    # Write to cache
    write_cache(
        "grid_drivers",
        {"drivers": [d.model_dump() for d in drivers], "note": note},
        **cache_args,
    )

    return drivers, note


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/calendar", response_model=GridCalendarResponse)
def get_grid_calendar():
    """Full season calendar with next-race detection."""
    from datetime import date, datetime

    cache_args = {"scope": "grid_calendar", "version": "v1"}
    cached = read_cache("grid_calendar", ttl_seconds=CACHE_TTL, **cache_args)
    if cached:
        return GridCalendarResponse(**cached)

    raw_events = _get_events()
    events = [_enrich_event(e) for e in raw_events]

    today = date.today()
    next_event: RaceEvent | None = None
    days_until_next = 0
    season_status = "pre_season"

    race_dates: list[date] = []
    for ev in events:
        try:
            race_dates.append(datetime.strptime(ev.date, "%Y-%m-%d").date())
        except (ValueError, AttributeError):
            pass

    for ev in events:
        try:
            ev_date = datetime.strptime(ev.date, "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            continue
        if ev_date >= today:
            next_event = ev
            days_until_next = (ev_date - today).days
            break

    if race_dates:
        actual_race_dates = [
            d for d, ev in zip(race_dates, events) if not ev.is_testing
        ]
        if actual_race_dates:
            if today < actual_race_dates[0]:
                season_status = "pre_season"
            elif today <= actual_race_dates[-1]:
                season_status = "in_season"
            else:
                season_status = "post_season"

    result = GridCalendarResponse(
        events=events,
        next_event=next_event,
        days_until_next=days_until_next,
        season_status=season_status,
        note=f"{len(events)} events loaded",
    )

    write_cache("grid_calendar", result.model_dump(), **cache_args)
    return result


@router.get("/drivers", response_model=GridDriversResponse)
def get_grid_drivers():
    """Current driver grid via Jolpica F1 API."""
    drivers, note = _get_grid_drivers()
    return GridDriversResponse(drivers=drivers, note=note)


@router.get("/teams", response_model=GridTeamsResponse)
def get_grid_teams():
    """Teams grouped with their drivers."""
    cache_args = {"scope": "grid_teams", "version": "v2"}
    cached = read_cache("grid_teams", ttl_seconds=CACHE_TTL, **cache_args)
    if cached:
        return GridTeamsResponse(**cached)

    drivers, _ = _get_grid_drivers()

    # Group by team
    teams_map: dict[str, list[Driver]] = {}
    colour_map: dict[str, str] = {}
    for d in drivers:
        teams_map.setdefault(d.team_name, []).append(d)
        colour_map[d.team_name] = d.team_colour

    teams = [
        TeamEntry(
            team_name=name,
            team_colour=colour_map.get(name, "555555"),
            drivers=members,
        )
        for name, members in teams_map.items()
    ]

    result = GridTeamsResponse(teams=teams, note=f"{len(teams)} teams")
    write_cache("grid_teams", result.model_dump(), **cache_args)
    return result
