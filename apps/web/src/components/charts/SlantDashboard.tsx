"use client";
import type { SlantSummary, Probe, ModelScore, ProbeScore } from "@/lib/types";
import { slantLabel, slantColor } from "@/lib/utils";
import { api } from "@/lib/api";
import { useState } from "react";

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

function ScoreCell({ score }: { score: number }) {
  return (
    <span className="font-mono text-xs px-1.5 py-0.5 rounded" style={{ color: slantColor(score) }}>
      {score >= 0 ? "+" : ""}{score.toFixed(3)}
    </span>
  );
}

export function SlantDashboard({
  summary,
  probes,
}: {
  summary: SlantSummary | null;
  probes: Probe[];
}) {
  const [activeTab, setActiveTab] = useState<"models" | "probes">("models");
  const [runLoading, setRunLoading] = useState(false);
  const [runStatus, setRunStatus] = useState<{ ok: boolean; message: string } | null>(null);

  const modelScores = summary?.model_scores ?? [];
  const probeScores = summary?.probe_scores ?? [];
  const models = modelScores.map(m => m.model_slug);

  // Group probes by category
  const probesByCategory: Record<string, ProbeScore[]> = {};
  for (const ps of probeScores) {
    if (!probesByCategory[ps.category]) probesByCategory[ps.category] = [];
    probesByCategory[ps.category].push(ps);
  }

  const isEmpty = modelScores.length === 0;

  async function handleRunProbe() {
    setRunLoading(true);
    setRunStatus(null);
    try {
      const probeIds = probes.map(p => p.id);
      const modelSlugs = models.length > 0 ? models : [];
      const result = await api.probes.triggerRun({ probe_ids: probeIds, model_slugs: modelSlugs });
      setRunStatus({ ok: true, message: `Probe run queued (run #${result.run_id}). Refresh in a few minutes to see results.` });
    } catch (err) {
      setRunStatus({ ok: false, message: `Failed to trigger probe run: ${err instanceof Error ? err.message : "Unknown error"}` });
    } finally {
      setRunLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Run Probe Button */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleRunProbe}
          disabled={runLoading}
          className="px-4 py-2 text-sm font-medium rounded-lg bg-accent text-white hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {runLoading ? "Running..." : "Run Probe"}
        </button>
        {runStatus && (
          <span className={`text-sm ${runStatus.ok ? "text-green-400" : "text-red-400"}`}>
            {runStatus.message}
          </span>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[var(--border)]">
        {(["models", "probes"] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm capitalize transition-colors ${
              activeTab === tab
                ? "border-b-2 border-accent text-white"
                : "text-[var(--muted)] hover:text-white"
            }`}>
            {tab === "models" ? "Model Comparison" : "Per-Probe Breakdown"}
          </button>
        ))}
      </div>

      {isEmpty ? (
        <div className="text-center py-12 text-[var(--muted)]">
          <p className="text-lg mb-2">No probe runs yet</p>
          <p className="text-sm">Run <code className="bg-surface-2 px-1.5 py-0.5 rounded">make probe</code> to trigger your first slant analysis</p>
        </div>
      ) : activeTab === "models" ? (
        /* ── Model Comparison ─────────────────────────────────────── */
        <div className="rounded-xl border border-[var(--border)] overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface-2">
              <tr>
                <th className="text-left px-4 py-3 text-[var(--muted)] font-normal">Model</th>
                <th className="text-left px-4 py-3 text-[var(--muted)] font-normal w-48">Composite Slant</th>
                <th className="px-4 py-3 text-[var(--muted)] font-normal text-center">Lean</th>
                <th className="px-4 py-3 text-[var(--muted)] font-normal text-center">Std Dev</th>
                <th className="px-4 py-3 text-[var(--muted)] font-normal text-center">Samples</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {modelScores.map((m) => (
                <tr key={m.model_slug} className="bg-surface-1 hover:bg-surface-2 transition-colors">
                  <td className="px-4 py-3 font-medium">{m.model_slug}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <ScoreCell score={m.mean_composite_slant} />
                      <SlantBar score={m.mean_composite_slant} />
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-xs px-2 py-0.5 rounded" style={{ color: slantColor(m.mean_composite_slant) }}>
                      {slantLabel(m.mean_composite_slant)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center font-mono text-xs text-[var(--muted)]">
                    ±{m.std.toFixed(3)}
                  </td>
                  <td className="px-4 py-3 text-center text-[var(--muted)]">{m.n_samples}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* ── Per-Probe Breakdown ──────────────────────────────────── */
        <div className="space-y-6">
          {Object.entries(probesByCategory).map(([category, categoryProbes]) => (
            <div key={category}>
              <h3 className="text-xs uppercase tracking-wider text-[var(--muted)] mb-3">{category}</h3>
              <div className="rounded-xl border border-[var(--border)] overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-surface-2">
                    <tr>
                      <th className="text-left px-3 py-2 text-[var(--muted)] font-normal w-48">Probe</th>
                      {models.map(m => (
                        <th key={m} className="px-3 py-2 text-[var(--muted)] font-normal text-center whitespace-nowrap">{m}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)]">
                    {categoryProbes.map(ps => (
                      <tr key={ps.probe_key} className="bg-surface-1">
                        <td className="px-3 py-2 font-mono text-[var(--muted)]">{ps.probe_key}</td>
                        {models.map(m => {
                          const score = ps.mean_slant_by_model[m];
                          return (
                            <td key={m} className="px-3 py-2 text-center">
                              {score != null ? <ScoreCell score={score} /> : <span className="text-[var(--muted)]">—</span>}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}

          {/* Legend */}
          <div className="flex gap-6 text-xs text-[var(--muted)]">
            <span><span className="inline-block w-2 h-2 rounded-full mr-1" style={{ background: "#3b82f6" }}/>Liberal (&gt;+0.3)</span>
            <span><span className="inline-block w-2 h-2 rounded-full mr-1" style={{ background: "#6b7280" }}/>Neutral (±0.3)</span>
            <span><span className="inline-block w-2 h-2 rounded-full mr-1" style={{ background: "#ef4444" }}/>Conservative (&lt;-0.3)</span>
          </div>
        </div>
      )}
    </div>
  );
}
