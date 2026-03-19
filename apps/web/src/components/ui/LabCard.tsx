import type { Lab } from "@/lib/types";
import Link from "next/link";

export function LabCard({ lab }: { lab: Lab }) {
  const color = lab.color_hex ?? "#7c6af7";
  return (
    <Link
      href={`/labs/${lab.slug}`}
      className="block p-5 rounded-xl border border-[var(--border)] bg-surface-1 hover:bg-surface-2 hover:border-[var(--border-light)] transition-all group"
    >
      <div className="flex items-center gap-3 mb-2">
        <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: color }} />
        <span className="font-semibold group-hover:text-accent transition-colors">{lab.name}</span>
      </div>
      <p className="text-sm text-[var(--muted)]">
        {lab.document_count} document{lab.document_count !== 1 ? "s" : ""} tracked
      </p>
    </Link>
  );
}
