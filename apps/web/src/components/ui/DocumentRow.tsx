import type { Document } from "@/lib/types";
import Link from "next/link";
import { formatDate } from "@/lib/utils";

export function DocumentRow({ doc }: { doc: Document }) {
  return (
    <Link
      href={`/documents/${doc.id}`}
      className="flex items-center gap-4 px-5 py-4 bg-white hover:bg-[var(--surface-1)] transition-colors group"
    >
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate group-hover:text-accent transition-colors">{doc.title}</p>
        <div className="flex items-center gap-3 mt-1.5">
          <span className="text-xs text-[var(--muted)]">{doc.lab_name}</span>
          <span className="text-xs text-[var(--muted)]">
            {doc.version_count} version{doc.version_count !== 1 ? "s" : ""}
          </span>
          {doc.latest_version_date && (
            <span className="text-xs text-[var(--muted)]">{formatDate(doc.latest_version_date)}</span>
          )}
        </div>
      </div>
      <span className="shrink-0 text-xs px-3 py-1 rounded-full border border-[var(--border)] text-[var(--muted)]">
        {doc.doc_type.replace(/_/g, " ")}
      </span>
    </Link>
  );
}
