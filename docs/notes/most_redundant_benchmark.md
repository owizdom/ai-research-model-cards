# The most redundant benchmark

Note on Du, Ji et al., "Which LLM Benchmarks Are Redundant? A Correlation
and Dimensionality Analysis" (clawrxiv:2603.00394, Mar 31 2026). Six
common benchmarks across 40 published models, PCA + hierarchical
clustering + greedy selection.

## The headline number

The first two principal components explain **97.4%** of the variance
across all six benchmarks — meaning the six are doing almost two
independent jobs, not six. PC1 (74.0%) tracks model scale; PC2 (23.4%)
tracks essentially TruthfulQA.

## Which benchmark is "most redundant"

The candidate is **WinoGrande**.

| pair | correlation |
|---|---|
| ARC-Challenge ↔ WinoGrande | r = 0.985 |
| HellaSwag ↔ WinoGrande | r = 0.971 |
| MMLU ↔ GSM8K | r = 0.967 |

WinoGrande is the only benchmark that appears in the top correlated
pairs with *two* other benchmarks. ARC-Challenge and HellaSwag each
recover almost all of WinoGrande's signal on their own. The paper's
"minimal sufficient set" keeps ARC-Challenge and drops WinoGrande:

> ARC-Challenge + TruthfulQA recovers 95.4% of total variance.
> Adding GSM8K brings this to 98.2%.

So in the greedy-selection result, WinoGrande never gets picked —
it's strictly dominated by ARC-Challenge.

## Why TruthfulQA is the survivor

The five "general capability" benchmarks (MMLU, ARC, HellaSwag,
WinoGrande, GSM8K) all load onto PC1 — model-scale. They're measuring
"is this a bigger model" with different question styles. TruthfulQA
loads onto PC2 with *negative* correlations to the others: it's the
only benchmark that doesn't reward general capability scaling. That's
why it's in every minimal sufficient set even though it's a smaller
benchmark.

## Implication for our corpus

Cards in our DB report all six of these benchmarks often. The paper
suggests we can compress the "general capability" axis to one
benchmark (ARC-Challenge is the paper's pick; MMLU is the
community's). Keeping WinoGrande as a separate column on dashboard
comparison tables adds visual width but almost no analytical
information beyond what's already in ARC-Challenge.

A defensible reporting axis would be:
- ARC-Challenge (or MMLU) for general capability
- GSM8K for math reasoning
- TruthfulQA for orthogonal truthfulness signal

Three columns; 98.2% of the six-column information per the paper.

## Re-running the analysis on *our* corpus

The paper used 40 published models spanning 70M to 70B parameters
across 11 families (mostly older / smaller open-weights). Our corpus
is the opposite: ~50 frontier model cards from Anthropic, OpenAI,
Google DeepMind, Meta, Mistral, xAI. We replicated the correlation
analysis against our `eval_results` table to see whether the paper's
conclusions hold up at our slice of the scale curve.

### Top 10 benchmarks by distinct-model coverage in our corpus

| benchmark | distinct models | |
|---|---|---|
| MMLU | 37 | |
| MATH | 23 | |
| GPQA | 17 | |
| MGSM | 16 | |
| MMMU | 14 | |
| SWE-bench | 14 | |
| GPQA-Diamond | 13 | |
| HumanEval | 11 | |
| TruthfulQA | 11 | |
| MBPP | 11 | |

### Strongest correlations in our data (n = shared models)

| pair | r | n |
|---|---|---|
| HumanEval ↔ MBPP | **+0.983** | 5 |
| MMLU ↔ TruthfulQA | +0.956 | 8 |
| MGSM ↔ HumanEval | +0.922 | 8 |
| MGSM ↔ GPQA-Diamond | +0.908 | 5 |
| MMLU ↔ GPQA-Diamond | +0.889 | 11 |
| MATH ↔ MBPP | +0.868 | 11 |
| GPQA ↔ HumanEval | +0.864 | 6 |
| SWE-bench ↔ GPQA-Diamond | +0.853 | 7 |
| MMMU ↔ GPQA-Diamond | +0.847 | 8 |
| MATH ↔ HumanEval | +0.808 | 9 |

### Average |r| with other benchmarks (higher = more redundant)

| benchmark | avg \|r\| | n pairs |
|---|---|---|
| HumanEval | **0.806** | 5 |
| GPQA-Diamond | 0.710 | 5 |
| MGSM | 0.694 | 7 |
| MBPP | 0.660 | 5 |
| GPQA | 0.604 | 6 |
| MMLU | 0.589 | 9 |
| MATH | 0.548 | 7 |
| MMMU | 0.463 | 6 |
| **SWE-bench** | **0.412** | 3 |

(TruthfulQA excluded — only 1 pair with sufficient n, see note.)

### What our corpus says

- **Most redundant benchmark: HumanEval.** r = 0.983 with MBPP, plus
  high correlations with MATH, MGSM, GPQA. Drop HumanEval, keep MBPP,
  and you preserve the code-generation signal almost intact.
- **Least redundant: SWE-bench and MMMU.** Agentic coding
  (SWE-bench) and multimodal reasoning (MMMU) sit further from the
  general-scaling axis than the rest. They earn their column.
- **Where we disagree with the paper: TruthfulQA.** Du et al. had
  TruthfulQA on its own principal component, *negatively* correlated
  with the capability cluster. In our corpus MMLU ↔ TruthfulQA =
  +0.956. The likely cause is the model population: their 40 models
  span 70M–70B with weaker models on the low end; ours is almost all
  frontier (Claude 4.x, GPT-5.x, Gemini 3, Llama 4). At the frontier
  end of the scale curve, TruthfulQA scores climb with everything
  else — so the "truthfulness is a separate axis" claim degrades
  precisely at the slice of models we care about.

### Caveats

- Sample sizes are small (n = 5–15 shared models per pair). 95%
  CIs around these correlations are wide; treat the rank order as
  more reliable than the absolute r values.
- We aggregated across split/method variants with a median. A
  proper analysis would split MMLU-base vs MMLU-Pro, GPQA vs
  GPQA-Diamond, etc.
- Comparison rows have been purged from the corpus (only each card's
  primary model is reported), which reduces n per pair. Re-running
  this with the multi-model rows intact would give tighter
  correlations.

### Implication for our dashboards

For the modelcards.net comparison surface, three benchmarks would
carry most of the information from our top-10:

- **MMLU** — general capability
- **SWE-bench** — orthogonal agentic-coding signal
- **MMMU** — orthogonal multimodal signal

MATH/GPQA/MGSM/HumanEval/MBPP largely re-tell the same story as MMLU
once you have a few of them. They're not wrong to display — they're
just redundant with MMLU at the frontier slice.
