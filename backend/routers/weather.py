"""
Weather router — fetches 48-hour forecast from OpenWeatherMap One Call API 3.0.

Provides air temperature, humidity, wind, rain probability, and a derived
track temperature estimate for the selected circuit's coordinates.

Track temp heuristic:
    track_temp ≈ air_temp + 15°C
    (Real track temps depend on surface type, cloud cover, sun angle, etc.
     This is a rough but commonly used approximation in F1 strategy.)

Requires OPENWEATHER_API_KEY in .env (free tier supports One Call 3.0 with
1,000 calls/day).
"""

import os
import logging
from datetime import datetime
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
    Fetch 48-hour weather forecast for the given circuit coordinates.

    Requires OPENWEATHER_API_KEY environment variable.
    Falls back to a placeholder response if the key is missing or the API fails,
    so the rest of the app remains usable during development.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY", "")

    if not api_key:
        logger.warning("OPENWEATHER_API_KEY not set — returning placeholder weather data")
        return _placeholder_response(circuit, lat, lon)

    try:
        # One Call API 3.0 — provides current + 48h hourly + 8-day daily
        url = "https://api.openweathermap.org/data/3.0/onecall"
        params = {
            "lat": lat,
            "lon": lon,
            "appid": api_key,
            "units": "metric",
            "exclude": "minutely,daily,alerts",
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.HTTPError as e:
        # If 401, the key is invalid; if 429, rate limited
        status = e.response.status_code if e.response else 500
        logger.error(f"OpenWeatherMap API error ({status}): {e}")
        if status == 401:
            raise HTTPException(
                status_code=502,
                detail="Invalid OPENWEATHER_API_KEY. Check your .env file.",
            )
        raise HTTPException(status_code=502, detail=f"Weather API error: {status}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Weather fetch failed: {e}")
        return _placeholder_response(circuit, lat, lon)

    # Parse current conditions
    current = data.get("current", {})
    current_air = current.get("temp")
    current_track = (current_air + TRACK_TEMP_OFFSET) if current_air is not None else None

    # Parse hourly forecast (up to 48 hours)
    hourly_data = data.get("hourly", [])
    hourly_list: list[HourlyForecast] = []

    for h in hourly_data:
        air_temp = h.get("temp", 0.0)
        weather_info = h.get("weather", [{}])[0]

        hourly_list.append(HourlyForecast(
            dt_utc=datetime.utcfromtimestamp(h["dt"]).isoformat() + "Z",
            air_temp_c=round(air_temp, 1),
            track_temp_c=round(air_temp + TRACK_TEMP_OFFSET, 1),
            humidity_pct=h.get("humidity", 0),
            wind_speed_ms=h.get("wind_speed", 0.0),
            wind_deg=h.get("wind_deg", 0),
            rain_probability=round(h.get("pop", 0.0), 2),
            weather_desc=weather_info.get("description", ""),
            weather_icon=weather_info.get("icon", "01d"),
        ))

    return WeatherResponse(
        circuit=circuit,
        lat=lat,
        lon=lon,
        forecast_hours=len(hourly_list),
        current_air_temp_c=round(current_air, 1) if current_air is not None else None,
        current_track_temp_c=round(current_track, 1) if current_track is not None else None,
        hourly=hourly_list,
    )


def _placeholder_response(circuit: str, lat: float, lon: float) -> WeatherResponse:
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
        note=(
            "Placeholder data — OPENWEATHER_API_KEY not configured or API unavailable. "
            "Set OPENWEATHER_API_KEY in backend/.env to get real forecasts."
        ),
    )
