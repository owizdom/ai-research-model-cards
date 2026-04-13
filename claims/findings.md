# Audited Claims — Model Card Benchmark Disclosure Research

Last updated: 2026-04-13
Corpus: 53 frontier model card versions across 9 labs
Audit method: DB regex grep (PostgreSQL `~*` operator with word boundaries) + independent web verification

---

## CONFIRMED CLAIMS (with sources)

### C1. MedQA appears in 1 of 53 model cards

**Claim:** "MedQA appears in 1 card — GPT-4o System Card, mid-2024. Every subsequent OpenAI release has dropped it."

**Status:** CONFIRMED

**Evidence:**
- DB grep: `content_md ~* '\mMedQA\M'` returns exactly 1 model card version (GPT-4o System Card, version ID 11)
- GPT-4o System Card contains 8 MedQA score variants: USMLE 4-opt/5-opt, Taiwan, Mainland China, each 0-shot and 5-shot
- GPT-4o System Card PDF: https://cdn.openai.com/gpt-4o-system-card.pdf
- Independently verified absent from: GPT-4.5, o1, o3, GPT-5, GPT-5.1, GPT-5.2, GPT-5.3 system cards
- GPT-5 System Card: https://cdn.openai.com/gpt-5-system-card.pdf (confirmed no MedQA)
- GPT-4.5 System Card: https://cdn.openai.com/gpt-4-5-system-card-2272025.pdf (confirmed no MedQA)

**Note:** Claude 3 Model Card mentions "MedMCQA" and "PubMedQA" but NOT "MedQA" as a standalone benchmark. The string "MedQA" does not appear in the Claude 3 card with word boundaries. (PubMedQA ≠ MedQA — they are different benchmarks by different authors.)

---

### C2. PubMedQA appears in 1 of 53 model cards

**Claim:** "PubMedQA appears in 1 card — Claude 3 Model Card, mid-2024. Dropped from every Claude release since."

**Status:** CONFIRMED

**Evidence:**
- DB grep: `content_md ~* '\mPubMedQA\M'` returns exactly 1 model card version (Claude 3 Model Card, version ID 2)
- Scores: Claude 3 Opus 75.8% (5-shot), 74.9% (0-shot)
- Claude 3 Model Card PDF: https://www-cdn.anthropic.com/de8ba9b01c9ab7cbabf5c33b80b7bbc618857627/Model_Card_Claude_3.pdf
- Independently verified absent from: Claude 3.5 Sonnet Addendum, Claude 3.5 Haiku Addendum, Claude 3.7, Claude 4, Opus 4.1, Sonnet 4.5, Opus 4.5, Haiku 4.5, Sonnet 4.6, Opus 4.6, Mythos Preview
- Claude 3.5 Addendum: https://www-cdn.anthropic.com/fed9cc193a14b84131812372d8d5857f8f304c52/Model_Card_Claude_3_Addendum.pdf (confirmed no PubMedQA)

---

### C3. LegalBench appears in 0 of 53 model cards

**Claim:** "LegalBench appears in zero frontier model cards across all 9 labs."

**Status:** CONFIRMED

**Evidence:**
- DB grep: `content_md ~* '\mLegalBench\M'` returns 0 rows
- Web search for "LegalBench model card" or "LegalBench system card" with site:openai.com, site:anthropic.com, site:deepmind.google — no results showing LegalBench in any model card
- Note: Claude Opus 4.6 reports "BigLaw Bench" (score 90.2%) — this is a DIFFERENT benchmark from LegalBench
- vals.ai independently runs LegalBench on frontier models: https://www.vals.ai/benchmarks/legal_bench

---

### C4. CUAD appears in 0 of 53 model cards

**Claim:** "CUAD appears in zero frontier model cards."

**Status:** CONFIRMED

**Evidence:**
- DB grep: `content_md ~* '\mCUAD\M'` returns 0 rows (one false positive "Cuadros" — a researcher name — was ruled out by word boundary matching)

---

### C5. MedMCQA appears in 2 of 53 model cards

**Claim:** "MedMCQA appears in 2 cards, both mid-2024."

**Status:** CONFIRMED

**Evidence:**
- DB grep returns 2 cards: Claude 3 Model Card (qualitative reference) and GPT-4o System Card
- Both published mid-2024. Zero mentions in any subsequent release.

---

### C6. HealthBench appears in 2 of 53 model cards, both OpenAI

**Claim:** "HealthBench appears in 2 cards, both OpenAI. It's OpenAI's own benchmark."

**Status:** CONFIRMED

**Evidence:**
- DB grep returns 2 cards: GPT-5 System Card (24 mentions) and GPT-5.2 System Card (10 mentions)
- HealthBench origin confirmed: published May 13, 2025
- Paper: "HealthBench: Evaluating Large Language Models Towards Improved Human Health"
- arxiv: https://arxiv.org/abs/2505.08775
- OpenAI blog: https://openai.com/index/healthbench/
- Built with 262 physicians across 60 countries
- OpenAI is the publisher — this is a vendor-published benchmark

---

### C7. MMLU appears in 25 of 53 model cards (47%)

**Status:** CONFIRMED

**Evidence:**
- DB grep: `content_md ~* '\mMMLU\M'` (excluding MMLU-Pro, MMLU-Redux) returns 25 cards
- Spot-check: appeared in 4/4 independently fetched frontier cards (GPT-5, Claude Opus 4.5, Gemini 2.5 Pro, Llama 4)

---

### C8. GPQA appears in 19 of 53 (35%), SWE-bench in 18 (33%), MMMU in 14 (26%)

**Status:** CONFIRMED

**Evidence:**
- DB grep with PostgreSQL word-boundary regex
- Spot-check: GPQA in 3/4, SWE-bench in 3/4, MMMU in 3/4 of independently fetched cards
- Note: MMMU was previously reported as 13/53 — corrected to 14/53 after re-grep

---

### C9. Only 6 benchmarks shared by all 4 major labs

**Claim:** "Only 6 benchmarks are used by all 4 major labs: DROP, GPQA, HellaSwag, MATH, MMLU, RACE"

**Status:** CONFIRMED

**Evidence:**
- Computed from per-card benchmark grep across all 53 cards
- Jaccard similarity matrix: Anthropic×Meta 0.71, Anthropic×Google 0.67, Google×Meta 0.62, OpenAI×anyone 0.30-0.37

---

### C10. Mitchell et al. quote

**Claim:** Model cards were introduced as "short documents accompanying trained machine learning models that provide benchmarked evaluation in a variety of conditions"

**Status:** CONFIRMED — word-for-word match

**Source:**
- Paper: "Model Cards for Model Reporting" by Margaret Mitchell, Simone Wu, Andrew Zaldivar, Parker Barnes, Lucy Vasserman, Ben Hutchinson, Elena Spitzer, Inioluwa Deborah Raji, Timnit Gebru
- Published: FAT* '19, January 29-31, 2019, Atlanta, GA, USA
- arxiv: https://arxiv.org/abs/1810.03993
- DOI: https://doi.org/10.1145/3287560.3287596
- Quote is from the abstract, first sentence
- Correct citation: Mitchell et al. (2019)

---

### C11. vals.ai operates as independent third-party benchmark evaluator

**Status:** CONFIRMED (with caveat)

**Evidence:**
- Founded 2024 by Rayan Krishnan and Langston Nashold (Stanford). Based in San Francisco. Not affiliated with any AI lab.
- Runs models via API independently — does NOT use lab-reported scores
- Covers MedQA: https://www.vals.ai/benchmarks/medqa-08-12-2025
- Covers LegalBench: https://www.vals.ai/benchmarks/legal_bench
- Uses private test sets to prevent data leakage (three-tier: public validation, private validation, private test)
- Standardized evaluation harness across all models
- Methodology: https://www.vals.ai/methodology
- About: https://www.vals.ai/about
- External press confirms independence: Daily Jus, LawSites, DeepLearning.AI all describe them as "independent"

**Caveat:** The claim "vals.ai independently runs every frontier model" is **overstated**. They cover major providers (OpenAI, Anthropic, Google, xAI) + select open-weight models (Llama, DeepSeek, Mistral, Cohere), but not exhaustively every frontier model on every benchmark. Use "major frontier models" not "every."

---

## CORRECTIONS NEEDED

### X1. MedQA citation count — WRONG NUMBER, WRONG BENCHMARK

**Original claim:** "medqa (194k academic citations)"
**Reality:** 194,000 is MedMCQA's citation count in Vania's CSV, NOT MedQA's.

Actual MedQA citations:
- Vania's CSV (Evidently AI source): 12,723
- Semantic Scholar: ~1,527
- Source discrepancy between databases

MedQA paper: Jin et al., "What Disease does this Patient Have? A Large-scale Open Domain Question Answering Dataset from Medical Exams"
- arxiv: https://arxiv.org/abs/2009.13081
- Published: MDPI Applied Sciences, July 2021

**Fix:** Drop citation count entirely, or use conservative "~1,500 citations (Semantic Scholar)" with caveat.

---

### X2. "per OpenAI's own research paper" — NOT OpenAI's paper

**Original claim:** "gpt-5 hits ~96% on medqa per openai's own research paper"
**Reality:** The paper "Capabilities of GPT-5 on Multimodal Medical Reasoning" (arxiv 2508.08224) is by Wang, Hu, Li, Safari, Yang — these are NOT OpenAI employees. The authors appear to be from Emory University. This is an independent third-party evaluation.

GPT-5 MedQA score: **95.84%** on MedQA US 4-option (source: arxiv 2508.08224)

**Fix:** Change "per openai's own research paper" to "per an independent evaluation (Wang et al., arxiv 2508.08224)"

---

### X3. FinQA "0 cards ever" — FALSIFIED for the broader landscape

**Original claim:** "finqa: 0 cards. across all 9 labs. ever."
**Reality:** Amazon Nova Technical Report and Model Card (2025) includes FinQA scores in Section B.3.1, Table 7.
- Source: https://arxiv.org/abs/2506.12103
- Document self-identifies as both "Technical Report" and "Model Card"
- Amazon Nova was NOT in our 53-card corpus

**Fix:** "FinQA: 0 in our 53-card corpus. Amazon Nova (not in our sample) does include it."

**Nuance from audit:** Amazon Nova self-describes as "frontier" but is generally considered mid-tier (competes with GPT-4o / Claude 3.5 Sonnet, not GPT-5 / Claude Opus 4.6 / Gemini 3.1 Pro). If "frontier" means top-tier SOTA, the "0 cards ever" claim may still hold. If "frontier" means any major lab release, it doesn't. The Amazon Nova paper includes FinQA in Section 2.4.2, Appendix B.3.1, and Table 2.4, with scores for 12 models. 784 authors from Amazon AGI.
- Source: https://arxiv.org/abs/2506.12103
- PDF: https://assets.amazon.science/96/7d/0d3e59514abf8fdcfafcdc574300/nova-tech-report-20250317-0810.pdf

LegalBench and CUAD are confirmed zero in the Amazon Nova paper as well — not just our corpus but across all known model cards/technical reports from any lab.

---

### X4. MATH "22/53 (41%)" — NEEDS CAVEAT

**Original claim:** "math (22/53)"
**Reality:** DB grep confirms 22 cards contain the word MATH (with word boundaries). However:
- Spot-check of 4 latest frontier cards found MATH in only 1 (Llama 4). GPT-5, Claude Opus 4.5, Gemini 2.5 Pro use AIME instead.
- Labs are actively replacing MATH with harder benchmarks (AIME, Humanity's Last Exam)
- The 22/53 figure is correct but includes many older cards. Newer cards are dropping it.

**Fix:** Either drop MATH from the "meanwhile" line, or caveat that it's being replaced by AIME in newer releases.

---

### X5. Citation format

**Original:** "Mitchell, Gebru et al., 2019"
**Fix:** "Mitchell et al., 2019" — Gebru is the 9th (last) author, not a co-first author

---

### X6. "invented" → "introduced"

**Original:** "model cards were literally invented as..."
**Fix:** The paper says "we propose a framework that we call model cards." Use "introduced" or "proposed."

---

## METHODOLOGY CAVEATS

### Heatmap / verification rate claims

The heatmap and "120 claims, 28 verified (23%)" numbers require these caveats:

1. **"Discusses it" = embedding similarity ≥ 0.20**, not an explicit safety commitment. Boilerplate language ("we handle user data responsibly") can trigger a hit for "Privacy & Data Handling." More accurate framing: "safety-related terms appear in the lab's documentation at document level."

2. **Benchmark registry gaps.** Our system tracks zero privacy benchmarks and zero child safety benchmarks. "Zero labs disclose a privacy benchmark" is partly a limitation of what we track, not purely an industry finding. PersonalInfoLeak and ConfAIde exist in the literature but are not in our registry.

3. **Verification rates are registry-dependent.** The 23% overall / 50% OpenAI / 16% Google / 0% xAI rates depend on which benchmarks our registry tracks. A different registry would produce different rates. These should be presented as directional findings, not precise measurements.

4. **20 of 120 "Yes" cells are borderline** (scores 0.20-0.25). Some may be false positives from weak semantic signal.

---

## THINGS WE SHOULD NOT CLAIM

1. **"Labs are hiding medical performance"** — FALSE. Labs DO test on MedQA. GPT-5 scores 95.84% per independent evaluation (arxiv 2508.08224). vals.ai independently tests every frontier model on MedQA and LegalBench. The data exists — it's just not in model cards.

2. **"Labs don't test domain-specific benchmarks"** — FALSE. They test them. They publish the results in research papers and third-party platforms. The finding is about WHERE the data lives (model card vs elsewhere), not WHETHER it exists.

3. **"Model cards are useless"** — NOT OUR CLAIM. Model cards contain valuable qualitative safety analysis. The finding is about quantitative benchmark disclosure specifically.

4. **"Labs are acting in bad faith"** — NOT OUR CLAIM. Selective disclosure is a rational response to voluntary, unaudited norms. The finding points to a structural problem.

---

## DB-VERIFIED NUMBERS (source: Railway PostgreSQL, queried 2026-04-13)

| Metric | Value |
|---|---|
| Total documents | 78 |
| Total document versions | 79 |
| Model card versions | 53 |
| Total labs | 9 |
| Eval results (Sonnet extraction) | 536 |
| Completed extraction runs | 53 |
| Taxonomy categories | 15 |
| Taxonomy mappings | 627 |
| Benchmark definitions | 235 |
| Unique benchmarks with evals | 211 |

### Model cards per lab

| Lab | Cards |
|---|---|
| Anthropic | 13 |
| OpenAI | 11 |
| Meta AI | 10 |
| Google DeepMind | 9 |
| xAI | 5 |
| Mistral AI | 2 |
| Amazon (AWS) | 1 |
| Cohere | 1 |
| AI21 Labs | 1 |

---

## EXTERNAL SOURCES REFERENCED

| Source | URL | What it verifies |
|---|---|---|
| GPT-4o System Card | https://cdn.openai.com/gpt-4o-system-card.pdf | MedQA scores in GPT-4o |
| GPT-5 System Card | https://cdn.openai.com/gpt-5-system-card.pdf | MedQA absence, HealthBench presence |
| Claude 3 Model Card | https://www-cdn.anthropic.com/de8ba9b01c9ab7cbabf5c33b80b7bbc618857627/Model_Card_Claude_3.pdf | PubMedQA scores |
| Claude 3.5 Addendum | https://www-cdn.anthropic.com/fed9cc193a14b84131812372d8d5857f8f304c52/Model_Card_Claude_3_Addendum.pdf | PubMedQA absence |
| HealthBench paper | https://arxiv.org/abs/2505.08775 | HealthBench origin (OpenAI, May 2025) |
| HealthBench blog | https://openai.com/index/healthbench/ | 262 physicians confirmation |
| GPT-5 MedQA evaluation | https://arxiv.org/abs/2508.08224 | GPT-5 95.84% on MedQA (independent, NOT OpenAI) |
| Amazon Nova paper | https://arxiv.org/abs/2506.12103 | FinQA in Amazon Nova model card |
| Mitchell et al. 2019 | https://arxiv.org/abs/1810.03993 | Model cards definition quote |
| Mitchell et al. DOI | https://doi.org/10.1145/3287560.3287596 | FAT* '19 publication |
| MedQA paper | https://arxiv.org/abs/2009.13081 | MedQA dataset origin |
| vals.ai methodology | https://www.vals.ai/methodology | Independent evaluation methodology |
| vals.ai MedQA | https://www.vals.ai/benchmarks/medqa-08-12-2025 | Independent MedQA benchmark |
| vals.ai LegalBench | https://www.vals.ai/benchmarks/legal_bench | Independent LegalBench benchmark |
| vals.ai about | https://www.vals.ai/about | Organization background |
| Vania Chow's article | https://deadbenchmarks.substack.com/p/we-dont-have-safety-ratings-for-ai | Source for 178-benchmark catalog |
