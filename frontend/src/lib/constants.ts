/** Compound accent colours — used for charts, pills, timeline bars. */
export const COMPOUND_COLORS: Record<string, string> = {
  C1: "#d4d4d8",
  C2: "#a1a1aa",
  C3: "#eab308",
  C4: "#ef4444",
  C5: "#dc2626",
  INTERMEDIATE: "#22c55e",
  WET: "#3b82f6",
};

/** Lighter background tints for cards and chart areas. */
export const COMPOUND_BG: Record<string, string> = {
  C1: "rgba(212,212,216,0.10)",
  C2: "rgba(161,161,170,0.10)",
  C3: "rgba(234,179,8,0.10)",
  C4: "rgba(239,68,68,0.10)",
  C5: "rgba(220,38,38,0.10)",
  INTERMEDIATE: "rgba(34,197,94,0.10)",
  WET: "rgba(59,130,246,0.10)",
};

/** Short display labels for compound pills. */
export const COMPOUND_LABELS: Record<string, string> = {
  C1: "C1",
  C2: "C2",
  C3: "C3",
  C4: "C4",
  C5: "C5",
  INTERMEDIATE: "INTER",
  WET: "WET",
};

/** Country name → flag emoji */
export const FLAG_EMOJI: Record<string, string> = {
  Bahrain: "\u{1F1E7}\u{1F1ED}",
  "Saudi Arabia": "\u{1F1F8}\u{1F1E6}",
  Australia: "\u{1F1E6}\u{1F1FA}",
  Japan: "\u{1F1EF}\u{1F1F5}",
  China: "\u{1F1E8}\u{1F1F3}",
  "United States": "\u{1F1FA}\u{1F1F8}",
  Italy: "\u{1F1EE}\u{1F1F9}",
  Monaco: "\u{1F1F2}\u{1F1E8}",
  Canada: "\u{1F1E8}\u{1F1E6}",
  Spain: "\u{1F1EA}\u{1F1F8}",
  Austria: "\u{1F1E6}\u{1F1F9}",
  "United Kingdom": "\u{1F1EC}\u{1F1E7}",
  Hungary: "\u{1F1ED}\u{1F1FA}",
  Belgium: "\u{1F1E7}\u{1F1EA}",
  Netherlands: "\u{1F1F3}\u{1F1F1}",
  Azerbaijan: "\u{1F1E6}\u{1F1FF}",
  Singapore: "\u{1F1F8}\u{1F1EC}",
  Mexico: "\u{1F1F2}\u{1F1FD}",
  Brazil: "\u{1F1E7}\u{1F1F7}",
  Qatar: "\u{1F1F6}\u{1F1E6}",
  "United Arab Emirates": "\u{1F1E6}\u{1F1EA}",
};

/**
 * Generate a theoretical degradation curve from compound parameters.
 * Returns one { lap, delta } point per lap (0-indexed).
 */
export function computeDegCurve(
  degRate: number,
  cliffOnset: number,
  cliffRate: number,
  maxLaps: number
): { lap: number; delta: number }[] {
  const pts: { lap: number; delta: number }[] = [];
  for (let n = 0; n <= maxLaps; n++) {
    let d = n * degRate;
    if (n > cliffOnset) {
      d += cliffRate * (n - cliffOnset) ** 2;
    }
    pts.push({ lap: n, delta: Math.round(d * 1000) / 1000 });
  }
  return pts;
}
