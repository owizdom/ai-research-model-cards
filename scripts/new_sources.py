"""New sources for Model Card Explorer collector registry.

Verified 2026-04-17. All URLs confirmed 200 via HEAD checks; benchmark
coverage verified via HTML mirrors where possible. arxiv uses /pdf/{id}.
"""

NEW_LABS = [
    {"slug": "deepseek", "name": "DeepSeek", "country": "CN", "website": "https://www.deepseek.com"},
    {"slug": "alibaba", "name": "Alibaba (Qwen)", "country": "CN", "website": "https://qwenlm.github.io"},
]

NEW_SOURCES = [
    # AI21 (currently 0 evals)
    {
        "slug": "ai21_jamba_1_5_paper", "lab_slug": "ai21",
        "title": "Jamba-1.5: Hybrid Transformer-Mamba Models at Scale",
        "doc_type": "technical_paper", "url": "https://arxiv.org/pdf/2408.12570",
        "method": "pdf", "selector": None, "track_history": True,
        "justification": "Primary Jamba 1.5 Mini (12B) + Large (94B) paper. HTML mirror verified: MMLU, MMLU-Pro, GSM8K, HumanEval, BBH, ARC-C, GPQA, IFEval, BFCL, RealToxicity, TruthfulQA; Section 6.1 table.",
    },
    {
        "slug": "ai21_jamba_family_announcement", "lab_slug": "ai21",
        "title": "The Jamba 1.5 Open Model Family announcement",
        "doc_type": "model_card", "url": "https://www.ai21.com/blog/announcing-jamba-model-family/",
        "method": "html", "selector": None, "track_history": True,
        "justification": "HTML-verified: Arena Hard (Mini 46.1, Large 65.4) and RULER long-context numbers.",
    },

    # Cohere (currently 0 evals)
    {
        "slug": "cohere_command_a_paper", "lab_slug": "cohere",
        "title": "Command A: An Enterprise-Ready Large Language Model",
        "doc_type": "technical_paper", "url": "https://arxiv.org/pdf/2504.00698",
        "method": "pdf", "selector": None, "track_history": True,
        "justification": "March 2025 Command A (111B) + Command R7B technical report with RAG, tool-use, multilingual benchmarks.",
    },

    # Mistral (currently 0 evals)
    {
        "slug": "mistral_large_2_blog", "lab_slug": "mistral",
        "title": "Mistral Large 2 Release (Large Enough)",
        "doc_type": "model_card", "url": "https://mistral.ai/news/mistral-large-2407",
        "method": "html", "selector": None, "track_history": True,
        "justification": "HTML-verified: MMLU 84.0, GSM8K, MATH, HumanEval 92.0, Multilingual MMLU (9 languages).",
    },
    {
        "slug": "mistral_small_3_blog", "lab_slug": "mistral",
        "title": "Mistral Small 3 Release",
        "doc_type": "model_card", "url": "https://mistral.ai/news/mistral-small-3",
        "method": "html", "selector": None, "track_history": True,
        "justification": "HTML-verified: MMLU ~81, side-by-side vs Llama 3.3 70B, Qwen 2.5 32B, GPT-4o-mini.",
    },
    {
        "slug": "mistral_small_3_hf_card", "lab_slug": "mistral",
        "title": "Mistral Small 24B Instruct 2501 Model Card",
        "doc_type": "model_card",
        "url": "https://huggingface.co/mistralai/Mistral-Small-24B-Instruct-2501/raw/main/README.md",
        "method": "raw", "selector": None, "track_history": True,
        "justification": "Raw HF card, verified: MMLU-Pro CoT 66.3, GPQA CoT 45.3, HumanEval pass@1 84.8, math_instruct 70+; full side-by-side tables.",
    },
    {
        "slug": "mistral_codestral_blog", "lab_slug": "mistral",
        "title": "Codestral Release Blog",
        "doc_type": "model_card", "url": "https://mistral.ai/news/codestral",
        "method": "html", "selector": None, "track_history": True,
        "justification": "HTML-verified: HumanEval pass@1, MBPP, CruxEval, RepoBench-EM, Spider; multilingual HumanEval + FIM eval.",
    },

    # Amazon (currently 0 evals)
    {
        "slug": "amazon_nova_tech_report", "lab_slug": "amazon",
        "title": "The Amazon Nova Family of Models: Technical Report and Model Card",
        "doc_type": "technical_paper", "url": "https://arxiv.org/pdf/2506.12103",
        "method": "pdf", "selector": None, "track_history": True,
        "justification": "48-page report on Nova Pro, Lite, Micro, Canvas, Reel: core capabilities, agentic, long context, functional adaptation, runtime, human eval.",
    },
    {
        "slug": "amazon_nova_premier_report", "lab_slug": "amazon",
        "title": "Amazon Nova Premier: Technical Report and Model Card",
        "doc_type": "technical_paper",
        "url": "https://assets.amazon.science/e5/e6/ccc5378c42dca467d1abe1628ec9/amazon-nova-premier-technical-report-and-model-card.pdf",
        "method": "pdf", "selector": None, "track_history": True,
        "justification": "April 2025 addendum for Amazon's flagship Nova Premier with frontier benchmark comparisons.",
    },

    # DeepSeek (NEW lab)
    {
        "slug": "deepseek_v3_paper", "lab_slug": "deepseek",
        "title": "DeepSeek-V3 Technical Report",
        "doc_type": "technical_paper", "url": "https://arxiv.org/pdf/2412.19437",
        "method": "pdf", "selector": None, "track_history": True,
        "justification": "DeepSeek-V3 (671B MoE / 37B active). HTML-verified scores (Table 3): MMLU 87.1, BBH 87.5, DROP 89.0, ARC-E 98.9, ARC-C 95.3, GSM8K 89.3, MATH 61.6, HumanEval 65.2.",
    },
    {
        "slug": "deepseek_r1_paper", "lab_slug": "deepseek",
        "title": "DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via RL",
        "doc_type": "technical_paper", "url": "https://arxiv.org/pdf/2501.12948",
        "method": "pdf", "selector": None, "track_history": True,
        "justification": "DeepSeek-R1 reasoning model. Benchmarks: MMLU, AIME, GSM8K, GPQA, HumanEval, MATH, SimpleQA, CMMLU, LiveCodeBench — comparable to OpenAI o1.",
    },

    # Alibaba / Qwen (NEW lab)
    {
        "slug": "qwen_2_5_paper", "lab_slug": "alibaba",
        "title": "Qwen2.5 Technical Report",
        "doc_type": "technical_paper", "url": "https://arxiv.org/pdf/2412.15115",
        "method": "pdf", "selector": None, "track_history": True,
        "justification": "Qwen 2.5 family (0.5B-72B dense + Turbo/Plus MoE). Covers MMLU, MMLU-Pro, GSM8K, MATH, HumanEval, MBPP, BBH, IFEval, Arena-Hard.",
    },
    {
        "slug": "qwen_2_5_vl_paper", "lab_slug": "alibaba",
        "title": "Qwen2.5-VL Technical Report",
        "doc_type": "technical_paper", "url": "https://arxiv.org/pdf/2502.13923",
        "method": "pdf", "selector": None, "track_history": True,
        "justification": "Qwen2.5-VL (3B/7B/72B). Feb 2025. Benchmarks: DocVQA, ChartQA, MathVista, MMMU, video understanding, object localization.",
    },
    {
        "slug": "qwen_2_5_coder_paper", "lab_slug": "alibaba",
        "title": "Qwen2.5-Coder Technical Report",
        "doc_type": "technical_paper", "url": "https://arxiv.org/pdf/2409.12186",
        "method": "pdf", "selector": None, "track_history": True,
        "justification": "Qwen2.5-Coder, 5.5T code tokens. Benchmarks: HumanEval, MBPP, MultiPL-E, LiveCodeBench + MMLU, ARC-C, TruthfulQA, WinoGrande, HellaSwag.",
    },
    {
        "slug": "qwen_3_paper", "lab_slug": "alibaba",
        "title": "Qwen3 Technical Report",
        "doc_type": "technical_paper", "url": "https://arxiv.org/pdf/2505.09388",
        "method": "pdf", "selector": None, "track_history": True,
        "justification": "Qwen3 (235B MoE flagship + dense 0.6B-32B). 15 benchmarks — flagship AIME'24 85.7, AIME'25 81.5, LiveCodeBench v5 70.7, BFCL v3 70.8.",
    },
    {
        "slug": "qwen_qwq_blog", "lab_slug": "alibaba",
        "title": "QwQ: Reflect Deeply on the Boundaries of the Unknown",
        "doc_type": "model_card", "url": "https://qwenlm.github.io/blog/qwq-32b-preview/",
        "method": "html", "selector": None, "track_history": True,
        "justification": "QwQ-32B-Preview Qwen blog. HTML-verified: GPQA, AIME, MATH-500, LiveCodeBench sections. HF card has no benchmark tables.",
    },
]


SKIPPED = [
    "xai_grok3: no data.x.ai/grok-3 PDF exists; x.ai/news/grok-3 returns 403 to crawlers (Cloudflare). Grok 4/4-Fast/4.1 cards are registered.",
    "ai21_jamba_1_5_hf_card (Mini+Large), mistral_large_2_hf_card, cohere_command_r_plus_hf_card: HF repos gated (401). arxiv/blog cover benchmarks.",
    "openai_o3, openai_o3mini, openai_gpt45, openai_o1: already in registry.py (lines 60-63).",
    "google_gemini_2_card (2.0 Flash), 25_card (2.5 Flash), 25_pro_card, 3_card, 3_pro_card, 31_pro_card, 25dt_card: all already registered (lines 74-80).",
    "meta_llama32_card, meta_responsible_use (Llama 3.3 card), meta_llama4_card: all already registered (lines 88, 94, 97).",
    "anthropic Claude 4.x / 4.5 / 4.6 / Opus 4.6 / Mythos / Sonnet 4.6 / Haiku 4.5: all already registered (lines 38-48).",
    "cohere_command_r_card (docs.cohere.com/docs/command-r-plus): already registered; page is a buildwithfern SPA so html scraping yields no benchmarks. Command A paper supersedes.",
    "frontier_2026 (Claude 5 / GPT-6 / Gemini 4): no verified public model cards as of 2026-04-17. Current flagships already covered.",
]
