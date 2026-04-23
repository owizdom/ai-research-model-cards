"use client";
import { useState } from "react";
import type { HeatstripSegment } from "@/lib/types";

const CATEGORY_COLORS: Record<string, string> = {
  safety: "#D97757",
  evals: "#4A7FC1",
  risks: "#C44343",
  mitigations: "#2E7D5B",
  deployment: "#C17E2B",
  other: "#B0AFA8",
};

const CATEGORY_LABELS: Record<string, string> = {
  safety: "Safety",
  evals: "Evals",
  risks: "Risks",
  mitigations: "Mitigations",
  deployment: "Deployment",
  other: "Other",
};

export function Heatstrip({ segments }: { segments: HeatstripSegment[] }) {
  const [hovered, setHovered] = useState<HeatstripSegment | null>(null);
  if (segments.length === 0) return null;

  const maxIntensity = Math.max(...segments.map(s => s.intensity), 1);

  // Aggregate: total keyword hits by category for the legend
  const totals = new Map<string, number>();
  for (const s of segments) {
    for (const [cat, n] of Object.entries(s.scores)) {
      totals.set(cat, (totals.get(cat) ?? 0) + n);
    }
  }
  const topCats = Array.from(totals.entries())
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1]);

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs uppercase tracking-wide text-[var(--muted)]">
          Document composition
        </div>
        <div className="text-[11px] text-[var(--muted)]">
          Hover a segment to see topic mix
        </div>
      </div>

      <div className="flex h-5 rounded-md overflow-hidden border border-[var(--border)] bg-[var(--surface-2)]">
        {segments.map(seg => {
          const color = CATEGORY_COLORS[seg.dominant] ?? CATEGORY_COLORS.other;
          const opacity = seg.intensity === 0 ? 0.15 : 0.35 + 0.65 * (seg.intensity / maxIntensity);
          return (
            <div
              key={seg.index}
              className="flex-1 cursor-pointer transition-opacity"
              style={{ background: color, opacity }}
              onMouseEnter={() => setHovered(seg)}
              onMouseLeave={() => setHovered(null)}
              title={`${CATEGORY_LABELS[seg.dominant] ?? seg.dominant}: ${seg.intensity} hits`}
            />
          );
        })}
      </div>

      <div className="flex items-center justify-between mt-1.5 text-[11px] text-[var(--muted)]">
        <span>start</span>
        <span>end of document</span>
      </div>

      {hovered && (
        <div className="mt-3 p-3 rounded-md bg-[var(--surface-2)] text-xs text-[var(--muted)]">
          <span className="font-medium text-[var(--text)]">
            Segment {hovered.index + 1} / {segments.length}:
          </span>{" "}
          {topCategoriesForSeg(hovered)
            .map(([cat, n]) => `${CATEGORY_LABELS[cat] ?? cat} ${n}`)
            .join(" · ") || "no keyword hits"}
        </div>
      )}

      <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-3 text-xs text-[var(--muted)]">
        {topCats.map(([cat, n]) => (
          <div key={cat} className="flex items-center gap-1.5">
            <span
              className="w-2.5 h-2.5 rounded-sm shrink-0"
              style={{ background: CATEGORY_COLORS[cat] ?? CATEGORY_COLORS.other }}
            />
            <span>{CATEGORY_LABELS[cat] ?? cat}</span>
            <span className="tabular-nums">{n}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function topCategoriesForSeg(seg: HeatstripSegment): [string, number][] {
  return Object.entries(seg.scores)
    .filter(([, n]) => n > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4);
}
