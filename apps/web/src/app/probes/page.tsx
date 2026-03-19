import { api } from "@/lib/api";
import { SlantDashboard } from "@/components/charts/SlantDashboard";

export const revalidate = 60;

export default async function ProbesPage() {
  const [summary, probes] = await Promise.all([
    api.analysis.slantSummary().catch(() => null),
    api.probes.list().catch(() => []),
  ]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Political Slant Monitor</h1>
      <p className="text-[var(--muted)] mb-8 text-sm max-w-2xl">
        Composite political slant scores across models, measured via embedding centroids,
        moral foundations, and political valence lexicon. Positive = liberal lean, negative = conservative lean.
      </p>
      <SlantDashboard summary={summary} probes={probes} />
    </div>
  );
}
