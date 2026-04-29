import { api } from "@/lib/api";
import { MouseGlow } from "@/components/ui/MouseGlow";
import { FragmentationSection } from "@/components/fragmentation/FragmentationSection";
import Link from "next/link";

export const revalidate = 300;

export default async function HomePage() {
  const [labs, timeline, fragmentation] = await Promise.all([
    api.labs.list().catch(() => []),
    api.evals.timeline().catch(() => []),
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

      {/* Next-step CTA → Coverage */}
      <section className="mb-20">
        <Link
          href="/analysis"
          className="block p-6 rounded-xl border border-[var(--border)] bg-white shadow-sm hover:shadow-md hover:bg-[var(--surface-1)] transition-colors group"
        >
          <div className="flex items-center justify-between gap-6">
            <div className="flex-1 min-w-0">
              <p className="text-xs text-[var(--accent)] font-medium tracking-wide uppercase mb-2">Next →</p>
              <h2 className="font-serif text-2xl font-semibold mb-2 group-hover:text-accent transition-colors">
                Which safety topics each lab covers
              </h2>
              <p className="text-sm text-[var(--muted)] leading-relaxed max-w-2xl">
                A matrix across {labs.length} labs and 15 categories, from child safety to political neutrality —
                how strongly each lab&apos;s public docs address each topic.
              </p>
            </div>
            <span aria-hidden className="text-2xl text-[var(--muted)] group-hover:text-[var(--text)] transition-colors">→</span>
          </div>
        </Link>
      </section>
    </div>
  );
}
