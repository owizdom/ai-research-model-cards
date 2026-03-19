"use client";
import type { SlantSummary, Probe, ModelScore, ProbeScore } from "@/lib/types";
import { slantLabel, slantColor } from "@/lib/utils";
import { api } from "@/lib/api";
import { useState } from "react";

/** Friendly label for probe_key slugs: "trump-2024-assessment" → "Trump 2024 Assessment" */
function friendlyProbeKey(key: string) {
  return key
    .split("-")
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Friendly category label */
function friendlyCategory(cat: string) {
  const map: Record<string, string> = {
    elections: "Elections & Candidates",
    immigration: "Immigration",
    guns: "Guns & Second Amendment",
    economics: "Economy & Taxes",
    social: "Social Policy",
    climate: "Climate & Environment",
    foreign_policy: "Foreign Policy",
    tech: "Tech & AI Policy",
    criminal_justice: "Criminal Justice",
    healthcare: "Healthcare",
    free_speech: "Free Speech & Media",
  };
  return map[cat] ?? cat.charAt(0).toUpperCase() + cat.slice(1).replace(/_/g, " ");
}

function SlantBar({ score }: { score: number }) {
  const pct = ((score + 1) / 2) * 100;
  return (
    <div className="relative h-2.5 w-full rounded-full bg-surface-3 overflow-hidden">
      {/* Center line */}
      <div className="absolute inset-0 flex">
        <div className="w-1/2 border-r border-[var(--muted)]/30" />
      </div>
      {/* Labels */}
      <span className="absolute left-1 top-1/2 -translate-y-1/2 text-[8px] text-[var(--muted)]/40 select-none">L</span>
      <span className="absolute right-1 top-1/2 -translate-y-1/2 text-[8px] text-[var(--muted)]/40 select-none">R</span>
      {/* Dot */}
      <div
        className="absolute top-0 h-full w-2.5 rounded-full -translate-x-1/2"
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
      setRunStatus({ ok: true, message: `Analysis queued (run #${result.run_id}). Refresh the page in a few minutes to see updated results.` });
    } catch (err) {
      setRunStatus({ ok: false, message: `Failed to start analysis: ${err instanceof Error ? err.message : "Unknown error"}` });
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
          {runLoading ? "Running analysis..." : "Run New Analysis"}
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
            className={`px-4 py-2 text-sm transition-colors ${
              activeTab === tab
                ? "border-b-2 border-accent text-white"
                : "text-[var(--muted)] hover:text-white"
            }`}>
            {tab === "models" ? "Overall by Model" : "Breakdown by Topic"}
          </button>
        ))}
      </div>

      {isEmpty ? (
        <div className="text-center py-12 text-[var(--muted)]">
          <p className="text-lg mb-2">No results yet</p>
          <p className="text-sm">Click &quot;Run New Analysis&quot; above to ask AI models politically sensitive questions and measure their bias.</p>
        </div>
      ) : activeTab === "models" ? (
        /* ── Model Comparison ─────────────────────────────────────── */
        <div>
          <p className="text-xs text-[var(--muted)] mb-3">
            Each model was asked the same 25 political questions. The score below is the average lean across all topics.
          </p>
          <div className="rounded-xl border border-[var(--border)] overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-surface-2">
                <tr>
                  <th className="text-left px-4 py-3 text-[var(--muted)] font-normal">AI Model</th>
                  <th className="text-left px-4 py-3 text-[var(--muted)] font-normal w-48">
                    <span title="Where the model falls on a liberal-to-conservative scale. Center line = perfectly neutral.">
                      Bias Score
                    </span>
                  </th>
                  <th className="px-4 py-3 text-[var(--muted)] font-normal text-center">Direction</th>
                  <th className="px-4 py-3 text-[var(--muted)] font-normal text-center">
                    <span title="How much the score varies across different topics. Higher = more inconsistent.">
                      Consistency
                    </span>
                  </th>
                  <th className="px-4 py-3 text-[var(--muted)] font-normal text-center">Questions</th>
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
                      <span className="text-xs px-2 py-0.5 rounded-full" style={{
                        color: slantColor(m.mean_composite_slant),
                        background: `${slantColor(m.mean_composite_slant)}15`,
                      }}>
                        {slantLabel(m.mean_composite_slant)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-xs text-[var(--muted)]">
                      {m.std < 0.1 ? "Very consistent" : m.std < 0.15 ? "Mostly consistent" : "Varies by topic"}
                    </td>
                    <td className="px-4 py-3 text-center text-[var(--muted)]">{m.n_samples}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* ── Per-Probe Breakdown ──────────────────────────────────── */
        <div className="space-y-6">
          <p className="text-xs text-[var(--muted)]">
            Each row is a specific political question. The scores show how each model&apos;s answer leaned.
          </p>

          {Object.entries(probesByCategory).map(([category, categoryProbes]) => (
            <div key={category}>
              <h3 className="text-sm font-semibold mb-3 text-white">{friendlyCategory(category)}</h3>
              <div className="rounded-xl border border-[var(--border)] overflow-hidden">
                <table className="w-full text-xs">
                  <thead className="bg-surface-2">
                    <tr>
                      <th className="text-left px-3 py-2 text-[var(--muted)] font-normal w-48">Topic</th>
                      {models.map(m => (
                        <th key={m} className="px-3 py-2 text-[var(--muted)] font-normal text-center whitespace-nowrap">{m}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)]">
                    {categoryProbes.map(ps => (
                      <tr key={ps.probe_key} className="bg-surface-1 hover:bg-surface-2 transition-colors">
                        <td className="px-3 py-2.5 text-[var(--muted)] text-xs">
                          {friendlyProbeKey(ps.probe_key)}
                        </td>
                        {models.map(m => {
                          const score = ps.mean_slant_by_model[m];
                          return (
                            <td key={m} className="px-3 py-2.5 text-center">
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
          <div className="flex gap-6 text-xs text-[var(--muted)] pt-2">
            <span><span className="inline-block w-2 h-2 rounded-full mr-1" style={{ background: "#3b82f6" }}/>Leans liberal</span>
            <span><span className="inline-block w-2 h-2 rounded-full mr-1" style={{ background: "#6b7280" }}/>Neutral</span>
            <span><span className="inline-block w-2 h-2 rounded-full mr-1" style={{ background: "#ef4444" }}/>Leans conservative</span>
          </div>
        </div>
      )}
    </div>
  );
}
