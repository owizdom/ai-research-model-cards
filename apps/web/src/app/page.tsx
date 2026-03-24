import { api } from "@/lib/api";
import { LabCard } from "@/components/ui/LabCard";
import { MouseGlow } from "@/components/ui/MouseGlow";
import Link from "next/link";

export const revalidate = 300;

export default async function HomePage() {
  const [labs, matrix, timeline, families] = await Promise.all([
    api.labs.list().catch(() => []),
    api.analysis.intersection({ threshold: 0.35 }).catch(() => null),
    api.evals.timeline().catch(() => []),
    api.families.list().catch(() => []),
  ]);

  const totalDocs = labs.reduce((sum, l) => sum + l.document_count, 0);
  const gapCount = matrix?.covered_by_none?.length ?? 0;
  const totalEvals = timeline.reduce((sum, t) => sum + t.eval_count, 0);

  return (
    <div>
      <MouseGlow />
      {/* Hero */}
      <section className="mb-24 pt-4">
        <p className="text-[var(--accent)] text-sm font-medium mb-4 tracking-wide uppercase">Open Research Platform</p>
        <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl font-bold mb-6 leading-[1.1] tracking-tight">
          Model Card Explorer
        </h1>
        <p className="text-[var(--muted)] max-w-2xl text-lg sm:text-xl leading-relaxed mb-10">
          We collect and analyze model cards, safety documentation, and governance frameworks
          from {labs.length} major AI labs. Discover what each lab discloses about safety, evaluations,
          and responsible deployment across {totalDocs} documents.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link href="/analysis" className="px-6 py-3 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:opacity-90 transition-opacity">
            Explore Safety Coverage
          </Link>
          <Link href="/documents" className="px-6 py-3 rounded-lg border border-[var(--border)] text-sm font-medium text-[var(--muted)] hover:text-[var(--text)] hover:border-[var(--border-light)] transition-colors">
            Browse Model Cards
          </Link>
        </div>
      </section>

      {/* Stats row */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-24">
        <div className="p-6 rounded-xl border border-[var(--border)] bg-white shadow-sm">
          <div className="text-3xl font-bold tracking-tight">{labs.length}</div>
          <div className="text-sm text-[var(--muted)] mt-1">AI Labs Tracked</div>
        </div>
        <div className="p-6 rounded-xl border border-[var(--border)] bg-white shadow-sm">
          <div className="text-3xl font-bold tracking-tight">{totalDocs}</div>
          <div className="text-sm text-[var(--muted)] mt-1">Policy Documents</div>
        </div>
        <div className="p-6 rounded-xl border border-[var(--border)] bg-white shadow-sm">
          <div className="text-3xl font-bold tracking-tight">15</div>
          <div className="text-sm text-[var(--muted)] mt-1">Safety Categories</div>
        </div>
        <div className="p-6 rounded-xl border border-[var(--border)] bg-white shadow-sm">
          <div className="text-3xl font-bold tracking-tight">{gapCount}</div>
          <div className="text-sm text-[var(--muted)] mt-1">Uncovered Safety Gaps</div>
        </div>
      </section>

      {/* Key findings preview */}
      <section className="mb-20">
        <h2 className="text-xl font-semibold mb-6">Key Findings</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Safety coverage finding */}
          <Link href="/analysis" className="block p-6 rounded-xl border border-[var(--border)] bg-white shadow-sm hover:shadow-md hover:bg-[var(--surface-1)] transition-colors group">
            <div className="flex items-start justify-between mb-3">
              <h3 className="font-semibold group-hover:text-accent transition-colors">Safety Coverage Gaps</h3>
              <span className="text-xs text-[var(--muted)] bg-[var(--surface-2)] px-2 py-0.5 rounded">Coverage</span>
            </div>
            {gapCount > 0 ? (
              <p className="text-sm text-[var(--muted)] leading-relaxed mb-3">
                {gapCount} critical safety {gapCount === 1 ? "category has" : "categories have"} no
                dedicated policy from any of the {labs.length} labs we track. These include topics
                like bias, misinformation, and mental health.
              </p>
            ) : (
              <p className="text-sm text-[var(--muted)] leading-relaxed mb-3">
                See which safety topics each lab covers in their official policies, and where
                the industry has critical gaps.
              </p>
            )}
            {matrix?.covered_by_none && matrix.covered_by_none.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {matrix.covered_by_none.slice(0, 4).map(slug => (
                  <span key={slug} className="text-xs px-2 py-0.5 rounded bg-red-50 text-red-600 border border-red-200">
                    {matrix.category_names[slug] ?? slug}
                  </span>
                ))}
                {matrix.covered_by_none.length > 4 && (
                  <span className="text-xs px-2 py-0.5 rounded text-[var(--muted)]">
                    +{matrix.covered_by_none.length - 4} more
                  </span>
                )}
              </div>
            )}
          </Link>

          {/* Latest model cards */}
          <Link href="/documents" className="block p-6 rounded-xl border border-[var(--border)] bg-white shadow-sm hover:shadow-md hover:bg-[var(--surface-1)] transition-colors group">
            <div className="flex items-start justify-between mb-3">
              <h3 className="font-semibold group-hover:text-accent transition-colors">Model Cards Library</h3>
              <span className="text-xs text-[var(--muted)] bg-[var(--surface-2)] px-2 py-0.5 rounded">Documents</span>
            </div>
            <p className="text-sm text-[var(--muted)] leading-relaxed mb-3">
              Browse {totalDocs} documents across {labs.length} labs including model cards,
              usage policies, and safety frameworks. Track changes over time with version history
              and Wayback Machine snapshots.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {labs.slice(0, 5).map(lab => (
                <span key={lab.slug} className="text-xs px-2 py-0.5 rounded bg-[var(--surface-2)] text-[var(--muted)]">
                  {lab.name}
                </span>
              ))}
              {labs.length > 5 && (
                <span className="text-xs px-2 py-0.5 rounded text-[var(--muted)]">
                  +{labs.length - 5} more
                </span>
              )}
            </div>
          </Link>
        </div>
      </section>

      {/* Eval & Families row */}
      {(totalEvals > 0 || families.length > 0) && (
        <section className="mb-20">
          <h2 className="text-xl font-semibold mb-6">Eval Intelligence</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Link href="/evals" className="block p-6 rounded-xl border border-[var(--border)] bg-white shadow-sm hover:shadow-md hover:bg-[var(--surface-1)] transition-colors group">
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-semibold group-hover:text-accent transition-colors">Eval Explorer</h3>
                <span className="text-xs text-[var(--muted)] bg-[var(--surface-2)] px-2 py-0.5 rounded">Benchmarks</span>
              </div>
              <p className="text-sm text-[var(--muted)] leading-relaxed">
                {totalEvals > 0
                  ? `${totalEvals} benchmark results extracted from model cards. Track eval disclosure trends across labs.`
                  : "Explore extracted benchmark results from model cards and track disclosure trends."}
              </p>
            </Link>

            <Link href="/families" className="block p-6 rounded-xl border border-[var(--border)] bg-white shadow-sm hover:shadow-md hover:bg-[var(--surface-1)] transition-colors group">
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-semibold group-hover:text-accent transition-colors">Model Families</h3>
                <span className="text-xs text-[var(--muted)] bg-[var(--surface-2)] px-2 py-0.5 rounded">Comparison</span>
              </div>
              <p className="text-sm text-[var(--muted)] leading-relaxed mb-3">
                {families.length > 0
                  ? `Compare evaluations across ${families.length} model families and their generations.`
                  : "Compare evaluations across model generations within each AI lab."}
              </p>
              {families.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {families.slice(0, 5).map(f => (
                    <span key={f.slug} className="text-xs px-2 py-0.5 rounded bg-[var(--surface-2)] text-[var(--muted)]">
                      {f.name}
                    </span>
                  ))}
                </div>
              )}
            </Link>
          </div>
        </section>
      )}

      {/* Labs grid */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Labs We Track</h2>
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
