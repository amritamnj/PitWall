import { memo } from "react";
import { motion } from "framer-motion";
import { History, TrendingUp } from "lucide-react";
import type { CircuitHistoricalProfile } from "../types";

interface Props {
  profile: CircuitHistoricalProfile;
  totalLaps: number;
}

function HistoricalContextInner({ profile, totalLaps }: Props) {
  const { first_stop_lap, stop_count_distribution, common_strategy_sequences, undercut_overcut, notes } = profile;
  const seasonsLabel = profile.seasons_used.join(", ");

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="glass-card p-5"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <History size={14} className="text-f1-dim" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-f1-dim">
            Historical Context
          </h3>
        </div>
        <span className="text-[10px] font-mono text-f1-dim px-2 py-1 bg-f1-surface rounded">
          {seasonsLabel} &middot; {profile.races_used} race{profile.races_used !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="space-y-4">
        {/* Pit Window Bar */}
        {first_stop_lap && (
          <div>
            <div className="text-[10px] text-f1-dim uppercase tracking-wider mb-1.5">
              First Stop Window
            </div>
            <div className="relative h-6 bg-f1-surface rounded overflow-hidden">
              {/* IQR range */}
              <div
                className="absolute top-0 h-full bg-compound-c3/20 border-l border-r border-compound-c3/40"
                style={{
                  left: `${(first_stop_lap.p25 / totalLaps) * 100}%`,
                  width: `${((first_stop_lap.p75 - first_stop_lap.p25) / totalLaps) * 100}%`,
                }}
              />
              {/* Median marker */}
              <div
                className="absolute top-0 h-full w-0.5 bg-compound-c3"
                style={{ left: `${(first_stop_lap.median / totalLaps) * 100}%` }}
              />
              {/* Labels */}
              <div className="absolute inset-0 flex items-center justify-between px-2 text-[10px] font-mono">
                <span className="text-f1-dim">L1</span>
                <span className="text-compound-c3 font-semibold">
                  L{Math.round(first_stop_lap.p25)}–L{Math.round(first_stop_lap.p75)}
                  <span className="text-f1-dim ml-1">(median L{Math.round(first_stop_lap.median)})</span>
                </span>
                <span className="text-f1-dim">L{totalLaps}</span>
              </div>
            </div>
            <div className="text-[10px] text-f1-dim mt-1 font-mono">
              n={first_stop_lap.n} drivers
            </div>
          </div>
        )}

        {/* Stop Distribution Bar */}
        {stop_count_distribution && (
          <div>
            <div className="text-[10px] text-f1-dim uppercase tracking-wider mb-1.5">
              Stop Count Distribution
            </div>
            <div className="flex h-5 rounded overflow-hidden text-[10px] font-mono font-semibold">
              {stop_count_distribution.one_stop_pct > 0 && (
                <div
                  className="flex items-center justify-center bg-emerald-500/30 text-emerald-400 border-r border-f1-bg/50"
                  style={{ width: `${stop_count_distribution.one_stop_pct}%` }}
                >
                  {stop_count_distribution.one_stop_pct >= 10 &&
                    `1-stop ${Math.round(stop_count_distribution.one_stop_pct)}%`}
                </div>
              )}
              {stop_count_distribution.two_stop_pct > 0 && (
                <div
                  className="flex items-center justify-center bg-blue-500/30 text-blue-400 border-r border-f1-bg/50"
                  style={{ width: `${stop_count_distribution.two_stop_pct}%` }}
                >
                  {stop_count_distribution.two_stop_pct >= 10 &&
                    `2-stop ${Math.round(stop_count_distribution.two_stop_pct)}%`}
                </div>
              )}
              {stop_count_distribution.three_plus_pct > 0 && (
                <div
                  className="flex items-center justify-center bg-purple-500/30 text-purple-400"
                  style={{ width: `${stop_count_distribution.three_plus_pct}%` }}
                >
                  {stop_count_distribution.three_plus_pct >= 10 &&
                    `3+ ${Math.round(stop_count_distribution.three_plus_pct)}%`}
                </div>
              )}
            </div>
            <div className="text-[10px] text-f1-dim mt-1 font-mono">
              n={stop_count_distribution.n} drivers
            </div>
          </div>
        )}

        {/* Common Sequences */}
        {common_strategy_sequences.length > 0 && (
          <div>
            <div className="text-[10px] text-f1-dim uppercase tracking-wider mb-1.5">
              Common Sequences
            </div>
            <div className="flex flex-wrap gap-2">
              {common_strategy_sequences.slice(0, 3).map((seq, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-f1-surface border border-f1-border text-xs font-mono"
                >
                  {seq.sequence.join(" \u2192 ")}
                  <span className="text-f1-dim ml-1">
                    {Math.round(seq.frequency_pct)}%
                  </span>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Undercut note */}
        {undercut_overcut && undercut_overcut.undercut_attempts > 0 && (
          <div className="flex items-center gap-2 text-xs">
            <TrendingUp size={12} className="text-f1-dim" />
            <span className="font-mono text-f1-dim">
              Undercut success: {Math.round(undercut_overcut.undercut_success_rate * 100)}%
              from {undercut_overcut.undercut_attempts} attempt{undercut_overcut.undercut_attempts !== 1 ? "s" : ""}
              {undercut_overcut.typical_undercut_gain_s > 0 &&
                ` (avg gain ${undercut_overcut.typical_undercut_gain_s.toFixed(1)}s)`}
            </span>
          </div>
        )}

        {/* Notes */}
        {notes.length > 0 && (
          <div className="text-[10px] text-f1-dim italic space-y-0.5">
            {notes.map((note, i) => (
              <p key={i}>{note}</p>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

export const HistoricalContext = memo(HistoricalContextInner);
