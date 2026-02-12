import { memo, useMemo } from "react";
import { motion } from "framer-motion";
import { Search, User } from "lucide-react";
import { useGridStore } from "../../store/useGridStore";
import { COUNTRY_CODE_FLAGS } from "../../lib/constants";
import { SkeletonCard } from "../LoadingSkeleton";
import type { GridDriver } from "../../types";

/* ------------------------------------------------------------------ */
/* Driver card                                                        */
/* ------------------------------------------------------------------ */

function DriverCard({ driver, index }: { driver: GridDriver; index: number }) {
  const flag = driver.country_code
    ? COUNTRY_CODE_FLAGS[driver.country_code] ?? ""
    : "";
  const teamColour = `#${driver.team_colour}`;
  const initial = driver.team_name.charAt(0).toUpperCase();

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      className="glass-card p-4 flex items-center gap-3"
    >
      {/* Team initial badge */}
      <div
        className="shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold"
        style={{ backgroundColor: `${teamColour}30`, color: teamColour }}
      >
        {initial}
      </div>

      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold truncate">{driver.full_name}</p>
        <p className="text-[11px] text-f1-dim truncate">{driver.team_name}</p>
      </div>

      <div className="text-right shrink-0">
        <div
          className="text-lg font-black font-mono"
          style={{ color: teamColour }}
        >
          {driver.driver_number}
        </div>
        <div className="flex items-center justify-end gap-1 text-[10px] text-f1-dim">
          {flag && <span>{flag}</span>}
          <span className="font-mono">{driver.name_acronym}</span>
        </div>
      </div>
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/* Drivers view                                                       */
/* ------------------------------------------------------------------ */

function DriversViewInner() {
  const { drivers, loadingDrivers, driverSearch, setDriverSearch } =
    useGridStore();

  const filtered = useMemo(() => {
    if (!drivers) return [];
    const q = driverSearch.toLowerCase().trim();
    if (!q) return drivers.drivers;
    return drivers.drivers.filter(
      (d) =>
        d.full_name.toLowerCase().includes(q) ||
        d.name_acronym.toLowerCase().includes(q) ||
        d.team_name.toLowerCase().includes(q) ||
        String(d.driver_number).includes(q),
    );
  }, [drivers, driverSearch]);

  if (loadingDrivers || !drivers) {
    return (
      <div className="space-y-4">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  return (
    <div className="space-y-4 max-w-5xl">
      {/* Search */}
      <div className="relative">
        <Search
          size={14}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-f1-dim"
        />
        <input
          type="text"
          placeholder="Search drivers, teams, numbers..."
          value={driverSearch}
          onChange={(e) => setDriverSearch(e.target.value)}
          className="w-full pl-9 pr-3 py-2 rounded-lg bg-f1-card border border-f1-border text-sm text-f1-text placeholder:text-f1-dim/60 focus:outline-none focus:ring-1 focus:ring-compound-c3/50"
        />
      </div>

      {/* Grid */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <User size={40} className="text-f1-muted mb-3" />
          <p className="text-sm text-f1-dim">No drivers match your search</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map((driver, i) => (
            <DriverCard
              key={driver.driver_number}
              driver={driver}
              index={i}
            />
          ))}
        </div>
      )}

      {/* Note */}
      <p className="text-[10px] text-f1-dim text-center font-mono">
        {drivers.note}
      </p>
    </div>
  );
}

export const DriversView = memo(DriversViewInner);
