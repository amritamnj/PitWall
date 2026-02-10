import { create } from "zustand";
import type {
  RaceEvent,
  TyreNominationResponse,
  WeatherResponse,
  DegradationResponse,
  SimulateResponse,
  CircuitHistoricalProfile,
  WeatherCondition,
  WeatherSource,
  UnifiedWeather,
  TabId,
  CompoundParams,
} from "../types";
import { deriveWeatherMode } from "../types";
import * as api from "../lib/api";

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

/** Extract unified weather values from the backend API response. */
function weatherFromApi(
  apiData: WeatherResponse,
): Omit<UnifiedWeather, "source"> {
  const hourly = apiData.hourly.slice(0, 6);
  const rainProbability =
    hourly.length > 0
      ? Math.max(...hourly.map((h) => h.rain_probability))
      : 0;
  const windSpeed =
    hourly.length > 0
      ? hourly.reduce((s, h) => s + h.wind_speed_ms, 0) / hourly.length
      : 0;
  // Best approximation — the API provides probability, not measured intensity.
  const rainIntensity = rainProbability;

  return {
    airTemp: apiData.current_air_temp_c ?? 25,
    trackTemp: Math.round(apiData.current_track_temp_c ?? 35),
    rainProbability,
    rainIntensity,
    windSpeed: Math.round(windSpeed * 10) / 10,
    mode: deriveWeatherMode(rainProbability, rainIntensity),
  };
}

/* ------------------------------------------------------------------ */
/* Store shape                                                        */
/* ------------------------------------------------------------------ */

interface StrategyState {
  /* --- Race context --- */
  race: RaceEvent | null;
  daysUntil: number;
  seasonStatus: string;

  /* --- Unified weather (single source of truth) --- */
  unifiedWeather: UnifiedWeather;

  /* --- User controls (non-weather) --- */
  baseLapTimeOverride: number | null;
  pitLossOverride: number | null;

  /* --- Data --- */
  tyres: TyreNominationResponse | null;
  weatherApi: WeatherResponse | null;
  degradation: DegradationResponse | null;
  simulation: SimulateResponse | null;
  historicalProfile: CircuitHistoricalProfile | null;

  /** Snapshot of weather conditions used for the last simulation run. */
  simWeatherSnapshot: {
    source: WeatherSource;
    trackTemp: number;
    mode: WeatherCondition;
    liveTrackTemp: number | null;
    liveMode: WeatherCondition | null;
  } | null;

  /* --- UI --- */
  activeTab: TabId;
  sidebarOpen: boolean;
  error: string | null;

  /* --- Loading flags --- */
  loadingInit: boolean;
  loadingDeg: boolean;
  loadingSim: boolean;

  /* --- Actions --- */
  setActiveTab: (tab: TabId) => void;
  toggleSidebar: () => void;
  setWeatherSource: (source: WeatherSource) => void;
  setTrackTemp: (t: number) => void;
  setRainIntensity: (r: number) => void;
  setWeatherModePreset: (mode: WeatherCondition) => void;
  setBaseLapTimeOverride: (v: number | null) => void;
  setPitLossOverride: (v: number | null) => void;
  clearError: () => void;

  /* --- Async --- */
  fetchInitialData: () => Promise<void>;
  fetchDegradation: () => Promise<void>;
  runSimulation: () => Promise<void>;
}

/* ------------------------------------------------------------------ */
/* Store implementation                                               */
/* ------------------------------------------------------------------ */

export const useStrategyStore = create<StrategyState>((set, get) => ({
  /* defaults */
  race: null,
  daysUntil: 0,
  seasonStatus: "pre_season",

  unifiedWeather: {
    source: "live",
    airTemp: 25,
    trackTemp: 35,
    rainProbability: 0,
    rainIntensity: 0,
    windSpeed: 0,
    mode: "dry",
  },

  baseLapTimeOverride: null,
  pitLossOverride: null,

  tyres: null,
  weatherApi: null,
  degradation: null,
  simulation: null,
  historicalProfile: null,
  simWeatherSnapshot: null,

  activeTab: "overview",
  sidebarOpen: true,
  error: null,

  loadingInit: true,
  loadingDeg: false,
  loadingSim: false,

  /* ---- simple setters ---- */

  setActiveTab: (tab) => set({ activeTab: tab }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  setWeatherSource: (source) => {
    const state = get();
    if (source === "live") {
      if (!state.weatherApi) return;
      const liveWeather = weatherFromApi(state.weatherApi);
      const prevTrackTemp = state.unifiedWeather.trackTemp;
      set({ unifiedWeather: { source: "live", ...liveWeather } });
      // If track temp changed, refetch degradation (which chains to simulation).
      // Otherwise just re-run simulation with updated weather params.
      if (liveWeather.trackTemp !== prevTrackTemp) {
        get().fetchDegradation();
      } else {
        get().runSimulation();
      }
    } else {
      // Switch to manual — keep current values so user can fine-tune
      set((s) => ({
        unifiedWeather: { ...s.unifiedWeather, source: "manual" },
      }));
    }
  },

  setTrackTemp: (t) =>
    set((s) => ({
      unifiedWeather: { ...s.unifiedWeather, trackTemp: t },
    })),

  setRainIntensity: (r) =>
    set((s) => {
      // In manual mode, keep rainProbability synced with rainIntensity
      const rainProbability =
        s.unifiedWeather.source === "manual" ? r : s.unifiedWeather.rainProbability;
      return {
        unifiedWeather: {
          ...s.unifiedWeather,
          rainIntensity: r,
          rainProbability,
          mode: deriveWeatherMode(rainProbability, r),
        },
      };
    }),

  /** Quick-set rain presets so the mode derives to the selected condition. */
  setWeatherModePreset: (mode) =>
    set((s) => {
      const presets: Record<
        WeatherCondition,
        { rainProbability: number; rainIntensity: number }
      > = {
        dry: { rainProbability: 0, rainIntensity: 0 },
        damp: { rainProbability: 0.25, rainIntensity: 0.25 },
        wet: { rainProbability: 0.5, rainIntensity: 0.5 },
        extreme: { rainProbability: 0.85, rainIntensity: 0.85 },
      };
      const p = presets[mode];
      return {
        unifiedWeather: {
          ...s.unifiedWeather,
          rainProbability: p.rainProbability,
          rainIntensity: p.rainIntensity,
          mode: deriveWeatherMode(p.rainProbability, p.rainIntensity),
        },
      };
    }),

  setBaseLapTimeOverride: (v) => set({ baseLapTimeOverride: v }),
  setPitLossOverride: (v) => set({ pitLossOverride: v }),
  clearError: () => set({ error: null }),

  /* ---- fetch initial data (race + tyres + weather) ---- */

  fetchInitialData: async () => {
    set({ loadingInit: true, error: null });
    try {
      const nextRace = await api.fetchNextRace();
      const race = nextRace.event;

      // Parallel fetches for tyres + weather + historical
      const [tyres, weatherApi, historicalProfile] = await Promise.all([
        api.fetchTyreNominations(race.circuit_key),
        api.fetchWeather(race.lat, race.lon, race.circuit_full_name),
        api.fetchHistoricalProfile(race.circuit_key).catch(() => null),
      ]);

      // Sync unified weather from API response
      const liveWeather = weatherFromApi(weatherApi);

      set({
        race,
        daysUntil: nextRace.days_until,
        seasonStatus: nextRace.season_status,
        tyres,
        weatherApi,
        historicalProfile,
        unifiedWeather: { source: "live", ...liveWeather },
        loadingInit: false,
      });

      // Chain: fetch degradation + run simulation
      await get().fetchDegradation();
    } catch (e: any) {
      set({
        loadingInit: false,
        error: e?.message ?? "Failed to load initial data",
      });
    }
  },

  /* ---- fetch degradation for current circuit + temp ---- */

  fetchDegradation: async () => {
    const { race, unifiedWeather } = get();
    if (!race) return;

    set({ loadingDeg: true });
    try {
      const deg = await api.fetchDegradation(
        race.circuit_key,
        unifiedWeather.trackTemp,
      );
      set({ degradation: deg, loadingDeg: false });

      // Auto-run simulation with fresh degradation data
      await get().runSimulation();
    } catch (e: any) {
      set({
        loadingDeg: false,
        error: e?.message ?? "Degradation fetch failed",
      });
    }
  },

  /* ---- run simulation with current state ---- */

  runSimulation: async () => {
    const {
      race,
      degradation,
      tyres,
      unifiedWeather,
      baseLapTimeOverride,
      pitLossOverride,
    } = get();

    if (!race || !degradation) return;

    set({ loadingSim: true });

    try {
      // Determine which compounds to send.
      // Use nominated slick compounds, falling back to all degradation keys.
      const slickCodes = tyres
        ? tyres.slicks.map((s) => s.code)
        : Object.keys(degradation.compounds).filter((c) => c.startsWith("C"));

      const compounds: Record<string, CompoundParams> = {};
      for (const code of slickCodes) {
        const d = degradation.compounds[code];
        if (!d) continue;
        compounds[code] = {
          avg_deg_s_per_lap: d.avg_deg_s_per_lap,
          cliff_onset_lap: d.cliff_onset_lap,
          cliff_rate_s_per_lap2: d.cliff_rate_s_per_lap2,
          typical_max_stint_laps: d.typical_max_stint_laps,
          base_pace_offset: d.base_pace_offset,
        };
      }

      // Find reference lap time from softest available compound
      const softest = slickCodes
        .filter((c) => degradation.compounds[c])
        .sort((a, b) => {
          const na = parseInt(a.replace("C", ""));
          const nb = parseInt(b.replace("C", ""));
          return nb - na;
        })[0];
      const refLap =
        baseLapTimeOverride ??
        degradation.compounds[softest]?.avg_reference_lap_s ??
        85;

      // Snapshot weather conditions used for this simulation run
      const weatherApi = get().weatherApi;
      const liveWeather = weatherApi ? weatherFromApi(weatherApi) : null;
      const snapshot = {
        source: unifiedWeather.source,
        trackTemp: unifiedWeather.trackTemp,
        mode: unifiedWeather.mode,
        liveTrackTemp: liveWeather?.trackTemp ?? null,
        liveMode: liveWeather?.mode ?? null,
      };

      const sim = await api.runSimulation({
        total_laps: race.laps ?? 58,
        pit_loss_seconds: pitLossOverride ?? race.pit_loss ?? 22,
        base_lap_time_s: refLap,
        track_temp_c: unifiedWeather.trackTemp,
        weather_condition: unifiedWeather.mode,
        rain_intensity: unifiedWeather.rainIntensity,
        compounds,
        circuit_key: race.circuit_key,
      });

      set({ simulation: sim, simWeatherSnapshot: snapshot, loadingSim: false });
    } catch (e: any) {
      set({
        loadingSim: false,
        error: e?.message ?? "Simulation failed",
      });
    }
  },
}));
