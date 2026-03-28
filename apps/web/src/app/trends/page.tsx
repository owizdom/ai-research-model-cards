import { api } from "@/lib/api";
import { WordCountTrendChart } from "@/components/charts/WordCountTrend";
import { EvalCategoryTrendChart } from "@/components/charts/EvalCategoryTrend";

export const revalidate = 300;

export default async function TrendsPage() {
  const [wordCountData, categoryData, labs] = await Promise.all([
    api.documents.wordCountTimeline().catch(() => []),
    api.evals.categoryTimeline().catch(() => []),
    api.labs.list().catch(() => []),
  ]);

  const totalCards = new Set(wordCountData.map(d => d.document_slug)).size;
  const longestCard = wordCountData.length > 0
    ? wordCountData.reduce((max, d) => d.word_count > max.word_count ? d : max, wordCountData[0])
    : null;
  const labsWithEvals = new Set(categoryData.map(d => d.lab_slug)).size;
  const totalCategoryEvals = categoryData.reduce((s, d) => s + d.eval_count, 0);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold font-serif mb-2">Trends</h1>
        <p className="text-sm text-[var(--muted)]">
          Track how model card documentation and evaluation disclosure have evolved across AI labs.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        <div className="p-5 rounded-xl border border-[var(--border)] bg-white shadow-sm">
          <div className="text-3xl font-bold tracking-tight">{totalCards}</div>
          <div className="text-sm text-[var(--muted)] mt-1">Model Cards Tracked</div>
        </div>
        <div className="p-5 rounded-xl border border-[var(--border)] bg-white shadow-sm">
          <div className="text-3xl font-bold tracking-tight">
            {longestCard ? `${Math.round(longestCard.word_count / 1000)}k` : "—"}
          </div>
          <div className="text-sm text-[var(--muted)] mt-1">
            Longest Card {longestCard ? `(${longestCard.lab_name})` : ""}
          </div>
        </div>
        <div className="p-5 rounded-xl border border-[var(--border)] bg-white shadow-sm">
          <div className="text-3xl font-bold tracking-tight">{labsWithEvals}</div>
          <div className="text-sm text-[var(--muted)] mt-1">Labs with Evals</div>
        </div>
        <div className="p-5 rounded-xl border border-[var(--border)] bg-white shadow-sm">
          <div className="text-3xl font-bold tracking-tight">{totalCategoryEvals}</div>
          <div className="text-sm text-[var(--muted)] mt-1">Total Evals Extracted</div>
        </div>
      </div>

      {/* Chart A: Word Count */}
      <section className="mb-16">
        <h2 className="text-xl font-semibold font-serif mb-2">Card Length by Model</h2>
        <p className="text-sm text-[var(--muted)] mb-6">
          Word count of each model card, showing how detailed safety documentation varies across labs and models.
          Longer cards generally indicate more thorough safety analysis, evaluation reporting, and risk documentation.
        </p>
        <WordCountTrendChart data={wordCountData} />
      </section>

      {/* Chart B: Eval Categories */}
      <section>
        <h2 className="text-xl font-semibold font-serif mb-2">Evaluation Disclosure by Topic</h2>
        <p className="text-sm text-[var(--muted)] mb-6">
          How many evaluations each lab reports across different categories.
          Stacked bars show the distribution of eval topics — reasoning, coding, safety, math, and more.
        </p>
        <EvalCategoryTrendChart data={categoryData} />
      </section>
    </div>
  );
}
