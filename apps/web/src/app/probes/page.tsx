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
      <h1 className="text-2xl font-bold mb-2">AI Bias Tracker</h1>
      <p className="text-[var(--muted)] mb-4 text-sm max-w-2xl leading-relaxed">
        We ask AI models 25 politically sensitive questions &mdash; about immigration, gun control,
        climate policy, and more &mdash; then measure whether their answers lean liberal,
        conservative, or stay neutral.
      </p>

      {/* How to read this */}
      <div className="mb-8 p-4 rounded-xl border border-[var(--border)] bg-surface-1">
        <h3 className="text-sm font-semibold mb-2">How to read the scores</h3>
        <ul className="text-xs text-[var(--muted)] space-y-1.5 leading-relaxed">
          <li><span className="inline-block w-3 h-3 rounded-full mr-1.5 align-middle" style={{ background: "#3b82f6" }}></span><strong className="text-white">Positive (+)</strong> &mdash; Response leans <strong className="text-blue-400">liberal</strong>. Higher = stronger lean.</li>
          <li><span className="inline-block w-3 h-3 rounded-full mr-1.5 align-middle" style={{ background: "#ef4444" }}></span><strong className="text-white">Negative (-)</strong> &mdash; Response leans <strong className="text-red-400">conservative</strong>. Lower = stronger lean.</li>
          <li><span className="inline-block w-3 h-3 rounded-full mr-1.5 align-middle" style={{ background: "#6b7280" }}></span><strong className="text-white">Near zero (0.00)</strong> &mdash; Response is <strong className="text-gray-400">neutral</strong> or balanced.</li>
        </ul>
        <p className="text-xs text-[var(--muted)] mt-2">
          Scores combine three signals: how similar the response is to known liberal/conservative talking
          points, politically charged word usage, and moral framing patterns.
        </p>
      </div>

      <SlantDashboard summary={summary} probes={probes} />
    </div>
  );
}
