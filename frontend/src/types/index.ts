/* ------------------------------------------------------------------ */
/* Backend API response types — mirrors FastAPI Pydantic models       */
/* ------------------------------------------------------------------ */

export interface RaceEvent {
  round: string | number;
  name: string;
  circuit_key: string;
  circuit_full_name: string;
  country: string;
  date: string;
  lat: number;
  lon: number;
  laps: number | null;
  length_km: number | null;
  pit_loss: number | null;
  sprint: boolean;
  is_testing: boolean;
}

export interface NextRaceResponse {
  event: RaceEvent;
  days_until: number;
  season_status: "pre_season" | "in_season" | "post_season";
}

export interface CompoundInfo {
  code: string;
  label: string;
  colour: string;
  category: "slick" | "wet";
  role: "hard" | "medium" | "soft" | null;
}

export interface TyreNominationResponse {
  circuit_key: string;
  year: number;
  slicks: CompoundInfo[];
  wet: CompoundInfo[];
  all_compounds: CompoundInfo[];
}

export interface CompoundDegradation {
  avg_deg_s_per_lap: number;
  cliff_onset_lap: number;
  cliff_rate_s_per_lap2: number;
  typical_max_stint_laps: number;
  avg_reference_lap_s: number;
  base_pace_offset: number;
  temp_multiplier?: number;
}

export interface DegradationResponse {
  circuit: string;
  years_used: number[];
  track_temp_c: number | null;
  data_source: "historical" | "fallback";
  compounds: Record<string, CompoundDegradation>;
  notes: string[];
}

export interface CompoundParams {
  avg_deg_s_per_lap: number;
  cliff_onset_lap: number;
  cliff_rate_s_per_lap2: number;
  typical_max_stint_laps: number;
  base_pace_offset: number;
}

export interface SimulateRequest {
  total_laps: number;
  pit_loss_seconds: number;
  base_lap_time_s: number;
  track_temp_c?: number;
  weather_condition: string;
  rain_intensity: number;
  compounds: Record<string, CompoundParams>;
}

export interface StintDetail {
  stint_number: number;
  compound: string;
  start_lap: number;
  end_lap: number;
  laps: number;
  stint_time_s: number;
  avg_lap_time_s: number;
  final_lap_time_s: number;
  cliff_laps: number;
  is_wet_tyre: boolean;
}

export interface StrategyResult {
  name: string;
  stops: number;
  total_time_s: number;
  total_time_display: string;
  pit_stop_laps: number[];
  stints: StintDetail[];
  weather_note: string;
}

export interface SimulateResponse {
  total_laps: number;
  pit_loss_seconds: number;
  base_lap_time_s: number;
  track_temp_c: number | null;
  weather_condition: string;
  rain_intensity: number;
  strategies: StrategyResult[];
  recommended: string;
  delta_s: number;
  model: string;
}

export interface HourlyForecast {
  dt_utc: string;
  air_temp_c: number;
  track_temp_c: number;
  humidity_pct: number;
  wind_speed_ms: number;
  wind_deg: number;
  rain_probability: number;
  weather_desc: string;
  weather_icon: string;
}

export interface WeatherResponse {
  circuit: string;
  lat: number;
  lon: number;
  forecast_hours: number;
  current_air_temp_c: number | null;
  current_track_temp_c: number | null;
  hourly: HourlyForecast[];
  note: string;
}

export type WeatherCondition = "dry" | "damp" | "wet" | "extreme";
export type TabId = "overview" | "degradation" | "strategy";
