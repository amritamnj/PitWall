import { memo } from "react";
import { motion } from "framer-motion";
import {
  Thermometer,
  Wind,
  Droplets,
  CloudRain,
} from "lucide-react";
import type { WeatherResponse } from "../types";

interface Props {
  weather: WeatherResponse;
}

function WeatherSummaryInner({ weather }: Props) {
  const airTemp = weather.current_air_temp_c;
  const trackTemp = weather.current_track_temp_c;

  // Upcoming rain probability (max over next 6 hours)
  const maxRain =
    weather.hourly.length > 0
      ? Math.max(...weather.hourly.slice(0, 6).map((h) => h.rain_probability))
      : 0;

  const avgWind =
    weather.hourly.length > 0
      ? weather.hourly.slice(0, 6).reduce((s, h) => s + h.wind_speed_ms, 0) /
        Math.min(6, weather.hourly.length)
      : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card p-4"
    >
      <h3 className="text-xs font-semibold uppercase tracking-wider text-f1-dim mb-3">
        Weather Forecast
      </h3>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Metric
          icon={<Thermometer size={14} className="text-orange-400" />}
          label="Air"
          value={airTemp != null ? `${airTemp}°C` : "—"}
        />
        <Metric
          icon={<Thermometer size={14} className="text-red-400" />}
          label="Track"
          value={trackTemp != null ? `${trackTemp}°C` : "—"}
        />
        <Metric
          icon={<CloudRain size={14} className="text-blue-400" />}
          label="Rain"
          value={`${Math.round(maxRain * 100)}%`}
        />
        <Metric
          icon={<Wind size={14} className="text-teal-400" />}
          label="Wind"
          value={`${avgWind.toFixed(1)} m/s`}
        />
      </div>

      {weather.forecast_hours === 0 && (
        <p className="text-[10px] text-f1-dim mt-2 italic">{weather.note}</p>
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
