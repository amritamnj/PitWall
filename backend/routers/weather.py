"""
Weather router — fetches current conditions + 5-day forecast from
OpenWeatherMap free-tier endpoints (2.5).

Uses two endpoints (both included in every free API key):
    /data/2.5/weather   — current conditions
    /data/2.5/forecast  — 5-day / 3-hour forecast (up to 40 entries)

Track temp heuristic:
    track_temp ≈ air_temp + 15°C
    (Real track temps depend on surface type, cloud cover, sun angle, etc.
     This is a rough but commonly used approximation in F1 strategy.)

Requires OPENWEATHER_API_KEY in .env.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/weather", tags=["weather"])

TRACK_TEMP_OFFSET = 15.0  # degrees C added to air temp


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class HourlyForecast(BaseModel):
    dt_utc: str  # ISO 8601
    air_temp_c: float
    track_temp_c: float  # derived: air_temp + 15
    humidity_pct: float
    wind_speed_ms: float
    wind_deg: int
    rain_probability: float  # 0.0 – 1.0
    weather_desc: str
    weather_icon: str  # OpenWeatherMap icon code


class WeatherResponse(BaseModel):
    circuit: str
    lat: float
    lon: float
    forecast_hours: int
    current_air_temp_c: Optional[float] = None
    current_track_temp_c: Optional[float] = None
    hourly: list[HourlyForecast]
    note: str = (
        "track_temp is estimated as air_temp + 15°C. "
        "Actual track temps vary with surface, sun exposure, and cloud cover."
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/", response_model=WeatherResponse)
def get_weather(
    lat: float = Query(..., description="Circuit latitude"),
    lon: float = Query(..., description="Circuit longitude"),
    circuit: str = Query("Unknown Circuit", description="Circuit name for display"),
):
    """
    Fetch current weather + 5-day forecast for the given circuit coordinates.

    Requires OPENWEATHER_API_KEY environment variable.
    Falls back to a placeholder response if the key is missing or the API fails,
    so the rest of the app remains usable during development.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY", "")

    if not api_key:
        logger.warning("OPENWEATHER_API_KEY not set — returning placeholder weather data")
        return _placeholder_response(circuit, lat, lon)

    base_params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}

    # --- Fetch current conditions ---
    current_air: Optional[float] = None
    current_track: Optional[float] = None

    try:
        resp_cur = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params=base_params,
            timeout=10,
        )
        resp_cur.raise_for_status()
        cur_data = resp_cur.json()
        current_air = cur_data.get("main", {}).get("temp")
        if current_air is not None:
            current_track = current_air + TRACK_TEMP_OFFSET
    except requests.exceptions.HTTPError as e:
        # Note: bool(Response) is False for 4xx/5xx, so use `is not None`
        status = e.response.status_code if e.response is not None else 500
        logger.error(f"OpenWeatherMap current-weather error ({status}): {e}")
        if status == 401:
            logger.warning(
                "API key rejected (401). New keys take up to 2 hours to activate. "
                "Falling back to placeholder data."
            )
            return _placeholder_response(
                circuit, lat, lon,
                note=(
                    "API key not yet active — new OpenWeatherMap keys take up to 2 hours. "
                    "The app will use real weather data once the key activates."
                ),
            )
        raise HTTPException(status_code=502, detail=f"Weather API error: {status}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Current weather fetch failed: {e}")
        return _placeholder_response(circuit, lat, lon)

    # --- Fetch 5-day / 3-hour forecast ---
    hourly_list: list[HourlyForecast] = []

    try:
        resp_fc = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params=base_params,
            timeout=10,
        )
        resp_fc.raise_for_status()
        fc_data = resp_fc.json()

        for entry in fc_data.get("list", []):
            air_temp = entry.get("main", {}).get("temp", 0.0)
            weather_info = entry.get("weather", [{}])[0]

            hourly_list.append(HourlyForecast(
                dt_utc=datetime.fromtimestamp(entry["dt"], tz=timezone.utc).isoformat(),
                air_temp_c=round(air_temp, 1),
                track_temp_c=round(air_temp + TRACK_TEMP_OFFSET, 1),
                humidity_pct=entry.get("main", {}).get("humidity", 0),
                wind_speed_ms=entry.get("wind", {}).get("speed", 0.0),
                wind_deg=entry.get("wind", {}).get("deg", 0),
                rain_probability=round(entry.get("pop", 0.0), 2),
                weather_desc=weather_info.get("description", ""),
                weather_icon=weather_info.get("icon", "01d"),
            ))
    except requests.exceptions.RequestException as e:
        logger.error(f"Forecast fetch failed: {e}")
        # Continue with current-only data; hourly_list stays empty

    return WeatherResponse(
        circuit=circuit,
        lat=lat,
        lon=lon,
        forecast_hours=len(hourly_list),
        current_air_temp_c=round(current_air, 1) if current_air is not None else None,
        current_track_temp_c=round(current_track, 1) if current_track is not None else None,
        hourly=hourly_list,
    )


def _placeholder_response(
    circuit: str, lat: float, lon: float, *, note: Optional[str] = None,
) -> WeatherResponse:
    """
    Return a minimal placeholder when the API key is missing or the API is down.
    This lets the frontend render without crashing during development.
    """
    return WeatherResponse(
        circuit=circuit,
        lat=lat,
        lon=lon,
        forecast_hours=0,
        current_air_temp_c=25.0,
        current_track_temp_c=40.0,
        hourly=[],
        note=note or (
            "Placeholder data — OPENWEATHER_API_KEY not configured or API unavailable. "
            "Set OPENWEATHER_API_KEY in backend/.env to get real forecasts."
        ),
    )
