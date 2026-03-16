import type { Document } from "@/lib/types";
import Link from "next/link";
import { formatDate } from "@/lib/utils";

export function DocumentRow({ doc }: { doc: Document }) {
  return (
    <Link
      href={`/documents/${doc.id}`}
      className="flex items-center gap-4 px-5 py-4 bg-surface-1 hover:bg-surface-2 transition-colors"
    >
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{doc.title}</p>
        <p className="text-sm text-[var(--muted)]">
          {doc.lab_name} · {doc.version_count} version{doc.version_count !== 1 ? "s" : ""}
          {doc.latest_version_date ? ` · ${formatDate(doc.latest_version_date)}` : ""}
        </p>
      </div>
      <span className="shrink-0 text-xs px-2 py-0.5 rounded bg-surface-3 font-mono text-[var(--muted)]">
        {doc.doc_type}
      </span>
    </Link>
  );
}
