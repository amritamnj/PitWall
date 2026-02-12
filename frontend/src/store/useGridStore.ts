import { create } from "zustand";
import type {
  GridSubView,
  GridCalendarResponse,
  GridDriversResponse,
  GridTeamsResponse,
} from "../types";
import * as api from "../lib/api";

/* ------------------------------------------------------------------ */
/* Store shape                                                        */
/* ------------------------------------------------------------------ */

interface GridState {
  /* --- Data --- */
  calendar: GridCalendarResponse | null;
  drivers: GridDriversResponse | null;
  teams: GridTeamsResponse | null;

  /* --- UI --- */
  activeSubView: GridSubView;
  driverSearch: string;
  expandedTeam: string | null;

  /* --- Loading --- */
  loadingCalendar: boolean;
  loadingDrivers: boolean;
  loadingTeams: boolean;
  error: string | null;
  initialized: boolean;

  /* --- Actions --- */
  setSubView: (view: GridSubView) => void;
  setDriverSearch: (q: string) => void;
  toggleTeamExpand: (teamName: string) => void;
  clearError: () => void;
  fetchAllGridData: () => Promise<void>;
}

/* ------------------------------------------------------------------ */
/* Store implementation                                               */
/* ------------------------------------------------------------------ */

export const useGridStore = create<GridState>((set, get) => ({
  calendar: null,
  drivers: null,
  teams: null,

  activeSubView: "calendar",
  driverSearch: "",
  expandedTeam: null,

  loadingCalendar: false,
  loadingDrivers: false,
  loadingTeams: false,
  error: null,
  initialized: false,

  setSubView: (view) => set({ activeSubView: view }),
  setDriverSearch: (q) => set({ driverSearch: q }),
  toggleTeamExpand: (teamName) =>
    set((s) => ({
      expandedTeam: s.expandedTeam === teamName ? null : teamName,
    })),
  clearError: () => set({ error: null }),

  fetchAllGridData: async () => {
    if (get().initialized) return;
    set({
      loadingCalendar: true,
      loadingDrivers: true,
      loadingTeams: true,
      error: null,
    });

    const results = await Promise.allSettled([
      api.fetchGridCalendar(),
      api.fetchGridDrivers(),
      api.fetchGridTeams(),
    ]);

    const calendar =
      results[0].status === "fulfilled" ? results[0].value : null;
    const drivers =
      results[1].status === "fulfilled" ? results[1].value : null;
    const teams =
      results[2].status === "fulfilled" ? results[2].value : null;

    const errors = results
      .filter((r) => r.status === "rejected")
      .map((r) => (r as PromiseRejectedResult).reason?.message ?? "Unknown error");

    set({
      calendar,
      drivers,
      teams,
      loadingCalendar: false,
      loadingDrivers: false,
      loadingTeams: false,
      initialized: true,
      error: errors.length > 0 ? errors.join("; ") : null,
    });
  },
}));
