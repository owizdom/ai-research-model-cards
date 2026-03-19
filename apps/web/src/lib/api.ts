import type {
  Lab, Document, DocumentDetail, IntersectionMatrix,
  SlantSeries, SlantSummary, Probe, ProbeRun,
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
    documents: (slug: string) => get<Document[]>(`/labs/${slug}/documents`),
  },

  documents: {
    list: (params?: { lab?: string; doc_type?: string; search?: string; limit?: number; offset?: number }) =>
      get<Document[]>("/documents", params as Record<string, string | number | boolean>),
    get: (id: number) => get<DocumentDetail>(`/documents/${id}`),
    version: (id: number, versionId: number) =>
      get<{ content_md: string }>(`/documents/${id}/versions/${versionId}`),
  },

  analysis: {
    intersection: (params?: { labs?: string; threshold?: number }) =>
      get<IntersectionMatrix>("/analysis/intersection", params as Record<string, string | number | boolean>),
    slantSummary: (params?: { probe_category?: string }) =>
      get<SlantSummary>("/analysis/slant", params as Record<string, string | number | boolean>),
    slantSeries: (modelSlug: string, probeSlug?: string) =>
      get<SlantSeries[]>("/analysis/slant/series", { model: modelSlug, ...(probeSlug ? { probe: probeSlug } : {}) }),
  },

  probes: {
    list: () => get<Probe[]>("/probes"),
    runs: () => get<ProbeRun[]>("/probes/runs"),
    triggerRun: (body: { probe_ids: number[]; model_slugs: string[] }) =>
      post<ProbeRun>("/probes/runs", body),
  },

  responses: {
    list: (params: { run_id?: number; probe_id?: number; model_slug?: string }) =>
      get<unknown[]>("/responses", params as Record<string, string | number | boolean>),
  },
};
