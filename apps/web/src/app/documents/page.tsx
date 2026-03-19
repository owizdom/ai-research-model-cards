import { api } from "@/lib/api";
import { DocumentRow } from "@/components/ui/DocumentRow";
import { DocumentFilters } from "@/components/ui/DocumentFilters";

export const revalidate = 120;

export default async function DocumentsPage({
  searchParams,
}: {
  searchParams: Promise<{ lab?: string; doc_type?: string; search?: string }>;
}) {
  const params = await searchParams;
  const [docs, labs] = await Promise.all([
    api.documents.list({
      ...(params.lab && { lab: params.lab }),
      ...(params.doc_type && { doc_type: params.doc_type }),
      ...(params.search && { search: params.search }),
      limit: 100,
    }).catch(() => []),
    api.labs.list().catch(() => []),
  ]);

  const labSlugs = [...new Set(labs.map(l => l.slug))].sort();
  const docTypes = [...new Set(docs.map(d => d.doc_type))].sort();

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-2">Policy Documents</h1>
        <p className="text-sm text-[var(--muted)]">
          {docs.length} documents from {labs.length} AI labs. Filter by lab, type, or search by keyword.
        </p>
      </div>

      <DocumentFilters
        labs={labSlugs}
        docTypes={docTypes}
        currentLab={params.lab}
        currentType={params.doc_type}
        currentSearch={params.search}
      />

      <div className="divide-y divide-[var(--border)] border border-[var(--border)] rounded-xl overflow-hidden">
        {docs.length === 0 ? (
          <div className="p-8 text-center text-[var(--muted)]">
            <p className="mb-1">No documents match your filters.</p>
            <p className="text-xs">
              <a href="/documents" className="text-accent hover:underline">Clear all filters</a>
            </p>
          </div>
        ) : (
          docs.map((doc) => <DocumentRow key={doc.id} doc={doc} />)
        )}
      </div>
    </div>
  );
}
