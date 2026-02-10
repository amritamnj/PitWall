import { memo } from "react";
import { motion } from "framer-motion";
import {
  Thermometer,
  Wind,
  CloudRain,
  Radio,
  SlidersHorizontal,
} from "lucide-react";
import clsx from "clsx";
import { useStrategyStore } from "../store/useStrategyStore";

function WeatherSummaryInner() {
  const { unifiedWeather, weatherApi, setWeatherSource } = useStrategyStore();
  const { source, airTemp, trackTemp, rainProbability, windSpeed, mode } =
    unifiedWeather;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-4"
    >
      {/* Header with source toggle */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-f1-dim">
          Weather Forecast
        </h3>
        <div className="flex items-center gap-0.5 bg-f1-surface rounded-md p-0.5">
          <button
            onClick={() => setWeatherSource("live")}
            className={clsx(
              "flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium transition-colors",
              source === "live"
                ? "bg-f1-card text-green-400"
                : "text-f1-dim hover:text-f1-text",
            )}
          >
            <Radio size={10} />
            Live
          </button>
          <button
            onClick={() => setWeatherSource("manual")}
            className={clsx(
              "flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium transition-colors",
              source === "manual"
                ? "bg-f1-card text-orange-400"
                : "text-f1-dim hover:text-f1-text",
            )}
          >
            <SlidersHorizontal size={10} />
            Manual
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Metric
          icon={<Thermometer size={14} className="text-orange-400" />}
          label="Air"
          value={`${Math.round(airTemp)}°C`}
        />
        <Metric
          icon={<Thermometer size={14} className="text-red-400" />}
          label="Track"
          value={`${trackTemp}°C`}
        />
        <Metric
          icon={<CloudRain size={14} className="text-blue-400" />}
          label="Rain"
          value={`${Math.round(rainProbability * 100)}%`}
        />
        <Metric
          icon={<Wind size={14} className="text-teal-400" />}
          label="Wind"
          value={`${windSpeed.toFixed(1)} m/s`}
        />
      </div>

      {source === "live" && weatherApi?.forecast_hours === 0 && (
        <p className="text-[10px] text-f1-dim mt-2 italic">{weatherApi.note}</p>
      )}
      {source === "manual" && (
        <p className="text-[10px] text-f1-dim mt-2 italic">
          Manual override — derived mode: {mode}
        </p>
      )}
    </motion.div>
  );
}

function Metric({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-2">
      {icon}
      <div>
        <div className="text-[10px] text-f1-dim uppercase">{label}</div>
        <div className="text-sm font-mono font-semibold">{value}</div>
      </div>
    </div>
  );
}

export const WeatherSummary = memo(WeatherSummaryInner);
