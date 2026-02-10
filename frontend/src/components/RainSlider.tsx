import { memo, useCallback } from "react";
import { Droplets } from "lucide-react";

interface Props {
  value: number;
  onChange: (v: number) => void;
  onCommit?: (v: number) => void;
  disabled?: boolean;
}

function RainSliderInner({ value, onChange, onCommit, disabled }: Props) {
  const pct = value * 100;
  const label =
    value === 0
      ? "Bone Dry"
      : value < 0.3
        ? "Light"
        : value < 0.6
          ? "Moderate"
          : value < 0.8
            ? "Heavy"
            : "Monsoon";

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      onChange(Number(e.target.value));
    },
    [onChange]
  );

  const handleCommit = useCallback(() => {
    onCommit?.(value);
  }, [onCommit, value]);

  return (
    <div className={`space-y-2${disabled ? " opacity-50 pointer-events-none" : ""}`}>
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-1.5 text-f1-dim">
          <Droplets size={14} />
          Rain Intensity
        </span>
        <span className="font-mono font-semibold text-blue-400">
          {Math.round(pct)}% — {label}
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={value}
        onChange={handleChange}
        onMouseUp={handleCommit}
        onTouchEnd={handleCommit}
        className="slider-track w-full"
      />
    </div>
  );
}

export const RainSlider = memo(RainSliderInner);
