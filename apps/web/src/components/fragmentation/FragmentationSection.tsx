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

  const current = view === "raw" ? data.raw : data.families;
  const otherView = view === "raw" ? data.families : data.raw;
  const otherLabel = view === "raw" ? "families" : "raw names";

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
      <SelectionPatternWidget byLab={data.by_lab} />
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

// Palette tuned to the site's warm/muted theme (terracotta accent + earthy greens).
const CATEGORY_COLORS: Record<string, string> = {
  safety: "#D97757",              // terracotta — the site's primary accent
  agentic: "#2E7D5B",             // forest green
  coding: "#4A7FC1",              // steel blue
  math: "#8B6CAF",                // muted purple
  reasoning: "#1A7A6D",           // teal
  knowledge: "#C17E2B",           // amber
  multimodal: "#5B8A72",          // sage
  multilingual: "#7A6850",        // warm taupe
  long_context: "#426888",        // deep blue
  instruction_following: "#A8446B", // mauve
  arena: "#9B7B3A",               // ochre
  medical: "#6B4E71",             // plum
  vision: "#5B8A72",
  other: "#B0AFA8",               // neutral
};

function SelectionPatternWidget({ byLab }: { byLab: LabUniqueness[] }) {
  // Sort labs by count (largest first) to make the rank order obvious
  const labs = [...byLab].sort((a, b) => b.only_them_count - a.only_them_count);
  const maxCount = Math.max(...labs.map(l => l.only_them_count), 1);

  // Build (lab → ordered [category, count] list) with categories sorted by count desc
  const labRows = labs.map(lab => {
    const catCounts = new Map<string, number>();
    for (const b of lab.only_them) {
      const cat = b.category || "other";
      catCounts.set(cat, (catCounts.get(cat) ?? 0) + 1);
    }
    const segments = Array.from(catCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([cat, count]) => ({ cat, count }));
    return { lab, segments };
  });

  // Global category ordering for the shared legend (sorted by total volume across all labs)
  const globalCatTotals = new Map<string, number>();
  for (const { segments } of labRows) {
    for (const s of segments) {
      globalCatTotals.set(s.cat, (globalCatTotals.get(s.cat) ?? 0) + s.count);
    }
  }
  const legendCats = Array.from(globalCatTotals.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([cat]) => cat);

  return (
    <div className="border border-[var(--border)] rounded-xl bg-white p-6 sm:p-8">
      <div className="mb-6">
        <h3 className="font-semibold text-base mb-1">What each lab uniquely emphasizes</h3>
        <p className="text-sm text-[var(--muted)]">
          Benchmarks reported by only one lab, grouped by type. Bar length shows total count;
          segment colors show the category mix.
        </p>
      </div>

      {/* Shared legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 mb-6 text-xs text-[var(--muted)]">
        {legendCats.map(cat => (
          <div key={cat} className="flex items-center gap-1.5">
            <span
              className="w-2.5 h-2.5 rounded-sm shrink-0"
              style={{ background: CATEGORY_COLORS[cat] ?? CATEGORY_COLORS.other }}
            />
            <span>{CATEGORY_LABELS[cat] ?? cat.replace(/_/g, " ")}</span>
          </div>
        ))}
      </div>

      {/* Small multiples: one row per lab */}
      <div className="space-y-3">
        {labRows.map(({ lab, segments }) => {
          const widthPct = (lab.only_them_count / maxCount) * 100;
          const topCat = segments[0];
          const topLabel = topCat
            ? `${CATEGORY_LABELS[topCat.cat] ?? topCat.cat} ${Math.round((topCat.count / lab.only_them_count) * 100)}%`
            : "";
          return (
            <div key={lab.lab_slug} className="flex items-center gap-3 text-sm">
              <div className="w-32 shrink-0 font-medium text-[var(--text)] truncate">
                {lab.lab_name}
              </div>
              <div className="w-10 text-right tabular-nums text-[var(--muted)] shrink-0">
                {lab.only_them_count}
              </div>
              <div className="flex-1 h-5 relative">
                {/* Track background */}
                <div className="absolute inset-0 bg-[var(--surface-2)] rounded-sm" />
                {/* The stacked bar, width-scaled to maxCount so you see size AND mix */}
                <div
                  className="absolute left-0 top-0 bottom-0 flex rounded-sm overflow-hidden"
                  style={{ width: `${widthPct}%` }}
                >
                  {segments.map(({ cat, count }) => {
                    const segPct = (count / lab.only_them_count) * 100;
                    const color = CATEGORY_COLORS[cat] ?? CATEGORY_COLORS.other;
                    const label = CATEGORY_LABELS[cat] ?? cat;
                    return (
                      <div
                        key={cat}
                        style={{ width: `${segPct}%`, background: color }}
                        title={`${label}: ${count}`}
                      />
                    );
                  })}
                </div>
              </div>
              <div className="w-40 shrink-0 text-xs text-[var(--muted)] truncate">
                {topLabel}
              </div>
            </div>
          );
        })}
      </div>

      <p className="text-xs text-[var(--muted)] mt-6 leading-relaxed">
        Anthropic and OpenAI concentrate their unique benchmarks on safety; Google spreads across
        multimodal and multilingual; Mistral reports only human-preference comparisons. No lab is
        grading itself on a scoreboard another lab uses.
      </p>
    </div>
  );
}
