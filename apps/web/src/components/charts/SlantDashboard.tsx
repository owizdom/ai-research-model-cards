"use client";
import type { SlantSummary, Probe } from "@/lib/types";
import { slantLabel, slantColor } from "@/lib/utils";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

function SlantBar({ score }: { score: number }) {
  const pct = ((score + 1) / 2) * 100;
  return (
    <div className="relative h-2 w-full rounded-full bg-surface-3 overflow-hidden">
      <div className="absolute inset-0 flex">
        <div className="w-1/2 border-r border-[var(--border)]" />
      </div>
      <div
        className="absolute top-0 h-full w-2 rounded-full -translate-x-1/2"
        style={{ left: `${pct}%`, background: slantColor(score) }}
      />
    </div>
  );
}

export function SlantDashboard({
  summaries,
  probes,
}: {
  summaries: SlantSummary[];
  probes: Probe[];
}) {
  const [selected, setSelected] = useState<string | null>(null);

  const { data: series } = useQuery({
    queryKey: ["slant-series", selected],
    queryFn: () => api.analysis.slantSeries(selected!),
    enabled: !!selected,
  });

  return (
    <div className="space-y-6">
      {/* Summary table */}
      <div className="rounded-xl border border-[var(--border)] overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-surface-2">
            <tr>
              <th className="text-left px-4 py-3 text-[var(--muted)] font-normal">Model</th>
              <th className="text-left px-4 py-3 text-[var(--muted)] font-normal">Mean Slant</th>
              <th className="px-4 py-3 text-[var(--muted)] font-normal text-center">Lean</th>
              <th className="px-4 py-3 text-[var(--muted)] font-normal text-center hidden md:table-cell">Trump Δ Biden</th>
              <th className="px-4 py-3 text-[var(--muted)] font-normal text-center">Runs</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {summaries.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-[var(--muted)]">
                  No probe runs yet. Trigger a run below.
                </td>
              </tr>
            ) : (
              summaries.map((s) => (
                <tr
                  key={s.model_slug}
                  className={`bg-surface-1 hover:bg-surface-2 cursor-pointer transition-colors ${
                    selected === s.model_slug ? "ring-1 ring-inset ring-accent" : ""
                  }`}
                  onClick={() => setSelected(selected === s.model_slug ? null : s.model_slug)}
                >
                  <td className="px-4 py-3 font-medium">{s.model_name}</td>
                  <td className="px-4 py-3 w-48">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs w-14 text-right" style={{ color: slantColor(s.mean_slant) }}>
                        {s.mean_slant.toFixed(3)}
                      </span>
                      <SlantBar score={s.mean_slant} />
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-xs px-2 py-0.5 rounded" style={{ color: slantColor(s.mean_slant) }}>
                      {slantLabel(s.mean_slant)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center hidden md:table-cell">
                    {s.asymmetry != null ? (
                      <span className="font-mono text-xs">{s.asymmetry.toFixed(3)}</span>
                    ) : (
                      <span className="text-[var(--muted)]">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center text-[var(--muted)]">{s.run_count}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Series chart placeholder when a model is selected */}
      {selected && series && series.length > 0 && (
        <div className="p-5 rounded-xl border border-[var(--border)] bg-surface-1">
          <h3 className="text-sm font-medium mb-4">
            Slant over time — <span className="text-accent">{selected}</span>
          </h3>
          <div className="space-y-3">
            {series.map((s) => (
              <div key={s.probe_slug} className="flex items-center gap-3 text-xs">
                <span className="w-40 truncate text-[var(--muted)] font-mono">{s.probe_slug}</span>
                <span
                  className="px-2 py-0.5 rounded"
                  style={{ color: slantColor(s.composite_slant[s.composite_slant.length - 1] ?? 0) }}
                >
                  {s.trend_direction}
                </span>
                <span className="font-mono text-[var(--muted)]">
                  latest {(s.composite_slant[s.composite_slant.length - 1] ?? 0).toFixed(3)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
