"use client";
import type { IntersectionMatrix } from "@/lib/types";
import { useState } from "react";

const THRESHOLD = 0.35;

function scoreColor(score: number) {
  if (score >= 0.7) return "bg-accent text-white";
  if (score >= 0.5) return "bg-accent/60 text-white";
  if (score >= 0.35) return "bg-accent/30 text-white";
  if (score >= 0.15) return "bg-surface-3 text-[var(--muted)]";
  return "bg-surface-2 text-[var(--muted)]/40";
}

export function IntersectionExplorer({ matrix }: { matrix: IntersectionMatrix }) {
  const [activeTab, setActiveTab] = useState<"heatmap" | "overlaps">("heatmap");
  const labs = matrix.lab_slugs ?? [];
  const categories = Object.keys(matrix.category_names ?? {});

  if (labs.length === 0) {
    return <p className="text-[var(--muted)]">No data yet — run a collection first.</p>;
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
        {(["heatmap", "overlaps"] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm capitalize transition-colors ${
              activeTab === tab
                ? "border-b-2 border-accent text-white"
                : "text-[var(--muted)] hover:text-white"
            }`}>
            {tab === "heatmap" ? "Coverage Table" : "Gaps & Overlaps"}
          </button>
        ))}
      </div>

      {activeTab === "heatmap" && (
        <div className="space-y-6">
          <div className="overflow-x-auto">
            <table className="text-xs border-separate border-spacing-0.5">
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
                    <tr key={cat} className={isAll ? "outline outline-1 outline-accent/30 rounded" : ""}>
                      <td className="px-2 py-1.5 whitespace-nowrap max-w-[220px]">
                        <div className={`text-xs mb-0.5 ${isShared ? "text-white" : "text-[var(--muted)]"}`}>
                          {matrix.category_names[cat]}
                        </div>
                        <div className="flex flex-wrap gap-0.5">
                          {labs.filter(l => (matrix.matrix[cat]?.[l] ?? 0) >= THRESHOLD).map(l => (
                            <span key={l} className="px-1 py-px rounded bg-accent/20 text-accent text-[10px] leading-tight font-mono">
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
                            title={`${matrix.category_names[cat]} × ${lab}: ${score.toFixed(2)}`}>
                            {score > 0 ? score.toFixed(2) : "·"}
                          </td>
                        );
                      })}
                      {/* Overlap count badge */}
                      <td className="px-3 py-1.5 text-center">
                        {n === 0 ? (
                          <span className="text-red-400/60 text-xs">none</span>
                        ) : n === labs.length ? (
                          <span className="px-1.5 py-0.5 rounded bg-accent/20 text-accent text-xs font-semibold">all {n}</span>
                        ) : (
                          <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${n >= 2 ? "bg-accent/10 text-accent/80" : "bg-surface-3 text-[var(--muted)]"}`}>
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
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-accent inline-block"/>Strong</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-accent/60 inline-block"/>Moderate</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-accent/30 inline-block"/>Weak</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded bg-surface-2 inline-block"/>Missing</span>
            <span className="ml-auto text-[var(--muted)]/60">Sorted by most-covered topics first</span>
          </div>
        </div>
      )}

      {activeTab === "overlaps" && (
        <div className="space-y-4">
          {/* All labs */}
          {matrix.covered_by_all.length > 0 && (
            <div className="p-4 rounded-xl border border-accent/40 bg-accent/5">
              <h3 className="text-sm font-semibold mb-2 text-accent">
                Every lab has policy on these ({matrix.covered_by_all.length})
              </h3>
              <div className="flex flex-wrap gap-2">
                {matrix.covered_by_all.map(c => (
                  <span key={c} className="px-2 py-0.5 rounded bg-accent/20 text-xs">
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
                    <div key={labCombo} className="p-4 rounded-xl border border-accent/20 bg-accent/5">
                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="text-sm font-medium">
                          {labList.map((l, i) => (
                            <span key={l}>
                              <span className="text-accent">{l}</span>
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
                        <span className="text-accent">{labCombo}</span> only
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
            <div className="p-4 rounded-xl border border-red-900/40 bg-red-950/20">
              <h3 className="text-sm font-semibold mb-2 text-red-400">Critical gaps &mdash; no lab has policy on these ({matrix.covered_by_none.length})</h3>
              <div className="flex flex-wrap gap-2">
                {matrix.covered_by_none.map(c => (
                  <span key={c} className="px-2 py-0.5 rounded bg-red-900/20 text-xs text-red-400">
                    {matrix.category_names[c]}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
