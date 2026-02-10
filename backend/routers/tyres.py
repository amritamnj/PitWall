"""
Tyre Compounds router — Pirelli nomination data per race.

Returns the 3 dry slick compounds nominated for a specific round,
plus Intermediate (green) and Full Wet (blue) which are always available.

Pirelli nominates from C1 (hardest) to C5 (softest). The nomination changes
per circuit based on surface roughness, corner speeds, and temperatures.
The mapping is maintained in fastf1_helpers.COMPOUND_NOMINATIONS and updated
from Pirelli press releases before each race.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from utils.fastf1_helpers import (
    CIRCUIT_INFO,
    get_compound_nominations,
    normalize_circuit_name,
)

router = APIRouter(prefix="/api/v1/tyres", tags=["tyres"])

# Pirelli compound colours and display labels
COMPOUND_DISPLAY: dict[str, dict[str, str]] = {
    "C1": {"label": "C1 (Hardest)", "colour": "#FFFFFF", "category": "slick"},
    "C2": {"label": "C2 (Hard)",    "colour": "#FFFFFF", "category": "slick"},
    "C3": {"label": "C3 (Medium)",  "colour": "#FFD700", "category": "slick"},
    "C4": {"label": "C4 (Soft)",    "colour": "#FF3333", "category": "slick"},
    "C5": {"label": "C5 (Softest)", "colour": "#FF3333", "category": "slick"},
    "INTERMEDIATE": {"label": "Intermediate", "colour": "#00CC00", "category": "wet"},
    "WET":          {"label": "Full Wet",     "colour": "#0066FF", "category": "wet"},
}


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class CompoundInfo(BaseModel):
    code: str           # "C3", "INTERMEDIATE", etc.
    label: str          # "C3 (Medium)"
    colour: str         # hex colour for UI
    category: str       # "slick" | "wet"
    role: str | None    # "hard" | "medium" | "soft" | None (for wet)


class TyreNominationResponse(BaseModel):
    circuit_key: str
    year: int
    slicks: list[CompoundInfo]      # 3 dry compounds in order hard → soft
    wet: list[CompoundInfo]         # always [Intermediate, Full Wet]
    all_compounds: list[CompoundInfo]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/{circuit_key}", response_model=TyreNominationResponse)
def get_tyre_nomination(
    circuit_key: str,
    year: int = Query(2026, description="Season year for compound selection"),
):
    """
    Return the Pirelli compound nomination for a specific circuit + year.

    The 3 dry slick compounds vary per race. Inters and Full Wets are always available.
    If no nomination data exists for this circuit/year, falls back to C2/C3/C4.
    """
    key = normalize_circuit_name(circuit_key)
    noms = get_compound_nominations(year, key)

    slicks: list[CompoundInfo] = []
    for role in ("hard", "medium", "soft"):
        code = noms[role]
        display = COMPOUND_DISPLAY.get(code, {"label": code, "colour": "#CCCCCC", "category": "slick"})
        slicks.append(CompoundInfo(
            code=code,
            label=display["label"],
            colour=display["colour"],
            category="slick",
            role=role,
        ))

    wet = [
        CompoundInfo(
            code="INTERMEDIATE",
            label="Intermediate",
            colour="#00CC00",
            category="wet",
            role=None,
        ),
        CompoundInfo(
            code="WET",
            label="Full Wet",
            colour="#0066FF",
            category="wet",
            role=None,
        ),
    ]

    return TyreNominationResponse(
        circuit_key=key,
        year=year,
        slicks=slicks,
        wet=wet,
        all_compounds=slicks + wet,
    )
