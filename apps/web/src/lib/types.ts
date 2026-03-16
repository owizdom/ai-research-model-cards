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

export interface SlantSummary {
  model_slug: string;
  model_name: string;
  mean_slant: number;
  std_slant: number;
  trump_slant: number | null;
  biden_slant: number | null;
  asymmetry: number | null;
  run_count: number;
}

export interface Probe {
  id: number;
  slug: string;
  category: string;
  slant_axis: string;
  prompt_text: string;
}

export interface ProbeRun {
  id: number;
  status: "pending" | "running" | "completed" | "failed";
  created_at: string;
  probe_ids: number[];
  model_slugs: string[];
}
