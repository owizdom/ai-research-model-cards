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

// Eval types
export interface Benchmark {
  id: number;
  slug: string;
  name: string;
  category: string;
  description: string | null;
  metric_name: string | null;
  metric_unit: string | null;
  higher_is_better: boolean;
}

export interface GenerationBrief {
  id: number;
  slug: string;
  name: string;
  version_label: string | null;
}

export interface EvalResult {
  id: number;
  benchmark: Benchmark;
  generation: GenerationBrief | null;
  score: number;
  variant: string;
  score_details: Record<string, unknown> | null;
  extraction_confidence: number | null;
  is_self_reported: boolean;
  source_type: string;
  extracted_at: string;
}

export interface ModelFamily {
  id: number;
  slug: string;
  name: string;
  lab_slug: string;
  generation_count: number;
}

export interface ModelGeneration {
  id: number;
  slug: string;
  name: string;
  version_label: string | null;
  release_date: string | null;
  parameter_count: string | null;
  eval_count: number;
  document_id: number | null;
}

export interface ModelFamilyDetail extends ModelFamily {
  generations: ModelGeneration[];
}

export interface GenerationComparison {
  family_slug: string;
  family_name: string;
  benchmarks: string[];
  generations: string[];
  matrix: Record<string, Record<string, number | null>>;
}

export interface EvalTimeline {
  period: string;
  lab_slug: string;
  eval_count: number;
  document_count: number;
}

export interface PerCardEvalPoint {
  document_id: number;
  document_title: string;
  lab_slug: string;
  version_date: string;
  eval_count: number;
}

