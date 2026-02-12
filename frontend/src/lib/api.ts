import axios from "axios";
import type {
  NextRaceResponse,
  TyreNominationResponse,
  WeatherResponse,
  DegradationResponse,
  SimulateRequest,
  SimulateResponse,
  CircuitHistoricalProfile,
  GridCalendarResponse,
  GridDriversResponse,
  GridTeamsResponse,
} from "../types";

const client = axios.create({ baseURL: "/api/v1", timeout: 120_000 });

/* ---------- Calendar ---------- */

export async function fetchNextRace(): Promise<NextRaceResponse> {
  const { data } = await client.get<NextRaceResponse>("/calendar/next");
  return data;
}

/* ---------- Tyres ---------- */

export async function fetchTyreNominations(
  circuitKey: string,
  year = 2026
): Promise<TyreNominationResponse> {
  const { data } = await client.get<TyreNominationResponse>(
    `/tyres/${encodeURIComponent(circuitKey)}`,
    { params: { year } }
  );
  return data;
}

/* ---------- Weather ---------- */

export async function fetchWeather(
  lat: number,
  lon: number,
  circuit: string
): Promise<WeatherResponse> {
  const { data } = await client.get<WeatherResponse>("/weather/", {
    params: { lat, lon, circuit },
  });
  return data;
}

/* ---------- Degradation ---------- */

export async function fetchDegradation(
  circuit: string,
  trackTemp?: number
): Promise<DegradationResponse> {
  const { data } = await client.get<DegradationResponse>("/degradation/", {
    params: { circuit, track_temp: trackTemp },
  });
  return data;
}

/* ---------- Historical ---------- */

export async function fetchHistoricalProfile(
  circuitKey: string,
  seasons?: number[]
): Promise<CircuitHistoricalProfile> {
  const { data } = await client.get<CircuitHistoricalProfile>(
    "/historical/profile",
    {
      params: {
        circuit_key: circuitKey,
        ...(seasons ? { seasons: seasons.join(",") } : {}),
      },
    }
  );
  return data;
}

/* ---------- Grid ---------- */

export async function fetchGridCalendar(): Promise<GridCalendarResponse> {
  const { data } = await client.get<GridCalendarResponse>("/grid/calendar");
  return data;
}

export async function fetchGridDrivers(): Promise<GridDriversResponse> {
  const { data } = await client.get<GridDriversResponse>("/grid/drivers");
  return data;
}

export async function fetchGridTeams(): Promise<GridTeamsResponse> {
  const { data } = await client.get<GridTeamsResponse>("/grid/teams");
  return data;
}

/* ---------- Simulate ---------- */

export async function runSimulation(
  req: SimulateRequest
): Promise<SimulateResponse> {
  const { data } = await client.post<SimulateResponse>("/simulate/", req);
  return data;
}
