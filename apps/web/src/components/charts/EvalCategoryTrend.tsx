"use client";
import { useState, useMemo } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import type { CategoryTimelinePoint } from "@/lib/types";

const labColors: Record<string, string> = {
  anthropic: "#D97757",
  openai: "#2E7D5B",
  google: "#4A7FC1",
  meta: "#8B6CAF",
  xai: "#1A7A6D",
  mistral: "#FF7000",
};

const categoryColors: Record<string, string> = {
  reasoning: "#4A7FC1",
  knowledge: "#2E7D5B",
  coding: "#D97757",
  math: "#8B6CAF",
  safety: "#C44343",
  instruction_following: "#C17E2B",
  multilingual: "#1A7A6D",
  vision: "#5B8A72",
  arena: "#7A6850",
  other: "#B0AFA8",
};

const categoryLabels: Record<string, string> = {
  reasoning: "Reasoning",
  knowledge: "Knowledge",
  coding: "Coding",
  math: "Math",
  safety: "Safety",
  instruction_following: "Instruction Following",
  multilingual: "Multilingual",
  vision: "Vision",
  arena: "Arena",
  other: "Other",
};

// Chronological generation order per lab
const GEN_ORDER: Record<string, number> = {
  anthropic_claude2_card: 1, anthropic_model_card: 2, anthropic_35_addendum: 3,
  anthropic_35h_addendum: 4, anthropic_37_card: 5,
  anthropic_claude4_card: 6, anthropic_opus41_card: 7,
  anthropic_opus45_card: 8, anthropic_sonnet45_card: 9,
  anthropic_haiku45_card: 10, anthropic_sonnet46_card: 11, anthropic_opus46_card: 12,
  openai_gpt4_system_card: 1, openai_gpt4o_system_card: 2, openai_gpt45_system_card: 3,
  openai_o1_system_card: 4, openai_operator_card: 5, openai_o3mini_card: 6,
  openai_o3_system_card: 7, openai_gpt5_system_card: 8,
  openai_gpt51_system_card: 9, openai_gpt52_system_card: 10, openai_gpt53_codex_card: 11,
  google_gemini_report: 1, google_gemini_1_5_report: 2, google_gemini_2_card: 3,
  google_gemini_25_card: 4, google_gemini_25_pro_card: 5, google_gemini_25dt_card: 6,
  google_gemini_3_card: 7, google_gemini_3_pro_card: 8, google_gemini_31_pro_card: 9,
  meta_llama2_card: 1, meta_llama3_model_card: 2, meta_llama31_card: 3,
  meta_llama3_paper: 3, meta_llama32_card: 4, meta_responsible_use: 5,
  meta_llama4_card: 6, meta_llama_guard: 10, meta_llamaguard_card: 11,
  meta_llamaguard3_card: 12,
  xai_grok4_card: 1, xai_grok4_fast_card: 2, xai_grok41_card: 3, xai_grok_docs: 10,
  mistral_7b_model_card: 1, mistral_mixtral_model_card: 2,
};

export function EvalCategoryTrendChart({ data }: { data: CategoryTimelinePoint[] }) {
  const [selectedLab, setSelectedLab] = useState<string | null>(null);

  const { chartData, categories, labSlugs, labNames } = useMemo(() => {
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

    // Pivot: one row per document, one column per category
    const byDoc: Record<string, { name: string; lab: string; slug: string; [cat: string]: string | number }> = {};
    const cats = new Set<string>();
    const names: Record<string, string> = {};

    for (const d of filtered) {
      if (!byDoc[d.document_slug]) {
        byDoc[d.document_slug] = {
          name: shortenTitle(d.document_title),
          lab: d.lab_slug,
          slug: d.document_slug,
        };
      }
      byDoc[d.document_slug][d.benchmark_category] = d.eval_count;
      cats.add(d.benchmark_category);
      names[d.lab_slug] = d.lab_name;
    }

    // Sort chronologically within each lab
    const rows = Object.values(byDoc).sort((a, b) => {
      const labCmp = (a.lab as string).localeCompare(b.lab as string);
      if (labCmp !== 0) return labCmp;
      return (GEN_ORDER[a.slug as string] ?? 99) - (GEN_ORDER[b.slug as string] ?? 99);
    });

    return {
      chartData: rows,
      categories: [...cats].sort(),
      labSlugs: [...new Set(data.map(d => d.lab_slug))].sort(),
      labNames: names,
    };
  }, [data, selectedLab]);

  if (data.length === 0) {
    return (
      <div className="p-8 text-center text-[var(--muted)] border border-[var(--border)] rounded-xl">
        No category data available.
      </div>
    );
  }

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
          <BarChart data={chartData} margin={{ top: 20, right: 20, bottom: 90, left: 20 }}>
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
              allowDecimals={false}
              label={{
                value: "Evals reported",
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
              formatter={(value: number, name: string) => [value, categoryLabels[name] ?? name]}
            />
            <Legend
              wrapperStyle={{ fontSize: "11px", color: "#737373", paddingTop: "8px" }}
              formatter={(value: string) => categoryLabels[value] ?? value}
            />
            {categories.map(cat => (
              <Bar
                key={cat}
                dataKey={cat}
                stackId="a"
                fill={categoryColors[cat] ?? "#B0AFA8"}
                name={cat}
                radius={categories.length > 0 && cat === categories[categories.length - 1] ? [3, 3, 0, 0] : undefined}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
