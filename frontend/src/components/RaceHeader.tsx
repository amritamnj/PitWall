import { memo } from "react";
import { motion } from "framer-motion";
import { Calendar, MapPin, Flag, Timer, Zap } from "lucide-react";
import type { RaceEvent } from "../types";
import { FLAG_EMOJI } from "../lib/constants";

interface Props {
  race: RaceEvent;
  daysUntil: number;
  seasonStatus: string;
}

function RaceHeaderInner({ race, daysUntil, seasonStatus }: Props) {
  const flag = FLAG_EMOJI[race.country] ?? "";
  const dateObj = new Date(race.date + "T00:00:00");
  const dateStr = dateObj.toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-3"
    >
      {/* Status badge */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] uppercase tracking-widest text-f1-dim font-semibold">
          {seasonStatus === "pre_season"
            ? "Pre-Season"
            : seasonStatus === "in_season"
              ? "Season Active"
              : "Post-Season"}
        </span>
        {race.sprint && (
          <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded-full">
            <Zap size={10} /> Sprint
          </span>
        )}
      </div>

      {/* Race name */}
      <div>
        <h1 className="text-lg font-bold leading-tight">{race.name}</h1>
        <p className="text-sm text-f1-dim flex items-center gap-1.5 mt-0.5">
          <MapPin size={12} />
          {race.circuit_full_name}
        </p>
      </div>

      {/* Countdown + meta */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-f1-surface rounded-lg px-3 py-2">
          <div className="text-[10px] text-f1-dim uppercase tracking-wider mb-0.5">
            Race Day
          </div>
          <div className="flex items-center gap-1.5">
            <Calendar size={13} className="text-compound-c3" />
            <span className="text-sm font-medium">{dateStr}</span>
          </div>
        </div>
        <div className="bg-f1-surface rounded-lg px-3 py-2">
          <div className="text-[10px] text-f1-dim uppercase tracking-wider mb-0.5">
            Countdown
          </div>
          <div className="flex items-center gap-1.5">
            <Timer size={13} className="text-compound-c4" />
            <span className="text-sm font-semibold">
              {daysUntil === 0 ? (
                <span className="text-green-400">Race Day!</span>
              ) : (
                <>
                  {daysUntil} day{daysUntil !== 1 ? "s" : ""}
                </>
              )}
            </span>
          </div>
        </div>
      </div>

      {/* Country + circuit stats */}
      <div className="flex items-center gap-3 text-xs text-f1-dim">
        <span className="flex items-center gap-1">
          <Flag size={11} /> {flag} {race.country}
        </span>
        {race.laps && <span>{race.laps} laps</span>}
        {race.length_km && <span>{race.length_km} km</span>}
        {race.pit_loss && (
          <span className="text-amber-400/70">~{race.pit_loss}s pit loss</span>
        )}
      </div>
    </motion.div>
  );
}

export const RaceHeader = memo(RaceHeaderInner);
