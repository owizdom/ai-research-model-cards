import { api } from "@/lib/api";
import { IntersectionExplorer } from "@/components/charts/IntersectionExplorer";

export const revalidate = 300;

export default async function AnalysisPage() {
  const [matrix, evalDepth] = await Promise.all([
    api.analysis.intersection({ threshold: 0.35 }).catch(() => null),
    api.evals.depth().catch(() => ({})),
  ]);

  return (
    <div>
      <h1 className="text-2xl font-bold font-serif mb-2">Safety Coverage</h1>
      <p className="text-[var(--muted)] mb-4 text-sm max-w-2xl leading-relaxed">
        We checked which safety topics each AI lab writes about in their official policies.
        This table shows how well each lab covers 15 important safety categories,
        from child safety to political neutrality.
      </p>

      {/* How to read this */}
      <div className="mb-8 p-4 rounded-xl border border-[var(--border)] bg-white shadow-sm">
        <h3 className="text-sm font-semibold mb-2">How to read this</h3>
        <ul className="text-xs text-[var(--muted)] space-y-1.5 leading-relaxed">
          <li><span className="inline-flex w-5 h-5 items-center justify-center rounded bg-data text-white text-[10px] font-bold align-middle mr-1.5">A</span><strong className="text-[var(--text)]">Strong</strong> — The lab has detailed, dedicated policy on this topic</li>
          <li><span className="inline-flex w-5 h-5 items-center justify-center rounded bg-data-moderate text-[10px] font-bold align-middle mr-1.5">B</span><strong className="text-[var(--text)]">Moderate</strong> — The lab addresses this topic meaningfully</li>
          <li><span className="inline-flex w-5 h-5 items-center justify-center rounded bg-data-weak text-[10px] font-bold align-middle mr-1.5">C</span><strong className="text-[var(--text)]">Weak</strong> — Brief mention, but not a focused policy</li>
          <li><span className="inline-flex w-5 h-5 items-center justify-center rounded bg-data-missing text-[10px] font-bold align-middle mr-1.5">—</span><strong className="text-[var(--text)]">Not covered</strong> — No meaningful coverage found in their public documents</li>
        </ul>
        <p className="text-[10px] text-[var(--muted)] mt-2 italic">Hover any cell for the exact similarity score.</p>
      </div>

      {matrix ? (
        <IntersectionExplorer matrix={matrix} evalDepth={evalDepth} />
      ) : (
        <p className="text-[var(--muted)]">No data yet. Run a collection first.</p>
      )}

      {/* Export */}
      <div className="flex gap-3 mt-8">
        <a
          href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/export/taxonomy-coverage.csv`}
          className="px-4 py-2 rounded-lg border border-[var(--border)] text-xs text-[var(--muted)] hover:text-[var(--text)] hover:border-[var(--muted)] transition-colors"
          download
        >
          Export coverage data (CSV)
        </a>
        <a
          href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/export/benchmark-coverage.csv`}
          className="px-4 py-2 rounded-lg border border-[var(--border)] text-xs text-[var(--muted)] hover:text-[var(--text)] hover:border-[var(--muted)] transition-colors"
          download
        >
          Export benchmark matrix (CSV)
        </a>
      </div>
    </div>
  );
}
