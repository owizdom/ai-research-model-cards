import { api } from "@/lib/api";
import { LabCard } from "@/components/ui/LabCard";

export const revalidate = 300;

export default async function HomePage() {
  const labs = await api.labs.list().catch(() => []);
  const totalDocs = labs.reduce((sum, l) => sum + l.document_count, 0);

  return (
    <div>
      {/* Hero */}
      <div className="mb-10">
        <h1 className="text-3xl font-bold mb-3">AI Policy Intelligence</h1>
        <p className="text-[var(--muted)] max-w-2xl text-base leading-relaxed">
          We track what the biggest AI companies say they will and won&apos;t do &mdash; their safety
          policies, model cards, and usage rules &mdash; and test whether their AI models
          actually follow through.
        </p>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
        <div className="p-4 rounded-xl border border-[var(--border)] bg-surface-1 text-center">
          <div className="text-2xl font-bold">{labs.length}</div>
          <div className="text-xs text-[var(--muted)] mt-1">AI Labs Tracked</div>
        </div>
        <div className="p-4 rounded-xl border border-[var(--border)] bg-surface-1 text-center">
          <div className="text-2xl font-bold">{totalDocs}</div>
          <div className="text-xs text-[var(--muted)] mt-1">Policy Documents</div>
        </div>
        <div className="p-4 rounded-xl border border-[var(--border)] bg-surface-1 text-center">
          <div className="text-2xl font-bold">15</div>
          <div className="text-xs text-[var(--muted)] mt-1">Safety Categories</div>
        </div>
        <div className="p-4 rounded-xl border border-[var(--border)] bg-surface-1 text-center">
          <div className="text-2xl font-bold">25</div>
          <div className="text-xs text-[var(--muted)] mt-1">Political Bias Probes</div>
        </div>
      </div>

      {/* Two main features */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
        <a href="/analysis" className="block p-6 rounded-xl border border-[var(--border)] bg-surface-1 hover:bg-surface-2 transition-colors group">
          <div className="text-accent text-2xl mb-3">&#x1F6E1;</div>
          <h3 className="font-semibold mb-2 group-hover:text-accent transition-colors">Safety Coverage</h3>
          <p className="text-sm text-[var(--muted)] leading-relaxed">
            Which safety topics does each AI lab actually write policies about?
            See where the industry agrees &mdash; and where critical gaps exist.
          </p>
        </a>
        <a href="/probes" className="block p-6 rounded-xl border border-[var(--border)] bg-surface-1 hover:bg-surface-2 transition-colors group">
          <div className="text-accent text-2xl mb-3">&#x2696;</div>
          <h3 className="font-semibold mb-2 group-hover:text-accent transition-colors">Bias Tracker</h3>
          <p className="text-sm text-[var(--muted)] leading-relaxed">
            We ask AI models the same politically sensitive questions and measure
            if they lean left, right, or stay neutral. See the results for yourself.
          </p>
        </a>
      </section>

      {/* Labs grid */}
      <section>
        <h2 className="text-sm font-semibold mb-4 text-[var(--muted)] uppercase tracking-wider">
          Labs We Track
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {labs.map((lab) => <LabCard key={lab.slug} lab={lab} />)}
        </div>
      </section>
    </div>
  );
}
