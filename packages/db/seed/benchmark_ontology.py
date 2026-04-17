"""Canonical benchmark ontology — single source of truth.

Each entry enumerates:
  slug, name, category, description, metric_name, metric_unit,
  higher_is_better, score_min, score_max, source_url, aliases.

Policy decisions baked in:
- MultiPL-E is NOT a benchmark; its language variants map to humaneval
  or mbpp with language carried in the variant string. See MIGRATION_PLAN.
- MMLU-2021 and MMLU-2024 are one entry for now; temporal versioning
  is a separate sprint item.
- Subsets with independent provenance (GPQA Diamond, SWE-bench Verified)
  get their own entries.
"""

CATEGORIES = {
    "general_knowledge", "reasoning", "math", "coding", "multimodal",
    "safety", "multilingual", "agent", "long_context", "medical", "legal",
    "finance",
}

METRIC_UNITS = {"percent", "score", "elo", "pass_at_k", "f1", "bleu", "rouge", "perplexity"}


BENCHMARKS = [
    # ── general_knowledge ───────────────────────────────────────────────
    {
        "slug": "mmlu", "name": "MMLU", "category": "general_knowledge",
        "description": "Massive Multitask Language Understanding — 57 multiple-choice subject categories.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2009.03300",
        "aliases": ["Massive Multitask Language Understanding", "MMLU (5-shot)"],
    },
    {
        "slug": "mmlu_pro", "name": "MMLU-Pro", "category": "general_knowledge",
        "description": "Harder MMLU successor with 10 answer choices and more reasoning-heavy items.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2406.01574",
        "aliases": ["MMLU Pro"],
    },
    {
        "slug": "mmmlu", "name": "Multilingual MMLU", "category": "multilingual",
        "description": "MMLU translated into 14+ languages.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "",
        "aliases": ["MMMLU", "Multilingual-MMLU"],
    },
    {
        "slug": "big_bench_hard", "name": "BIG-Bench Hard", "category": "reasoning",
        "description": "23 challenging tasks from BIG-Bench where prior LMs under-performed humans.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2210.09261",
        "aliases": ["BBH", "BIG-Bench-Hard", "BigBenchHard"],
    },
    {
        "slug": "arc_challenge", "name": "ARC-Challenge", "category": "general_knowledge",
        "description": "AI2 Reasoning Challenge — grade-school science multiple-choice.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/1803.05457",
        "aliases": ["ARC", "ARC Challenge"],
    },
    {
        "slug": "hellaswag", "name": "HellaSwag", "category": "reasoning",
        "description": "Commonsense sentence-completion.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/1905.07830",
        "aliases": [],
    },
    {
        "slug": "winogrande", "name": "WinoGrande", "category": "reasoning",
        "description": "Large-scale Winograd Schema Challenge for commonsense.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/1907.10641",
        "aliases": [],
    },
    {
        "slug": "truthfulqa", "name": "TruthfulQA", "category": "safety",
        "description": "Questions designed to elicit imitative falsehoods.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2109.07958",
        "aliases": [],
    },
    {
        "slug": "triviaqa", "name": "TriviaQA", "category": "general_knowledge",
        "description": "Open-domain factoid question answering.",
        "metric_name": "exact_match", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/1705.03551",
        "aliases": [],
    },
    {
        "slug": "natural_questions", "name": "Natural Questions", "category": "general_knowledge",
        "description": "Google NQ — real queries to Google Search with answer spans.",
        "metric_name": "exact_match", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "",
        "aliases": ["NQ", "NaturalQuestions"],
    },
    {
        "slug": "fever", "name": "FEVER", "category": "general_knowledge",
        "description": "Fact Extraction and VERification over Wikipedia.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/1803.05355",
        "aliases": [],
    },

    # ── reasoning ────────────────────────────────────────────────────────
    {
        "slug": "gpqa", "name": "GPQA", "category": "reasoning",
        "description": "Graduate-Level Google-Proof Q&A — expert-written STEM questions.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2311.12022",
        "aliases": ["GPQA-Main"],
    },
    {
        "slug": "gpqa_diamond", "name": "GPQA-Diamond", "category": "reasoning",
        "description": "Hardest curated subset of GPQA (198 highest-quality questions).",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2311.12022",
        "aliases": ["GPQA Diamond"],
    },
    {
        "slug": "aime_2024", "name": "AIME 2024", "category": "math",
        "description": "American Invitational Math Exam 2024 problem set.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "",
        "aliases": ["AIME24"],
    },
    {
        "slug": "aime_2025", "name": "AIME 2025", "category": "math",
        "description": "American Invitational Math Exam 2025 problem set.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "",
        "aliases": ["AIME25"],
    },
    {
        "slug": "aime", "name": "AIME", "category": "math",
        "description": "AIME (unspecified year — see aime_2024/aime_2025 for versioned).",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "",
        "aliases": [],
    },
    {
        "slug": "arc_agi", "name": "ARC-AGI", "category": "reasoning",
        "description": "Abstraction and Reasoning Corpus — few-shot visual pattern reasoning.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "",
        "aliases": ["ARC-AGI-1"],
    },
    {
        "slug": "arc_agi_2", "name": "ARC-AGI-2", "category": "reasoning",
        "description": "Second generation of ARC-AGI; verified subset of harder tasks.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "",
        "aliases": ["ARC-AGI-2 Verified"],
    },

    # ── math ─────────────────────────────────────────────────────────────
    {
        "slug": "math", "name": "MATH", "category": "math",
        "description": "12,500 competition-math problems with step-by-step solutions.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2103.03874",
        "aliases": ["MATH Benchmark", "Hendrycks MATH"],
    },
    {
        "slug": "gsm8k", "name": "GSM8K", "category": "math",
        "description": "Grade-school math word problems.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2110.14168",
        "aliases": [],
    },
    {
        "slug": "mgsm", "name": "MGSM", "category": "multilingual",
        "description": "Multilingual grade-school math (GSM8K translated into 10 languages).",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2210.03057",
        "aliases": ["Multilingual GSM8K"],
    },

    # ── coding ───────────────────────────────────────────────────────────
    {
        "slug": "humaneval", "name": "HumanEval", "category": "coding",
        "description": "164 hand-written Python programming problems. Language variants (via MultiPL-E) live as variants.",
        "metric_name": "pass_at_1", "metric_unit": "pass_at_k", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2107.03374",
        "aliases": ["HumanEval+", "HumanEval Python"],
    },
    {
        "slug": "mbpp", "name": "MBPP", "category": "coding",
        "description": "Mostly Basic Python Problems. Language variants (via MultiPL-E) live as variants.",
        "metric_name": "pass_at_1", "metric_unit": "pass_at_k", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2108.07732",
        "aliases": ["MBPP+"],
    },
    {
        "slug": "swe_bench", "name": "SWE-bench", "category": "coding",
        "description": "Real GitHub issues from 12 Python repos; model must produce a fixing patch.",
        "metric_name": "resolved", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2310.06770",
        "aliases": ["SWE-Bench"],
    },
    {
        "slug": "swe_bench_verified", "name": "SWE-bench Verified", "category": "coding",
        "description": "Human-verified subset of SWE-bench (500 problems).",
        "metric_name": "resolved", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://openai.com/index/introducing-swe-bench-verified/",
        "aliases": ["SWE-Bench Verified"],
    },
    {
        "slug": "livecodebench", "name": "LiveCodeBench", "category": "coding",
        "description": "Contamination-resistant coding benchmark using problems dated after model training cutoff.",
        "metric_name": "pass_at_1", "metric_unit": "pass_at_k", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2403.07974",
        "aliases": ["Live Code Bench"],
    },
    {
        "slug": "bfcl", "name": "BFCL", "category": "coding",
        "description": "Berkeley Function Calling Leaderboard — tool-use / function-calling evaluation.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://gorilla.cs.berkeley.edu/leaderboard.html",
        "aliases": ["Berkeley Function Calling"],
    },
    {
        "slug": "agentic_coding", "name": "Agentic Coding", "category": "coding",
        "description": "Anthropic internal agentic-coding benchmark surfaced in Opus 4.x system cards.",
        "metric_name": "success_rate", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "",
        "aliases": [],
    },

    # ── multimodal ───────────────────────────────────────────────────────
    {
        "slug": "mmmu", "name": "MMMU", "category": "multimodal",
        "description": "Massive Multi-discipline Multimodal Understanding (11,500 college-level items).",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2311.16502",
        "aliases": ["MMMU-Pro"],
    },
    {
        "slug": "mathvista", "name": "MathVista", "category": "multimodal",
        "description": "Visual mathematical reasoning benchmark.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2310.02255",
        "aliases": ["MathVista testmini"],
    },
    {
        "slug": "chartqa", "name": "ChartQA", "category": "multimodal",
        "description": "Question answering over charts and plots.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2203.10244",
        "aliases": [],
    },
    {
        "slug": "docvqa", "name": "DocVQA", "category": "multimodal",
        "description": "Question answering over document images.",
        "metric_name": "anls", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2007.00398",
        "aliases": [],
    },

    # ── safety ───────────────────────────────────────────────────────────
    {
        "slug": "bbq", "name": "BBQ", "category": "safety",
        "description": "Bias Benchmark for QA — social bias across 9 categories.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2110.08193",
        "aliases": [],
    },
    {
        "slug": "toxigen", "name": "ToxiGen", "category": "safety",
        "description": "Toxicity detection on AI-generated adversarial statements.",
        "metric_name": "toxicity_rate", "metric_unit": "percent", "higher_is_better": False,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2203.09509",
        "aliases": [],
    },
    {
        "slug": "xstest", "name": "XSTest", "category": "safety",
        "description": "Exaggerated Safety Test — false-refusal rate on safe queries.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2308.01263",
        "aliases": [],
    },
    {
        "slug": "realtoxicityprompts", "name": "RealToxicityPrompts", "category": "safety",
        "description": "Toxicity of model continuations on web-scraped prompts.",
        "metric_name": "toxicity", "metric_unit": "score", "higher_is_better": False,
        "score_min": 0.0, "score_max": 1.0,
        "source_url": "https://arxiv.org/abs/2009.11462",
        "aliases": ["Real Toxicity Prompts"],
    },

    # ── medical ──────────────────────────────────────────────────────────
    {
        "slug": "medqa", "name": "MedQA", "category": "medical",
        "description": "USMLE-style medical QA (USMLE Step 1-3).",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2009.13081",
        "aliases": ["MedQA-USMLE"],
    },
    {
        "slug": "pubmedqa", "name": "PubMedQA", "category": "medical",
        "description": "Yes/no/maybe biomedical QA over PubMed abstracts.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/1909.06146",
        "aliases": [],
    },
    {
        "slug": "medmcqa", "name": "MedMCQA", "category": "medical",
        "description": "Indian medical school entrance MCQs.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2203.14371",
        "aliases": [],
    },
    {
        "slug": "healthbench", "name": "HealthBench", "category": "medical",
        "description": "OpenAI's realistic physician-written health conversations benchmark.",
        "metric_name": "score", "metric_unit": "score", "higher_is_better": True,
        "score_min": 0.0, "score_max": 1.0,
        "source_url": "https://arxiv.org/abs/2505.08775",
        "aliases": [],
    },
    {
        "slug": "usmle", "name": "USMLE", "category": "medical",
        "description": "US Medical Licensing Exam style questions (distinct from MedQA).",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "",
        "aliases": [],
    },

    # ── legal ────────────────────────────────────────────────────────────
    {
        "slug": "legalbench", "name": "LegalBench", "category": "legal",
        "description": "Collaborative legal reasoning benchmark (162 tasks).",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2308.11462",
        "aliases": [],
    },
    {
        "slug": "cuad", "name": "CUAD", "category": "legal",
        "description": "Contract Understanding Atticus Dataset — legal contract review.",
        "metric_name": "f1", "metric_unit": "f1", "higher_is_better": True,
        "score_min": 0.0, "score_max": 1.0,
        "source_url": "https://arxiv.org/abs/2103.06268",
        "aliases": [],
    },

    # ── finance ──────────────────────────────────────────────────────────
    {
        "slug": "finqa", "name": "FinQA", "category": "finance",
        "description": "Financial reasoning over annual-report tables + text.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2109.00122",
        "aliases": [],
    },

    # ── multilingual ─────────────────────────────────────────────────────
    {
        "slug": "flores", "name": "FLORES", "category": "multilingual",
        "description": "FLORES-200 evaluation benchmark for 200 languages MT.",
        "metric_name": "spbleu", "metric_unit": "bleu", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2207.04672",
        "aliases": ["FLORES-200"],
    },
    {
        "slug": "xnli", "name": "XNLI", "category": "multilingual",
        "description": "Cross-lingual natural language inference (15 languages).",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/1809.05053",
        "aliases": [],
    },

    # ── agent ────────────────────────────────────────────────────────────
    {
        "slug": "webarena", "name": "WebArena", "category": "agent",
        "description": "Realistic web task benchmark (shopping, maps, wiki, etc).",
        "metric_name": "success_rate", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2307.13854",
        "aliases": [],
    },
    {
        "slug": "osworld", "name": "OSWorld", "category": "agent",
        "description": "Real OS screenshot/action benchmark.",
        "metric_name": "success_rate", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2404.07972",
        "aliases": [],
    },
    {
        "slug": "osworld_verified", "name": "OSWorld-Verified", "category": "agent",
        "description": "Human-verified subset of OSWorld.",
        "metric_name": "success_rate", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "",
        "aliases": ["OSWorld Verified"],
    },
    {
        "slug": "browsecomp", "name": "BrowseComp", "category": "agent",
        "description": "Browser-based information-retrieval research agent benchmark.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "",
        "aliases": [],
    },
    {
        "slug": "cybench", "name": "Cybench", "category": "agent",
        "description": "Cybersecurity capability-evaluation benchmark (CTF-style).",
        "metric_name": "pass_at_k", "metric_unit": "pass_at_k", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2408.08926",
        "aliases": [],
    },
    {
        "slug": "cybergym", "name": "CyberGym", "category": "agent",
        "description": "Cybersecurity agent benchmark with broad attack-defense tasks.",
        "metric_name": "pass_at_1", "metric_unit": "pass_at_k", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "",
        "aliases": [],
    },
    {
        "slug": "nexus", "name": "Nexus", "category": "agent",
        "description": "Function-calling benchmark used in Llama 3.1 paper.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "",
        "aliases": [],
    },

    # ── long_context ─────────────────────────────────────────────────────
    {
        "slug": "infinitebench_en_mc", "name": "InfiniteBench En.MC", "category": "long_context",
        "description": "Long-context multiple-choice English subset of InfiniteBench.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2402.13718",
        "aliases": ["InfiniteBench"],
    },
    {
        "slug": "nih_multi_needle", "name": "Needle-in-a-Haystack Multi", "category": "long_context",
        "description": "Needle-in-a-haystack retrieval with multiple targets — long-context stress test.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "",
        "aliases": ["NIAH Multi", "NIH multi-needle"],
    },
    {
        "slug": "quality", "name": "QuALITY", "category": "long_context",
        "description": "Question Answering with Long Input Texts, Yes! — long-context MC.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2112.08608",
        "aliases": [],
    },

    # ── instruction following ────────────────────────────────────────────
    {
        "slug": "ifeval", "name": "IFEval", "category": "reasoning",
        "description": "Verifiable instruction-following prompts.",
        "metric_name": "accuracy", "metric_unit": "percent", "higher_is_better": True,
        "score_min": 0.0, "score_max": 100.0,
        "source_url": "https://arxiv.org/abs/2311.07911",
        "aliases": [],
    },
]


MIGRATION_PLAN = {
    # MultiPL-E rows are not a distinct benchmark — each variant maps to
    # either humaneval or mbpp based on the suffix in the variant string.
    "multipl_e": {
        "action": "delete",
        "migrate_rows": "reassign_to_humaneval_or_mbpp_by_variant_suffix",
        "notes": (
            "Rows like multipl_e|variant=C++/HumanEval|... become "
            "humaneval|variant=C++|... and multipl_e|variant=C#/MBPP become "
            "mbpp|variant=C#. Same score, cleaner ontology."
        ),
    },
}
