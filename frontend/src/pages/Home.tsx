import { useEffect, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  LineChart,
  Target,
  AlertTriangle,
  X,
  Play,
  RotateCcw,
} from "lucide-react";
import clsx from "clsx";
import { useStrategyStore } from "../store/useStrategyStore";
import { Sidebar } from "../components/Sidebar";
import { WeatherSummary } from "../components/WeatherSummary";
import { TyrePills } from "../components/TyrePills";
import { DegradationChart } from "../components/DegradationChart";
import { CompoundCards } from "../components/CompoundCards";
import { StintTimeline } from "../components/StintTimeline";
import { StrategyTable } from "../components/StrategyTable";
import { HistoricalContext } from "../components/HistoricalContext";
import { SkeletonChart, SkeletonCard } from "../components/LoadingSkeleton";
import type { TabId } from "../types";

/* ------------------------------------------------------------------ */
/* Tab config                                                         */
/* ------------------------------------------------------------------ */

const TABS: { id: TabId; label: string; icon: typeof LayoutDashboard }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "degradation", label: "Degradation", icon: LineChart },
  { id: "strategy", label: "Strategy", icon: Target },
];

/* ------------------------------------------------------------------ */
/* Page animation variants                                            */
/* ------------------------------------------------------------------ */

const pageVariants = {
  initial: { opacity: 0, y: 12 },
  in: { opacity: 1, y: 0 },
  out: { opacity: 0, y: -12 },
};

/* ------------------------------------------------------------------ */
/* Home Page                                                          */
/* ------------------------------------------------------------------ */

export default function Home() {
  const {
    race,
    activeTab,
    setActiveTab,
    loadingInit,
    error,
    clearError,
    fetchInitialData,
  } = useStrategyStore();

  // Fetch on mount
  const initRan = useRef(false);
  useEffect(() => {
    if (!initRan.current) {
      initRan.current = true;
      fetchInitialData();
    }
  }, [fetchInitialData]);

  return (
    <div className="flex h-screen overflow-hidden bg-f1-bg">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Tab navigation */}
        <nav className="flex-shrink-0 flex items-center gap-1 px-6 pt-4 pb-0 border-b border-f1-border/50 bg-f1-bg/80 backdrop-blur-sm">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx("tab-button", isActive && "active")}
              >
                <span className="flex items-center gap-1.5">
                  <Icon size={14} />
                  {tab.label}
                </span>
              </button>
            );
          })}

          {/* Race badge in tab bar */}
          {race && (
            <span className="ml-auto text-[10px] font-mono text-f1-dim">
              {race.circuit_full_name} — {race.laps} laps
            </span>
          )}
        </nav>

        {/* Error toast */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mx-6 mt-3 flex items-center gap-2 px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-400"
            >
              <AlertTriangle size={14} />
              <span className="flex-1">{error}</span>
              <button onClick={clearError} className="hover:text-red-300">
                <X size={14} />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          <AnimatePresence mode="wait">
            {activeTab === "overview" && (
              <motion.div
                key="overview"
                variants={pageVariants}
                initial="initial"
                animate="in"
                exit="out"
                transition={{ duration: 0.25 }}
              >
                <OverviewTab />
              </motion.div>
            )}
            {activeTab === "degradation" && (
              <motion.div
                key="degradation"
                variants={pageVariants}
                initial="initial"
                animate="in"
                exit="out"
                transition={{ duration: 0.25 }}
              >
                <DegradationTab />
              </motion.div>
            )}
            {activeTab === "strategy" && (
              <motion.div
                key="strategy"
                variants={pageVariants}
                initial="initial"
                animate="in"
                exit="out"
                transition={{ duration: 0.25 }}
              >
                <StrategyTab />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Overview Tab                                                       */
/* ------------------------------------------------------------------ */

function OverviewTab() {
  const { tyres, degradation, simulation, race, loadingInit } =
    useStrategyStore();

  if (loadingInit) {
    return (
      <div className="space-y-4">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-5xl">
      {/* Weather */}
      <WeatherSummary />

      {/* Quick tyre info */}
      {tyres && (
        <div className="glass-card p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-f1-dim mb-3">
            Pirelli Allocation — {tyres.circuit_key}
          </h3>
          <TyrePills compounds={tyres.all_compounds} />
        </div>
      )}

      {/* Quick strategy summary */}
      {simulation && simulation.strategies.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-5 glow-border"
        >
          <h3 className="text-xs font-semibold uppercase tracking-wider text-f1-dim mb-2">
            Recommended Strategy
          </h3>
          <div className="flex items-center gap-3">
            <Target size={20} className="text-compound-c3" />
            <div>
              <p className="font-bold text-lg text-compound-c3">
                {simulation.recommended}
              </p>
              <p className="text-xs text-f1-dim font-mono">
                {simulation.strategies[0].total_time_display}
                {simulation.delta_s > 0 && (
                  <span className="text-green-400 ml-2">
                    wins by {simulation.delta_s.toFixed(1)}s
                  </span>
                )}
              </p>
            </div>
          </div>

          {/* Mini stint bar */}
          <div className="flex mt-3 h-6 rounded overflow-hidden">
            {simulation.strategies[0].stints.map((stint, i) => {
              const color =
                {
                  C1: "#d4d4d8",
                  C2: "#a1a1aa",
                  C3: "#eab308",
                  C4: "#ef4444",
                  C5: "#dc2626",
                  INTERMEDIATE: "#22c55e",
                  WET: "#3b82f6",
                }[stint.compound] ?? "#555";
              const w = (stint.laps / (race?.laps ?? 58)) * 100;
              return (
                <div
                  key={i}
                  className="flex items-center justify-center text-[10px] font-bold"
                  style={{
                    width: `${w}%`,
                    backgroundColor: `${color}90`,
                    color:
                      stint.compound === "C1" || stint.compound === "C2"
                        ? "#1a1d27"
                        : "#fff",
                  }}
                >
                  {stint.compound} ({stint.laps})
                </div>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* Quick deg summary */}
      {degradation && (
        <div className="glass-card p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-f1-dim mb-2">
            Degradation Summary
          </h3>
          <div className="flex flex-wrap gap-4 text-xs">
            {Object.entries(degradation.compounds)
              .filter(([k]) => k.startsWith("C"))
              .sort(([a], [b]) => a.localeCompare(b))
              .map(([code, d]) => (
                <div key={code} className="flex items-center gap-2">
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{
                      backgroundColor:
                        {
                          C1: "#d4d4d8",
                          C2: "#a1a1aa",
                          C3: "#eab308",
                          C4: "#ef4444",
                          C5: "#dc2626",
                        }[code] ?? "#555",
                    }}
                  />
                  <span className="font-mono">
                    {code}: {d.avg_deg_s_per_lap.toFixed(3)}s/lap
                  </span>
                </div>
              ))}
          </div>
          <div className="mt-2 text-[10px] text-f1-dim">
            Source: {degradation.data_source} |{" "}
            {degradation.track_temp_c
              ? `Track temp: ${degradation.track_temp_c}°C`
              : "No temp adjustment"}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Degradation Tab                                                    */
/* ------------------------------------------------------------------ */

function DegradationTab() {
  const { degradation, tyres, race, loadingDeg } = useStrategyStore();

  if (loadingDeg || !degradation) {
    return (
      <div className="space-y-4">
        <SkeletonChart />
        <div className="grid grid-cols-3 gap-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-5xl">
      <DegradationChart
        degradation={degradation}
        tyres={tyres}
        totalLaps={race?.laps ?? 58}
      />

      <CompoundCards degradation={degradation} tyres={tyres} />

      {/* Notes */}
      {degradation.notes.length > 0 && (
        <div className="text-[10px] text-f1-dim space-y-1">
          {degradation.notes.map((note, i) => (
            <p key={i}>• {note}</p>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Strategy Tab                                                       */
/* ------------------------------------------------------------------ */

function StrategyTab() {
  const { simulation, race, historicalProfile, loadingSim, runSimulation } = useStrategyStore();

  const handleRun = useCallback(() => {
    runSimulation();
  }, [runSimulation]);

  if (loadingSim && !simulation) {
    return (
      <div className="space-y-4">
        <SkeletonChart />
        <SkeletonCard />
      </div>
    );
  }

  if (!simulation || simulation.strategies.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <Target size={48} className="text-f1-muted mb-4" />
        <h3 className="text-lg font-semibold mb-2">No Simulation Results</h3>
        <p className="text-sm text-f1-dim mb-6 max-w-md">
          Adjust the track temperature and weather conditions in the sidebar,
          then run a simulation to compare pit strategies.
        </p>
        <button
          onClick={handleRun}
          className="flex items-center gap-2 px-6 py-2.5 rounded-lg bg-gradient-to-r from-compound-c3 to-compound-c4 text-black font-semibold text-sm hover:brightness-110 transition-all"
        >
          <Play size={16} />
          Run Simulation
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-6xl">
      {/* Re-run button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold">Strategy Comparison</h2>
          <p className="text-xs text-f1-dim">
            {simulation.weather_condition === "dry"
              ? "Dry conditions"
              : `${simulation.weather_condition} — rain: ${Math.round(simulation.rain_intensity * 100)}%`}
            {" • "}
            {simulation.model}
          </p>
        </div>
        <button
          onClick={handleRun}
          disabled={loadingSim}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-f1-card border border-f1-border text-xs font-medium hover:bg-f1-surface transition-colors disabled:opacity-50"
        >
          <RotateCcw size={12} className={loadingSim ? "animate-spin" : ""} />
          {loadingSim ? "Running..." : "Re-run"}
        </button>
      </div>

      {/* Historical Context */}
      {historicalProfile && historicalProfile.races_used > 0 && (
        <HistoricalContext
          profile={historicalProfile}
          totalLaps={race?.laps ?? simulation.total_laps}
        />
      )}

      {/* Stint Timeline */}
      <StintTimeline
        strategies={simulation.strategies}
        totalLaps={race?.laps ?? simulation.total_laps}
        recommended={simulation.recommended}
      />

      {/* Strategy Table */}
      <StrategyTable
        strategies={simulation.strategies}
        recommended={simulation.recommended}
        deltaS={simulation.delta_s}
        simulation={simulation}
      />
    </div>
  );
}
