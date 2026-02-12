import { memo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Users } from "lucide-react";
import clsx from "clsx";
import { useGridStore } from "../../store/useGridStore";
import { COUNTRY_CODE_FLAGS } from "../../lib/constants";
import { SkeletonCard } from "../LoadingSkeleton";

/* ------------------------------------------------------------------ */
/* Teams view                                                         */
/* ------------------------------------------------------------------ */

function TeamsViewInner() {
  const { teams, loadingTeams, expandedTeam, toggleTeamExpand } =
    useGridStore();

  if (loadingTeams || !teams) {
    return (
      <div className="space-y-3">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  return (
    <div className="space-y-3 max-w-4xl">
      {teams.teams.map((team) => {
        const colour = `#${team.team_colour}`;
        const isExpanded = expandedTeam === team.team_name;
        const initial = team.team_name.charAt(0).toUpperCase();

        return (
          <div key={team.team_name} className="glass-card overflow-hidden">
            {/* Header */}
            <button
              onClick={() => toggleTeamExpand(team.team_name)}
              className="w-full flex items-center gap-3 px-4 py-3 hover:bg-f1-surface/50 transition-colors"
            >
              {/* Team badge */}
              <div
                className="shrink-0 w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold"
                style={{
                  backgroundColor: `${colour}25`,
                  color: colour,
                }}
              >
                {initial}
              </div>

              <div className="flex-1 text-left min-w-0">
                <p className="text-sm font-semibold truncate">
                  {team.team_name}
                </p>
                <p className="text-[10px] text-f1-dim">
                  {team.drivers.length} drivers
                </p>
              </div>

              {/* Colour bar */}
              <div
                className="w-16 h-1.5 rounded-full"
                style={{ backgroundColor: colour }}
              />

              <ChevronDown
                size={16}
                className={clsx(
                  "text-f1-dim transition-transform duration-200 shrink-0",
                  isExpanded && "rotate-180",
                )}
              />
            </button>

            {/* Expanded drivers */}
            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden border-t border-f1-border/30"
                >
                  <div className="px-4 py-3 space-y-2 bg-f1-surface/20">
                    {team.drivers.map((d) => {
                      const flag = d.country_code
                        ? COUNTRY_CODE_FLAGS[d.country_code] ?? ""
                        : "";

                      return (
                        <div
                          key={d.driver_number}
                          className="flex items-center gap-3 py-1"
                        >
                          {/* Number badge */}
                          <div
                            className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold font-mono"
                            style={{
                              backgroundColor: `${colour}20`,
                              color: colour,
                            }}
                          >
                            {d.driver_number}
                          </div>

                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">
                              {d.full_name}
                            </p>
                          </div>

                          <span className="text-xs font-mono text-f1-dim">
                            {d.name_acronym}
                          </span>
                          {flag && (
                            <span className="text-sm">{flag}</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      })}

      <p className="text-[10px] text-f1-dim text-center font-mono">
        {teams.note}
      </p>
    </div>
  );
}

export const TeamsView = memo(TeamsViewInner);
