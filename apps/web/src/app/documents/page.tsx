import { api } from "@/lib/api";
import { DocumentRow } from "@/components/ui/DocumentRow";
import { DocumentFilters } from "@/components/ui/DocumentFilters";
import Link from "next/link";

export const revalidate = 120;

const PAGE_SIZE = 12;

export default async function DocumentsPage({
  searchParams,
}: {
  searchParams: Promise<{ lab?: string; doc_type?: string; search?: string; page?: string }>;
}) {
  const params = await searchParams;
  const currentPage = Math.max(1, parseInt(params.page ?? "1", 10) || 1);
  const offset = (currentPage - 1) * PAGE_SIZE;

  const [docs, labs] = await Promise.all([
    api.documents.list({
      ...(params.lab && { lab: params.lab }),
      ...(params.doc_type && { doc_type: params.doc_type }),
      ...(params.search && { search: params.search }),
      limit: PAGE_SIZE + 1, // fetch one extra to know if there's a next page
      offset,
    }).catch(() => []),
    api.labs.list().catch(() => []),
  ]);

  const hasNextPage = docs.length > PAGE_SIZE;
  const displayDocs = docs.slice(0, PAGE_SIZE);

  const labOptions = labs
    .map(l => ({ slug: l.slug, name: l.name }))
    .sort((a, b) => a.name.localeCompare(b.name));
  const docTypes = ["model_card", "usage_policy", "constitution"].sort();

  // Build pagination URLs preserving filters
  const buildPageUrl = (page: number) => {
    const p = new URLSearchParams();
    if (params.lab) p.set("lab", params.lab);
    if (params.doc_type) p.set("doc_type", params.doc_type);
    if (params.search) p.set("search", params.search);
    if (page > 1) p.set("page", String(page));
    const qs = p.toString();
    return `/documents${qs ? `?${qs}` : ""}`;
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold font-serif mb-2">Model Cards & Safety Documents</h1>
        <p className="text-sm text-[var(--muted)]">
          Browse documents from {labs.length} AI labs. Filter by lab, type, or search by keyword.
        </p>
      </div>

      <DocumentFilters
        labs={labOptions}
        docTypes={docTypes}
        currentLab={params.lab}
        currentType={params.doc_type}
        currentSearch={params.search}
      />

      {displayDocs.length === 0 ? (
        <div className="p-12 text-center text-[var(--muted)] border border-[var(--border)] rounded-2xl">
          <p className="mb-2">No documents match your filters.</p>
          <a href="/documents" className="text-sm text-accent hover:underline">Clear all filters</a>
        </div>
      ) : (
        <>
          <div className="divide-y divide-[var(--border)] border border-[var(--border)] rounded-2xl overflow-hidden">
            {displayDocs.map((doc) => <DocumentRow key={doc.id} doc={doc} />)}
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between mt-6">
            <div className="text-sm text-[var(--muted)]">
              Page {currentPage}
            </div>
            <div className="flex items-center gap-2">
              {currentPage > 1 && (
                <Link
                  href={buildPageUrl(currentPage - 1)}
                  className="px-4 py-2 rounded-lg border border-[var(--border)] text-sm font-medium text-[var(--muted)] hover:text-[var(--text)] hover:border-[var(--border-light)] transition-colors"
                >
                  Previous
                </Link>
              )}
              {hasNextPage && (
                <Link
                  href={buildPageUrl(currentPage + 1)}
                  className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:opacity-90 transition-opacity"
                >
                  Next
                </Link>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
