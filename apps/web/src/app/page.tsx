import { api } from "@/lib/api";
import { LabCard } from "@/components/ui/LabCard";
import { MouseGlow } from "@/components/ui/MouseGlow";
import { FragmentationSection } from "@/components/fragmentation/FragmentationSection";
import Link from "next/link";

export const revalidate = 300;

export default async function HomePage() {
  const [labs, timeline, families, fragmentation] = await Promise.all([
    api.labs.list().catch(() => []),
    api.evals.timeline().catch(() => []),
    api.families.list().catch(() => []),
    api.evals.fragmentation().catch(() => null),
  ]);

  const totalDocs = labs.reduce((sum, l) => sum + l.document_count, 0);
  const totalEvals = timeline.reduce((sum, t) => sum + t.eval_count, 0);

  return (
    <div>
      <MouseGlow />
      {/* Fragmentation — the finding, above the fold */}
      {fragmentation ? (
        <FragmentationSection
          data={fragmentation}
          corpusSummary={{
            total_docs: totalDocs,
            total_evals: totalEvals,
            n_labs: labs.length,
          }}
        />
      ) : (
        <section className="mb-24 pt-4">
          <p className="text-[var(--accent)] text-sm font-medium mb-4 tracking-wide uppercase">Model Card Explorer</p>
          <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl font-bold mb-6 leading-[1.1] tracking-tight">
            Benchmark reporting across frontier labs.
          </h1>
          <p className="text-[var(--muted)] max-w-3xl text-lg leading-relaxed">
            Loading fragmentation analysis…
          </p>
        </section>
      )}

      {/* Explore the data */}
      <section className="mb-20">
        <h2 className="text-xl font-semibold mb-6">Explore the data</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link href="/evals" className="block p-6 rounded-xl border border-[var(--border)] bg-white shadow-sm hover:shadow-md hover:bg-[var(--surface-1)] transition-colors group">
            <div className="flex items-start justify-between mb-3">
              <h3 className="font-semibold group-hover:text-accent transition-colors">Eval Explorer</h3>
              <span className="text-xs text-[var(--muted)] bg-[var(--surface-2)] px-2 py-0.5 rounded">Benchmarks</span>
            </div>
            <p className="text-sm text-[var(--muted)] leading-relaxed">
              Browse every benchmark result, filter by lab, search by name.
            </p>
          </Link>

          <Link href="/families" className="block p-6 rounded-xl border border-[var(--border)] bg-white shadow-sm hover:shadow-md hover:bg-[var(--surface-1)] transition-colors group">
            <div className="flex items-start justify-between mb-3">
              <h3 className="font-semibold group-hover:text-accent transition-colors">Model Families</h3>
              <span className="text-xs text-[var(--muted)] bg-[var(--surface-2)] px-2 py-0.5 rounded">Comparison</span>
            </div>
            <p className="text-sm text-[var(--muted)] leading-relaxed">
              Compare generations within a family — {families.length} families tracked.
            </p>
          </Link>

          <Link href="/documents" className="block p-6 rounded-xl border border-[var(--border)] bg-white shadow-sm hover:shadow-md hover:bg-[var(--surface-1)] transition-colors group">
            <div className="flex items-start justify-between mb-3">
              <h3 className="font-semibold group-hover:text-accent transition-colors">Model Cards</h3>
              <span className="text-xs text-[var(--muted)] bg-[var(--surface-2)] px-2 py-0.5 rounded">Documents</span>
            </div>
            <p className="text-sm text-[var(--muted)] leading-relaxed">
              {totalDocs} source documents with version history and snapshots.
            </p>
          </Link>
        </div>
      </section>

      {/* Labs */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Labs</h2>
          <Link href="/documents" className="text-sm text-[var(--muted)] hover:text-[var(--text)] transition-colors">
            View all documents
          </Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {labs.map((lab) => <LabCard key={lab.slug} lab={lab} />)}
        </div>
      </section>
    </div>
  );
}
