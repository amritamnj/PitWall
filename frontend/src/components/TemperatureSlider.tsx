import { memo, useCallback, useRef } from "react";
import { Thermometer } from "lucide-react";

interface Props {
  value: number;
  onChange: (v: number) => void;
  /** Fires once on mouse-up / touch-end — use for debounced fetch */
  onCommit?: (v: number) => void;
  min?: number;
  max?: number;
  disabled?: boolean;
}

function SliderInner({ value, onChange, onCommit, min = 15, max = 55, disabled }: Props) {
  const commitRef = useRef(onCommit);
  commitRef.current = onCommit;

  const pct = ((value - min) / (max - min)) * 100;

  // Color gradient: blue (cold) → green → yellow → red (hot)
  const hue = 240 - (pct / 100) * 240; // 240=blue → 0=red
  const trackColor = `hsl(${hue}, 75%, 55%)`;

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange(Number(e.target.value));
    },
    [onChange]
  );

  const handleCommit = useCallback(() => {
    commitRef.current?.(value);
  }, [value]);

  return (
    <div className={`space-y-2${disabled ? " opacity-50 pointer-events-none" : ""}`}>
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-1.5 text-f1-dim">
          <Thermometer size={14} />
          Track Temperature
        </span>
        <span className="font-mono font-semibold" style={{ color: trackColor }}>
          {value}°C
        </span>
      </div>
      <div className="relative">
        <div
          className="absolute top-1/2 left-0 h-1.5 rounded-full -translate-y-1/2 pointer-events-none transition-all duration-100"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, #3b82f6, #22c55e, #eab308, #ef4444)`,
            backgroundSize: `${(100 / pct) * 100}% 100%`,
          }}
        />
        <input
          type="range"
          min={min}
          max={max}
          step={1}
          value={value}
          onChange={handleChange}
          onMouseUp={handleCommit}
          onTouchEnd={handleCommit}
          className="slider-track w-full relative z-10"
          style={
            {
              "--thumb-color": trackColor,
            } as React.CSSProperties
          }
        />
      </div>
      <div className="flex justify-between text-[10px] text-f1-dim/50 font-mono">
        <span>{min}°</span>
        <span>{max}°</span>
      </div>
    </div>
  );
}

export const TemperatureSlider = memo(SliderInner);
