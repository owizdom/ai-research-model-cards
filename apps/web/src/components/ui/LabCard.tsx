import type { Lab } from "@/lib/types";
import Link from "next/link";

export function LabCard({ lab }: { lab: Lab }) {
  const color = lab.color_hex ?? "#7c6af7";
  return (
    <Link
      href={`/labs/${lab.slug}`}
      className="block p-5 rounded-xl border border-[var(--border)] bg-surface-1 hover:bg-surface-2 transition-colors"
    >
      <div className="flex items-center gap-3 mb-3">
        <div className="w-3 h-3 rounded-full" style={{ background: color }} />
        <span className="font-semibold">{lab.name}</span>
      </div>
      <p className="text-sm text-[var(--muted)]">
        {lab.document_count} document{lab.document_count !== 1 ? "s" : ""}
      </p>
    </Link>
  );
}
