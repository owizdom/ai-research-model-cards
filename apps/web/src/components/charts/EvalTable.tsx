"use client";
import { useState } from "react";
import type { EvalResult } from "@/lib/types";
import { BenchmarkPopover } from "@/components/ui/BenchmarkPopover";

function scoreColor(score: number): string {
  if (score >= 90) return "text-green-600";
  if (score >= 70) return "text-yellow-600";
  if (score >= 50) return "text-orange-600";
  return "text-red-600";
}

export function EvalTable({ evals }: { evals: EvalResult[] }) {
  const [sortBy, setSortBy] = useState<"score" | "category" | "name">("category");

  if (evals.length === 0) {
    return (
      <div className="p-6 text-center text-[var(--muted)] border border-[var(--border)] rounded-xl">
        No evaluations extracted yet for this document.
      </div>
    );
  }

  const sorted = [...evals].sort((a, b) => {
    if (sortBy === "score") return (b.score ?? -Infinity) - (a.score ?? -Infinity);
    if (sortBy === "name") return a.benchmark.name.localeCompare(b.benchmark.name);
    // category
    const catCmp = a.benchmark.category.localeCompare(b.benchmark.category);
    return catCmp !== 0 ? catCmp : (b.score ?? -Infinity) - (a.score ?? -Infinity);
  });

  // Group by category
  const categories = [...new Set(sorted.map(e => e.benchmark.category))];

  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
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
        <span className="ml-auto text-xs text-[var(--muted)]">{evals.length} evals</span>
      </div>

      <div className="border border-[var(--border)] rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] bg-[var(--surface-1)]">
              <th className="text-left px-4 py-3 font-medium text-[var(--muted)]">Benchmark</th>
              <th className="text-left px-4 py-3 font-medium text-[var(--muted)]">Category</th>
              <th className="text-left px-4 py-3 font-medium text-[var(--muted)]">State</th>
              <th className="text-right px-4 py-3 font-medium text-[var(--muted)]">Score</th>
              <th className="text-left px-4 py-3 font-medium text-[var(--muted)]">Variant</th>
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
              return (
              <tr key={e.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--surface-1)]">
                <td className="px-4 py-3"><BenchmarkPopover benchmark={e.benchmark} /></td>
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
                  {e.score !== null && e.score !== undefined
                    ? `${e.score.toFixed(1)}${e.benchmark.metric_unit === "%" ? "%" : ""}`
                    : "—"}
                </td>
                <td className="px-4 py-3 text-[var(--muted)]">
                  {e.variant !== "default" ? e.variant : "-"}
                </td>
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
