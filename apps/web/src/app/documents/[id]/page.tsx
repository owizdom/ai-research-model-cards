import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { VersionTimeline } from "@/components/ui/VersionTimeline";
import { EvalTable } from "@/components/charts/EvalTable";
import { DocumentReader } from "@/components/doc-reader/DocumentReader";
import { GistCard } from "@/components/doc-reader/GistCard";
import { Heatstrip } from "@/components/doc-reader/Heatstrip";
import { notFound } from "next/navigation";

export default async function DocumentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const docId = Number(id);
  const [doc, content, evalsData] = await Promise.all([
    api.documents.get(docId).catch(() => null) as any,
    api.documents.content(docId).catch(() => null),
    api.evals.byDocument(docId).catch(() => null),
  ]);
  if (!doc) notFound();

  const versions = doc.versions ?? [];
  const latest = versions[0];
  const evals = evalsData?.evals ?? [];

  return (
    <div>
      {/* Header strip */}
      <div className="max-w-6xl mb-8">
        <div className="mb-2 text-sm text-[var(--muted)]">
          <a href="/documents" className="hover:text-[var(--text)]">Model Cards</a>
          {" / "}
          <span>{doc.lab?.name ?? doc.lab_name ?? "Unknown"}</span>
        </div>

        <h1 className="text-3xl font-bold font-serif mb-3 leading-tight">{doc.title}</h1>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mb-4 text-sm text-[var(--muted)]">
          <span className="px-2 py-0.5 rounded bg-[var(--surface-2)] font-mono text-xs">
            {doc.doc_type.replace(/_/g, " ")}
          </span>
          {content && (
            <>
              <span>{content.word_count.toLocaleString()} words</span>
              <span>·</span>
              <span>{content.read_minutes} min read</span>
            </>
          )}
          {latest?.version_date && (
            <>
              <span>·</span>
              <span>{formatDate(latest.version_date)}</span>
            </>
          )}
          {doc.source_url && (
            <>
              <span>·</span>
              <a
                href={doc.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[var(--accent)] underline hover:opacity-80"
              >
                Source
              </a>
            </>
          )}
          {latest?.wayback_url && (
            <>
              <span>·</span>
              <a
                href={latest.wayback_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[var(--accent)] underline hover:opacity-80"
              >
                Wayback
              </a>
            </>
          )}
        </div>

        {versions.length > 1 && (
          <div className="mb-6 p-4 rounded-xl border border-[var(--border)] bg-white">
            <div className="text-xs uppercase tracking-wide text-[var(--muted)] mb-2">
              Version History
            </div>
            <VersionTimeline versions={versions} docId={doc.id} />
          </div>
        )}
      </div>

      {/* Phase 2: Gist + Heatstrip above the fold */}
      {content && (
        <div className="max-w-5xl mb-8">
          {content.gist && <GistCard gist={content.gist} />}
          {content.heatstrip.length > 0 && <Heatstrip segments={content.heatstrip} />}
        </div>
      )}

      {/* Document body + sidebar */}
      {content ? (
        <DocumentReader content={content} />
      ) : (
        <div className="p-8 text-center text-[var(--muted)] border border-[var(--border)] rounded-xl bg-white">
          Document content is still being processed.
        </div>
      )}

      {/* Extracted evaluations */}
      {doc.doc_type === "model_card" && evals.length > 0 && (
        <div className="mt-12 pt-8 border-t border-[var(--border)] max-w-5xl">
          <h2 className="text-lg font-semibold mb-4">
            Extracted Evaluations
            <span className="text-sm font-normal text-[var(--muted)] ml-2">
              ({evals.length} results)
            </span>
          </h2>
          <EvalTable evals={evals} />
        </div>
      )}
    </div>
  );
}
