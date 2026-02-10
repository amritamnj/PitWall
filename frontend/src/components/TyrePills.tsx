import { memo } from "react";
import { motion } from "framer-motion";
import type { CompoundInfo } from "../types";
import { COMPOUND_COLORS } from "../lib/constants";

interface Props {
  compounds: CompoundInfo[];
}

function TyrePillsInner({ compounds }: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {compounds.map((c, i) => {
        const color = COMPOUND_COLORS[c.code] ?? "#888";
        const isLight = ["C1", "C2"].includes(c.code);
        return (
          <motion.span
            key={c.code}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.05, type: "spring", stiffness: 300 }}
            className="compound-pill"
            style={{
              borderColor: color,
              backgroundColor: `${color}18`,
              color: isLight ? "#e2e8f0" : color,
            }}
          >
            <span
              className="w-2.5 h-2.5 rounded-full inline-block"
              style={{ backgroundColor: color }}
            />
            {c.role ? (
              <span>
                <span className="opacity-70 uppercase text-[10px]">
                  {c.role}
                </span>{" "}
                {c.code}
              </span>
            ) : (
              <span>{c.label}</span>
            )}
          </motion.span>
        );
      })}
    </div>
  );
}

export const TyrePills = memo(TyrePillsInner);
