import { api } from "@/lib/api";
import { SlantDashboard } from "@/components/charts/SlantDashboard";

export const revalidate = 60;

export default async function ProbesPage() {
  const [summaries, probes] = await Promise.all([
    api.analysis.slantSummary().catch(() => []),
    api.probes.list().catch(() => []),
  ]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Political Slant Monitor</h1>
      <p className="text-[var(--muted)] mb-8 text-sm max-w-2xl">
        Composite political slant scores across models, measured via embedding centroids,
        moral foundations, and political valence lexicon. Positive = liberal lean.
      </p>
      <SlantDashboard summaries={summaries} probes={probes} />
    </div>
  );
}
