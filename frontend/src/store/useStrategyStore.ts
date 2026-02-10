import { create } from "zustand";
import type {
  RaceEvent,
  TyreNominationResponse,
  WeatherResponse,
  DegradationResponse,
  SimulateResponse,
  WeatherCondition,
  TabId,
  CompoundParams,
} from "../types";
import * as api from "../lib/api";

/* ------------------------------------------------------------------ */
/* Store shape                                                        */
/* ------------------------------------------------------------------ */

interface StrategyState {
  /* --- Race context --- */
  race: RaceEvent | null;
  daysUntil: number;
  seasonStatus: string;

  /* --- User controls --- */
  trackTemp: number;
  weatherCondition: WeatherCondition;
  rainIntensity: number;
  baseLapTimeOverride: number | null;
  pitLossOverride: number | null;

  /* --- Data --- */
  tyres: TyreNominationResponse | null;
  weather: WeatherResponse | null;
  degradation: DegradationResponse | null;
  simulation: SimulateResponse | null;

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
  setTrackTemp: (t: number) => void;
  setWeatherCondition: (w: WeatherCondition) => void;
  setRainIntensity: (r: number) => void;
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

  trackTemp: 35,
  weatherCondition: "dry",
  rainIntensity: 0,
  baseLapTimeOverride: null,
  pitLossOverride: null,

  tyres: null,
  weather: null,
  degradation: null,
  simulation: null,

  activeTab: "overview",
  sidebarOpen: true,
  error: null,

  loadingInit: true,
  loadingDeg: false,
  loadingSim: false,

  /* ---- simple setters ---- */

  setActiveTab: (tab) => set({ activeTab: tab }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setTrackTemp: (t) => set({ trackTemp: t }),
  setWeatherCondition: (w) => set({ weatherCondition: w }),
  setRainIntensity: (r) => set({ rainIntensity: r }),
  setBaseLapTimeOverride: (v) => set({ baseLapTimeOverride: v }),
  setPitLossOverride: (v) => set({ pitLossOverride: v }),
  clearError: () => set({ error: null }),

  /* ---- fetch initial data (race + tyres + weather) ---- */

  fetchInitialData: async () => {
    set({ loadingInit: true, error: null });
    try {
      const nextRace = await api.fetchNextRace();
      const race = nextRace.event;

      // Parallel fetches for tyres + weather
      const [tyres, weather] = await Promise.all([
        api.fetchTyreNominations(race.circuit_key),
        api.fetchWeather(race.lat, race.lon, race.circuit_full_name),
      ]);

      // Use weather track temp if available
      const initialTemp = weather.current_track_temp_c ?? 35;

      set({
        race,
        daysUntil: nextRace.days_until,
        seasonStatus: nextRace.season_status,
        tyres,
        weather,
        trackTemp: Math.round(initialTemp),
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
    const { race, trackTemp } = get();
    if (!race) return;

    set({ loadingDeg: true });
    try {
      const deg = await api.fetchDegradation(race.circuit_key, trackTemp);
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
      trackTemp,
      weatherCondition,
      rainIntensity,
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

      const sim = await api.runSimulation({
        total_laps: race.laps ?? 58,
        pit_loss_seconds: pitLossOverride ?? race.pit_loss ?? 22,
        base_lap_time_s: refLap,
        track_temp_c: trackTemp,
        weather_condition: weatherCondition,
        rain_intensity: rainIntensity,
        compounds,
      });

      set({ simulation: sim, loadingSim: false });
    } catch (e: any) {
      set({
        loadingSim: false,
        error: e?.message ?? "Simulation failed",
      });
    }
  },
}));
