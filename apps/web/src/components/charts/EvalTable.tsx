"use client";
import { useMemo, useState } from "react";
import type { EvalResult, DivergentGroup } from "@/lib/types";
import { BenchmarkPopover } from "@/components/ui/BenchmarkPopover";

/** Inline indicator that this row participates in a cross-document
 * disagreement above the 5-point threshold. EvalCards comparability
 * signal (paper Section 4.2). */
function ConflictBadge({ group }: { group: DivergentGroup }) {
  const otherReports = group.report_count - 1;
  const partyLabel = group.cross_party ? "across self-reported + third-party" : "across same-party reports";
  const fieldsLabel = group.differing_fields.length > 0
    ? ` Setup fields that vary: ${group.differing_fields.join(", ")}.`
    : "";
  const tip = `Conflicting reports: ${group.report_count} sources rate ${group.model_name} on ${group.benchmark_name} from ${group.score_min.toFixed(1)} to ${group.score_max.toFixed(1)} (${group.score_spread.toFixed(1)} spread, ${partyLabel}).${fieldsLabel}`;
  return (
    <span
      title={tip}
      className="text-[10px] px-1.5 py-0.5 rounded bg-red-50 text-red-700 font-medium whitespace-nowrap cursor-help"
    >
      ⚠ {otherReports} other{otherReports === 1 ? "" : "s"} disagree
    </span>
  );
}

function scoreColor(score: number): string {
  if (score >= 90) return "text-green-600";
  if (score >= 70) return "text-yellow-600";
  if (score >= 50) return "text-orange-600";
  return "text-red-600";
}

/**
 * Per-row Setup cell: stacked pills for what was reported + italic pills
 * naming what wasn't. Implements the EvalCards paper's "missingness as
 * content" principle (Section 4.2) — silence becomes signal.
 */
function SetupCell({ e }: { e: EvalResult }) {
  const populated: { label: string; tip: string }[] = [];
  if (e.shot_count !== null && e.shot_count !== undefined)
    populated.push({ label: `${e.shot_count}-shot`, tip: "Shot count disclosed" });
  if (e.method && e.method !== "none")
    populated.push({ label: e.method, tip: "Sampling/prompting method disclosed" });
  if (e.language && e.language !== "English")
    populated.push({ label: e.language, tip: "Evaluation language disclosed" });
  else if (e.language === "English")
    populated.push({ label: "EN", tip: "Evaluation language: English" });
  if (e.training_state && e.training_state !== "unknown")
    populated.push({ label: e.training_state, tip: "Model training state disclosed" });

  const missing = e.reproducibility?.missing_fields ?? [];

  return (
    <div className="flex flex-wrap gap-1 max-w-xs">
      {populated.map(p => (
        <span
          key={p.label}
          title={p.tip}
          className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700 font-medium"
        >
          {p.label}
        </span>
      ))}
      {missing.map(field => (
        <span
          key={field}
          title={`The model card did not disclose ${field.replace(/_/g, " ")} for this eval — not independently reproducible on this axis.`}
          className="text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 italic"
        >
          missing: {field.replace(/_/g, " ")}
        </span>
      ))}
    </div>
  );
}

export function EvalTable({
  evals,
  divergentGroups = [],
}: {
  evals: EvalResult[];
  divergentGroups?: DivergentGroup[];
}) {
  const [sortBy, setSortBy] = useState<"score" | "category" | "name">("category");
  // Default ON: the doc detail page primarily exists to show *this* model's
  // scores. Comparison rows extracted from cards' own competitor tables stay
  // in the DB (EvalCards thesis: cross-source data is signal, not noise — see
  // divergentGroups) but are hidden by default to keep the table readable.
  const [hideCompetitors, setHideCompetitors] = useState(true);

  // (benchmark_slug, model_name) → divergent group, for O(1) row matching.
  const conflictMap = useMemo(() => {
    const m = new Map<string, DivergentGroup>();
    for (const g of divergentGroups) {
      m.set(`${g.benchmark_slug}::${g.model_name}`, g);
    }
    return m;
  }, [divergentGroups]);
  const conflictsOnThisDoc = evals.filter(e => e.model_name && conflictMap.has(`${e.benchmark.slug}::${e.model_name}`)).length;

  // Primary model = the most frequent model_name in this doc's evals. Cards
  // like Anthropic system cards include comparison rows for Opus 4.7, GPT-5.5,
  // Gemini etc. — those would otherwise look like duplicates of the doc's
  // own scores. Mark the dominant model and let the reader hide competitors.
  const { primaryModel, competitorCount } = useMemo(() => {
    const counts = new Map<string, number>();
    for (const e of evals) {
      if (!e.model_name) continue;
      counts.set(e.model_name, (counts.get(e.model_name) ?? 0) + 1);
    }
    const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1]);
    const top = sorted[0];
    const others = sorted.slice(1).reduce((sum, [, n]) => sum + n, 0);
    return { primaryModel: top?.[0], competitorCount: others };
  }, [evals]);

  if (evals.length === 0) {
    return (
      <div className="p-6 text-center text-[var(--muted)] border border-[var(--border)] rounded-xl">
        No evaluations extracted yet for this document.
      </div>
    );
  }

  const filtered = hideCompetitors && primaryModel
    ? evals.filter(e => !e.model_name || e.model_name === primaryModel)
    : evals;

  const sorted = [...filtered].sort((a, b) => {
    if (sortBy === "score") return (b.score ?? -Infinity) - (a.score ?? -Infinity);
    if (sortBy === "name") return a.benchmark.name.localeCompare(b.benchmark.name);
    const catCmp = a.benchmark.category.localeCompare(b.benchmark.category);
    return catCmp !== 0 ? catCmp : (b.score ?? -Infinity) - (a.score ?? -Infinity);
  });

  // Reproducibility summary across the doc — mirrors EvalCards paper Finding 1
  // ("result-level reproducibility is the dominant reporting gap"). Even at our
  // sub-schema, ~95% of rows lack at least one field on typical model cards.
  const fullyReproducible = evals.filter(e => e.reproducibility?.score === 1).length;
  const reproPct = Math.round((fullyReproducible / evals.length) * 100);

  return (
    <div>
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <span className="text-xs text-[var(--muted)]">Sort by:</span>
        {(["category", "score", "name"] as const).map(key => (
          <button
            key={key}
            onClick={() => setSortBy(key)}
            className={`text-xs px-2 py-1 rounded ${
              sortBy === key ? "bg-accent text-white" : "bg-[var(--surface-2)] text-[var(--muted)] hover:text-[var(--text)]"
            }`}
          >
            {key.charAt(0).toUpperCase() + key.slice(1)}
          </button>
        ))}
        {primaryModel && competitorCount > 0 && (
          <button
            onClick={() => setHideCompetitors(v => !v)}
            className={`text-xs px-2 py-1 rounded ${
              hideCompetitors ? "bg-accent text-white" : "bg-[var(--surface-2)] text-[var(--muted)] hover:text-[var(--text)]"
            }`}
            title={`The card lists ${competitorCount} eval row${competitorCount === 1 ? "" : "s"} for competitor models (not ${primaryModel}). Toggle to hide them.`}
          >
            {hideCompetitors ? `Show competitors (${competitorCount})` : `Hide competitors (${competitorCount})`}
          </button>
        )}
        <span className="ml-auto text-xs text-[var(--muted)] flex items-center gap-3">
          {conflictsOnThisDoc > 0 && (
            <span
              className="text-red-700"
              title="Eval rows on this doc whose (benchmark, model_name) pair has a disagreement of >5 points across the corpus."
            >
              ⚠ {conflictsOnThisDoc} conflicting report{conflictsOnThisDoc === 1 ? "" : "s"}
            </span>
          )}
          <span
            className={reproPct < 30 ? "text-amber-700" : reproPct < 70 ? "text-yellow-700" : "text-emerald-700"}
            title="A row is 'fully reproducible' when shot_count, method, language, and training_state were all disclosed. Per the EvalCards paper, this is the dominant reporting gap across the public corpus."
          >
            {fullyReproducible}/{evals.length} rows fully reproducible ({reproPct}%)
          </span>
        </span>
      </div>

      <div className="border border-[var(--border)] rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] bg-[var(--surface-1)]">
              <th className="text-left px-4 py-3 font-medium text-[var(--muted)]">Benchmark</th>
              <th className="text-left px-4 py-3 font-medium text-[var(--muted)]">Category</th>
              <th className="text-left px-4 py-3 font-medium text-[var(--muted)]">State</th>
              <th className="text-right px-4 py-3 font-medium text-[var(--muted)]">Score</th>
              <th className="text-left px-4 py-3 font-medium text-[var(--muted)]">Setup</th>
              <th className="text-left px-4 py-3 font-medium text-[var(--muted)]">Source</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((e) => {
              const state = (e as unknown as { state?: string }).state ?? "scored";
              const stateColor =
                state === "scored" ? "bg-green-100 text-green-800"
                : state === "mentioned" ? "bg-yellow-100 text-yellow-800"
                : "bg-gray-100 text-gray-700";
              const conflict = e.model_name ? conflictMap.get(`${e.benchmark.slug}::${e.model_name}`) : undefined;
              const isCompetitor = primaryModel != null && e.model_name != null && e.model_name !== primaryModel;
              return (
              <tr key={e.id} className={`border-b border-[var(--border)] last:border-0 hover:bg-[var(--surface-1)] ${isCompetitor ? "bg-[var(--surface-1)]/40" : ""}`}>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <BenchmarkPopover benchmark={e.benchmark} />
                    {e.split && (
                      <span
                        title={`Split: ${e.split.replace(/_/g, " ")} — sub-task or subset within ${e.benchmark.name} (EvalCards hierarchy level)`}
                        className="text-[10px] px-1.5 py-0.5 rounded bg-violet-50 text-violet-700 font-mono"
                      >
                        / {e.split}
                      </span>
                    )}
                    {conflict && <ConflictBadge group={conflict} />}
                  </div>
                  {e.model_name && (
                    <div
                      className={`mt-1 text-[11px] ${
                        isCompetitor
                          ? "text-[var(--muted)] italic"
                          : "text-[var(--text)] font-medium"
                      }`}
                      title={isCompetitor ? `Competitor row — score reported by this card for ${e.model_name}, not its own model` : `This card's own score on ${e.benchmark.name}`}
                    >
                      {e.model_name}
                      {isCompetitor && <span className="ml-1 text-[10px] uppercase tracking-wide text-[var(--muted)]">· comparison</span>}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className="text-xs px-2 py-0.5 rounded bg-[var(--surface-2)] text-[var(--muted)]">
                    {e.benchmark.category}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`text-[11px] px-2 py-0.5 rounded font-medium uppercase tracking-wide ${stateColor}`}>
                    {state}
                  </span>
                </td>
                <td className={`px-4 py-3 text-right font-mono font-semibold ${e.score !== null && e.score !== undefined ? scoreColor(e.score) : "text-[var(--muted)]"}`}>
                  <div>
                    {e.score !== null && e.score !== undefined
                      ? `${e.score.toFixed(1)}${e.benchmark.metric_unit === "%" ? "%" : ""}`
                      : "—"}
                  </div>
                  {e.metric_path && (
                    <div
                      title={`Scoring rule: ${e.metric_path.replace(/_/g, " ")} (EvalCards metric_path)`}
                      className="text-[9px] text-[var(--muted)] font-normal uppercase tracking-wide mt-0.5"
                    >
                      {e.metric_path.replace(/_/g, " ")}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3"><SetupCell e={e} /></td>
                <td className="px-4 py-3">
                  <span
                    className={`text-[11px] px-2 py-0.5 rounded ${e.is_self_reported ? "bg-blue-50 text-blue-700" : "bg-emerald-50 text-emerald-700"}`}
                    title={e.is_self_reported ? "Score extracted from the lab's own model card/paper" : "Score from an independent third-party evaluation"}
                  >
                    {e.is_self_reported ? "self-reported" : "third-party"}
                  </span>
                </td>
              </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
