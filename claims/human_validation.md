# Human Validation Sample

5 model cards × 39 canonical benchmarks, verified by direct regex against stored content_md.

## Results per card

### Card 1: Claude 3 Model Card (v2, Anthropic)
Found 20/39: MMLU, GPQA, MATH, GSM8K, HumanEval, MBPP, MMMU, ARC, HellaSwag, WinoGrande, BBQ, XSTest, PubMedQA, MedMCQA, USMLE, MGSM, FLORES, ChartQA, DocVQA, MathVista

Not found in THIS card: SWE-bench, BBH/BIG-Bench-Hard, IFEval, AIME, ToxiGen, TruthfulQA, RealToxicityPrompts, MedQA, HealthBench, LegalBench, CUAD, FinQA, XNLI, MMMLU, TriviaQA, Natural Questions, FEVER, LiveCodeBench, BrowseComp

Note: BBH ("BIG-Bench-Hard") IS in this card per independent audit (Claude 3 Table 1 p.6) but our regex for "BIG-Bench Hard" (space) doesn't match "BIG-Bench-Hard" (hyphen). ALIAS BUG — need to add hyphen variant to regex.

Note: MedMCQA and USMLE are CITATION REFERENCES ("We use... USMLE [70], and MedMCQA [71]"), not scored benchmarks. The scored/mentioned distinction in the deploy API addresses this.

### Card 2: GPT-4o System Card (v11, OpenAI)
Found 10/39: MMLU, MATH, SWE-bench, ARC, HellaSwag, TruthfulQA, MedQA, MedMCQA, USMLE, TriviaQA

Not found: GPQA, GSM8K, HumanEval, MBPP, MMMU, BBH, WinoGrande, IFEval, AIME, BBQ, ToxiGen, XSTest, RealToxicityPrompts, PubMedQA, HealthBench, LegalBench, CUAD, FinQA, MGSM, FLORES, XNLI, MMMLU, Natural Questions, FEVER, ChartQA, DocVQA, MathVista, LiveCodeBench, BrowseComp

Note: This is a SAFETY-focused system card. Capability benchmarks like HumanEval, GPQA, MMMU are in OpenAI's separate Technical Report, not this document.

### Card 3: Grok 4 Model Card (v35, xAI)
Found 0/39.

Confirmed: xAI's Grok 4 card is a pure safety/biosecurity report using only proprietary benchmarks (BioLP-Bench, VCT, WMDP Bio, AgentHarm, AgentDojo, MASK, etc.). Zero overlap with the 39 canonical benchmarks.

### Card 4: Llama 4 Model Card (v31, Meta)
Found 10/39: MMLU, GPQA, MATH, MBPP, MMMU, MGSM, ChartQA, DocVQA, MathVista, LiveCodeBench

Not found: GSM8K, HumanEval, SWE-bench, BBH, ARC, HellaSwag, WinoGrande, IFEval, AIME, BBQ, ToxiGen, XSTest, TruthfulQA, RealToxicityPrompts, MedQA, PubMedQA, MedMCQA, HealthBench, USMLE, LegalBench, CUAD, FinQA, FLORES, XNLI, MMMLU, TriviaQA, Natural Questions, FEVER, BrowseComp

Note: Llama 4 card is newer and shorter than Llama 3.1 paper. Many benchmarks (GSM8K, HumanEval, BBH, ARC, HellaSwag, etc.) appeared in OLDER Llama cards but were dropped from Llama 4.

### Card 5: GPT-5 System Card (v12, OpenAI)
Found 4/39: MMLU, SWE-bench, BBQ, HealthBench

Confirmed: GPT-5 System Card is heavily safety-focused. Only 4 of the 39 canonical benchmarks appear. HealthBench (OpenAI's own) is prominently featured. Standard capability benchmarks (GPQA, MATH, AIME, HumanEval) are absent from the system card.

## Cross-reference against CSV export

The per-LAB CSV aggregates across ALL cards. So Anthropic's row reflects Claude 2 + Claude 3 + Claude 3.5 + ... + Mythos combined. This validation checks individual cards, which is stricter.

Key consistency checks:
- Anthropic × BBH = 0 in CSV → but BBH IS in Claude 3 card (hyphen alias bug). FIX NEEDED.
- OpenAI × HumanEval = 0 in CSV → confirmed absent from both GPT-4o and GPT-5 system cards. CORRECT.
- xAI × all = 0 → confirmed. CORRECT.
- Llama 4 dropped GSM8K, HumanEval, BBH, ARC, HellaSwag from Llama 3.x. CONFIRMED temporal narrowing.

## Validation methodology

- Direct PostgreSQL regex `content_md ~* '\mBENCHMARK\M'` against stored document content
- Word-boundary matching (PostgreSQL `\m...\M` = start/end of word)
- Each benchmark checked individually with explicit alias variants
- 5 cards selected for diversity: 2 labs with most coverage (Anthropic, OpenAI), 1 with zero (xAI), 1 mid-tier (Meta), 1 safety-focused (GPT-5)

## Known limitations

1. Word-boundary regex cannot distinguish SCORED benchmarks from CITATION REFERENCES (e.g., "MedMCQA [71]" matches the same as "MedMCQA: 78.3%")
2. Benchmark name variants with hyphens vs spaces are not fully aliased (BBH/BIG-Bench-Hard bug)
3. This validation checks regex against stored content_md, not against the original PDF — if PDF extraction lost text, the regex would show FALSE even if the original PDF had the benchmark
