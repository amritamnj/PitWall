import { memo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { StrategyResult, StintDetail } from "../types";
import { COMPOUND_COLORS } from "../lib/constants";

interface Props {
  strategies: StrategyResult[];
  totalLaps: number;
  recommended: string;
}

function StintTimelineInner({ strategies, totalLaps, recommended }: Props) {
  const [hoveredStint, setHoveredStint] = useState<{
    stratIdx: number;
    stintIdx: number;
  } | null>(null);

  const barH = 36;
  const rowGap = 10;
  const labelW = 200;
  const padR = 16;
  const chartW = `calc(100% - ${labelW + padR}px)`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="glass-card p-5 overflow-x-auto"
    >
      <h3 className="text-sm font-semibold mb-1">Stint Timeline</h3>
      <p className="text-xs text-f1-dim mb-4">
        Hover a stint for details. Width = proportion of total laps.
      </p>

      {/* Lap markers */}
      <div className="flex" style={{ paddingLeft: labelW }}>
        <div className="relative w-full h-5">
          {[0, 0.25, 0.5, 0.75, 1].map((frac) => {
            const lap = Math.round(frac * totalLaps);
            return (
              <span
                key={frac}
                className="absolute text-[9px] font-mono text-f1-dim -translate-x-1/2"
                style={{ left: `${frac * 100}%` }}
              >
                L{lap}
              </span>
            );
          })}
        </div>
      </div>

      {/* Strategy rows */}
      <div className="space-y-0">
        {strategies.map((strat, si) => {
          const isRecommended = strat.name === recommended;
          return (
            <div key={si} className="flex items-center" style={{ height: barH + rowGap }}>
              {/* Label */}
              <div
                className="flex-shrink-0 pr-3 text-right"
                style={{ width: labelW }}
              >
                <div
                  className="text-xs font-medium truncate"
                  title={strat.name}
                >
                  {isRecommended && (
                    <span className="text-compound-c3 mr-1">★</span>
                  )}
                  {strat.stops}-Stop
                </div>
                <div className="text-[10px] font-mono text-f1-dim">
                  {strat.total_time_display}
                </div>
              </div>

              {/* Bars */}
              <div
                className="relative flex items-center"
                style={{ width: chartW, height: barH }}
              >
                {strat.stints.map((stint, sti) => {
                  const widthPct = (stint.laps / totalLaps) * 100;
                  const color = COMPOUND_COLORS[stint.compound] ?? "#555";
                  const isHovered =
                    hoveredStint?.stratIdx === si &&
                    hoveredStint?.stintIdx === sti;

                  return (
                    <motion.div
                      key={sti}
                      className="relative h-full cursor-pointer"
                      onMouseEnter={() =>
                        setHoveredStint({ stratIdx: si, stintIdx: sti })
                      }
                      onMouseLeave={() => setHoveredStint(null)}
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: 1 }}
                      transition={{
                        delay: si * 0.1 + sti * 0.05,
                        type: "spring",
                        stiffness: 200,
                        damping: 25,
                      }}
                      style={{
                        width: `${widthPct}%`,
                        transformOrigin: "left",
                      }}
                    >
                      <div
                        className="h-full rounded-sm mx-[1px] transition-all duration-150 flex items-center justify-center"
                        style={{
                          backgroundColor: isHovered
                            ? color
                            : `${color}80`,
                          boxShadow: isHovered
                            ? `0 0 12px ${color}40`
                            : "none",
                          transform: isHovered ? "scaleY(1.15)" : "scaleY(1)",
                        }}
                      >
                        <span
                          className="text-[10px] font-bold"
                          style={{
                            color:
                              stint.compound === "C1" ||
                              stint.compound === "C2"
                                ? "#1a1d27"
                                : "#fff",
                            textShadow: "0 1px 2px rgba(0,0,0,0.5)",
                          }}
                        >
                          {stint.compound}
                        </span>
                      </div>

                      {/* Tooltip */}
                      <AnimatePresence>
                        {isHovered && (
                          <StintTooltip stint={stint} color={color} />
                        )}
                      </AnimatePresence>
                    </motion.div>
                  );
                })}

                {/* Pit stop markers */}
                {strat.pit_stop_laps.map((lap, pi) => (
                  <div
                    key={`pit-${pi}`}
                    className="absolute top-0 h-full w-[2px] bg-white/40 pointer-events-none"
                    style={{ left: `${(lap / totalLaps) * 100}%` }}
                  >
                    <div className="absolute -top-1 -left-1 w-2 h-2 rounded-full bg-white/60" />
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </motion.div>
  );
}

function StintTooltip({
  stint,
  color,
}: {
  stint: StintDetail;
  color: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 5 }}
      className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 p-3 rounded-lg border bg-f1-card/95 backdrop-blur-sm shadow-xl whitespace-nowrap"
      style={{ borderColor: `${color}40` }}
    >
      <div className="text-xs font-semibold mb-2" style={{ color }}>
        {stint.compound} — Stint {stint.stint_number}
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
        <span className="text-f1-dim">Laps</span>
        <span className="font-mono text-right">
          {stint.start_lap}–{stint.end_lap} ({stint.laps})
        </span>
        <span className="text-f1-dim">Avg Lap</span>
        <span className="font-mono text-right">
          {stint.avg_lap_time_s.toFixed(2)}s
        </span>
        <span className="text-f1-dim">Final Lap</span>
        <span className="font-mono text-right">
          {stint.final_lap_time_s.toFixed(2)}s
        </span>
        <span className="text-f1-dim">Stint Time</span>
        <span className="font-mono text-right">
          {(stint.stint_time_s / 60).toFixed(1)}m
        </span>
        {stint.cliff_laps > 0 && (
          <>
            <span className="text-amber-400">Cliff Laps</span>
            <span className="font-mono text-right text-amber-400">
              {stint.cliff_laps}
            </span>
          </>
        )}
      </div>
    </motion.div>
  );
}

export const StintTimeline = memo(StintTimelineInner);
