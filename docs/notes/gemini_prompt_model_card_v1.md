# Gemini prompt — generate the v1 model card component

Copy everything between the `---START---` and `---END---` markers below into
Gemini (2.5 Pro or later, long-context). The prompt is self-contained — it
restates the spec, the data shape, the tech stack, and the constraints so
Gemini doesn't need access to the rest of the repo.

---START---

You are an expert React / TypeScript engineer who writes accessible,
mobile-first components with Tailwind CSS. You write production code,
not pseudocode. Output exactly one TSX file with no surrounding prose.

## What I want you to build

A two-sided "model card" React component for **modelcards.net**, a
research project about AI evaluation transparency. The visual mental
model is a Pokémon TCG card: a glanceable identity-plus-stats face,
and a flipped technical-detail face. It must work as a single
self-contained component file.

The card represents one AI model (e.g. Claude Opus 4.8, GPT-5.5,
Llama 4) and is grounded in the EvalCards 2 (NeurIPS 2026) framework
plus our own user survey (n=4, small but directional). Design intent:

- 75% of our respondents use cards for research / benchmarking, not
  vendor pitching. Default reader is technical.
- The biggest gaps respondents flagged were **training data
  provenance** and **failure modes / edge cases**. The card must give
  these prominent back-side zones, with explicit empty-state pills
  when the data isn't present (the EvalCards principle: make absence
  visible).
- 98.2% of (model, benchmark) pairs in the corpus are reported by
  only one source. The card must communicate this uncertainty
  through four interpretive signal badges (Reproducibility, Reporting
  Completeness, Provenance, Comparability) — not hide it with smoothed
  averages.

## Front side (Policy mode, default visible)

Fits in one mobile-portrait screen without scrolling. Zones top-to-bottom:

1. **Identity strip**: model name (large, serif), lab name + lab color
   accent dot, generation slug as small monospace chip, release date,
   context window size, parameter count (or "undisclosed" pill).
2. **Type tag row**: 2–5 chips drawn from
   `["agentic", "multimodal", "coding", "reasoning", "long-context", "safety"]`
   based on which categories the card's evaluations cover.
3. **Top-line capability index**: one number 0–100, large. Subtitle
   "weighted MMLU + SWE-bench + MMMU" (these three were the
   information-orthogonal triplet from our corpus correlation analysis).
4. **Stat block**, 3–5 rows: each row is a benchmark *family* with the
   model's score, the metric path, and a small badge tagging
   `self-reported` or `third-party`. Family is the top level of the
   EvalCards 5-level rollout (Family → Composite → Benchmark → Split
   → Metric); show only the family rollup here, not the leaf rows.
5. **Vitals strip**: tokens/sec, $ per 1M tokens, latency p50 and p95.
   If a field is missing, render it as `—` with a small amber
   "undisclosed" pill underneath. Never hide a missing field.
6. **Reliability flags**, four colored badges in a row. Each badge has
   a label, a 0–100 number, and a color band (green ≥80, yellow 50–79,
   red <50). Labels: Reproducibility, Completeness, Provenance,
   Comparability. Clicking a badge expands a one-paragraph tooltip
   explaining what's missing.
7. **Practical demo**: one example user prompt and one example model
   completion, shown as a chat-bubble pair. If `demo` prop is null,
   show a small "demo pending" placeholder card.
8. **One-line takeaway**: italicized single sentence at the bottom
   summarizing what the model is good at.

## Back side (Research mode, on flip)

Scrollable. Zones in order:

1. **Full eval table**: every row at full Family → Composite → Benchmark
   → Split → Metric path. Columns: benchmark name + split, category
   chip, state (scored / mentioned / cited), score + metric, setup pills
   (shot count, method, training state, language, with explicit
   "missing: ..." italic pills for what isn't disclosed), source badge
   (self-reported vs third-party). Rows where this card disagrees with
   another card's report of the same fact get a red "conflict" badge
   on the right.
2. **Training data provenance** — cutoff date, disclosed sources, known
   exclusions, contamination notices. Render each as a labeled field.
   When the whole zone is empty, show a red "Not disclosed" pill at
   the section heading.
3. **Failure modes / edge cases** — known weaknesses, edge cases the
   lab disclosed, red-team findings. Same empty-state treatment.
4. **Threshold assessments** — for safety-critical benchmarks, the
   threshold value, what crossing it means, which result is
   load-bearing for the lab's go/no-go decision. Bulleted list.
5. **Reproducibility recipe** — links to eval harness, container
   image, seed, prompt template. Code-block styling.
6. **Cross-source comparison** — table of (other source, score they
   reported) rows for any (model, benchmark) pair with ≥2 sources.
   Highlight rows where the divergence exceeds 5%.
7. **Citation + provenance** — source PDF link, benchmark paper links,
   dataset license, lab contact.

## Behavior

- Card flips with a CSS 3D transform on a button click (button labeled
  "Methodology" → "Summary" when flipped). Animation 400ms ease-out.
  Respect `prefers-reduced-motion`.
- Every score on the front is a button. Clicking it flips to the back
  AND scrolls the eval table to that row, highlighting it for ~1
  second.
- Keyboard: Tab through all interactive elements, Enter/Space to
  activate. Escape on either side returns focus to the flip button.
- ARIA: front and back are `region` landmarks. The flip button has
  `aria-pressed` reflecting state.
- Mobile-first. At ≥640px width, two-column layout for the back-side
  zones (eval table left, provenance/failure modes right).

## Tech stack constraints

- React 18 with hooks. No class components.
- TypeScript strict mode. Export both the component and its prop type.
- Tailwind CSS only. No styled-components, no CSS-in-JS, no external
  UI libraries (no shadcn, no Radix, no Material).
- Use these existing CSS variables (do not redefine):
  `--accent` (brand red-orange), `--text` (near-black), `--muted`
  (gray-500ish), `--border` (light gray), `--surface-0` (white),
  `--surface-1` (off-white), `--surface-2` (lighter gray).
- The project already has a `BenchmarkPopover` component imported from
  `@/components/ui/BenchmarkPopover` that renders the benchmark name as
  a clickable popover. Reuse it for benchmark cells in the eval table.

## Prop type

Generate the component to accept exactly this prop shape:

```ts
export type ModelCardProps = {
  identity: {
    name: string;
    lab: { name: string; color_hex: string };
    generation_slug: string;
    release_date: string | null;
    context_window: number | null;
    param_count: number | null;
  };
  type_tags: string[];
  capability_index: number | null;
  stat_block: Array<{
    family_name: string;
    score: number;
    metric_path: string;
    is_self_reported: boolean;
    eval_row_id: number;
  }>;
  vitals: {
    tokens_per_sec: number | null;
    cost_per_million: number | null;
    latency_p50_ms: number | null;
    latency_p95_ms: number | null;
  };
  reliability_flags: {
    reproducibility: number;
    completeness: number;
    provenance: number;
    comparability: number;
  };
  demo: { prompt: string; completion: string } | null;
  takeaway: string;
  evals: Array<{
    id: number;
    benchmark: { slug: string; name: string; category: string; policy_note?: unknown };
    family_name: string;
    composite_name: string | null;
    split: string | null;
    state: "scored" | "mentioned" | "cited";
    score: number | null;
    metric_path: string | null;
    shot_count: number | null;
    method: string | null;
    training_state: string | null;
    language: string | null;
    model_name: string | null;
    is_self_reported: boolean;
    missing_fields: string[];
    conflict: { other_sources: number; spread: number } | null;
  }>;
  provenance: {
    cutoff_date: string | null;
    disclosed_sources: string[];
    known_exclusions: string[];
    contamination_notes: string | null;
  };
  failure_modes: Array<{ category: string; description: string }>;
  threshold_assessments: Array<{
    benchmark_name: string;
    threshold: number;
    meaning: string;
    load_bearing: boolean;
  }>;
  reproducibility_recipe: {
    harness_url: string | null;
    container_image: string | null;
    seed: number | null;
    prompt_template: string | null;
  } | null;
  cross_source: Array<{
    benchmark_name: string;
    sources: Array<{ source_label: string; score: number; is_self_reported: boolean }>;
    spread: number;
  }>;
  citations: {
    source_url: string;
    benchmark_papers: Array<{ name: string; url: string }>;
    license: string | null;
    contact: string | null;
  };
};
```

## Output

One TSX file. Path: `apps/web/src/components/ui/ModelCard.tsx`.

At the bottom of the file, include one usage example as a commented-out
block showing the component called with a realistic Claude Opus 4.8
example object (you can make up plausible numbers for the placeholder
example). The example is documentation only, not executable code.

Do not include explanations, README sections, or commentary outside the
code. Just the TSX file.

---END---
