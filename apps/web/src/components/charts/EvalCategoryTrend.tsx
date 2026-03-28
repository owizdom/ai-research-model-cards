"use client";
import { useMemo } from "react";
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
  other: "#A0A0A0",
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

export function EvalCategoryTrendChart({ data }: { data: CategoryTimelinePoint[] }) {
  const { chartData, categories, labNames } = useMemo(() => {
    // Pivot: one row per lab, one column per category
    const byLab: Record<string, Record<string, number>> = {};
    const names: Record<string, string> = {};
    const cats = new Set<string>();

    for (const d of data) {
      if (!byLab[d.lab_slug]) byLab[d.lab_slug] = {};
      byLab[d.lab_slug][d.benchmark_category] = d.eval_count;
      names[d.lab_slug] = d.lab_name;
      cats.add(d.benchmark_category);
    }

    const rows = Object.entries(byLab)
      .map(([slug, counts]) => ({ lab: names[slug] ?? slug, ...counts }))
      .sort((a, b) => {
        const totalA = Object.values(a).reduce((s, v) => s + (typeof v === "number" ? v : 0), 0);
        const totalB = Object.values(b).reduce((s, v) => s + (typeof v === "number" ? v : 0), 0);
        return totalB - totalA;
      });

    return {
      chartData: rows,
      categories: [...cats].sort(),
      labNames: names,
    };
  }, [data]);

  if (data.length === 0) {
    return (
      <div className="p-8 text-center text-[var(--muted)] border border-[var(--border)] rounded-xl">
        No category data available.
      </div>
    );
  }

  return (
    <div>
      <div className="border border-[var(--border)] rounded-xl p-4 sm:p-6 bg-white">
        <ResponsiveContainer width="100%" height={380}>
          <BarChart data={chartData} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <CartesianGrid stroke="rgba(0,0,0,0.06)" vertical={false} />
            <XAxis
              dataKey="lab"
              tick={{ fill: "#737373", fontSize: 12 }}
              stroke="rgba(0,0,0,0.1)"
            />
            <YAxis
              tick={{ fill: "#737373", fontSize: 11 }}
              stroke="rgba(0,0,0,0.1)"
              allowDecimals={false}
              label={{
                value: "Eval count",
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
            />
            <Legend
              wrapperStyle={{ fontSize: "11px", color: "#737373" }}
              formatter={(value: string) => categoryLabels[value] ?? value}
            />
            {categories.map(cat => (
              <Bar
                key={cat}
                dataKey={cat}
                stackId="a"
                fill={categoryColors[cat] ?? "#A0A0A0"}
                name={cat}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
