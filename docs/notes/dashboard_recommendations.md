# Dashboard Improvement Recommendations

Based on research across Stanford FMTI, OECD AI Observatory, AI Incident Database, Epoch AI, Chatbot Arena, HELM, HuggingFace Open LLM Leaderboard, Vals.ai, and cross-industry disclosure frameworks (SEC, FDA, NHTSA/Euro NCAP, CDP).

---

## Core Design Principle

**Make absence visible.** Every effective transparency tool (EFF scorecard, Freedom House ratings, Stanford FMTI) works because it creates a standardized expectation and then shows who falls short. The taxonomy of "what should be disclosed" is more important than the data collected. Define the standard first, then grade against it.

## Proven: Public Scoring Changes Lab Behavior

Stanford's Foundation Model Transparency Index ([crfm.stanford.edu/fmti](https://crfm.stanford.edu/fmti/)) scored 13 labs on 100 yes/no transparency indicators. After the first scoring, **all 8 labs improved — mean +21 points. AI21 jumped +50.** Labs disclosed information they had never previously made public just because someone was scoring them.

Source: [The Foundation Model Transparency Index (2024)](https://arxiv.org/abs/2407.12929)

However, 2025 scores dropped back to ~40/100 when harder indicators were added and new opaque labs entered — proving the grid must evolve to stay effective.

Source: [The 2025 Foundation Model Transparency Index](https://arxiv.org/abs/2512.10169)

---

## Top 7 Features — Ranked by Impact

### 1. Deployment Risk Matrix (Priority: BUILD FIRST)

A grid: labs on one axis, deployment sectors (healthcare, legal, finance, education, government) on the other. Each cell is red/yellow/green based on whether the lab reports domain-specific benchmarks for sectors they actively market to.

A red cell reading **"Deployed to 12 hospitals. 0 medical benchmarks reported."** is the single most useful thing a procurement officer can screenshot.

**Why it works:** Converts abstract transparency concerns into purchasing decisions. This is what gets embedded in RFP documents and board presentations.

**Prior art:** FMTI's binary heatmap, EFF "Who Has Your Back" scorecard.

### 2. Disclosure Score (0-100) (Priority: BUILD FIRST)

Single composite number per lab. Weighted by:
- Benchmark breadth (how many distinct benchmarks reported)
- Domain coverage (medical, legal, financial benchmarks present)
- Consistency across releases (benchmarks not dropped between versions)
- Methodology transparency (eval methodology, prompting strategy, confidence intervals disclosed)

Updated with each model release. Modeled on credit scores — instantly comparable, easy to cite.

**Why it works:** One number = one headline. "Anthropic: 67. OpenAI: 43. xAI: 22." The number itself becomes the story. Journalists, procurement teams, and regulators need a single comparable metric.

**Prior art:** CDP climate disclosure scores (A through F), FMTI percentage scores.

### 3. "What's Missing" Negative Space View (Priority: HIGH)

Instead of showing what labs report, show what they DON'T. A unified benchmark taxonomy (40 benchmarks across 8 domains) with filled/empty cells per lab. The visual weight of absence is more powerful than presence.

- Filled star = benchmark reported
- Empty circle = benchmark exists but not reported
- Red X = previously reported, then dropped

**Why it works:** The FMTI proved that binary yes/no grids where empty cells are visually loud create the strongest pressure. We already have the claims-vs-evidence heatmap — make it the homepage hero.

**Prior art:** FMTI binary heatmap, EFF scorecard checkmark/X pattern.

### 4. Version Diff Tracker (Priority: HIGH)

Show exactly which benchmarks were added or dropped between model releases. Diff format (green additions, red deletions) is universally understood.

Example: "Claude 3 reported 21 benchmarks. Claude 4 reported 5. Here are the 17 that disappeared."

**Why it works:** Catches the pattern of labs quietly removing benchmarks where newer models regress. Makes the deletion visible and attributable. Our data already shows Claude 4 dropped 17/21 benchmarks from Claude 3 in a single generation.

**Prior art:** Epoch AI longitudinal tracking, FMTI edition-over-edition score deltas.

### 5. Buyer Persona Dashboards (Priority: HIGH)

Three filtered views with deployment-specific benchmark relevance:

- **Hospital CTO:** Shows MedQA, MedMCQA, PubMedQA, HealthBench, USMLE coverage per lab
- **Government Procurement:** Shows safety benchmarks, bias/fairness, multilingual coverage per lab
- **Financial Services:** Shows FinQA, math reasoning, RAG accuracy per lab

Each view: "Of N relevant benchmarks, Lab X reports M. Lab Y reports 0."

**Why it works:** A hospital CTO doesn't care about SWE-bench. They care about MedQA. The filtered view gives them exactly the comparison that matters for their purchasing decision.

**Prior art:** Vals.ai domain-segmented benchmarks (law, finance, healthcare).

### 6. Disclosure Trend Timeline (Priority: MEDIUM)

Time-series showing each lab's disclosure breadth (number of distinct benchmarks reported) over releases. Interactive, with model release dates marked.

**Why it works:** If the trend is narrowing — labs reporting fewer benchmarks over time despite deploying to more domains — that is a systemic story. Journalists need trend lines, not snapshots. Our data shows: early cards used 46 unique benchmarks, later cards use 27. Visualize that decline.

**Prior art:** Epoch AI interactive timelines with confidence intervals.

### 7. Public API + Embeddable Widgets (Priority: MEDIUM)

REST API returning structured JSON per lab, per model, per benchmark. Plus embeddable widgets:

- Badge: "Lab X Disclosure Score: 34/100"
- Mini-heatmap: embeddable 3x5 grid for a specific lab
- Comparison widget: side-by-side of two labs on a specific domain

**Why it works:** The data spreading beyond the dashboard is what creates sustained pressure. Journalists embed the badge in articles. Procurement sites reference the API. The dashboard becomes infrastructure, not just a website.

**Prior art:** Papers With Code embeddable leaderboard links, CDP scores used in Bloomberg terminals.

---

## Regulatory Model: Euro NCAP + CDP (No Laws Required)

From cross-industry research, two patterns require zero regulatory authority to implement:

### Euro NCAP Model (Independent Testing)
An independent consortium that buys vehicles off the lot and tests them without manufacturer cooperation. Results published regardless of outcome. Star ratings measurably hurt sales of low-rated vehicles.

**Applied to AI:** The dashboard evaluates models using standardized benchmarks (via vals.ai data or independent runs) and publishes results whether the lab likes them or not. Models don't opt in — if a model is publicly available, it gets evaluated.

Source: [Euro NCAP](https://www.euroncap.com/)

### CDP Model (Score Silence as Failure)
Companies that refuse to respond to CDP climate questionnaires receive an automatic F grade visible to institutional investors. Creates a "disclose or be shamed" dynamic.

**Applied to AI:** Labs that don't provide model card data don't get a blank on the dashboard — they get a failing disclosure grade. Silence is scored, not ignored.

Source: [CDP Scoring Methodology](https://www.cdp.net/en/scores/cdp-scores-explained)

### Combined Approach
Test independently (Euro NCAP) + score silence as failure (CDP). The FMTI already proved this combination moves the needle: +21 points average improvement after first public scoring, with labs proactively disclosing previously-withheld information.

---

## Bonus Features (Build Later)

### 8. Benchmark Cherry-Pick Detector
Flag when a lab reports only benchmarks where it ranks #1 or top-3 and omits benchmarks where competitors score higher. Requires cross-referencing reported results against independent leaderboards (vals.ai). "Lab X reports 4 of 7 reasoning benchmarks — all 4 where it leads."

### 9. Methodology Transparency Grade
Separate from benchmark coverage: does the lab disclose eval methodology, prompting strategy, number of runs, confidence intervals, dataset contamination checks? Grade on A-F. A lab could report 30 benchmarks with zero reproducibility information — this catches that failure mode.

### 10. Cross-Lab Intersection View
UpSet plot showing the set of benchmarks all labs report on. The punchline: only 6 benchmarks are shared by all 4 major labs. This single visualization frames the entire fragmentation problem.

### 11. AI Incident Linkage
Link disclosed (or undisclosed) safety information to real-world harm reports from the AI Incident Database (incidentdatabase.ai). When a model causes a documented incident in healthcare, flag whether the lab had disclosed any medical benchmarks in its model card. Creates a feedback loop between disclosure and consequences.

### 12. Community Flagging
Let users flag disclosures as incomplete or misleading. Combined with contamination-style auditing, prevents the dashboard from becoming a rubber stamp. Borrowed from HuggingFace Open LLM Leaderboard v2.

---

## Build Priority Summary

| Priority | Feature | Effort | Impact |
|---|---|---|---|
| 1 | Claims vs Evidence heatmap as homepage hero | Low (exists) | Immediate |
| 2 | Disclosure Score per lab (0-100) | Medium | High — one number = one headline |
| 3 | Buyer persona views (Healthcare / Legal / Finance) | Medium | High — converts data to procurement decisions |
| 4 | Version diff tracker | Medium | High — catches quiet benchmark deletion |
| 5 | Public API + embed widgets | Medium | Medium — lets data spread beyond dashboard |
| 6 | Disclosure trend timeline | Low (data exists) | Medium — journalists need trend lines |
| 7 | Deployment risk matrix | Medium | Highest — but needs deployment data we don't have yet |

---

## Sources

| Source | URL |
|---|---|
| Stanford FMTI | https://crfm.stanford.edu/fmti/ |
| FMTI 2024 paper | https://arxiv.org/abs/2407.12929 |
| FMTI 2025 paper | https://arxiv.org/abs/2512.10169 |
| FMTI "What Changed" analysis | https://www.techpolicy.press/the-foundation-model-transparency-index-what-changed-in-6-months/ |
| Epoch AI | https://epoch.ai/data/ai-models/ |
| Chatbot Arena | https://lmarena.ai/ |
| HELM | https://crfm.stanford.edu/helm/ |
| Vals.ai | https://www.vals.ai/benchmarks |
| AI Incident Database | https://incidentdatabase.ai/ |
| EU AI Act Article 71 | https://artificialintelligenceact.eu/article/71/ |
| OECD AI Observatory | https://oecd.ai/en/dashboards/overview |
| HuggingFace Open LLM Leaderboard | https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard |
| Euro NCAP | https://www.euroncap.com/ |
| CDP Scoring | https://www.cdp.net/en/scores/cdp-scores-explained |
| EFF "Who Has Your Back" | https://www.eff.org/who-has-your-back |
