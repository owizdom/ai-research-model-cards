"use client";
import type { GenerationComparison } from "@/lib/types";

function scoreColor(score: number | null | undefined): string {
  if (score == null) return "text-[var(--muted)]";
  if (score >= 90) return "text-green-600";
  if (score >= 70) return "text-yellow-600";
  if (score >= 50) return "text-orange-600";
  return "text-red-600";
}

function deltaLabel(current: number | null, previous: number | null): string | null {
  if (current == null || previous == null) return null;
  const delta = current - previous;
  if (delta === 0) return "0.0";
  return `${delta > 0 ? "+" : ""}${delta.toFixed(1)}`;
}

export function GenerationComparisonChart({ data }: { data: GenerationComparison }) {
  if (data.benchmarks.length === 0 || data.generations.length === 0) {
    return (
      <div className="p-8 text-center text-[var(--muted)] border border-[var(--border)] rounded-xl">
        No eval data available for this model family yet.
      </div>
    );
  }

  const { generations, benchmarks, matrix } = data;

  return (
    <div className="border border-[var(--border)] rounded-xl overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] bg-[var(--surface-1)]">
            <th className="text-left px-4 py-3 font-medium text-[var(--muted)] sticky left-0 bg-[var(--surface-1)]">
              Benchmark
            </th>
            {generations.map((gen, i) => (
              <th key={gen} className="text-center px-4 py-3 font-medium">
                <div>{gen}</div>
                {i > 0 && (
                  <div className="text-[10px] text-[var(--muted)] font-normal mt-0.5">vs prev</div>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {benchmarks.map(benchmark => (
            <tr key={benchmark} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--surface-1)]/50">
              <td className="px-4 py-3 font-medium sticky left-0 bg-white">{benchmark}</td>
              {generations.map((gen, i) => {
                const score = matrix[gen]?.[benchmark] ?? null;
                const prevScore = i > 0 ? (matrix[generations[i - 1]]?.[benchmark] ?? null) : null;
                const delta = deltaLabel(score, prevScore);
                return (
                  <td key={gen} className="px-4 py-3 text-center">
                    <div className={`font-mono font-semibold ${scoreColor(score)}`}>
                      {score != null ? score.toFixed(1) : "-"}
                    </div>
                    {i > 0 && delta && (
                      <div className={`text-[10px] mt-0.5 ${
                        parseFloat(delta) > 0 ? "text-green-600" : parseFloat(delta) < 0 ? "text-red-600" : "text-[var(--muted)]"
                      }`}>
                        {delta}
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
