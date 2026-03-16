import { api } from "@/lib/api";
import { LabCard } from "@/components/ui/LabCard";

export const revalidate = 300;

export default async function HomePage() {
  const labs = await api.labs.list().catch(() => []);

  return (
    <div>
      <div className="mb-10">
        <h1 className="text-3xl font-bold mb-2">AI Policy Intelligence</h1>
        <p className="text-[var(--muted)] max-w-2xl">
          Track policy documents, model cards, and system prompts from major AI labs.
          Analyze coverage overlap and monitor political slant in model outputs over time.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-lg font-semibold mb-4 text-[var(--muted)] uppercase tracking-wider text-xs">
          Tracked Labs
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {labs.map((lab) => <LabCard key={lab.slug} lab={lab} />)}
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <a href="/analysis" className="block p-6 rounded-xl border border-[var(--border)] bg-surface-1 hover:bg-surface-2 transition-colors">
          <h3 className="font-semibold mb-1">Intersection Analysis</h3>
          <p className="text-sm text-[var(--muted)]">
            Explore which safety categories are covered by which labs — and where the gaps are.
          </p>
        </a>
        <a href="/probes" className="block p-6 rounded-xl border border-[var(--border)] bg-surface-1 hover:bg-surface-2 transition-colors">
          <h3 className="font-semibold mb-1">Political Slant Monitor</h3>
          <p className="text-sm text-[var(--muted)]">
            Run probes across 10+ models and track composite political slant scores over time.
          </p>
        </a>
      </section>
    </div>
  );
}
