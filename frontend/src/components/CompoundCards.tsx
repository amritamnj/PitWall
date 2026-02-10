import { memo } from "react";
import { motion } from "framer-motion";
import type { DegradationResponse, TyreNominationResponse } from "../types";
import { COMPOUND_COLORS, COMPOUND_BG } from "../lib/constants";

interface Props {
  degradation: DegradationResponse;
  tyres: TyreNominationResponse | null;
}

function CompoundCardsInner({ degradation, tyres }: Props) {
  const codes = tyres
    ? tyres.slicks.map((s) => s.code)
    : Object.keys(degradation.compounds)
        .filter((c) => c.startsWith("C"))
        .sort();

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
      {codes.map((code, i) => {
        const d = degradation.compounds[code];
        if (!d) return null;
        const color = COMPOUND_COLORS[code] ?? "#888";
        const bg = COMPOUND_BG[code] ?? "rgba(136,136,136,0.1)";
        const role = tyres?.slicks.find((s) => s.code === code)?.role;

        return (
          <motion.div
            key={code}
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            className="rounded-xl border p-4 transition-all duration-200 hover:scale-[1.02]"
            style={{
              borderColor: `${color}30`,
              backgroundColor: bg,
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div
                  className="w-3.5 h-3.5 rounded-full"
                  style={{ backgroundColor: color }}
                />
                <span className="font-bold text-sm" style={{ color }}>
                  {code}
                </span>
                {role && (
                  <span className="text-[10px] uppercase tracking-wider text-f1-dim">
                    {role}
                  </span>
                )}
              </div>
              {d.temp_multiplier && (
                <span className="text-[10px] font-mono text-f1-dim">
                  {d.temp_multiplier.toFixed(2)}x temp
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
              <Stat label="Deg Rate" value={`${d.avg_deg_s_per_lap.toFixed(3)}s/lap`} />
              <Stat label="Cliff Onset" value={`Lap ${d.cliff_onset_lap}`} />
              <Stat
                label="Cliff Rate"
                value={`${d.cliff_rate_s_per_lap2.toFixed(4)}s/lap²`}
              />
              <Stat label="Max Stint" value={`${d.typical_max_stint_laps} laps`} />
              <Stat
                label="Pace Offset"
                value={`+${d.base_pace_offset.toFixed(2)}s`}
              />
              <Stat
                label="Ref Lap"
                value={`${d.avg_reference_lap_s.toFixed(2)}s`}
              />
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-f1-dim text-[10px] uppercase tracking-wider">
        {label}
      </div>
      <div className="font-mono font-medium">{value}</div>
    </div>
  );
}

export const CompoundCards = memo(CompoundCardsInner);
