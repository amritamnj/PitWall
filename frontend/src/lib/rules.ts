/**
 * Rule extraction — converts pre-computed simulation outputs into
 * structured RuleHit[] for display and explanation.
 *
 * IMPORTANT: This extracts facts that already exist in the simulation
 * response. It must NOT invent new analysis or predictions.
 */

import type { StrategyResult, SimulateResponse, RuleHit } from "../types";

export function extractRuleHits(
  strategy: StrategyResult,
  simulation: SimulateResponse,
): RuleHit[] {
  const hits: RuleHit[] = [];
  const bestTime = simulation.strategies[0]?.total_time_s ?? 0;
  const delta = strategy.total_time_s - bestTime;
  const isRecommended = strategy.name === simulation.recommended;

  // --- Weather ---
  hits.push({
    category: "Weather",
    rule_name: "Condition",
    observed_value: simulation.weather_condition,
    impact:
      simulation.weather_condition === "dry"
        ? "Slick tyres only"
        : `Wet tyres required — rain intensity ${Math.round(simulation.rain_intensity * 100)}%`,
  });

  if (simulation.track_temp_c != null) {
    hits.push({
      category: "Weather",
      rule_name: "Track temperature",
      observed_value: `${simulation.track_temp_c}°C`,
      impact:
        simulation.track_temp_c > 45
          ? "High track temp increases degradation"
          : simulation.track_temp_c < 25
            ? "Low track temp reduces tyre warm-up"
            : "Moderate track temperature",
    });
  }

  // --- Strategy shape ---
  hits.push({
    category: "Strategy",
    rule_name: "Pit stops",
    observed_value: `${strategy.stops}`,
    impact:
      strategy.stops === 0
        ? "No pit stop — full race on one set"
        : `${strategy.stops} stop(s) at lap${strategy.stops > 1 ? "s" : ""} ${strategy.pit_stop_laps.join(", ")}`,
  });

  hits.push({
    category: "Strategy",
    rule_name: "Total race time",
    observed_value: strategy.total_time_display,
    impact: isRecommended
      ? `Fastest strategy — wins by ${simulation.delta_s.toFixed(1)}s`
      : `+${delta.toFixed(1)}s off the optimal`,
  });

  // --- Stint details ---
  for (const stint of strategy.stints) {
    const stintHit: RuleHit = {
      category: "Stint",
      rule_name: `S${stint.stint_number}: ${stint.compound}`,
      observed_value: `${stint.laps} laps (L${stint.start_lap}–L${stint.end_lap})`,
      impact: `Avg ${stint.avg_lap_time_s.toFixed(2)}s/lap`,
    };

    if (stint.cliff_laps > 0) {
      stintHit.impact += ` — ${stint.cliff_laps} cliff laps (tyre drop-off)`;
    }
    if (stint.is_wet_tyre) {
      stintHit.impact += " [wet tyre]";
    }

    hits.push(stintHit);
  }

  // --- Weather note (from simulation) ---
  if (strategy.weather_note) {
    hits.push({
      category: "Weather",
      rule_name: "Race note",
      observed_value: strategy.weather_note,
      impact: "Pre-computed by simulation engine",
    });
  }

  // --- Historical alignment notes ---
  if (strategy.historical_notes && strategy.historical_notes.length > 0) {
    for (const note of strategy.historical_notes) {
      hits.push({
        category: "Historical",
        rule_name: "Pattern",
        observed_value: note,
        impact:
          strategy.historical_adjustment_s != null
            ? `${strategy.historical_adjustment_s > 0 ? "+" : ""}${strategy.historical_adjustment_s.toFixed(1)}s adjustment`
            : "Advisory",
      });
    }
  }

  return hits;
}

/* ------------------------------------------------------------------ */
/* Deterministic explanation — converts RuleHit[] into prose           */
/* ------------------------------------------------------------------ */

const STOP_WORDS = ["no", "one", "two", "three", "four", "five"];

/**
 * Generate a concise natural-language explanation from structured rule hits.
 * Uses ONLY the data present in the hits — no speculation, no external calls.
 */
export function generateRuleExplanation(ruleHits: RuleHit[]): string {
  // Index hits by category/rule_name for easy lookup
  const byKey = new Map<string, RuleHit>();
  const stints: RuleHit[] = [];

  for (const hit of ruleHits) {
    if (hit.category === "Stint") {
      stints.push(hit);
    } else {
      byKey.set(`${hit.category}/${hit.rule_name}`, hit);
    }
  }

  const condition = byKey.get("Weather/Condition");
  const trackTemp = byKey.get("Weather/Track temperature");
  const pitStops = byKey.get("Strategy/Pit stops");
  const totalTime = byKey.get("Strategy/Total race time");
  const raceNote = byKey.get("Weather/Race note");

  // --- Paragraph 1: Strategy shape + weather context ---
  const p1: string[] = [];

  const stops = parseInt(pitStops?.observed_value ?? "0", 10);
  const stopLabel = `${STOP_WORDS[stops] ?? stops}-stop`;

  let opener = `This ${stopLabel} strategy`;
  if (condition) {
    const tempClause = trackTemp
      ? ` with a track temperature of ${trackTemp.observed_value}`
      : "";
    opener += ` is evaluated under ${condition.observed_value} conditions${tempClause}.`;
  } else {
    opener += " covers the full race distance.";
  }
  p1.push(opener);

  if (trackTemp) {
    const tempC = parseFloat(trackTemp.observed_value);
    if (!isNaN(tempC)) {
      if (tempC > 45) {
        p1.push(
          "The elevated track temperature increases tyre degradation, " +
            "pushing compounds toward their performance limits more quickly.",
        );
      } else if (tempC > 35) {
        p1.push(
          "The warm track surface accelerates tyre wear, " +
            "which can shorten effective stint lengths on softer compounds.",
        );
      } else if (tempC < 25) {
        p1.push(
          "The cooler track temperature slows tyre warm-up, " +
            "which may reduce early-stint grip but extends compound life.",
        );
      }
    }
  }

  if (condition && condition.observed_value !== "dry") {
    p1.push(
      condition.impact.endsWith(".")
        ? condition.impact
        : condition.impact + ".",
    );
  }

  if (raceNote) {
    const note = raceNote.observed_value;
    p1.push(note.endsWith(".") ? note : note + ".");
  }

  // --- Paragraph 2: Stint breakdown + result ---
  const p2: string[] = [];

  if (stints.length > 0) {
    const compounds = stints.map(
      (s) => s.rule_name.split(": ")[1] ?? s.rule_name,
    );
    p2.push(
      `The tyre sequence is ${compounds.join(" \u2192 ")}, ` +
        `split across ${stints.length} stint${stints.length > 1 ? "s" : ""}.`,
    );

    const cliffStints = stints.filter((s) => s.impact.includes("cliff"));
    if (cliffStints.length === 1) {
      const compound =
        cliffStints[0].rule_name.split(": ")[1] ?? "the compound";
      p2.push(
        `Performance drop-off is observed on the ${compound} stint, ` +
          "indicating the tyres were pushed near their degradation limit.",
      );
    } else if (cliffStints.length > 1) {
      const unique = [
        ...new Set(
          cliffStints.map((s) => s.rule_name.split(": ")[1] ?? "?"),
        ),
      ];
      const label =
        unique.length === 1
          ? `both ${unique[0]}`
          : unique.join(" and ");
      p2.push(
        `Degradation cliff is reached on the ${label} stints, ` +
          "suggesting these runs approach the compound\u2019s effective limit.",
      );
    }
  }

  if (totalTime) {
    const impact = totalTime.impact;
    const winsMatch = impact.match(/wins by ([\d.]+)s/);
    const deltaMatch = impact.match(/\+([\d.]+)s/);

    if (winsMatch) {
      p2.push(
        `This is the optimal strategy, finishing ${winsMatch[1]}s ahead of the next-best alternative.`,
      );
    } else if (deltaMatch) {
      const delta = parseFloat(deltaMatch[1]);
      if (delta < 0.1) {
        p2.push(
          "This strategy effectively matches the optimal race time.",
        );
      } else {
        p2.push(
          `This strategy finishes ${deltaMatch[1]}s behind the optimal, ` +
            "making it a viable but slower alternative.",
        );
      }
    }
  }

  // --- Paragraph 3: Historical context (if any) ---
  const historicalHits = ruleHits.filter((h) => h.category === "Historical");
  const p3: string[] = [];
  if (historicalHits.length > 0) {
    const notes = historicalHits.map((h) => h.observed_value);
    p3.push(
      `Historical data: ${notes.join(". ").replace(/\.\./g, ".")}`,
    );
  }

  const paragraphs = [p1.join(" ")];
  if (p2.length > 0) paragraphs.push(p2.join(" "));
  if (p3.length > 0) paragraphs.push(p3.join(" "));
  return paragraphs.join("\n\n");
}
