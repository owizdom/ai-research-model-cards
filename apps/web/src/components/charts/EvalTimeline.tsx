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
  ReferenceLine,
} from "recharts";
import type { PerCardEvalPoint, Lab } from "@/lib/types";

export function EvalTimelineChart({
  data,
  labs,
}: {
  data: PerCardEvalPoint[];
  labs: Lab[];
}) {
  const [selectedLab, setSelectedLab] = useState<string | null>(null);

  // Distinct, muted palette for light backgrounds — each lab is immediately distinguishable
  const chartPalette: Record<string, string> = {
    anthropic: "#D97757",  // terracotta
    openai:    "#2E7D5B",  // forest green
    google:    "#4A7FC1",  // steel blue
    meta:      "#8B6CAF",  // muted purple
    mistral:   "#C17E2B",  // amber
    xai:       "#1A7A6D",  // teal
    cohere:    "#C44343",  // warm red
    amazon:    "#5B8A72",  // sage
    ai21:      "#7A6850",  // warm brown
  };
  const labColors: Record<string, string> = {};
  for (const lab of labs) {
    labColors[lab.slug] = chartPalette[lab.slug] ?? "#78776E";
  }

  const { bars, average, labSlugs } = useMemo(() => {
    const filtered = selectedLab ? data.filter(d => d.lab_slug === selectedLab) : data;

    const sorted = [...filtered].sort((a, b) => {
      const dateCmp = a.version_date.localeCompare(b.version_date);
      return dateCmp !== 0 ? dateCmp : b.eval_count - a.eval_count;
    });

    const shortenTitle = (title: string) =>
      title
        .replace(" System Card", "")
        .replace(" Model Card", "")
        .replace(" Technical Report", "")
        .replace(" Card", "")
        .replace(" Paper", "")
        .replace(" (GitHub)", "")
        .replace(" Addendum", "")
        .replace(" Documentation", "")
        .replace(" Overview", "");

    const barData = sorted.map(d => ({
      name: shortenTitle(d.document_title),
      evalCount: d.eval_count,
      lab: d.lab_slug,
      fullTitle: d.document_title,
    }));

    const avg = filtered.length > 0
      ? Math.round(filtered.reduce((s, d) => s + d.eval_count, 0) / filtered.length * 10) / 10
      : 0;

    return { bars: barData, average: avg, labSlugs: [...new Set(data.map(d => d.lab_slug))].sort() };
  }, [data, selectedLab]);

  if (data.length === 0) {
    return (
      <div className="p-8 text-center text-[var(--muted)] border border-[var(--border)] rounded-xl">
        No eval data yet. Extract evals from model cards to see the chart.
      </div>
    );
  }

  return (
    <div>
      {/* Lab filters */}
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
            <span className="w-2 h-2 rounded-full" style={{ background: labColors[slug] ?? "#D97757" }} />
            {labs.find(l => l.slug === slug)?.name ?? slug}
          </button>
        ))}
      </div>

      {/* Simple vertical bar chart */}
      <div className="border border-[var(--border)] rounded-xl p-4 sm:p-6 bg-white">
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={bars} margin={{ top: 20, right: 20, bottom: 60, left: 10 }}>
            <CartesianGrid stroke="rgba(0,0,0,0.06)" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: "#737373", fontSize: 11 }}
              stroke="rgba(0,0,0,0.1)"
              angle={-35}
              textAnchor="end"
              interval={0}
              height={70}
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
              formatter={(value: number) => [`${value}`, "Evals"]}
              labelFormatter={(label: string) => {
                const item = bars.find(b => b.name === label);
                return item ? `${item.fullTitle} — ${item.lab}` : label;
              }}
            />

            {/* Average line */}
            <ReferenceLine
              y={average}
              stroke="#D97757"
              strokeWidth={2}
              strokeDasharray="8 4"
              label={{
                value: `Avg: ${average}`,
                position: "right",
                fill: "#D97757",
                fontSize: 12,
                fontWeight: 600,
              }}
            />

            <Bar dataKey="evalCount" radius={[4, 4, 0, 0]} maxBarSize={60}>
              {bars.map((entry, i) => (
                <Cell key={i} fill={labColors[entry.lab] ?? "#D97757"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4 mt-4 text-xs text-[var(--muted)]">
        {labSlugs.map(slug => (
          <div key={slug} className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded" style={{ background: labColors[slug] ?? "#D97757" }} />
            {labs.find(l => l.slug === slug)?.name ?? slug}
          </div>
        ))}
        <div className="flex items-center gap-1.5 ml-auto">
          <span className="w-6 border-t-2 border-dashed border-accent inline-block" />
          Average: {average} evals/card
        </div>
      </div>
    </div>
  );
}
