import { useEffect, useRef, memo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Calendar, Users, Building2 } from "lucide-react";
import clsx from "clsx";
import { useGridStore } from "../../store/useGridStore";
import { CalendarView } from "./CalendarView";
import { DriversView } from "./DriversView";
import { TeamsView } from "./TeamsView";
import type { GridSubView } from "../../types";

/* ------------------------------------------------------------------ */
/* Sub-nav config                                                     */
/* ------------------------------------------------------------------ */

const SUB_VIEWS: { id: GridSubView; label: string; icon: typeof Calendar }[] = [
  { id: "calendar", label: "Calendar", icon: Calendar },
  { id: "drivers", label: "Drivers", icon: Users },
  { id: "teams", label: "Teams", icon: Building2 },
];

const pageVariants = {
  initial: { opacity: 0, y: 8 },
  in: { opacity: 1, y: 0 },
  out: { opacity: 0, y: -8 },
};

/* ------------------------------------------------------------------ */
/* Grid Tab                                                           */
/* ------------------------------------------------------------------ */

function GridTabInner() {
  const { activeSubView, setSubView, fetchAllGridData } = useGridStore();

  // Fetch on first mount
  const initRan = useRef(false);
  useEffect(() => {
    if (!initRan.current) {
      initRan.current = true;
      fetchAllGridData();
    }
  }, [fetchAllGridData]);

  return (
    <div className="space-y-4">
      {/* Sub-navigation */}
      <div className="flex items-center gap-1 pb-0">
        {SUB_VIEWS.map((sv) => {
          const Icon = sv.icon;
          const isActive = activeSubView === sv.id;
          return (
            <button
              key={sv.id}
              onClick={() => setSubView(sv.id)}
              className={clsx(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                isActive
                  ? "bg-f1-surface text-f1-text"
                  : "text-f1-dim hover:text-f1-text hover:bg-f1-surface/50",
              )}
            >
              <Icon size={12} />
              {sv.label}
            </button>
          );
        })}
      </div>

      {/* Sub-view content */}
      <AnimatePresence mode="wait">
        {activeSubView === "calendar" && (
          <motion.div
            key="calendar"
            variants={pageVariants}
            initial="initial"
            animate="in"
            exit="out"
            transition={{ duration: 0.2 }}
          >
            <CalendarView />
          </motion.div>
        )}
        {activeSubView === "drivers" && (
          <motion.div
            key="drivers"
            variants={pageVariants}
            initial="initial"
            animate="in"
            exit="out"
            transition={{ duration: 0.2 }}
          >
            <DriversView />
          </motion.div>
        )}
        {activeSubView === "teams" && (
          <motion.div
            key="teams"
            variants={pageVariants}
            initial="initial"
            animate="in"
            exit="out"
            transition={{ duration: 0.2 }}
          >
            <TeamsView />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export const GridTab = memo(GridTabInner);
