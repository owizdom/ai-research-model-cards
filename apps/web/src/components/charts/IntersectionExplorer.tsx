"use client";
import type { IntersectionMatrix } from "@/lib/types";
import { useState } from "react";

const THRESHOLD = 0.35;

function scoreLevel(score: number): string {
  if (score >= 0.7) return "Strong coverage";
  if (score >= 0.5) return "Moderate coverage";
  if (score >= 0.35) return "Weak coverage";
  if (score >= 0.15) return "Trace mention";
  return "No coverage";
}

function scoreColor(score: number) {
  if (score >= 0.7) return "bg-data text-white";
  if (score >= 0.5) return "bg-data-moderate text-[var(--data)]";
  if (score >= 0.35) return "bg-data-weak text-[var(--data)]";
  if (score >= 0.15) return "bg-[var(--surface-3)] text-[var(--muted)]";
  return "bg-data-missing text-gray-400";
}

export function IntersectionExplorer({
  matrix,
  evalDepth,
}: {
  matrix: IntersectionMatrix;
  evalDepth?: Record<string, Record<string, number>>;
}) {
  const [activeTab, setActiveTab] = useState<"heatmap" | "overlaps" | "eval_depth">("heatmap");
  const labs = matrix.lab_slugs ?? [];
  const categories = Object.keys(matrix.category_names ?? {});

  if (labs.length === 0) {
    return <p className="text-[var(--muted)]">No data yet. Run a collection first.</p>;
  }

  // Per-category: how many labs cover it (above threshold)
  const coverCount: Record<string, number> = {};
  for (const cat of categories) {
    coverCount[cat] = labs.filter(l => (matrix.matrix[cat]?.[l] ?? 0) >= THRESHOLD).length;
  }

  // Sort categories: most-covered first, then by name
  const sortedCategories = [...categories].sort((a, b) => {
    const diff = coverCount[b] - coverCount[a];
    return diff !== 0 ? diff : (matrix.category_names[a] ?? "").localeCompare(matrix.category_names[b] ?? "");
  });

  // Build overlap groups: for each category, which labs cover it?
  const overlapGroups: Record<string, string[]> = {};
  for (const cat of categories) {
    const covering = labs.filter(l => (matrix.matrix[cat]?.[l] ?? 0) >= THRESHOLD);
    if (covering.length === 0) continue;
    const key = covering.sort().join(" + ");
    if (!overlapGroups[key]) overlapGroups[key] = [];
    overlapGroups[key].push(cat);
  }
  const sortedGroups = Object.entries(overlapGroups)
    .sort((a, b) => b[1].length - a[1].length);

  return (
    <div className="space-y-6">
      {/* Tabs */}
      <div className="flex gap-1 border-b border-[var(--border)]">
        {([
          { key: "heatmap" as const, label: "Coverage Table" },
          { key: "overlaps" as const, label: "Gaps & Overlaps" },
          { key: "eval_depth" as const, label: "Eval Depth" },
        ]).map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm transition-colors ${
              activeTab === tab.key
                ? "border-b-2 border-accent text-[var(--text)]"
                : "text-[var(--muted)] hover:text-[var(--text)]"
            }`}>
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "heatmap" && (
        <div className="space-y-6">
          <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
            <table className="text-xs border-separate border-spacing-0.5 w-full min-w-[700px]">
              <thead>
                <tr>
                  <th className="w-48 text-left px-2 py-1 text-[var(--muted)]">Category</th>
                  {labs.map(lab => (
                    <th key={lab} className="px-3 py-1 text-center font-normal text-[var(--muted)] whitespace-nowrap">
                      {lab}
                    </th>
                  ))}
                  <th className="px-3 py-1 text-center font-normal text-[var(--muted)] whitespace-nowrap">
                    overlap
                  </th>
                </tr>
              </thead>
              <tbody>
                {sortedCategories.map(cat => {
                  const n = coverCount[cat];
                  const isShared = n >= 2;
                  const isAll = n === labs.length && labs.length > 0;
                  return (
                    <tr key={cat} className={isAll ? "outline outline-1 outline-data/20 rounded" : ""}>
                      <td className="px-2 py-1.5 whitespace-nowrap max-w-[220px]">
                        <div className={`text-xs mb-0.5 ${isShared ? "text-[var(--text)]" : "text-[var(--muted)]"}`}>
                          {matrix.category_names[cat]}
                        </div>
                        <div className="flex flex-wrap gap-0.5">
                          {labs.filter(l => (matrix.matrix[cat]?.[l] ?? 0) >= THRESHOLD).map(l => (
                            <span key={l} className="px-1 py-px rounded bg-data-weak text-data text-[10px] leading-tight font-mono">
                              {l}
                            </span>
                          ))}
                        </div>
                      </td>
                      {labs.map(lab => {
                        const score = matrix.matrix[cat]?.[lab] ?? 0;
                        return (
                          <td key={lab}
                            className={`px-3 py-1.5 rounded text-center font-mono ${scoreColor(score)}`}
                            title={`${matrix.category_names[cat]} / ${lab}: ${scoreLevel(score)} (${score.toFixed(2)})`}>
                            {score > 0 ? score.toFixed(2) : "·"}
                          </td>
                        );
                      })}
                      {/* Overlap count badge */}
                      <td className="px-3 py-1.5 text-center">
                        {n === 0 ? (
                          <span className="text-red-600 text-xs">none</span>
                        ) : n === labs.length ? (
                          <span className="px-1.5 py-0.5 rounded bg-data-weak text-data text-xs font-semibold">all {n}</span>
                        ) : (
                          <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${n >= 2 ? "bg-data-weak text-data/80" : "bg-[var(--surface-3)] text-[var(--muted)]"}`}>
                            {n}/{labs.length}
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-4 text-xs text-[var(--muted)]">
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-data inline-block"/>Strong</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-data-moderate inline-block"/>Moderate</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-data-weak inline-block"/>Weak</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-surface-2 inline-block"/>Missing</span>
            <span className="ml-auto text-[var(--muted)]/60">Sorted by most-covered topics first</span>
          </div>
        </div>
      )}

      {activeTab === "overlaps" && (
        <div className="space-y-4">
          {/* All labs */}
          {matrix.covered_by_all.length > 0 && (
            <div className="p-4 rounded-xl border border-data/15 bg-data/5">
              <h3 className="text-sm font-semibold mb-2 text-data">
                Every lab has policy on these ({matrix.covered_by_all.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {matrix.covered_by_all.map(c => (
                  <span key={c} className="px-2 py-0.5 rounded bg-data-weak text-xs">
                    {matrix.category_names[c]}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Partial intersections: 2+ labs, not all */}
          {(() => {
            const partials = sortedGroups.filter(([combo]) => {
              const n = combo.split(" + ").length;
              return n >= 2 && n < labs.length;
            });
            if (partials.length === 0) return null;
            return (
              <div className="space-y-3">
                <h3 className="text-xs uppercase tracking-wider text-[var(--muted)]">Shared by some labs</h3>
                {partials.map(([labCombo, cats]) => {
                  const labList = labCombo.split(" + ");
                  return (
                    <div key={labCombo} className="p-4 rounded-xl border border-data/10 bg-data/5">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="text-sm font-medium">
                          {labList.map((l, i) => (
                            <span key={l}>
                              <span className="text-data">{l}</span>
                              {i < labList.length - 1 && <span className="text-[var(--muted)]"> ∩ </span>}
                            </span>
                          ))}
                        </h3>
                        <span className="text-xs text-[var(--muted)]">({cats.length} categor{cats.length === 1 ? "y" : "ies"})</span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {cats.map(c => (
                          <span key={c} className="px-2 py-0.5 rounded bg-surface-2 text-xs">
                            {matrix.category_names[c]}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })()}

          {/* Unique to one lab */}
          {(() => {
            const uniques = sortedGroups.filter(([combo]) => combo.split(" + ").length === 1);
            if (uniques.length === 0) return null;
            return (
              <div className="space-y-3">
                <h3 className="text-xs uppercase tracking-wider text-[var(--muted)]">Only one lab covers these</h3>
                {uniques.map(([labCombo, cats]) => (
                  <div key={labCombo} className="p-4 rounded-xl border border-[var(--border)] bg-surface-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-sm font-medium">
                        <span className="text-data">{labCombo}</span> only
                      </h3>
                      <span className="text-xs text-[var(--muted)]">({cats.length} categor{cats.length === 1 ? "y" : "ies"})</span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {cats.map(c => (
                        <span key={c} className="px-2 py-0.5 rounded bg-surface-2 text-xs text-[var(--muted)]">
                          {matrix.category_names[c]}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            );
          })()}

          {/* Covered by none */}
          {matrix.covered_by_none.length > 0 && (
            <div className="p-4 rounded-xl border border-red-200 bg-red-50">
              <h3 className="text-sm font-semibold mb-2 text-red-600">Critical gaps: no lab has policy on these ({matrix.covered_by_none.length})</h3>
              <div className="flex flex-wrap gap-2">
                {matrix.covered_by_none.map(c => (
                  <span key={c} className="px-2 py-0.5 rounded bg-red-50 text-xs text-red-600">
                    {matrix.category_names[c]}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === "eval_depth" && (
        <div className="space-y-6">
          {evalDepth && Object.keys(evalDepth).length > 0 ? (
            <>
              <p className="text-sm text-[var(--muted)]">
                How many benchmark results each lab reports in their model cards, grouped by evaluation category.
              </p>
              <div className="overflow-x-auto rounded-xl border border-[var(--border)]">
                <table className="text-xs border-separate border-spacing-0.5 w-full min-w-[700px]">
                  <thead>
                    <tr>
                      <th className="w-48 text-left px-2 py-1 text-[var(--muted)]">Eval Category</th>
                      {labs.map(lab => (
                        <th key={lab} className="px-3 py-1 text-center font-normal text-[var(--muted)] whitespace-nowrap">
                          {lab}
                        </th>
                      ))}
                      <th className="px-3 py-1 text-center font-normal text-[var(--muted)]">total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(evalDepth).sort(([a], [b]) => a.localeCompare(b)).map(([category, labCounts]) => {
                      const total = Object.values(labCounts).reduce((s, v) => s + v, 0);
                      return (
                        <tr key={category}>
                          <td className="px-2 py-1.5 capitalize text-[var(--text)]">{category.replace("_", " ")}</td>
                          {labs.map(lab => {
                            const count = labCounts[lab] ?? 0;
                            return (
                              <td key={lab} className={`px-3 py-1.5 text-center font-mono rounded ${
                                count >= 5 ? "bg-data text-white" :
                                count >= 3 ? "bg-data-moderate text-data" :
                                count >= 1 ? "bg-data-weak text-data" :
                                "bg-gray-100 text-gray-400"
                              }`}>
                                {count > 0 ? count : "·"}
                              </td>
                            );
                          })}
                          <td className="px-3 py-1.5 text-center font-mono text-[var(--muted)]">{total}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="flex flex-wrap gap-4 text-xs text-[var(--muted)]">
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-data inline-block"/>5+ evals</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-data-moderate inline-block"/>3-4 evals</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-data-weak inline-block"/>1-2 evals</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-surface-2 inline-block"/>None</span>
              </div>
            </>
          ) : (
            <div className="p-8 text-center text-[var(--muted)] border border-[var(--border)] rounded-xl">
              <p className="mb-2">No eval data extracted yet.</p>
              <p className="text-xs">Run eval extraction on model cards to see how many benchmarks each lab reports per category.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
