import { api } from "@/lib/api";
import { EvalTimelineChart } from "@/components/charts/EvalTimeline";

export const revalidate = 300;

export default async function EvalsPage() {
  const [perCard, labs, benchmarks] = await Promise.all([
    api.evals.perCard().catch(() => []),
    api.labs.list().catch(() => []),
    api.evals.benchmarks().catch(() => []),
  ]);

  const totalEvals = perCard.reduce((sum, p) => sum + p.eval_count, 0);
  const avgPerCard = perCard.length > 0 ? Math.round(totalEvals / perCard.length * 10) / 10 : 0;
  const categories = [...new Set(benchmarks.map(b => b.category))].sort();

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold font-serif mb-2">Eval Explorer</h1>
        <p className="text-sm text-[var(--muted)]">
          Track how many evaluations AI labs report in their model cards and whether disclosure is increasing over time.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        <div className="p-5 rounded-xl border border-[var(--border)] bg-white shadow-sm">
          <div className="text-3xl font-bold tracking-tight">{totalEvals}</div>
          <div className="text-sm text-[var(--muted)] mt-1">Total Evals Extracted</div>
        </div>
        <div className="p-5 rounded-xl border border-[var(--border)] bg-white shadow-sm">
          <div className="text-3xl font-bold tracking-tight">{perCard.length}</div>
          <div className="text-sm text-[var(--muted)] mt-1">Model Cards with Evals</div>
        </div>
        <div className="p-5 rounded-xl border border-[var(--border)] bg-white shadow-sm">
          <div className="text-3xl font-bold tracking-tight">{avgPerCard}</div>
          <div className="text-sm text-[var(--muted)] mt-1">Avg Evals per Card</div>
        </div>
        <div className="p-5 rounded-xl border border-[var(--border)] bg-white shadow-sm">
          <div className="text-3xl font-bold tracking-tight">{benchmarks.length}</div>
          <div className="text-sm text-[var(--muted)] mt-1">Benchmarks Tracked</div>
        </div>
      </div>

      {/* The actual graph */}
      <section className="mb-12">
        <h2 className="text-xl font-semibold mb-2">Evals per Model Card</h2>
        <p className="text-sm text-[var(--muted)] mb-6">
          How many benchmark results each model card reports.
          Taller bars mean more eval disclosure. The dashed line is the industry average.
        </p>
        <EvalTimelineChart data={perCard} labs={labs} />
      </section>

      {/* Benchmark registry */}
      <section>
        <h2 className="font-serif text-xl font-semibold mb-3">Benchmark Registry</h2>
        <p className="text-sm text-[var(--muted)] mb-6 leading-relaxed">
          These are the standardized tests that AI labs use to measure their models.
          We extract benchmark scores from model cards to track what companies actually report.
          Currently tracking {benchmarks.length} benchmarks across {categories.length} categories.
        </p>
        <div className="border border-[var(--border)] rounded-2xl overflow-hidden bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] bg-[var(--surface-2)]">
                <th className="text-left px-5 py-3 font-medium text-[var(--muted)] text-xs uppercase tracking-wider">Category</th>
                <th className="text-left px-5 py-3 font-medium text-[var(--muted)] text-xs uppercase tracking-wider hidden sm:table-cell">What it tests</th>
                <th className="text-left px-5 py-3 font-medium text-[var(--muted)] text-xs uppercase tracking-wider">Benchmarks</th>
              </tr>
            </thead>
            <tbody>
              {([
                { key: "reasoning", desc: "Logic, commonsense, and analytical thinking" },
                { key: "knowledge", desc: "Academic and factual knowledge recall" },
                { key: "coding", desc: "Code generation and software engineering" },
                { key: "math", desc: "Mathematical problem solving" },
                { key: "safety", desc: "Toxicity, bias, and truthfulness" },
                { key: "instruction_following", desc: "Following complex user instructions" },
                { key: "multilingual", desc: "Performance across languages" },
                { key: "vision", desc: "Understanding images and visual content" },
                { key: "arena", desc: "Human preference rankings" },
              ] as const).map(({ key, desc }) => {
                  const catBenchmarks = benchmarks.filter(b => b.category === key);
                  if (catBenchmarks.length === 0) return null;
                  return (
                    <tr key={key} className="border-b border-[var(--border)] last:border-0">
                      <td className="px-5 py-3.5 font-medium capitalize whitespace-nowrap align-top">
                        {key.replace(/_/g, " ")}
                      </td>
                      <td className="px-5 py-3.5 text-[var(--muted)] text-xs align-top hidden sm:table-cell">
                        {desc}
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex flex-wrap gap-1.5">
                          {catBenchmarks.map(b => (
                            <span key={b.slug} className="text-xs px-2.5 py-1 rounded-full border border-[var(--border)] text-[var(--muted)]">
                              {b.name}
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              {/* Other category last, collapsed */}
              {(() => {
                const otherBenchmarks = benchmarks.filter(b => b.category === "other");
                if (otherBenchmarks.length === 0) return null;
                return (
                  <tr className="border-t border-[var(--border)]">
                    <td className="px-5 py-3.5 font-medium text-[var(--muted)] align-top">Other</td>
                    <td className="px-5 py-3.5 text-[var(--muted)] text-xs align-top hidden sm:table-cell">
                      Specialized and model-specific evaluations
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex flex-wrap gap-1.5">
                        {otherBenchmarks.slice(0, 6).map(b => (
                          <span key={b.slug} className="text-xs px-2.5 py-1 rounded-full border border-[var(--border)] text-[var(--muted)]">
                            {b.name}
                          </span>
                        ))}
                        {otherBenchmarks.length > 6 && (
                          <span className="text-xs px-2.5 py-1 text-[var(--muted)]">
                            +{otherBenchmarks.length - 6} more
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })()}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
