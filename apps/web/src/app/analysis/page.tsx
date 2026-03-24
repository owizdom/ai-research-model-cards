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
          <li><span className="inline-block w-3 h-3 rounded bg-data align-middle mr-1.5"></span><strong className="text-[var(--text)]">Strong (0.70+)</strong> = The lab has detailed, dedicated policy on this topic</li>
          <li><span className="inline-block w-3 h-3 rounded bg-data-moderate align-middle mr-1.5"></span><strong className="text-[var(--text)]">Moderate (0.50+)</strong> = The lab addresses this topic meaningfully</li>
          <li><span className="inline-block w-3 h-3 rounded bg-data-weak align-middle mr-1.5"></span><strong className="text-[var(--text)]">Weak (0.35+)</strong> = Brief mention, but not a focused policy</li>
          <li><span className="inline-block w-3 h-3 rounded bg-data-missing align-middle mr-1.5"></span><strong className="text-[var(--text)]">Missing</strong> = No meaningful coverage found in their public documents</li>
        </ul>
      </div>

      {matrix ? (
        <IntersectionExplorer matrix={matrix} evalDepth={evalDepth} />
      ) : (
        <p className="text-[var(--muted)]">No data yet. Run a collection first.</p>
      )}
    </div>
  );
}
