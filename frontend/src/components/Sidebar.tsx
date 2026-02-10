import { memo, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { PanelLeftClose, PanelLeft, Settings, RotateCcw } from "lucide-react";
import { useStrategyStore } from "../store/useStrategyStore";
import { RaceHeader } from "./RaceHeader";
import { TyrePills } from "./TyrePills";
import { TemperatureSlider } from "./TemperatureSlider";
import { WeatherModeToggle } from "./WeatherModeToggle";
import { RainSlider } from "./RainSlider";
import { SkeletonCard } from "./LoadingSkeleton";

function SidebarInner() {
  const {
    race,
    daysUntil,
    seasonStatus,
    tyres,
    trackTemp,
    weatherCondition,
    rainIntensity,
    sidebarOpen,
    loadingInit,
    loadingDeg,
    loadingSim,
    toggleSidebar,
    setTrackTemp,
    setWeatherCondition,
    setRainIntensity,
    fetchDegradation,
    runSimulation,
  } = useStrategyStore();

  // Debounced degradation fetch on slider commit
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const handleTempCommit = useCallback(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      fetchDegradation();
    }, 300);
  }, [fetchDegradation]);

  // Weather condition change triggers immediate simulation re-run
  const handleWeatherChange = useCallback(
    (w: "dry" | "damp" | "wet" | "extreme") => {
      setWeatherCondition(w);
      // Slight delay so state settles
      setTimeout(() => runSimulation(), 50);
    },
    [setWeatherCondition, runSimulation]
  );

  const handleRainCommit = useCallback(() => {
    setTimeout(() => runSimulation(), 50);
  }, [runSimulation]);

  const showWetControls = weatherCondition !== "dry";

  return (
    <>
      {/* Toggle button (visible when sidebar is closed) */}
      <AnimatePresence>
        {!sidebarOpen && (
          <motion.button
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            onClick={toggleSidebar}
            className="fixed top-4 left-4 z-50 p-2 rounded-lg bg-f1-card border border-f1-border hover:bg-f1-surface transition-colors"
          >
            <PanelLeft size={18} />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Sidebar panel */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.aside
            initial={{ x: -320, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -320, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
            className="flex-shrink-0 w-80 h-screen overflow-y-auto border-r border-f1-border bg-f1-surface/50 backdrop-blur-sm"
          >
            {/* Header bar */}
            <div className="sticky top-0 z-10 flex items-center justify-between px-5 py-3 bg-f1-surface/80 backdrop-blur-md border-b border-f1-border/50">
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-6 rounded-full bg-gradient-to-b from-compound-c3 to-compound-c4" />
                <span className="text-sm font-bold tracking-tight">
                  PitWall
                </span>
              </div>
              <button
                onClick={toggleSidebar}
                className="p-1.5 rounded-md hover:bg-f1-card transition-colors text-f1-dim hover:text-f1-text"
              >
                <PanelLeftClose size={16} />
              </button>
            </div>

            <div className="p-5 space-y-6">
              {/* Race info */}
              {loadingInit ? (
                <SkeletonCard />
              ) : race ? (
                <RaceHeader
                  race={race}
                  daysUntil={daysUntil}
                  seasonStatus={seasonStatus}
                />
              ) : (
                <div className="text-sm text-f1-dim">No race data loaded</div>
              )}

              {/* Divider */}
              <div className="h-px bg-f1-border" />

              {/* Controls */}
              <div className="space-y-5">
                <TemperatureSlider
                  value={trackTemp}
                  onChange={setTrackTemp}
                  onCommit={handleTempCommit}
                />

                <WeatherModeToggle
                  value={weatherCondition}
                  onChange={handleWeatherChange}
                />

                {/* Rain intensity (only in wet modes) */}
                <AnimatePresence>
                  {showWetControls && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <RainSlider
                        value={rainIntensity}
                        onChange={setRainIntensity}
                        onCommit={handleRainCommit}
                      />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Divider */}
              <div className="h-px bg-f1-border" />

              {/* Tyre nominations */}
              {tyres && (
                <div className="space-y-2">
                  <span className="text-[10px] uppercase tracking-widest text-f1-dim font-semibold">
                    Tyre Allocation
                  </span>
                  <TyrePills compounds={tyres.all_compounds} />
                </div>
              )}

              {/* Loading indicators */}
              {(loadingDeg || loadingSim) && (
                <div className="flex items-center gap-2 text-xs text-f1-dim">
                  <RotateCcw size={12} className="animate-spin" />
                  {loadingDeg
                    ? "Loading degradation data..."
                    : "Running simulation..."}
                </div>
              )}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
}

export const Sidebar = memo(SidebarInner);
