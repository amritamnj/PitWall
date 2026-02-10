/**
 * OpenAI API integration for AI-generated strategy explanations.
 *
 * The LLM is a RENDERER only — it rephrases pre-computed rule outputs
 * into natural language. It must not add new analysis or predictions.
 *
 * Requires VITE_OPENAI_API_KEY in the frontend environment.
 */

import type { RuleHit } from "../types";

const SYSTEM_PROMPT = `You are an assistant that rewrites structured race strategy rules into clear natural language.

Rules:
- You may ONLY use the information provided
- Do NOT add predictions, assumptions, or new data
- Do NOT speculate about safety cars, drivers, or outcomes
- Rephrase impacts clearly and concisely
- Keep the tone informative and neutral
- Output 1–2 short paragraphs suitable for an F1 fan
- Do NOT use bullet points or lists — write flowing prose

If information is insufficient, state that clearly instead of guessing.`;

function buildUserPrompt(ruleHits: RuleHit[]): string {
  const lines = ruleHits.map(
    (r) =>
      `[${r.category}] ${r.rule_name}: ${r.observed_value} → ${r.impact}`,
  );
  return `Rewrite these strategy rule outputs into a brief natural-language explanation:\n\n${lines.join("\n")}`;
}

export interface ExplanationResult {
  ok: true;
  text: string;
}

export interface ExplanationError {
  ok: false;
  error: string;
}

export type ExplanationResponse = ExplanationResult | ExplanationError;

export async function generateExplanation(
  ruleHits: RuleHit[],
): Promise<ExplanationResponse> {
  const apiKey = import.meta.env.VITE_OPENAI_API_KEY as string | undefined;

  if (!apiKey) {
    return {
      ok: false,
      error: "VITE_OPENAI_API_KEY not configured. Add it to frontend/.env.",
    };
  }

  try {
    const resp = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        temperature: 0.3,
        max_tokens: 300,
        messages: [
          { role: "system", content: SYSTEM_PROMPT },
          { role: "user", content: buildUserPrompt(ruleHits) },
        ],
      }),
    });

    if (!resp.ok) {
      const body = await resp.text();
      return {
        ok: false,
        error: `OpenAI API error (${resp.status}): ${body.slice(0, 200)}`,
      };
    }

    const data = await resp.json();
    const text = data.choices?.[0]?.message?.content?.trim();

    if (!text) {
      return { ok: false, error: "Empty response from OpenAI." };
    }

    return { ok: true, text };
  } catch (e: any) {
    return {
      ok: false,
      error: e?.message ?? "Failed to reach OpenAI API.",
    };
  }
}
