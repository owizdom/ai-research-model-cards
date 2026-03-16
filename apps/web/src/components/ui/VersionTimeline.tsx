"use client";
import type { DocumentVersion } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { useState } from "react";

export function VersionTimeline({
  versions,
  docId,
}: {
  versions: DocumentVersion[];
  docId: number;
}) {
  const [selected, setSelected] = useState<number | null>(null);

  return (
    <div className="flex gap-2 flex-wrap">
      {versions.map((v) => (
        <button
          key={v.id}
          onClick={() => setSelected(selected === v.id ? null : v.id)}
          className={`px-3 py-1.5 rounded-lg text-xs border transition-colors ${
            selected === v.id
              ? "border-accent bg-accent/20 text-white"
              : "border-[var(--border)] bg-surface-2 text-[var(--muted)] hover:text-white"
          }`}
        >
          {formatDate(v.version_date)}
          {v.wayback_url && <span className="ml-1 opacity-60">↗</span>}
        </button>
      ))}
    </div>
  );
}
