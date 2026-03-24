import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { VersionTimeline } from "@/components/ui/VersionTimeline";
import { EvalTable } from "@/components/charts/EvalTable";
import { notFound } from "next/navigation";

export default async function DocumentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const docId = Number(id);
  const [doc, evalsData] = await Promise.all([
    api.documents.get(docId).catch(() => null) as any,
    api.evals.byDocument(docId).catch(() => null),
  ]);
  if (!doc) notFound();

  const versions = doc.versions ?? [];
  const latest = versions[0];
  const evals = evalsData?.evals ?? [];

  return (
    <div className="max-w-4xl">
      <div className="mb-2 text-sm text-[var(--muted)]">
        <a href="/documents" className="hover:text-[var(--text)]">Model Cards</a>
        {" / "}
        <span>{doc.lab?.name ?? doc.lab_name ?? "Unknown"}</span>
      </div>

      <h1 className="text-2xl font-bold font-serif mb-1">{doc.title}</h1>
      <div className="flex gap-3 mb-6 text-sm text-[var(--muted)]">
        <span className="px-2 py-0.5 rounded bg-[var(--surface-2)] font-mono text-xs">{doc.doc_type}</span>
        {latest?.version_date && <span>{formatDate(latest.version_date)}</span>}
        {doc.source_url && (
          <a href={doc.source_url} target="_blank" rel="noopener noreferrer" className="hover:text-[var(--text)] underline">
            Source
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
        <div className="mt-4 p-6 rounded-xl border border-[var(--border)] bg-white shadow-sm">
          <h2 className="text-sm uppercase tracking-wider text-[var(--muted)] mb-4">
            Latest version: {formatDate(latest.version_date)}
            {latest.wayback_url && (
              <a href={latest.wayback_url} target="_blank" rel="noopener noreferrer"
                className="ml-3 text-accent hover:underline normal-case">
                Wayback
              </a>
            )}
          </h2>
          <p className="text-[var(--muted)] text-xs">
            {latest.word_count != null ? `${latest.word_count.toLocaleString()} words` : ""}
          </p>
        </div>
      )}

      {/* Extracted evaluations */}
      {doc.doc_type === "model_card" && (
        <div className="mt-10">
          <h2 className="text-lg font-semibold mb-4">
            Extracted Evaluations
            {evals.length > 0 && (
              <span className="text-sm font-normal text-[var(--muted)] ml-2">({evals.length} results)</span>
            )}
          </h2>
          <EvalTable evals={evals} />
        </div>
      )}
    </div>
  );
}
