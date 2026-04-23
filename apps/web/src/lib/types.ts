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

export interface DocumentOutlineItem {
  level: number;
  title: string;
  anchor: string;
}

export interface GistFields {
  title: string;
  overview: string | null;
  capability_claim: string | null;
  capability_offset: number | null;
  sharpest_risk: string | null;
  sharpest_risk_offset: number | null;
  deployment_scope: string | null;
  deployment_offset: number | null;
}

export interface HeatstripSegment {
  index: number;
  start: number;
  end: number;
  dominant: string;
  scores: Record<string, number>;
  intensity: number;
}

export interface DocumentContent {
  document_id: number;
  version_id: number;
  version_date: string;
  word_count: number;
  read_minutes: number;
  has_headers: boolean;
  outline: DocumentOutlineItem[];
  content_md: string;
  gist: GistFields | null;
  heatstrip: HeatstripSegment[];
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

export type EvalState = "scored" | "mentioned" | "cited";

export interface EvalResult {
  id: number;
  benchmark: Benchmark;
  generation: GenerationBrief | null;
  score: number | null;
  variant: string;
  model_name: string | null;
  state: EvalState | null;
  shot_count: number | null;
  method: string | null;
  language: string | null;
  training_state: string | null;
  extraction_protocol_version: number;
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

export interface WordCountTimelinePoint {
  lab_slug: string;
  lab_name: string;
  document_slug: string;
  document_title: string;
  version_date: string;
  word_count: number;
}

export interface FragmentationBucket {
  n_labs: number;
  count: number;
  slugs: string[];
  names: Record<string, string>;
}

export interface FragmentationView {
  total: number;
  one_lab_count: number;
  pct_unique: number;
  histogram: FragmentationBucket[];
}

export interface LabUniqueness {
  lab_slug: string;
  lab_name: string;
  total_reported: number;
  only_them_count: number;
  only_them: { slug: string; name: string; category: string }[];
}

export interface FragmentationResponse {
  labs: string[];
  raw: FragmentationView;
  families: FragmentationView;
  by_lab: LabUniqueness[];
}

export interface CategoryTimelinePoint {
  document_slug: string;
  document_title: string;
  lab_slug: string;
  lab_name: string;
  benchmark_category: string;
  eval_count: number;
}

