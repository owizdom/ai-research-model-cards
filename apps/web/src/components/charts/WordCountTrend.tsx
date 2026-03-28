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

export function WordCountTrendChart({ data }: { data: WordCountTimelinePoint[] }) {
  const [selectedLab, setSelectedLab] = useState<string | null>(null);

  const { bars, labSlugs, labNames } = useMemo(() => {
    const filtered = selectedLab ? data.filter(d => d.lab_slug === selectedLab) : data;

    const shortenTitle = (title: string) =>
      title
        .replace(" System Card", "")
        .replace(" Model Card", "")
        .replace(" Technical Report", "")
        .replace(" Card", "")
        .replace(" Paper", "")
        .replace(" (GitHub)", "")
        .replace(" Addendum", "")
        .replace(" Overview", "");

    const sorted = [...filtered].sort((a, b) => {
      const labCmp = a.lab_slug.localeCompare(b.lab_slug);
      if (labCmp !== 0) return labCmp;
      return a.version_date.localeCompare(b.version_date);
    });

    const barData = sorted.map(d => ({
      name: shortenTitle(d.document_title),
      wordCount: d.word_count,
      lab: d.lab_slug,
      fullTitle: d.document_title,
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
        <ResponsiveContainer width="100%" height={380}>
          <BarChart data={bars} margin={{ top: 20, right: 20, bottom: 80, left: 20 }}>
            <CartesianGrid stroke="rgba(0,0,0,0.06)" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: "#737373", fontSize: 10 }}
              stroke="rgba(0,0,0,0.1)"
              angle={-40}
              textAnchor="end"
              interval={0}
              height={90}
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
            <Bar dataKey="wordCount" radius={[4, 4, 0, 0]} maxBarSize={50}>
              {bars.map((entry, i) => (
                <Cell key={i} fill={labColors[entry.lab] ?? "#78776E"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="flex flex-wrap items-center gap-4 mt-4 text-xs text-[var(--muted)]">
        {labSlugs.map(slug => (
          <div key={slug} className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded" style={{ background: labColors[slug] ?? "#78776E" }} />
            {labNames[slug] ?? slug}
          </div>
        ))}
      </div>
    </div>
  );
}
