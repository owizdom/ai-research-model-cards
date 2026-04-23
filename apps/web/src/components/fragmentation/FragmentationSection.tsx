"use client";
import { useState } from "react";
import type { FragmentationResponse, FragmentationView, LabUniqueness } from "@/lib/types";

type ViewMode = "raw" | "families";

interface CorpusSummary {
  total_docs: number;
  total_evals: number;
  n_labs: number;
}

export function FragmentationSection({
  data,
  corpusSummary,
}: {
  data: FragmentationResponse;
  corpusSummary: CorpusSummary;
}) {
  const [view, setView] = useState<ViewMode>("raw");
  const [selectedBucket, setSelectedBucket] = useState<number | null>(null);
  const [selectedLab, setSelectedLab] = useState<string>(data.by_lab[0]?.lab_slug ?? "");

  const current = view === "raw" ? data.raw : data.families;
  const otherView = view === "raw" ? data.families : data.raw;
  const otherLabel = view === "raw" ? "families" : "raw names";

  const selectedLabData = data.by_lab.find(l => l.lab_slug === selectedLab);

  return (
    <section className="mb-24">
      <FragmentationHero
        view={view}
        setView={setView}
        current={current}
        otherPct={otherView.pct_unique}
        otherLabel={otherLabel}
        corpusSummary={corpusSummary}
      />
      <FragmentationHistogram
        view={current}
        selectedBucket={selectedBucket}
        setSelectedBucket={setSelectedBucket}
      />
      <OnlyLabWidget
        byLab={data.by_lab}
        selectedLab={selectedLab}
        setSelectedLab={setSelectedLab}
        selectedLabData={selectedLabData}
      />
      <p className="text-xs text-[var(--muted)] mt-10 leading-relaxed max-w-3xl">
        We measure what labs publicly <em>report</em> in their model cards — not what they privately evaluate.
        Fragmentation of reporting does not imply concealment.
        Covers {data.labs.length} Western frontier labs: Anthropic, Google, Meta, Mistral, OpenAI, xAI.
        Last updated from {corpusSummary.total_docs} public documents.
        See <a href="/about" className="underline hover:text-[var(--text)]">methodology</a> for the
        family canonicalization rule.
      </p>
    </section>
  );
}

function FragmentationHero({
  view, setView, current, otherPct, otherLabel, corpusSummary,
}: {
  view: ViewMode;
  setView: (v: ViewMode) => void;
  current: FragmentationView;
  otherPct: number;
  otherLabel: string;
  corpusSummary: CorpusSummary;
}) {
  return (
    <div className="mb-10 pt-4">
      <p className="text-[var(--accent)] text-sm font-medium mb-4 tracking-wide uppercase">
        Model Card Explorer
      </p>
      <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl font-bold leading-[1.1] tracking-tight mb-6 max-w-4xl">
        <span className="text-[var(--accent)]">{current.pct_unique}%</span> of frontier benchmarks
        are reported by only one lab.
      </h1>
      <p className="text-[var(--muted)] max-w-3xl text-lg leading-relaxed mb-6">
        We extracted every benchmark from {corpusSummary.total_docs} public model cards across{" "}
        {corpusSummary.n_labs} frontier labs — {current.total} distinct{" "}
        {view === "raw" ? "benchmark names" : "benchmark families"} in total. Only{" "}
        {current.total - current.one_lab_count} are shared between two or more labs. MMLU is the
        single benchmark that five labs agree to disclose.
      </p>
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span className="text-[var(--muted)]">Count:</span>
        <div className="inline-flex rounded-full border border-[var(--border)] bg-white p-0.5">
          <button
            onClick={() => setView("raw")}
            className={`px-3 py-1 rounded-full transition-colors text-xs ${
              view === "raw" ? "bg-[var(--accent)] text-white" : "text-[var(--muted)] hover:text-[var(--text)]"
            }`}
          >
            Raw names
          </button>
          <button
            onClick={() => setView("families")}
            className={`px-3 py-1 rounded-full transition-colors text-xs ${
              view === "families" ? "bg-[var(--accent)] text-white" : "text-[var(--muted)] hover:text-[var(--text)]"
            }`}
          >
            Benchmark families
          </button>
        </div>
        <span className="text-[var(--muted)] text-xs">
          ({otherLabel}: {otherPct}%)
        </span>
      </div>
    </div>
  );
}

function FragmentationHistogram({
  view, selectedBucket, setSelectedBucket,
}: {
  view: FragmentationView;
  selectedBucket: number | null;
  setSelectedBucket: (n: number | null) => void;
}) {
  // Ensure all 6 buckets present (1..6), fill gaps with zeros
  const bucketMap = new Map(view.histogram.map(b => [b.n_labs, b]));
  const buckets = Array.from({ length: 6 }, (_, i) => {
    const n = i + 1;
    return bucketMap.get(n) ?? { n_labs: n, count: 0, slugs: [], names: {} };
  });
  const maxCount = Math.max(...buckets.map(b => b.count), 1);
  const selected = selectedBucket != null ? bucketMap.get(selectedBucket) : undefined;

  return (
    <div className="border border-[var(--border)] rounded-xl bg-white p-6 sm:p-8 mb-10">
      <div className="mb-6">
        <h3 className="font-semibold text-base mb-1">How many labs report each benchmark?</h3>
        <p className="text-sm text-[var(--muted)]">
          Click a column to list the benchmarks in that group.
        </p>
      </div>
      <div className="flex items-end gap-3 sm:gap-6 h-56 mb-4">
        {buckets.map(b => {
          const isSelected = selectedBucket === b.n_labs;
          const isEmpty = b.count === 0;
          const height = isEmpty ? 2 : Math.max((b.count / maxCount) * 100, 4);
          return (
            <button
              key={b.n_labs}
              disabled={isEmpty}
              onClick={() => setSelectedBucket(isSelected ? null : b.n_labs)}
              className={`flex-1 flex flex-col items-center justify-end gap-2 h-full group ${
                isEmpty ? "cursor-default" : "cursor-pointer"
              }`}
            >
              <div
                className={`text-sm font-semibold transition-colors ${
                  isSelected ? "text-[var(--accent)]" : isEmpty ? "text-[var(--border-light)]" : "text-[var(--text)]"
                }`}
              >
                {b.count}
              </div>
              <div
                className={`w-full rounded-t-md transition-colors ${
                  isSelected
                    ? "bg-[var(--accent)]"
                    : isEmpty
                      ? "bg-[var(--surface-2)]"
                      : "bg-[var(--accent-soft)] group-hover:bg-[var(--accent)]/30"
                }`}
                style={{ height: `${height}%` }}
              />
            </button>
          );
        })}
      </div>
      <div className="flex gap-3 sm:gap-6 text-xs text-[var(--muted)]">
        {buckets.map(b => (
          <div key={b.n_labs} className="flex-1 text-center">
            {b.n_labs} {b.n_labs === 1 ? "lab" : "labs"}
          </div>
        ))}
      </div>
      <div className="text-xs text-[var(--muted)] text-center mt-2">
        Number of labs reporting →
      </div>

      {selected && selected.slugs.length > 0 && (
        <div className="mt-6 pt-6 border-t border-[var(--border)]">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-medium">
              {selected.count} {selected.count === 1 ? "benchmark" : "benchmarks"} reported by{" "}
              {selected.n_labs === 1 ? "only one lab" : `exactly ${selected.n_labs} labs`}
            </div>
            <button
              onClick={() => setSelectedBucket(null)}
              className="text-xs text-[var(--muted)] hover:text-[var(--text)]"
            >
              Close ✕
            </button>
          </div>
          <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto pr-2">
            {selected.slugs.map(s => (
              <span
                key={s}
                className="text-xs px-2 py-1 rounded bg-[var(--surface-2)] text-[var(--muted)] font-mono"
                title={selected.names[s] ?? s}
              >
                {selected.names[s] ?? s}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

const CATEGORY_LABELS: Record<string, string> = {
  safety: "Safety",
  agentic: "Agentic",
  coding: "Coding",
  math: "Math",
  reasoning: "Reasoning",
  knowledge: "Knowledge",
  multimodal: "Multimodal",
  multilingual: "Multilingual",
  vision: "Vision",
  long_context: "Long Context",
  instruction_following: "Instruction Following",
  arena: "Arena / Preference",
  medical: "Medical",
  other: "Other",
};

const CATEGORY_COLORS: Record<string, string> = {
  safety: "#C44343",
  agentic: "#2E7D5B",
  coding: "#D97757",
  math: "#8B6CAF",
  reasoning: "#4A7FC1",
  knowledge: "#2E7D5B",
  multimodal: "#5B8A72",
  multilingual: "#1A7A6D",
  vision: "#5B8A72",
  long_context: "#4A7FC1",
  instruction_following: "#C17E2B",
  arena: "#7A6850",
  medical: "#A8446B",
  other: "#B0AFA8",
};

function OnlyLabWidget({
  byLab, selectedLab, setSelectedLab, selectedLabData,
}: {
  byLab: LabUniqueness[];
  selectedLab: string;
  setSelectedLab: (s: string) => void;
  selectedLabData: LabUniqueness | undefined;
}) {
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set());

  if (!selectedLabData) return null;
  const pctUnique = Math.round((selectedLabData.only_them_count / selectedLabData.total_reported) * 100);

  // Group benchmarks by category
  const grouped = new Map<string, { slug: string; name: string; category: string }[]>();
  for (const b of selectedLabData.only_them) {
    const cat = b.category || "other";
    if (!grouped.has(cat)) grouped.set(cat, []);
    grouped.get(cat)!.push(b);
  }

  // Sort categories by size (descending), sort benchmarks alphabetically within each
  const categoryRows = Array.from(grouped.entries())
    .map(([cat, benches]) => ({
      cat,
      benches: [...benches].sort((a, b) => a.name.localeCompare(b.name)),
    }))
    .sort((a, b) => b.benches.length - a.benches.length);

  const maxCount = categoryRows[0]?.benches.length ?? 1;
  const PREVIEW_N = 4;

  const toggleCat = (cat: string) => {
    const next = new Set(expandedCats);
    if (next.has(cat)) next.delete(cat); else next.add(cat);
    setExpandedCats(next);
  };

  return (
    <div className="border border-[var(--border)] rounded-xl bg-white p-6 sm:p-8">
      <div className="mb-6">
        <h3 className="font-semibold text-base mb-1">What only one lab reports</h3>
        <p className="text-sm text-[var(--muted)]">
          Each lab picks benchmarks no one else discloses — often chosen to showcase strengths.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2 mb-6">
        {byLab.map(l => (
          <button
            key={l.lab_slug}
            onClick={() => { setSelectedLab(l.lab_slug); setExpandedCats(new Set()); }}
            className={`text-xs px-3 py-1.5 rounded-full transition-colors ${
              selectedLab === l.lab_slug
                ? "bg-[var(--accent)] text-white"
                : "bg-[var(--surface-2)] text-[var(--muted)] hover:text-[var(--text)]"
            }`}
          >
            {l.lab_name}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 mb-6">
        <span className="font-serif text-3xl font-bold text-[var(--text)]">
          {selectedLabData.only_them_count}
        </span>
        <span className="text-[var(--muted)] text-sm">
          of {selectedLabData.total_reported} benchmarks ({pctUnique}%) are reported by{" "}
          <span className="text-[var(--text)] font-medium">{selectedLabData.lab_name}</span> alone.
        </span>
      </div>

      <div className="divide-y divide-[var(--border)]">
        {categoryRows.map(({ cat, benches }) => {
          const expanded = expandedCats.has(cat);
          const visible = expanded ? benches : benches.slice(0, PREVIEW_N);
          const color = CATEGORY_COLORS[cat] ?? CATEGORY_COLORS.other;
          const label = CATEGORY_LABELS[cat] ?? cat.replace(/_/g, " ");
          const barWidth = (benches.length / maxCount) * 100;
          return (
            <div key={cat} className="py-4 first:pt-0">
              <div className="flex items-center gap-4 mb-2">
                <div className="w-32 shrink-0 text-sm font-medium text-[var(--text)]">
                  {label}
                </div>
                <div className="w-10 text-sm tabular-nums font-semibold text-[var(--text)] text-right">
                  {benches.length}
                </div>
                <div className="flex-1 h-2 bg-[var(--surface-2)] rounded-sm overflow-hidden">
                  <div
                    className="h-full rounded-sm"
                    style={{ width: `${barWidth}%`, background: color }}
                  />
                </div>
              </div>
              <div className="ml-36 flex flex-wrap items-baseline gap-x-2 gap-y-1 text-sm text-[var(--muted)]">
                {visible.map((b, i) => (
                  <span key={b.slug}>
                    <span className="text-[var(--text)]">{b.name}</span>
                    {i < visible.length - 1 ? <span className="text-[var(--border-light)]">·</span> : null}
                  </span>
                ))}
                {benches.length > PREVIEW_N && (
                  <button
                    onClick={() => toggleCat(cat)}
                    className="text-xs text-[var(--accent)] hover:underline ml-1"
                  >
                    {expanded ? "show less" : `+${benches.length - PREVIEW_N} more`}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
