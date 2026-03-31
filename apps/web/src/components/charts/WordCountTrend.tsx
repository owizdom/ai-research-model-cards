"use client";
import { useState, useMemo } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from "recharts";
import type { WordCountTimelinePoint } from "@/lib/types";

const labColors: Record<string, string> = {
  anthropic: "#D97757",
  openai: "#2E7D5B",
  google: "#4A7FC1",
  meta: "#8B6CAF",
  mistral: "#C17E2B",
  xai: "#1A7A6D",
  cohere: "#C44343",
  amazon: "#5B8A72",
  ai21: "#7A6850",
};

// Chronological generation order per lab (earlier models first)
const GEN_ORDER: Record<string, number> = {
  anthropic_claude2_card: 1, anthropic_model_card: 2, anthropic_35_addendum: 3,
  anthropic_claude4_card: 4, anthropic_opus45_card: 5, anthropic_sonnet45_card: 6,
  anthropic_haiku45_card: 7,
  openai_gpt4_system_card: 1, openai_gpt4o_system_card: 2, openai_gpt45_system_card: 3,
  openai_gpt5_system_card: 4, openai_o1_system_card: 5, openai_o3_system_card: 6,
  google_gemini_report: 1, google_gemini_1_5_report: 2, google_gemini_2_card: 3,
  google_gemini_25_card: 4,
  meta_llama2_card: 1, meta_llama3_model_card: 2, meta_llama31_card: 3,
  meta_llama3_paper: 3, meta_llama32_card: 4, meta_responsible_use: 5,
  meta_llama4_card: 6, meta_llama_guard: 10, meta_llamaguard_card: 11,
  meta_llamaguard3_card: 12,
  xai_grok4_card: 1, xai_grok_docs: 2,
  mistral_7b_model_card: 1, mistral_mixtral_model_card: 2,
  cohere_command_r_card: 1, ai21_jamba_card: 1, amazon_bedrock_docs: 1,
};

export function WordCountTrendChart({ data }: { data: WordCountTimelinePoint[] }) {
  const [selectedLab, setSelectedLab] = useState<string | null>(null);

  const { bars, labSlugs, labNames } = useMemo(() => {
    const filtered = selectedLab ? data.filter(d => d.lab_slug === selectedLab) : data;

    const shortenTitle = (title: string) =>
      (title ?? "")
        .replace(" System Card", "")
        .replace(" Model Card", "")
        .replace(" Technical Report", "")
        .replace(" Card", "")
        .replace(" Paper", "")
        .replace(" (GitHub)", "")
        .replace(" Addendum", "")
        .replace(" Overview", "")
        .replace(" Documentation", "");

    // Sort by lab, then chronologically within each lab
    const sorted = [...filtered].sort((a, b) => {
      const labCmp = a.lab_slug.localeCompare(b.lab_slug);
      if (labCmp !== 0) return labCmp;
      return (GEN_ORDER[a.document_slug] ?? 99) - (GEN_ORDER[b.document_slug] ?? 99);
    });

    const barData = sorted.map(d => ({
      name: shortenTitle(d.document_title),
      wordCount: d.word_count,
      lab: d.lab_slug,
      fullTitle: d.document_title,
      slug: d.document_slug,
    }));

    const names: Record<string, string> = {};
    for (const d of data) names[d.lab_slug] = d.lab_name;

    return {
      bars: barData,
      labSlugs: [...new Set(data.map(d => d.lab_slug))].sort(),
      labNames: names,
    };
  }, [data, selectedLab]);

  if (data.length === 0) {
    return (
      <div className="p-8 text-center text-[var(--muted)] border border-[var(--border)] rounded-xl">
        No word count data available.
      </div>
    );
  }

  // Build trend line data: for each bar position, store wordCount keyed by lab
  const trendData = useMemo(() => {
    return bars.map((b, i) => ({ idx: i, [b.lab]: b.wordCount }));
  }, [bars]);

  // Get unique labs in the current view for trend lines
  const visibleLabs = useMemo(() => [...new Set(bars.map(b => b.lab))], [bars]);

  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-6">
        <button
          onClick={() => setSelectedLab(null)}
          className={`text-xs px-3 py-1.5 rounded-full transition-colors ${
            !selectedLab ? "bg-accent text-white" : "bg-[var(--surface-2)] text-[var(--muted)] hover:text-[var(--text)]"
          }`}
        >
          All Labs
        </button>
        {labSlugs.map(slug => (
          <button
            key={slug}
            onClick={() => setSelectedLab(slug === selectedLab ? null : slug)}
            className={`text-xs px-3 py-1.5 rounded-full flex items-center gap-1.5 transition-colors ${
              selectedLab === slug ? "bg-accent text-white" : "bg-[var(--surface-2)] text-[var(--muted)] hover:text-[var(--text)]"
            }`}
          >
            <span className="w-2 h-2 rounded-full" style={{ background: labColors[slug] ?? "#78776E" }} />
            {labNames[slug] ?? slug}
          </button>
        ))}
      </div>

      <div className="border border-[var(--border)] rounded-xl p-4 sm:p-6 bg-white">
        <ResponsiveContainer width="100%" height={400}>
          <ComposedChart data={bars} margin={{ top: 20, right: 20, bottom: 90, left: 20 }}>
            <CartesianGrid stroke="rgba(0,0,0,0.06)" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: "#737373", fontSize: 10 }}
              stroke="rgba(0,0,0,0.1)"
              angle={-45}
              textAnchor="end"
              interval={0}
              height={100}
            />
            <YAxis
              tick={{ fill: "#737373", fontSize: 11 }}
              stroke="rgba(0,0,0,0.1)"
              tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)}
              label={{
                value: "Word count",
                angle: -90,
                position: "insideLeft",
                offset: 5,
                style: { fill: "#737373", fontSize: 12 },
              }}
            />
            <Tooltip
              contentStyle={{
                background: "#FFFFFF",
                border: "1px solid #E5E5E5",
                borderRadius: "8px",
                fontSize: "13px",
                color: "#171717",
              }}
              cursor={{ fill: "rgba(0,0,0,0.03)" }}
              formatter={(value: number) => [`${value.toLocaleString()} words`, "Length"]}
              labelFormatter={(label: string) => {
                const item = bars.find(b => b.name === label);
                return item ? `${item.fullTitle} (${labNames[item.lab] ?? item.lab})` : label;
              }}
            />
            <Bar dataKey="wordCount" radius={[4, 4, 0, 0]} maxBarSize={45}>
              {bars.map((entry, i) => (
                <Cell key={i} fill={labColors[entry.lab] ?? "#78776E"} />
              ))}
            </Bar>
            {/* Trend line when viewing a single lab */}
            {selectedLab && (
              <Line
                dataKey="wordCount"
                stroke={labColors[selectedLab] ?? "#78776E"}
                strokeWidth={2.5}
                strokeDasharray="6 3"
                dot={false}
                type="monotone"
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="flex flex-wrap items-center gap-4 mt-4 text-xs text-[var(--muted)]">
        {labSlugs.map(slug => (
          <div key={slug} className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded" style={{ background: labColors[slug] ?? "#78776E" }} />
            {labNames[slug] ?? slug}
          </div>
        ))}
        {selectedLab && (
          <div className="flex items-center gap-1.5 ml-auto">
            <span className="w-6 border-t-2 border-dashed inline-block" style={{ borderColor: labColors[selectedLab] }} />
            Trend
          </div>
        )}
      </div>
    </div>
  );
}
