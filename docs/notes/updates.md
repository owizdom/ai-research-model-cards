# Path to Defensibility — 5-Sprint Plan

Goal: move from "looks sloppy to a DeepMind researcher" to publication-grade, peer-reviewable, and defensible to domain experts. Total: ~16 days focused work.

---

## Sprint 1 — Data completeness (3 days)

**Goal:** every claim in the DB is traceable to a source and internally consistent.

- **A: 405B schema fix + backfill** — foundational, unblocks multi-size papers.
- **D: canonical benchmark ontology** — pick `humaneval` as the single name; `multipl_e` language rows become variants. Define every benchmark's name, aliases, source paper, score range, units. This becomes the `benchmark_definitions` table's source of truth.
- **Source doc expansion** — curate and add: Jamba 1.5, Command R+, Mistral Large 2, Amazon Nova Pro/Lite/Micro, Gemini 2.5 Pro, o3 system card, Grok 3, DeepSeek V3 + R1, Qwen 2.5. Target: 110-120 versions, all major labs represented through 2026.
- **Benchmark score validation at extraction time** — reject impossible values.
- **Explicit doc_scope metadata** — is this doc a capability paper, safety paper, policy doc, or license? Shown everywhere in the UI — so "0 benchmarks" on a policy doc isn't a surprise.

## Sprint 2 — Rigor (4 days)

**Goal:** every extracted number has a credibility score attached.

- **B + C bundled** — re-extract all ~110 versions with a new prompt producing `(score, state ∈ {scored, mentioned, cited}, shot_count, method, language, training_state, metric)`. One expensive run (~6 hours wall time), but every row gains structured metadata.
- **E (Cohen's κ): 30 docs** (not 20) for inter-rater reliability. Use Claude Opus + Claude Sonnet as two independent extractors. Measure κ for benchmark extraction, taxonomy mapping, and state classification separately. Target: κ > 0.80 for all three. Publish the number.
- **Manual spot-check: 50 evals** (not 20), stratified across labs. Two humans independently verify against source text. Publish precision AND recall (missing some scores, not just mis-classifying).
- **F (temporal benchmarks)** — curate the top 20 benchmarks with explicit version years. MMLU-2021 ≠ MMLU-2024 in the DB. The long tail stays nullable with a "version unknown" flag.
- **Surface `is_self_reported` in the UI** — show whether a score came from the lab itself or an independent eval source.

## Sprint 3 — Code & reproducibility (3 days)

**Goal:** someone else can run the pipeline on their machine and get the same answers.

- **Test coverage beyond the parser** — collector tests, worker tests, API route tests, end-to-end smoke test. Target 70%+ line coverage.
- **GitHub Actions CI** — tests on every push, block merges on failure, periodic coverage check.
- **mypy strict on new code** — type hints throughout.
- **`docker-compose.yml`** — boots Postgres + Redis + all services locally with a seeded test dataset.
- **Versioned releases** — tag `v0.1.0` now. Every data milestone → new version tag + pinned Railway deploy.
- **Publish data dumps** — CSV + SQL snapshots + the raw Claude extraction outputs. Put them on Zenodo, get a DOI. Anyone can now reproduce the analysis.

## Sprint 4 — External validation (3 days)

**Goal:** at least one non-Claude source agrees with the extracted numbers.

- **HELM cross-check** — their leaderboards are public. For every (model, benchmark) in the DB that HELM also measures, compare scores. Publish agreement rate. Flag large disagreements.
- **vals.ai** — reach out for API access or scrape their public data. Same comparison.
- **Lab outreach** — email Anthropic/Meta/Google a short "can you verify this is complete?" checklist for the model cards captured. Even 1 lab confirming "yes, you captured everything from our Claude 3.5 Sonnet card" is a massive credibility boost.
- **Add `independent_verification` column to `eval_results`** — possible values: `verified_match`, `verified_mismatch`, `not_verified`. Show this in the UI — every score has a provenance signal.

## Sprint 5 — Publication package (3 days)

**Goal:** something citable.

- **Write `METHODOLOGY.md`** — the complete protocol. Inclusion criteria. Extraction pipeline. Handling of ambiguity. Known limits. Error rates from Sprints 2 and 4.
- **Write `DATASET.md`** — what's in the DB, how to access it, how to cite it.
- **README rewrite** — academic framing + DOI badge + citation block.
- **Draft a short preprint for arxiv** (cs.CY or cs.CL). Even 6 pages. Co-author with Andrew Hall and Vania Chow. This gives the dashboard a citable paper.
- **Add a public `CHANGELOG.md`** — dataset versions. v1.0 = current snapshot; future updates versioned cleanly.

---

## What's still not achievable after all this (and why that's fine)

- Cannot measure what labs don't publish. If internal benchmarks stay private, they're invisible. Document as scope limit.
- LLM extraction will never be 100%. Sprint 2 quantifies it (say 96%). Publish the floor.
- Benchmark semantics drift. New MMLU versions will emerge. Versioning (F) handles what's known; new ones need maintenance.
- Taxonomy mapping is inherently judgment. κ = 0.87 means 13% of mappings are contested. Disclose and move on.

Every one of these is a KNOWN LIMITATION documented in the methodology. That's the standard. Nothing in AI policy research is "perfect" — it's all "rigorous about what it knows and what it doesn't."

---

## Minimum-viable bulletproof

If skipping the full sprint and still hitting "defensible": **Sprints 1 + 2 + `METHODOLOGY.md` = ~8 days**. That's 80% of the credibility at 50% of the effort. The rest is infrastructure polish and external validation — valuable, but not what a first-pass reviewer will notice.
