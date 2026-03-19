import { api } from "@/lib/api";
import { LabCard } from "@/components/ui/LabCard";
import Link from "next/link";

export const revalidate = 300;

export default async function HomePage() {
  const [labs, slant, matrix] = await Promise.all([
    api.labs.list().catch(() => []),
    api.analysis.slantSummary().catch(() => null),
    api.analysis.intersection({ threshold: 0.35 }).catch(() => null),
  ]);

  const totalDocs = labs.reduce((sum, l) => sum + l.document_count, 0);
  const modelScores = slant?.model_scores ?? [];
  const gapCount = matrix?.covered_by_none?.length ?? 0;

  return (
    <div>
      {/* Hero */}
      <section className="mb-16">
        <p className="text-accent text-sm font-medium mb-3 tracking-wide uppercase">Open Research Platform</p>
        <h1 className="text-4xl sm:text-5xl font-bold mb-4 leading-tight tracking-tight">
          AI Policy Intelligence
        </h1>
        <p className="text-[var(--muted)] max-w-2xl text-lg leading-relaxed mb-8">
          We track what AI companies promise in their safety policies, then test whether
          their models follow through. Covering {labs.length} labs, {totalDocs} documents, and
          25 political bias probes.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link href="/analysis" className="px-5 py-2.5 rounded-lg bg-accent text-white text-sm font-medium hover:opacity-90 transition-opacity">
            Explore Safety Coverage
          </Link>
          <Link href="/probes" className="px-5 py-2.5 rounded-lg border border-[var(--border)] text-sm font-medium text-[var(--muted)] hover:text-white hover:border-[var(--border-light)] transition-colors">
            View Bias Results
          </Link>
        </div>
      </section>

      {/* Stats row */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-16">
        <div className="p-5 rounded-xl border border-[var(--border)] bg-surface-1">
          <div className="text-3xl font-bold tracking-tight">{labs.length}</div>
          <div className="text-sm text-[var(--muted)] mt-1">AI Labs Tracked</div>
        </div>
        <div className="p-5 rounded-xl border border-[var(--border)] bg-surface-1">
          <div className="text-3xl font-bold tracking-tight">{totalDocs}</div>
          <div className="text-sm text-[var(--muted)] mt-1">Policy Documents</div>
        </div>
        <div className="p-5 rounded-xl border border-[var(--border)] bg-surface-1">
          <div className="text-3xl font-bold tracking-tight">15</div>
          <div className="text-sm text-[var(--muted)] mt-1">Safety Categories</div>
        </div>
        <div className="p-5 rounded-xl border border-[var(--border)] bg-surface-1">
          <div className="text-3xl font-bold tracking-tight">{gapCount}</div>
          <div className="text-sm text-[var(--muted)] mt-1">Uncovered Safety Gaps</div>
        </div>
      </section>

      {/* Key findings preview */}
      <section className="mb-16">
        <h2 className="text-xl font-semibold mb-6">Key Findings</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Safety coverage finding */}
          <Link href="/analysis" className="block p-6 rounded-xl border border-[var(--border)] bg-surface-1 hover:bg-surface-2 transition-colors group">
            <div className="flex items-start justify-between mb-3">
              <h3 className="font-semibold group-hover:text-accent transition-colors">Safety Coverage Gaps</h3>
              <span className="text-xs text-[var(--muted)] bg-surface-3 px-2 py-0.5 rounded">Coverage</span>
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
                  <span key={slug} className="text-xs px-2 py-0.5 rounded bg-red-950/40 text-red-400 border border-red-900/30">
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

          {/* Bias finding */}
          <Link href="/probes" className="block p-6 rounded-xl border border-[var(--border)] bg-surface-1 hover:bg-surface-2 transition-colors group">
            <div className="flex items-start justify-between mb-3">
              <h3 className="font-semibold group-hover:text-accent transition-colors">Model Bias Results</h3>
              <span className="text-xs text-[var(--muted)] bg-surface-3 px-2 py-0.5 rounded">Bias</span>
            </div>
            {modelScores.length > 0 ? (
              <>
                <p className="text-sm text-[var(--muted)] leading-relaxed mb-3">
                  {modelScores.length} models tested across 25 political questions.
                  All models score near zero overall, but individual topics reveal significant asymmetries.
                </p>
                <div className="space-y-2">
                  {modelScores.slice(0, 3).map(m => (
                    <div key={m.model_slug} className="flex items-center gap-3">
                      <span className="text-xs text-[var(--muted)] w-28 truncate font-mono">{m.model_slug}</span>
                      <div className="flex-1 h-1.5 rounded-full bg-surface-3 overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${Math.min(Math.abs(m.mean_composite_slant) * 500 + 2, 100)}%`,
                            marginLeft: m.mean_composite_slant >= 0 ? "50%" : undefined,
                            marginRight: m.mean_composite_slant < 0 ? "50%" : undefined,
                            background: m.mean_composite_slant > 0.3 ? "#3b82f6" : m.mean_composite_slant < -0.3 ? "#ef4444" : "#6b7280",
                          }}
                        />
                      </div>
                      <span className="text-xs font-mono w-14 text-right" style={{
                        color: m.mean_composite_slant > 0.3 ? "#3b82f6" : m.mean_composite_slant < -0.3 ? "#ef4444" : "#6b7280"
                      }}>
                        {m.mean_composite_slant >= 0 ? "+" : ""}{m.mean_composite_slant.toFixed(3)}
                      </span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="text-sm text-[var(--muted)] leading-relaxed">
                We ask AI models the same politically sensitive questions and measure
                if they lean left, right, or stay neutral.
              </p>
            )}
          </Link>
        </div>
      </section>

      {/* Labs grid */}
      <section>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold">Labs We Track</h2>
          <Link href="/documents" className="text-sm text-[var(--muted)] hover:text-white transition-colors">
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
