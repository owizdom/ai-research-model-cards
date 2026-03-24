import { api } from "@/lib/api";
import { GenerationComparisonChart } from "@/components/charts/GenerationComparison";
import Link from "next/link";

export const revalidate = 300;

export default async function FamilyDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const [family, comparison] = await Promise.all([
    api.families.get(slug).catch(() => null),
    api.evals.compare(slug).catch(() => null),
  ]);

  if (!family || !family.id) {
    return (
      <div className="p-8 text-center text-[var(--muted)]">
        Model family &ldquo;{slug}&rdquo; not found.
      </div>
    );
  }

  return (
    <div>
      <div className="mb-2">
        <Link href="/families" className="text-sm text-[var(--muted)] hover:text-[var(--text)] transition-colors">
          Model Families
        </Link>
        <span className="text-[var(--muted)] mx-2">/</span>
      </div>

      <div className="mb-8">
        <h1 className="text-2xl font-bold font-serif mb-1">{family.name}</h1>
        <p className="text-sm text-[var(--muted)]">
          {family.lab_slug} &middot; {family.generation_count} generation{family.generation_count !== 1 ? "s" : ""}
        </p>
      </div>

      {/* Generations list */}
      <section className="mb-10">
        <h2 className="text-lg font-semibold mb-4">Generations</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {family.generations.map(gen => (
            <div key={gen.slug} className="p-4 rounded-xl border border-[var(--border)] bg-white shadow-sm">
              <div className="font-medium mb-1">{gen.name}</div>
              <div className="flex items-center gap-3 text-xs text-[var(--muted)]">
                {gen.version_label && <span>v{gen.version_label}</span>}
                {gen.parameter_count && <span>{gen.parameter_count}</span>}
                <span>{gen.eval_count} eval{gen.eval_count !== 1 ? "s" : ""}</span>
              </div>
              {gen.document_id && (
                <Link
                  href={`/documents/${gen.document_id}`}
                  className="text-xs text-accent hover:underline mt-2 inline-block"
                >
                  View model card
                </Link>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Cross-generation comparison */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Benchmark Comparison</h2>
        <p className="text-sm text-[var(--muted)] mb-6">
          Scores across generations for each benchmark. Green deltas indicate improvement.
        </p>
        {comparison ? (
          <GenerationComparisonChart data={comparison} />
        ) : (
          <div className="p-8 text-center text-[var(--muted)] border border-[var(--border)] rounded-xl">
            No comparison data available.
          </div>
        )}
      </section>
    </div>
  );
}
