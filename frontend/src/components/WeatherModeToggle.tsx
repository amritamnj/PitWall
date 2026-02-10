import { memo } from "react";
import { motion } from "framer-motion";
import { Sun, CloudDrizzle, CloudRain, CloudLightning } from "lucide-react";
import clsx from "clsx";
import type { WeatherCondition } from "../types";

const modes: {
  id: WeatherCondition;
  label: string;
  icon: typeof Sun;
  color: string;
}[] = [
  { id: "dry", label: "Dry", icon: Sun, color: "#eab308" },
  { id: "damp", label: "Damp", icon: CloudDrizzle, color: "#22c55e" },
  { id: "wet", label: "Wet", icon: CloudRain, color: "#3b82f6" },
  { id: "extreme", label: "Extreme", icon: CloudLightning, color: "#a855f7" },
];

interface Props {
  value: WeatherCondition;
  onChange: (v: WeatherCondition) => void;
}

function ToggleInner({ value, onChange }: Props) {
  return (
    <div className="space-y-2">
      <span className="text-sm text-f1-dim">Weather Condition</span>
      <div className="grid grid-cols-4 gap-1.5 p-1 bg-f1-surface rounded-lg">
        {modes.map((m) => {
          const active = value === m.id;
          const Icon = m.icon;
          return (
            <button
              key={m.id}
              onClick={() => onChange(m.id)}
              className={clsx(
                "relative flex flex-col items-center gap-1 py-2 px-1 rounded-md text-xs font-medium transition-colors duration-200",
                active ? "text-white" : "text-f1-dim hover:text-f1-text"
              )}
            >
              {active && (
                <motion.div
                  layoutId="weather-active"
                  className="absolute inset-0 rounded-md"
                  style={{ backgroundColor: `${m.color}25` }}
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
              <Icon
                size={16}
                className="relative z-10"
                style={{ color: active ? m.color : undefined }}
              />
              <span className="relative z-10">{m.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

export const WeatherModeToggle = memo(ToggleInner);
