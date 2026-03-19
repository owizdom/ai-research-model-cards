export interface Lab {
  id: number;
  slug: string;
  name: string;
  website: string | null;
  color_hex: string | null;
  document_count: number;
}

export interface Document {
  id: number;
  slug: string;
  title: string;
  doc_type: string;
  source_url: string;
  lab_slug: string;
  lab_name: string;
  latest_version_date: string | null;
  version_count: number;
}

export interface DocumentVersion {
  id: number;
  version_date: string;
  word_count: number | null;
  content_hash: string;
  wayback_url: string | null;
}

export interface DocumentDetail extends Document {
  versions: DocumentVersion[];
}

export interface IntersectionMatrix {
  lab_slugs: string[];
  category_names: Record<string, string>;
  matrix: Record<string, Record<string, number>>;
  covered_by_all: string[];
  covered_by_none: string[];
  unique_to: Record<string, string[]>;
  intersection_sets: IntersectionSet[];
}

export interface IntersectionSet {
  labs: string[];
  categories: string[];
  size: number;
}

export interface SlantSeries {
  model_slug: string;
  model_name: string;
  probe_slug: string;
  dates: string[];
  composite_slant: number[];
  trend_direction: "increasing" | "decreasing" | "no_trend";
  trend_p: number;
}

export interface ModelScore {
  model_slug: string;
  mean_composite_slant: number;
  std: number;
  n_samples: number;
}

export interface ProbeScore {
  probe_key: string;
  category: string;
  mean_slant_by_model: Record<string, number>;
}

export interface SlantSummary {
  model_scores: ModelScore[];
  probe_scores: ProbeScore[];
}

export interface Probe {
  id: number;
  probe_key: string;
  category: string;
  prompt: string;
  is_active: boolean;
}

export interface ProbeRun {
  id: number;
  status: "queued" | "running" | "completed" | "failed";
  triggered_by: string;
  started_at: string;
  probe_count: number | null;
  model_count: number | null;
}

export interface ProbeResponseDetail {
  id: number;
  model_slug: string;
  prompt_text: string;
  response_text: string;
  recorded_at: string;
  tokens: number | null;
  slant_score: {
    composite: number;
    economic: number | null;
    social: number | null;
    authority: number | null;
  } | null;
}
