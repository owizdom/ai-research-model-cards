import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { VersionTimeline } from "@/components/ui/VersionTimeline";
import { notFound } from "next/navigation";

export default async function DocumentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const doc = await api.documents.get(Number(id)).catch(() => null) as any;
  if (!doc) notFound();

  const versions = doc.versions ?? [];
  const latest = versions[0];

  return (
    <div className="max-w-4xl">
      <div className="mb-2 text-sm text-[var(--muted)]">
        <a href="/documents" className="hover:text-white">Documents</a>
        {" / "}
        <span>{doc.lab?.name ?? doc.lab_name ?? "Unknown"}</span>
      </div>

      <h1 className="text-2xl font-bold mb-1">{doc.title}</h1>
      <div className="flex gap-3 mb-6 text-sm text-[var(--muted)]">
        <span className="px-2 py-0.5 rounded bg-surface-2 font-mono text-xs">{doc.doc_type}</span>
        {latest?.version_date && <span>{formatDate(latest.version_date)}</span>}
        {doc.source_url && (
          <a href={doc.source_url} target="_blank" rel="noopener noreferrer" className="hover:text-white underline">
            Source ↗
          </a>
        )}
      </div>

      {versions.length > 1 && (
        <div className="mb-8">
          <h2 className="text-sm uppercase tracking-wider text-[var(--muted)] mb-3">Version History</h2>
          <VersionTimeline versions={versions} docId={doc.id} />
        </div>
      )}

      {latest && (
        <div className="mt-4 p-6 rounded-xl border border-[var(--border)] bg-surface-1">
          <h2 className="text-sm uppercase tracking-wider text-[var(--muted)] mb-4">
            Latest version: {formatDate(latest.version_date)}
            {latest.wayback_url && (
              <a href={latest.wayback_url} target="_blank" rel="noopener noreferrer"
                className="ml-3 text-accent hover:underline normal-case">
                Wayback ↗
              </a>
            )}
          </h2>
          <p className="text-[var(--muted)] text-xs">
            {latest.word_count != null ? `${latest.word_count.toLocaleString()} words` : ""}
          </p>
        </div>
      )}
    </div>
  );
}
