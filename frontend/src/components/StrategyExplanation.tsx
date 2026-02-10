import { memo, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, Info } from "lucide-react";
import clsx from "clsx";
import type { RuleHit } from "../types";
import { generateRuleExplanation } from "../lib/rules";
import { useStrategyStore } from "../store/useStrategyStore";

interface Props {
  ruleHits: RuleHit[];
}

function StrategyExplanationInner({ ruleHits }: Props) {
  const [expanded, setExpanded] = useState(false);
  const simSnapshot = useStrategyStore((s) => s.simWeatherSnapshot);
  const explanation = useMemo(
    () => generateRuleExplanation(ruleHits),
    [ruleHits],
  );

  // Build conditions label from snapshot
  const conditionsLabel = useMemo(() => {
    if (!simSnapshot) return null;
    const mode =
      simSnapshot.mode.charAt(0).toUpperCase() + simSnapshot.mode.slice(1);
    return `${mode} · Track temp ${simSnapshot.trackTemp}°C (${simSnapshot.source})`;
  }, [simSnapshot]);

  // Build live delta line (Fix 3)
  const liveDelta = useMemo(() => {
    if (!simSnapshot || simSnapshot.source === "live") return null;
    if (simSnapshot.liveTrackTemp == null || simSnapshot.liveMode == null)
      return null;

    const tempDiff = simSnapshot.trackTemp - simSnapshot.liveTrackTemp;
    const modeDiff = simSnapshot.mode !== simSnapshot.liveMode;
    if (tempDiff === 0 && !modeDiff) return null;

    const parts: string[] = [];
    if (simSnapshot.liveTrackTemp != null) {
      parts.push(`Live track temp: ${simSnapshot.liveTrackTemp}°C`);
    }
    parts.push(`Simulated: ${simSnapshot.trackTemp}°C`);
    if (modeDiff) {
      const liveLabel =
        simSnapshot.liveMode!.charAt(0).toUpperCase() +
        simSnapshot.liveMode!.slice(1);
      parts.push(`Live mode: ${liveLabel}`);
    }
    return parts.join(" · ");
  }, [simSnapshot]);

  return (
    <div className="space-y-3">
      {/* Simulation conditions banner (Fix 1) */}
      {conditionsLabel && (
        <div className="flex items-center gap-1.5 text-[10px] text-f1-dim font-mono">
          <Info size={10} className="shrink-0" />
          <span>Simulated conditions: {conditionsLabel}</span>
        </div>
      )}

      {/* Live vs simulated delta (Fix 3) */}
      {liveDelta && (
        <div className="text-[10px] text-amber-400/80 font-mono pl-4">
          {liveDelta}
        </div>
      )}

      {/* Rule-based bullets (always visible) */}
      <div className="space-y-1">
        {ruleHits.map((hit, i) => (
          <div key={i} className="flex gap-2 text-[11px]">
            <span className="text-f1-dim font-mono shrink-0 w-16 text-right">
              {hit.category}
            </span>
            <span className="text-f1-dim">
              {hit.rule_name}: {hit.observed_value}
            </span>
            <span className="text-f1-text ml-auto text-right">
              {hit.impact}
            </span>
          </div>
        ))}
      </div>

      {/* Explanation toggle */}
      <div className="flex items-center gap-2 pt-1 border-t border-f1-border/20">
        <button
          onClick={() => setExpanded((v) => !v)}
          className={clsx(
            "flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-medium transition-colors",
            expanded
              ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
              : "bg-f1-surface text-f1-dim border border-f1-border hover:text-f1-text",
          )}
        >
          <FileText size={10} />
          {expanded ? "Strategy Explanation ON" : "Strategy Explanation"}
        </button>
        {expanded && (
          <span className="text-[9px] text-f1-dim italic">
            Deterministic — generated from rule outputs only
          </span>
        )}
      </div>

      {/* Explanation panel */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="text-xs text-f1-text/90 leading-relaxed py-2 px-3 rounded-md bg-emerald-500/5 border border-emerald-500/15 whitespace-pre-line">
              {explanation}
              <p className="text-[9px] text-f1-dim mt-2 pt-1.5 border-t border-emerald-500/10 italic">
                This explanation is generated directly from the strategy rules
                above.
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export const StrategyExplanation = memo(StrategyExplanationInner);
