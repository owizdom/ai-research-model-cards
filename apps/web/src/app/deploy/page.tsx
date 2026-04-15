"use client";
import { useState, useEffect } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface BenchmarkStatus {
  name: string;
  description: string;
  status: "scored" | "mentioned" | "absent";
  reported: boolean;
  vals_url: string | null;
}

interface LabCoverage {
  slug: string;
  name: string;
  color_hex: string | null;
  benchmarks: BenchmarkStatus[];
  reported_count: number;
  total_count: number;
}

interface SectorData {
  sector: string;
  label: string;
  description: string;
  benchmarks: { name: string; description: string; vals_url: string | null }[];
  lab_coverage: LabCoverage[];
  summary: { total_labs: number; labs_with_any_coverage: number; total_benchmarks: number };
}

interface Sector {
  slug: string;
  label: string;
  description: string;
  benchmark_count: number;
}

const SECTOR_ICONS: Record<string, string> = {
  healthcare: "H",
  legal: "L",
  finance: "F",
  government: "G",
  education: "E",
};

export default function DeployPage() {
  const [sectors, setSectors] = useState<Sector[]>([]);
  const [activeSector, setActiveSector] = useState<string>("healthcare");
  const [data, setData] = useState<SectorData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${BASE}/api/v1/deploy/sectors`)
      .then((r) => r.json())
      .then(setSectors)
      .catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    fetch(`${BASE}/api/v1/deploy/${activeSector}`)
      .then((r) => r.json())
      .then((d) => { setData(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [activeSector]);

  return (
    <div className="space-y-10">
      {/* Header */}
      <section>
        <h1 className="font-serif text-3xl sm:text-4xl font-semibold tracking-tight mb-3">
          Deployment Readiness
        </h1>
        <p className="text-[var(--muted)] text-sm max-w-2xl leading-relaxed">
          Select your deployment context to see which frontier models have been
          evaluated on relevant domain-specific benchmarks in their official model cards.
        </p>
      </section>

      {/* Sector Tabs */}
      <div className="flex gap-2 flex-wrap">
        {sectors.map((s) => (
          <button
            key={s.slug}
            onClick={() => setActiveSector(s.slug)}
            className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeSector === s.slug
                ? "bg-[var(--text)] text-[var(--bg)] shadow-sm"
                : "bg-[var(--surface-1)] text-[var(--muted)] border border-[var(--border)] hover:border-[var(--muted)] hover:text-[var(--text)]"
            }`}
          >
            <span className="font-mono mr-1.5 opacity-50">{SECTOR_ICONS[s.slug] ?? "?"}</span>
            {s.label}
            <span className="ml-1.5 text-xs opacity-60">{s.benchmark_count}</span>
          </button>
        ))}
      </div>

      {loading && (
        <div className="text-[var(--muted)] text-sm py-12 text-center">Loading...</div>
      )}

      {data && !loading && (
        <>
          {/* Summary */}
          <div className="p-5 rounded-xl border border-[var(--border)] bg-[var(--surface-1)]">
            <h2 className="font-serif text-xl font-semibold mb-1">{data.label}</h2>
            <p className="text-sm text-[var(--muted)] mb-3">{data.description}</p>
            <div className="flex gap-6 text-sm">
              <div>
                <span className="text-2xl font-bold font-mono text-[var(--text)]">
                  {data.summary.labs_with_any_coverage}
                </span>
                <span className="text-[var(--muted)]"> / {data.summary.total_labs} labs</span>
                <p className="text-xs text-[var(--muted)]">report any {data.label.toLowerCase()} benchmark</p>
              </div>
              <div>
                <span className="text-2xl font-bold font-mono text-[var(--text)]">
                  {data.summary.total_benchmarks}
                </span>
                <p className="text-xs text-[var(--muted)]">relevant benchmarks tracked</p>
              </div>
            </div>
          </div>

          {/* Lab × Benchmark Grid */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  <th className="text-left p-3 font-normal text-[var(--muted)] w-44">Lab</th>
                  {data.benchmarks.map((b) => (
                    <th key={b.name} className="p-3 font-normal text-[var(--muted)] text-center min-w-[90px]">
                      <div className="text-xs leading-tight">{b.name}</div>
                    </th>
                  ))}
                  <th className="p-3 font-normal text-[var(--muted)] text-center w-20">Score</th>
                </tr>
              </thead>
              <tbody>
                {data.lab_coverage.map((lab) => (
                  <tr key={lab.slug} className="border-b border-[var(--border)] hover:bg-[var(--surface-1)] transition-colors">
                    <td className="p-3">
                      <span className="font-medium text-[var(--text)]">{lab.name}</span>
                    </td>
                    {lab.benchmarks.map((b: BenchmarkStatus) => (
                      <td key={b.name} className="p-3 text-center">
                        {b.status === "scored" ? (
                          <span className="inline-flex w-7 h-7 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold" title="Score reported in model card">
                            ✓
                          </span>
                        ) : b.status === "mentioned" ? (
                          <span className="inline-flex w-7 h-7 items-center justify-center rounded-full bg-amber-100 text-amber-600 text-xs font-bold" title="Referenced but no score reported">
                            ~
                          </span>
                        ) : (
                          <span className="inline-flex w-7 h-7 items-center justify-center rounded-full bg-red-50 text-red-300 text-xs" title="Not mentioned">
                            ✗
                          </span>
                        )}
                      </td>
                    ))}
                    <td className="p-3 text-center">
                      <span className={`font-mono font-bold text-lg ${
                        lab.scored_count === lab.total_count ? "text-emerald-600" :
                        lab.scored_count > 0 ? "text-amber-600" : "text-red-400"
                      }`}>
                        {lab.scored_count}/{lab.total_count}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-5 text-xs text-[var(--muted)] mt-2">
            <span className="flex items-center gap-1.5">
              <span className="inline-flex w-5 h-5 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 text-[10px] font-bold">✓</span>
              Score reported
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-flex w-5 h-5 items-center justify-center rounded-full bg-amber-100 text-amber-600 text-[10px] font-bold">~</span>
              Referenced without score
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-flex w-5 h-5 items-center justify-center rounded-full bg-red-50 text-red-300 text-[10px]">✗</span>
              Not mentioned
            </span>
          </div>

          {/* Independent Evaluation Links */}
          {data.benchmarks.some((b) => b.vals_url) && (
            <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface-1)]">
              <h3 className="text-sm font-semibold mb-2">Independent Evaluations</h3>
              <p className="text-xs text-[var(--muted)] mb-3">
                These benchmarks are also run independently by third parties, regardless of what labs self-report.
              </p>
              <div className="flex flex-wrap gap-2">
                {data.benchmarks.filter((b) => b.vals_url).map((b) => (
                  <a
                    key={b.name}
                    href={b.vals_url!}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1.5 rounded-lg border border-[var(--border)] text-xs hover:border-[var(--muted)] hover:text-[var(--text)] text-[var(--muted)] transition-colors"
                  >
                    {b.name} on vals.ai →
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Export */}
          <div className="flex gap-3">
            <a
              href={`${BASE}/api/v1/export/benchmark-coverage.csv`}
              className="px-4 py-2 rounded-lg border border-[var(--border)] text-xs text-[var(--muted)] hover:text-[var(--text)] hover:border-[var(--muted)] transition-colors"
              download
            >
              Export full benchmark coverage CSV
            </a>
            <a
              href={`${BASE}/api/v1/export/eval-results.csv`}
              className="px-4 py-2 rounded-lg border border-[var(--border)] text-xs text-[var(--muted)] hover:text-[var(--text)] hover:border-[var(--muted)] transition-colors"
              download
            >
              Export eval results CSV
            </a>
          </div>
        </>
      )}

      {/* Methodology */}
      <section className="text-xs text-[var(--muted)] border-t border-[var(--border)] pt-8 max-w-2xl">
        <p className="mb-2 font-semibold text-[var(--text)]">Methodology</p>
        <p className="leading-relaxed">
          We check whether each benchmark name appears in the lab&apos;s official model cards
          using PostgreSQL word-boundary regex matching (<code className="text-[10px] bg-[var(--surface-2)] px-1 rounded">\m...\M</code>) against the full document content.
          Content is aggregated across all model cards per lab. Documents over 500KB are excluded
          (one card with corrupted content). A checkmark means
          the benchmark name is mentioned — it does not guarantee a specific numerical score
          was reported. Some mentions may be qualitative references or citations.
        </p>
        <p className="mt-2 leading-relaxed">
          <strong className="text-[var(--text)]">Scope limitation:</strong> This dashboard tracks official model cards and system cards only — not
          technical reports, blog posts, or third-party evaluations. Some labs publish benchmark
          scores in separate documents not tracked here.
        </p>
        <p className="mt-2 leading-relaxed">
          Independent evaluations (where available) are run by{" "}
          <a href="https://www.vals.ai" className="text-accent hover:underline" target="_blank" rel="noopener noreferrer">
            vals.ai
          </a>
          , a third-party benchmark platform that tests frontier models directly via API with private test sets.
        </p>
        <p className="mt-2 leading-relaxed">
          <a href={`${BASE}/api/v1/export/codebook.csv`} className="text-accent hover:underline" download>
            Download data dictionary (codebook.csv)
          </a>
        </p>
      </section>
    </div>
  );
}
