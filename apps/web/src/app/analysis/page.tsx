import { api } from "@/lib/api";
import { IntersectionExplorer } from "@/components/charts/IntersectionExplorer";

export const revalidate = 300;

export default async function AnalysisPage() {
  const matrix = await api.analysis.intersection({ threshold: 0.35 }).catch(() => null);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">Intersection Analysis</h1>
      <p className="text-[var(--muted)] mb-8 text-sm max-w-2xl">
        Which safety and policy categories does each lab address? Coverage is determined by semantic
        similarity between document embeddings and category descriptions (threshold ≥ 0.35).
      </p>
      {matrix ? (
        <IntersectionExplorer matrix={matrix} />
      ) : (
        <p className="text-[var(--muted)]">No data yet — run a collection first.</p>
      )}
    </div>
  );
}
