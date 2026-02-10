import { memo, useMemo } from "react";
import { motion } from "framer-motion";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { DegradationResponse, TyreNominationResponse } from "../types";
import { COMPOUND_COLORS, computeDegCurve } from "../lib/constants";

interface Props {
  degradation: DegradationResponse;
  tyres: TyreNominationResponse | null;
  totalLaps: number;
}

function DegChartInner({ degradation, tyres, totalLaps }: Props) {
  // Determine which compounds to chart (nominated + any extras from deg data)
  const compoundCodes = useMemo(() => {
    const nominated = tyres ? tyres.slicks.map((s) => s.code) : [];
    const all = Object.keys(degradation.compounds).filter((c) =>
      c.startsWith("C")
    );
    // Show nominated first, then any extras
    const seen = new Set(nominated);
    return [...nominated, ...all.filter((c) => !seen.has(c))];
  }, [degradation, tyres]);

  // Build chart data: { lap, C2, C3, C4, ... } per lap
  const { chartData, cliffLines } = useMemo(() => {
    const maxLap = Math.min(totalLaps, 60);
    const curves: Record<string, { lap: number; delta: number }[]> = {};
    const cliffs: { code: string; onset: number }[] = [];

    for (const code of compoundCodes) {
      const d = degradation.compounds[code];
      if (!d) continue;
      curves[code] = computeDegCurve(
        d.avg_deg_s_per_lap,
        d.cliff_onset_lap,
        d.cliff_rate_s_per_lap2,
        maxLap
      );
      cliffs.push({ code, onset: d.cliff_onset_lap });
    }

    // Merge into single data array for Recharts
    const data: Record<string, number>[] = [];
    for (let lap = 0; lap <= maxLap; lap++) {
      const row: Record<string, number> = { lap };
      for (const code of compoundCodes) {
        const pt = curves[code]?.[lap];
        if (pt) row[code] = pt.delta;
      }
      data.push(row);
    }

    return { chartData: data, cliffLines: cliffs };
  }, [degradation, compoundCodes, totalLaps]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="glass-card p-5"
    >
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold">Tyre Degradation Curves</h3>
          <p className="text-xs text-f1-dim mt-0.5">
            Lap time delta vs fresh tyre (seconds)
          </p>
        </div>
        <span className="text-[10px] font-mono text-f1-dim px-2 py-1 bg-f1-surface rounded">
          {degradation.data_source === "historical"
            ? `Historical ${degradation.years_used.join(", ")}`
            : "Fallback estimates"}
        </span>
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <LineChart
          data={chartData}
          margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#262a36"
            vertical={false}
          />
          <XAxis
            dataKey="lap"
            stroke="#4a5068"
            fontSize={11}
            tickLine={false}
            label={{
              value: "Lap",
              position: "insideBottomRight",
              offset: -5,
              fontSize: 10,
              fill: "#6b7280",
            }}
          />
          <YAxis
            stroke="#4a5068"
            fontSize={11}
            tickLine={false}
            tickFormatter={(v: number) => `+${v.toFixed(1)}s`}
            label={{
              value: "Delta (s)",
              angle: -90,
              position: "insideLeft",
              offset: 10,
              fontSize: 10,
              fill: "#6b7280",
            }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#181b25",
              border: "1px solid #262a36",
              borderRadius: "8px",
              fontSize: "12px",
            }}
            itemStyle={{ padding: "2px 0" }}
            labelStyle={{ fontWeight: 600, marginBottom: 4 }}
            labelFormatter={(l) => `Lap ${l}`}
            formatter={(val: number, name: string) => [
              `+${val.toFixed(3)}s`,
              name,
            ]}
          />
          <Legend
            verticalAlign="top"
            align="right"
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: "11px", paddingBottom: "8px" }}
          />

          {/* Cliff onset reference lines */}
          {cliffLines.map((cl) => (
            <ReferenceLine
              key={`cliff-${cl.code}`}
              x={cl.onset}
              stroke={COMPOUND_COLORS[cl.code] ?? "#666"}
              strokeDasharray="4 4"
              strokeOpacity={0.4}
              label={{
                value: `${cl.code} cliff`,
                position: "top",
                fontSize: 9,
                fill: COMPOUND_COLORS[cl.code] ?? "#666",
              }}
            />
          ))}

          {/* Compound lines */}
          {compoundCodes.map((code) => (
            <Line
              key={code}
              type="monotone"
              dataKey={code}
              stroke={COMPOUND_COLORS[code] ?? "#888"}
              strokeWidth={2}
              dot={false}
              activeDot={{
                r: 4,
                stroke: COMPOUND_COLORS[code],
                strokeWidth: 2,
                fill: "#181b25",
              }}
              animationDuration={800}
              animationEasing="ease-out"
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </motion.div>
  );
}

export const DegradationChart = memo(DegChartInner);
