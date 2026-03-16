import { api } from "@/lib/api";
import { DocumentRow } from "@/components/ui/DocumentRow";

export const revalidate = 120;

export default async function DocumentsPage({
  searchParams,
}: {
  searchParams: Promise<{ lab?: string; doc_type?: string; search?: string }>;
}) {
  const params = await searchParams;
  const docs = await api.documents.list({
    ...(params.lab && { lab: params.lab }),
    ...(params.doc_type && { doc_type: params.doc_type }),
    ...(params.search && { search: params.search }),
    limit: 100,
  }).catch(() => []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Policy Documents</h1>
      <div className="divide-y divide-[var(--border)] border border-[var(--border)] rounded-xl overflow-hidden">
        {docs.length === 0 ? (
          <p className="p-6 text-[var(--muted)]">No documents found.</p>
        ) : (
          docs.map((doc) => <DocumentRow key={doc.id} doc={doc} />)
        )}
      </div>
    </div>
  );
}
