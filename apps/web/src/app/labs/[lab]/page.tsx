import { api } from "@/lib/api";
import { DocumentRow } from "@/components/ui/DocumentRow";
import { notFound } from "next/navigation";

export const revalidate = 120;

export default async function LabPage({ params }: { params: Promise<{ lab: string }> }) {
  const { lab: slug } = await params;
  const lab = await api.labs.get(slug).catch(() => null) as any;
  if (!lab) notFound();

  const docs = lab.documents ?? [];
  const color = lab.color_hex ?? "#D97757";

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <div className="w-4 h-4 rounded-full" style={{ background: color }} />
        <h1 className="text-2xl font-bold font-serif">{lab.name}</h1>
        {lab.website && (
          <a href={lab.website} target="_blank" rel="noopener noreferrer"
            className="text-sm text-[var(--muted)] hover:text-[var(--text)] underline">
            {lab.website.replace(/^https?:\/\//, "")} ↗
          </a>
        )}
      </div>

      <h2 className="text-xs uppercase tracking-wider text-[var(--muted)] mb-3">
        {docs.length} tracked document{docs.length !== 1 ? "s" : ""}
      </h2>
      <div className="divide-y divide-[var(--border)] border border-[var(--border)] rounded-xl overflow-hidden">
        {docs.length === 0
          ? <p className="p-6 text-[var(--muted)]">No documents collected yet.</p>
          : docs.map((doc: any) => (
              <a key={doc.id} href={`/documents/${doc.id}`}
                className="flex items-center gap-4 px-5 py-4 bg-white shadow-sm hover:shadow-md hover:bg-[var(--surface-1)] transition-colors">
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{doc.title}</p>
                </div>
                <span className="shrink-0 text-xs px-2 py-0.5 rounded bg-[var(--surface-2)] font-mono text-[var(--muted)]">
                  {doc.doc_type}
                </span>
              </a>
            ))
        }
      </div>
    </div>
  );
}
