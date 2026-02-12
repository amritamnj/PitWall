import { memo, useMemo } from "react";
import { motion } from "framer-motion";
import { Calendar, MapPin, Zap, Clock } from "lucide-react";
import clsx from "clsx";
import { useGridStore } from "../../store/useGridStore";
import { FLAG_EMOJI } from "../../lib/constants";
import { SkeletonCard } from "../LoadingSkeleton";
import type { RaceEvent } from "../../types";

/* ------------------------------------------------------------------ */
/* Next-race hero                                                     */
/* ------------------------------------------------------------------ */

function NextRaceHero({
  event,
  daysUntil,
}: {
  event: RaceEvent;
  daysUntil: number;
}) {
  const flag = FLAG_EMOJI[event.country] ?? "";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card glow-border p-6"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-f1-dim font-semibold mb-1">
            Next Up
          </p>
          <h2 className="text-xl font-bold">{event.name}</h2>
          <div className="flex items-center gap-2 mt-1 text-sm text-f1-dim">
            <MapPin size={12} />
            <span>
              {event.circuit_full_name} — {flag} {event.country}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1 text-sm text-f1-dim">
            <Calendar size={12} />
            <span>{event.date}</span>
          </div>
          {event.sprint && (
            <span className="inline-flex items-center gap-1 mt-2 px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-compound-c3/20 text-compound-c3">
              <Zap size={10} /> Sprint
            </span>
          )}
        </div>
        <div className="text-right">
          <div className="text-4xl font-black text-compound-c3">
            {daysUntil}
          </div>
          <p className="text-[10px] uppercase tracking-wider text-f1-dim">
            days away
          </p>
        </div>
      </div>

      {event.laps && (
        <div className="flex gap-4 mt-4 pt-3 border-t border-f1-border/30 text-xs text-f1-dim font-mono">
          <span>{event.laps} laps</span>
          {event.length_km && <span>{event.length_km} km</span>}
          {event.pit_loss && <span>Pit loss ~{event.pit_loss}s</span>}
        </div>
      )}
    </motion.div>
  );
}

/* ------------------------------------------------------------------ */
/* Season list                                                        */
/* ------------------------------------------------------------------ */

function CalendarViewInner() {
  const { calendar, loadingCalendar } = useGridStore();

  const today = useMemo(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }, []);

  if (loadingCalendar || !calendar) {
    return (
      <div className="space-y-4">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-5xl">
      {/* Hero */}
      {calendar.next_event && (
        <NextRaceHero
          event={calendar.next_event}
          daysUntil={calendar.days_until_next}
        />
      )}

      {/* Season grid */}
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-f1-dim mb-3">
          {calendar.season_status === "pre_season"
            ? "Upcoming Season"
            : "Full Season Calendar"}
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {calendar.events.map((ev, i) => {
            const isPast = ev.date < today;
            const isNext = calendar.next_event?.date === ev.date && calendar.next_event?.name === ev.name;
            const flag = FLAG_EMOJI[ev.country] ?? "";

            return (
              <motion.div
                key={`${ev.round}-${ev.date}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                className={clsx(
                  "glass-card p-3 transition-all",
                  isPast && "opacity-50",
                  isNext && "ring-1 ring-compound-c3/50",
                )}
              >
                <div className="flex items-start gap-3">
                  {/* Round badge */}
                  <div
                    className={clsx(
                      "shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold",
                      ev.is_testing
                        ? "bg-blue-500/20 text-blue-400"
                        : "bg-f1-surface text-f1-dim",
                    )}
                  >
                    {typeof ev.round === "string" && ev.round.startsWith("TEST")
                      ? "T"
                      : `R${ev.round}`}
                  </div>

                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold truncate">{ev.name}</p>
                    <p className="text-[11px] text-f1-dim truncate">
                      {flag} {ev.country} — {ev.circuit_full_name}
                    </p>
                    <div className="flex items-center gap-2 mt-1 text-[10px] text-f1-dim font-mono">
                      <Clock size={9} />
                      <span>{ev.date}</span>
                      {ev.sprint && (
                        <span className="px-1.5 py-0.5 rounded bg-compound-c3/20 text-compound-c3 font-bold uppercase">
                          Sprint
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export const CalendarView = memo(CalendarViewInner);
