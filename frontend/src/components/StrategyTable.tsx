import { memo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Trophy, Clock, ArrowDown } from "lucide-react";
import clsx from "clsx";
import type { StrategyResult } from "../types";
import { COMPOUND_COLORS } from "../lib/constants";

interface Props {
  strategies: StrategyResult[];
  recommended: string;
  deltaS: number;
}

function StrategyTableInner({ strategies, recommended, deltaS }: Props) {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const bestTime = strategies.length > 0 ? strategies[0].total_time_s : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className="glass-card overflow-hidden"
    >
      {/* Recommended banner */}
      {strategies.length > 0 && (
        <div className="px-5 py-3 border-b border-f1-border bg-gradient-to-r from-compound-c3/10 to-compound-c4/10">
          <div className="flex items-center gap-2">
            <Trophy size={14} className="text-compound-c3" />
            <span className="text-sm font-semibold text-compound-c3">
              Optimal: {recommended}
            </span>
            {deltaS > 0 && (
              <span className="text-xs text-f1-dim ml-auto">
                Wins by{" "}
                <span className="font-mono text-green-400">
                  {deltaS.toFixed(1)}s
                </span>
              </span>
            )}
          </div>
        </div>
      )}

      {/* Table header */}
      <div className="grid grid-cols-12 gap-2 px-5 py-2 text-[10px] uppercase tracking-wider text-f1-dim font-semibold border-b border-f1-border/50">
        <div className="col-span-1">#</div>
        <div className="col-span-4">Strategy</div>
        <div className="col-span-1 text-center">Stops</div>
        <div className="col-span-2 text-right">Total Time</div>
        <div className="col-span-2 text-right">Delta</div>
        <div className="col-span-2 text-right">Pit Laps</div>
      </div>

      {/* Rows */}
      {strategies.map((strat, i) => {
        const isRec = strat.name === recommended;
        const delta = strat.total_time_s - bestTime;
        const isExpanded = expandedIdx === i;

        return (
          <div key={i}>
            <motion.button
              onClick={() => setExpandedIdx(isExpanded ? null : i)}
              className={clsx(
                "w-full grid grid-cols-12 gap-2 px-5 py-3 text-sm items-center transition-colors duration-150",
                "hover:bg-f1-surface/50",
                isRec && "bg-compound-c3/5"
              )}
              initial={false}
            >
              {/* Rank */}
              <div className="col-span-1 font-mono text-f1-dim">{i + 1}</div>

              {/* Name with compound dots */}
              <div className="col-span-4 flex items-center gap-2 text-left">
                <div className="flex gap-0.5">
                  {strat.stints.map((s, si) => (
                    <div
                      key={si}
                      className="w-2 h-2 rounded-full"
                      style={{
                        backgroundColor: COMPOUND_COLORS[s.compound] ?? "#555",
                      }}
                    />
                  ))}
                </div>
                <span
                  className={clsx(
                    "truncate text-xs",
                    isRec ? "font-semibold text-f1-text" : "text-f1-dim"
                  )}
                >
                  {strat.stops}-Stop:{" "}
                  {strat.stints.map((s) => s.compound).join(" → ")}
                </span>
              </div>

              {/* Stops */}
              <div className="col-span-1 text-center font-mono">{strat.stops}</div>

              {/* Total time */}
              <div className="col-span-2 text-right font-mono text-xs">
                <Clock size={11} className="inline mr-1 opacity-40" />
                {strat.total_time_display}
              </div>

              {/* Delta */}
              <div
                className={clsx(
                  "col-span-2 text-right font-mono text-xs font-semibold",
                  delta === 0 ? "text-green-400" : "text-red-400/80"
                )}
              >
                {delta === 0 ? "BEST" : `+${delta.toFixed(1)}s`}
              </div>

              {/* Pit laps */}
              <div className="col-span-2 flex items-center justify-end gap-1">
                <span className="font-mono text-xs text-f1-dim">
                  {strat.pit_stop_laps.length > 0
                    ? strat.pit_stop_laps.join(", ")
                    : "—"}
                </span>
                <ChevronDown
                  size={14}
                  className={clsx(
                    "text-f1-dim transition-transform duration-200",
                    isExpanded && "rotate-180"
                  )}
                />
              </div>
            </motion.button>

            {/* Expanded detail */}
            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden border-t border-f1-border/30"
                >
                  <div className="px-5 py-3 bg-f1-surface/30">
                    {strat.weather_note && (
                      <p className="text-xs text-blue-400/80 mb-3 flex items-center gap-1">
                        <ArrowDown size={10} />
                        {strat.weather_note}
                      </p>
                    )}
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-[10px] uppercase tracking-wider text-f1-dim">
                          <th className="text-left pb-2">Stint</th>
                          <th className="text-left pb-2">Compound</th>
                          <th className="text-center pb-2">Laps</th>
                          <th className="text-right pb-2">Avg Lap</th>
                          <th className="text-right pb-2">Final Lap</th>
                          <th className="text-right pb-2">Stint Time</th>
                          <th className="text-right pb-2">Cliff</th>
                        </tr>
                      </thead>
                      <tbody>
                        {strat.stints.map((stint) => (
                          <tr
                            key={stint.stint_number}
                            className="border-t border-f1-border/20"
                          >
                            <td className="py-1.5 font-mono">
                              S{stint.stint_number}
                            </td>
                            <td className="py-1.5">
                              <span className="flex items-center gap-1.5">
                                <span
                                  className="w-2 h-2 rounded-full"
                                  style={{
                                    backgroundColor:
                                      COMPOUND_COLORS[stint.compound] ?? "#555",
                                  }}
                                />
                                {stint.compound}
                                {stint.is_wet_tyre && (
                                  <span className="text-[9px] text-blue-400">
                                    WET
                                  </span>
                                )}
                              </span>
                            </td>
                            <td className="text-center py-1.5 font-mono">
                              {stint.start_lap}–{stint.end_lap} ({stint.laps})
                            </td>
                            <td className="text-right py-1.5 font-mono">
                              {stint.avg_lap_time_s.toFixed(2)}s
                            </td>
                            <td className="text-right py-1.5 font-mono">
                              {stint.final_lap_time_s.toFixed(2)}s
                            </td>
                            <td className="text-right py-1.5 font-mono">
                              {(stint.stint_time_s / 60).toFixed(1)}m
                            </td>
                            <td
                              className={clsx(
                                "text-right py-1.5 font-mono",
                                stint.cliff_laps > 0 && "text-amber-400"
                              )}
                            >
                              {stint.cliff_laps > 0
                                ? `${stint.cliff_laps} laps`
                                : "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}
    </motion.div>
  );
}

export const StrategyTable = memo(StrategyTableInner);
