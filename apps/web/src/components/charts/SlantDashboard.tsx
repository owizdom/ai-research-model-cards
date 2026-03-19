"use client";
import type { SlantSummary, Probe, ModelScore, ProbeScore, ProbeResponseDetail } from "@/lib/types";
import { slantLabel, slantColor } from "@/lib/utils";
import { useState } from "react";
import { ResponseModal } from "@/components/ui/ResponseModal";

/** Friendly label for probe_key slugs: "trump-2024-assessment" -> "Trump 2024 Assessment" */
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
      <div className="absolute inset-0 flex">
        <div className="w-1/2 border-r border-[var(--muted)]/30" />
      </div>
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
  const [modalData, setModalData] = useState<{ response: ProbeResponseDetail; modelName: string; probeTopic: string } | null>(null);
  const [loadingCell, setLoadingCell] = useState<string | null>(null);

  async function handleCellClick(modelSlug: string, probeKey: string) {
    const cellKey = `${modelSlug}:${probeKey}`;
    setLoadingCell(cellKey);
    try {
      const probe = probes.find(p => p.probe_key === probeKey);
      if (!probe) return;
      const res = await fetch(`/api/v1/responses?model_slug=${encodeURIComponent(modelSlug)}&probe_id=${probe.id}`);
      if (!res.ok) throw new Error(`${res.status}`);
      const data: ProbeResponseDetail[] = await res.json();
      if (data.length > 0) {
        setModalData({
          response: data[0],
          modelName: modelSlug,
          probeTopic: friendlyProbeKey(probeKey),
        });
      }
    } catch {
      // silently fail - cell just stops loading
    } finally {
      setLoadingCell(null);
    }
  }

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
      // Use relative URL so the browser hits the Next.js rewrite proxy -> backend API
      const res = await fetch("/api/v1/probes/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ probe_ids: probeIds, model_slugs: modelSlugs }),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      const result = await res.json();
      setRunStatus({ ok: true, message: `Analysis queued (run #${result.run_id}). Refresh the page in a few minutes to see results.` });
    } catch (err) {
      setRunStatus({ ok: false, message: `Failed to start: ${err instanceof Error ? err.message : "Unknown error"}` });
    } finally {
      setRunLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Run Analysis */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleRunProbe}
          disabled={runLoading}
          className="px-4 py-2 text-sm font-medium rounded-lg bg-accent text-white hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {runLoading ? "Running..." : "Run New Analysis"}
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
        <div className="text-center py-16 text-[var(--muted)]">
          <p className="text-lg mb-2">No results yet</p>
          <p className="text-sm max-w-md mx-auto">
            Probe results will appear here once an analysis run completes.
            Analysis runs are triggered from the backend.
          </p>
        </div>
      ) : activeTab === "models" ? (
        /* -- Overall by Model ---------------------------------------- */
        <div>
          <p className="text-xs text-[var(--muted)] mb-3">
            Each model was asked the same 25 political questions. The score below is the average lean across all topics.
          </p>
          <div className="rounded-xl border border-[var(--border)] overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-surface-2">
                <tr>
                  <th className="text-left px-4 py-3 text-[var(--muted)] font-normal">AI Model</th>
                  <th className="text-left px-4 py-3 text-[var(--muted)] font-normal w-48">Bias Score</th>
                  <th className="px-4 py-3 text-[var(--muted)] font-normal text-center">Direction</th>
                  <th className="px-4 py-3 text-[var(--muted)] font-normal text-center">Consistency</th>
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
        /* -- Breakdown by Topic --------------------------------------- */
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
                          const cellKey = `${m}:${ps.probe_key}`;
                          const isLoading = loadingCell === cellKey;
                          return (
                            <td key={m} className="px-3 py-2.5 text-center">
                              {score != null ? (
                                <button
                                  onClick={() => handleCellClick(m, ps.probe_key)}
                                  className="cursor-pointer hover:bg-white/10 rounded px-1 py-0.5 transition-colors"
                                  title="Click to view full response"
                                >
                                  {isLoading ? (
                                    <span className="inline-block w-4 h-4 border-2 border-[var(--muted)] border-t-white rounded-full animate-spin" />
                                  ) : (
                                    <ScoreCell score={score} />
                                  )}
                                </button>
                              ) : <span className="text-[var(--muted)]">-</span>}
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

      {modalData && (
        <ResponseModal
          response={modalData.response}
          modelName={modalData.modelName}
          probeTopic={modalData.probeTopic}
          onClose={() => setModalData(null)}
        />
      )}
    </div>
  );
}
