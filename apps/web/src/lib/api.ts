import type {
  Lab, Document, DocumentDetail, DocumentContent, IntersectionMatrix,
  Benchmark, EvalResult, GenerationComparison, EvalTimeline, PerCardEvalPoint,
  ModelFamily, ModelFamilyDetail,
  WordCountTimelinePoint, CategoryTimelinePoint,
  FragmentationResponse, DivergenceResponse,
} from "./types";

// API_INTERNAL_URL is set server-side only (docker-compose env).
// NEXT_PUBLIC_API_URL is used client-side (baked in at build time).
const BASE = process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://api:8000";

async function get<T>(path: string, params?: Record<string, string | number | boolean>): Promise<T> {
  const url = new URL(`${BASE}/api/v1${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  }
  const res = await fetch(url.toString(), { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}/api/v1${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API POST ${path} → ${res.status}`);
  return res.json();
}

export const api = {
  labs: {
    list: () => get<Lab[]>("/labs"),
    get: (slug: string) => get<Lab>(`/labs/${slug}`),
  },

  documents: {
    list: (params?: { lab?: string; doc_type?: string; search?: string; limit?: number; offset?: number }) =>
      get<Document[]>("/documents", params as Record<string, string | number | boolean>),
    wordCountTimeline: () =>
      get<WordCountTimelinePoint[]>("/documents/word-count-timeline"),
    get: (id: number) => get<DocumentDetail>(`/documents/${id}`),
    content: (id: number, versionId?: number) =>
      get<DocumentContent>(
        `/documents/${id}/content`,
        versionId ? { version_id: versionId } : undefined,
      ),
  },

  analysis: {
    intersection: (params?: { labs?: string; threshold?: number }) =>
      get<IntersectionMatrix>("/analysis/intersection", params as Record<string, string | number | boolean>),
  },

  evals: {
    benchmarks: (category?: string) =>
      get<Benchmark[]>("/evals/benchmarks", category ? { category } : undefined),
    byDocument: (docId: number) =>
      get<{ document_id: number; title: string; lab_name: string; version_id: number; evals: EvalResult[] }>(`/evals/results/by-document/${docId}`),
    compare: (familySlug: string, benchmarks?: string) =>
      get<GenerationComparison>("/evals/compare/generations", { family_slug: familySlug, ...(benchmarks ? { benchmark_slugs: benchmarks } : {}) }),
    timeline: (labSlug?: string) =>
      get<EvalTimeline[]>("/evals/timeline", labSlug ? { lab_slug: labSlug } : undefined),
    perCard: () =>
      get<PerCardEvalPoint[]>("/evals/per-card"),
    depth: () =>
      get<Record<string, Record<string, number>>>("/evals/depth"),
    categoryTimeline: () =>
      get<CategoryTimelinePoint[]>("/evals/category-timeline"),
    fragmentation: () =>
      get<FragmentationResponse>("/evals/fragmentation"),
    divergence: (params?: { threshold?: number; benchmark_slug?: string; model_name?: string; limit?: number }) =>
      get<DivergenceResponse>("/evals/divergence", params as Record<string, string | number | boolean> | undefined),
  },

  families: {
    list: () => get<ModelFamily[]>("/families"),
    get: (slug: string) => get<ModelFamilyDetail>(`/families/${slug}`),
  },
};
