import { api } from "@/lib/api";
import { GistCard } from "@/components/doc-reader/GistCard";
import { Heatstrip } from "@/components/doc-reader/Heatstrip";
import { formatDate } from "@/lib/utils";
import Link from "next/link";
import { notFound } from "next/navigation";

export const revalidate = 300;

export default async function ComparePage({
  searchParams,
}: {
  searchParams: Promise<{ a?: string; b?: string }>;
}) {
  const params = await searchParams;
  const idA = Number(params.a);
  const idB = Number(params.b);

  if (!idA || !idB) {
    return <ComparePicker />;
  }

  const [docA, docB, contentA, contentB] = await Promise.all([
    api.documents.get(idA).catch(() => null) as any,
    api.documents.get(idB).catch(() => null) as any,
    api.documents.content(idA).catch(() => null),
    api.documents.content(idB).catch(() => null),
  ]);

  if (!docA || !docB) notFound();

  return (
    <div>
      <div className="mb-8">
        <div className="text-sm text-[var(--muted)] mb-2">
          <Link href="/documents" className="hover:text-[var(--text)]">Model Cards</Link>
          {" / "}Compare
        </div>
        <h1 className="font-serif text-3xl font-bold mb-1">Side-by-side</h1>
        <p className="text-[var(--muted)] text-sm">
          Gist fields, composition, and key facts from two documents, aligned.
        </p>
      </div>

      {/* Two-column headers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <CompareColumnHeader doc={docA} content={contentA} />
        <CompareColumnHeader doc={docB} content={contentB} />
      </div>

      {/* Gist comparison — paired rows */}
      <div className="mb-10">
        <h2 className="text-xs uppercase tracking-wide text-[var(--muted)] mb-3">
          60-second brief
        </h2>
        <div className="border border-[var(--border)] rounded-xl bg-white overflow-hidden">
          <GistCompareRow
            label="Overview"
            a={contentA?.gist?.overview}
            b={contentB?.gist?.overview}
          />
          <GistCompareRow
            label="Capability claim"
            a={contentA?.gist?.capability_claim ?? null}
            b={contentB?.gist?.capability_claim ?? null}
          />
          <GistCompareRow
            label="Sharpest risk"
            a={contentA?.gist?.sharpest_risk ?? null}
            b={contentB?.gist?.sharpest_risk ?? null}
          />
          <GistCompareRow
            label="Deployment scope"
            a={contentA?.gist?.deployment_scope ?? null}
            b={contentB?.gist?.deployment_scope ?? null}
          />
        </div>
      </div>

      {/* Heatstrip comparison */}
      <div className="mb-10">
        <h2 className="text-xs uppercase tracking-wide text-[var(--muted)] mb-3">
          Composition
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {contentA && (
            <div className="border border-[var(--border)] rounded-xl bg-white p-6">
              <div className="text-sm font-medium mb-3 truncate">{docA.title}</div>
              <Heatstrip segments={contentA.heatstrip} />
            </div>
          )}
          {contentB && (
            <div className="border border-[var(--border)] rounded-xl bg-white p-6">
              <div className="text-sm font-medium mb-3 truncate">{docB.title}</div>
              <Heatstrip segments={contentB.heatstrip} />
            </div>
          )}
        </div>
      </div>

      {/* Quick facts diff */}
      <div>
        <h2 className="text-xs uppercase tracking-wide text-[var(--muted)] mb-3">
          Stats
        </h2>
        <div className="border border-[var(--border)] rounded-xl bg-white overflow-hidden">
          <StatRow
            label="Word count"
            a={contentA ? contentA.word_count.toLocaleString() : "—"}
            b={contentB ? contentB.word_count.toLocaleString() : "—"}
          />
          <StatRow
            label="Read time"
            a={contentA ? `${contentA.read_minutes} min` : "—"}
            b={contentB ? `${contentB.read_minutes} min` : "—"}
          />
          <StatRow
            label="Sections"
            a={contentA ? String(contentA.outline.length) : "—"}
            b={contentB ? String(contentB.outline.length) : "—"}
          />
          <StatRow
            label="Published"
            a={contentA ? formatDate(contentA.version_date) : "—"}
            b={contentB ? formatDate(contentB.version_date) : "—"}
          />
        </div>
      </div>
    </div>
  );
}

function CompareColumnHeader({ doc, content }: { doc: any; content: any }) {
  return (
    <div className="border border-[var(--border)] rounded-xl bg-white p-5">
      <div className="text-xs text-[var(--muted)] mb-1">
        {doc.lab?.name ?? doc.lab_name ?? "—"}
      </div>
      <Link
        href={`/documents/${doc.id}`}
        className="block font-serif text-lg font-bold leading-tight hover:text-[var(--accent)] transition-colors"
      >
        {doc.title}
      </Link>
      {content && (
        <div className="mt-2 text-xs text-[var(--muted)] flex gap-3">
          <span>{content.word_count.toLocaleString()} words</span>
          <span>{content.read_minutes} min</span>
          <span>{formatDate(content.version_date)}</span>
        </div>
      )}
    </div>
  );
}

function GistCompareRow({
  label, a, b,
}: {
  label: string;
  a: string | null | undefined;
  b: string | null | undefined;
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-[140px_1fr_1fr] border-b border-[var(--border)] last:border-b-0">
      <div className="p-4 text-sm font-semibold bg-[var(--surface-2)]/30">
        {label}
      </div>
      <div className="p-4 text-sm text-[var(--muted)] italic border-r border-[var(--border)] leading-relaxed">
        {a ? `"${a}"` : <span className="not-italic text-[var(--border-light)]">— not detected</span>}
      </div>
      <div className="p-4 text-sm text-[var(--muted)] italic leading-relaxed">
        {b ? `"${b}"` : <span className="not-italic text-[var(--border-light)]">— not detected</span>}
      </div>
    </div>
  );
}

function StatRow({ label, a, b }: { label: string; a: string; b: string }) {
  return (
    <div className="grid grid-cols-[140px_1fr_1fr] border-b border-[var(--border)] last:border-b-0 text-sm">
      <div className="p-3 font-semibold bg-[var(--surface-2)]/30">{label}</div>
      <div className="p-3 tabular-nums border-r border-[var(--border)]">{a}</div>
      <div className="p-3 tabular-nums">{b}</div>
    </div>
  );
}

async function ComparePicker() {
  const docs = await api.documents.list({ limit: 200 }).catch(() => []);
  const modelCards = docs.filter(d => d.doc_type === "model_card");
  return (
    <div>
      <div className="mb-8">
        <div className="text-sm text-[var(--muted)] mb-2">
          <Link href="/documents" className="hover:text-[var(--text)]">Model Cards</Link>
          {" / "}Compare
        </div>
        <h1 className="font-serif text-3xl font-bold mb-1">Compare two model cards</h1>
        <p className="text-[var(--muted)] text-sm">
          Pass <code className="text-xs bg-[var(--surface-2)] px-1 rounded">?a=ID&amp;b=ID</code> to
          this page, or use the &ldquo;Compare to…&rdquo; dropdown on any model card page.
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {modelCards.slice(0, 30).map(doc => (
          <Link
            key={doc.id}
            href={`/documents/${doc.id}`}
            className="block p-4 rounded-xl border border-[var(--border)] bg-white hover:border-[var(--accent)] transition-colors"
          >
            <div className="text-xs text-[var(--muted)] mb-1">{doc.lab_name}</div>
            <div className="text-sm font-medium truncate">{doc.title}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
