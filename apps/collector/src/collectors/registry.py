"""Central source registry — single source of truth for all tracked documents."""
from dataclasses import dataclass


@dataclass
class Source:
    slug: str
    lab_slug: str
    title: str
    doc_type: str   # model_card | usage_policy | constitution | system_prompt
    url: str
    method: str     # html | pdf | raw
    selector: str | None = None
    track_history: bool = True


LAB_META: dict[str, dict] = {
    "anthropic": {"name": "Anthropic",       "website": "https://www.anthropic.com", "color_hex": "#D4791A"},
    "openai":    {"name": "OpenAI",           "website": "https://openai.com",        "color_hex": "#10A37F"},
    "google":    {"name": "Google DeepMind", "website": "https://deepmind.google",   "color_hex": "#4285F4"},
    "meta":      {"name": "Meta AI",          "website": "https://ai.meta.com",       "color_hex": "#0866FF"},
    "mistral":   {"name": "Mistral AI",       "website": "https://mistral.ai",        "color_hex": "#FF7000"},
    "xai":       {"name": "xAI",              "website": "https://x.ai",              "color_hex": "#1DA1F2"},
    "cohere":    {"name": "Cohere",           "website": "https://cohere.com",        "color_hex": "#39594D"},
    "amazon":    {"name": "Amazon (AWS)",     "website": "https://aws.amazon.com/bedrock", "color_hex": "#FF9900"},
    "ai21":      {"name": "AI21 Labs",        "website": "https://www.ai21.com",      "color_hex": "#6C3CE1"},
}

SOURCES: list[Source] = [
    # ── Anthropic ─────────────────────────────────────────────────────────────
    Source("anthropic_usage_policy",   "anthropic", "Acceptable Use Policy",      "usage_policy",  "https://www.anthropic.com/legal/aup",                                              "html"),
    Source("anthropic_claude2_card",   "anthropic", "Claude 2 Model Card",        "model_card",    "https://www-cdn.anthropic.com/bd2a28d2535bfb0494cc8e2a3bf135d2e7523226/Model-Card-Claude-2.pdf", "pdf"),
    Source("anthropic_model_card",     "anthropic", "Claude 3 Model Card",        "model_card",    "https://www-cdn.anthropic.com/de8ba9b01c9ab7cbabf5c33b80b7bbc618857627/Model_Card_Claude_3.pdf", "pdf"),
    Source("anthropic_rsp",            "anthropic", "Responsible Scaling Policy", "constitution",  "https://www.anthropic.com/responsible-scaling-policy",                            "html"),
    Source("anthropic_core_views",     "anthropic", "Core Views on AI Safety",    "constitution",  "https://www.anthropic.com/news/core-views-on-ai-safety",                          "html"),
    Source("anthropic_claude_character","anthropic","Claude's Character",         "constitution",  "https://www.anthropic.com/research/claude-character",                             "html"),
    Source("anthropic_constitutional_ai","anthropic","Constitutional AI Paper",   "constitution",  "https://arxiv.org/abs/2212.08073",                                                "html"),
    Source("anthropic_claude4_card",  "anthropic", "Claude 4 System Card",         "model_card",    "https://www-cdn.anthropic.com/4263b940cabb546aa0e3283f35b686f4f3b2ff47.pdf",    "pdf"),
    Source("anthropic_opus45_card",   "anthropic", "Claude Opus 4.5 System Card",  "model_card",    "https://assets.anthropic.com/m/64823ba7485345a7/Claude-Opus-4-5-System-Card.pdf","pdf"),
    Source("anthropic_sonnet45_card", "anthropic", "Claude Sonnet 4.5 System Card","model_card",    "https://assets.anthropic.com/m/12f214efcc2f457a/original/Claude-Sonnet-4-5-System-Card.pdf", "pdf"),
    Source("anthropic_haiku45_card",  "anthropic", "Claude Haiku 4.5 System Card","model_card",    "https://assets.anthropic.com/m/99128ddd009bdcb/Claude-Haiku-4-5-System-Card.pdf", "pdf"),
    Source("anthropic_opus41_card",   "anthropic", "Claude Opus 4.1 System Card","model_card",    "https://www-cdn.anthropic.com/9fa30625273bafdf5af82c93719d7ca606485a16.pdf", "pdf"),
    Source("anthropic_sonnet46_card", "anthropic", "Claude Sonnet 4.6 System Card","model_card",  "https://www-cdn.anthropic.com/78073f739564e986ff3e28522761a7a0b4484f84.pdf", "pdf"),
    Source("anthropic_35_addendum",   "anthropic", "Claude 3.5 Model Card Addendum","model_card",   "https://www-cdn.anthropic.com/fed9cc193a14b84131812372d8d5857f8f304c52/Model_Card_Claude_3_Addendum.pdf", "pdf"),
    Source("anthropic_35h_addendum", "anthropic", "Claude 3.5 Haiku Addendum",    "model_card",   "https://www-cdn.anthropic.com/c7822cdc35ad788ec87e14b3a9d45010f1f86c38.pdf", "pdf"),
    Source("anthropic_37_card",      "anthropic", "Claude 3.7 Sonnet System Card","model_card",   "https://www-cdn.anthropic.com/9ff93dfa8f445c932415d335c88852ef47f1201e.pdf", "pdf"),
    Source("anthropic_opus46_card",  "anthropic", "Claude Opus 4.6 System Card", "model_card",    "https://anthropic.com/claude-opus-4-6-system-card",                            "html"),
    Source("anthropic_mythos_card",  "anthropic", "Claude Mythos Preview System Card", "model_card", "https://www-cdn.anthropic.com/8b8380204f74670be75e81c820ca8dda846ab289.pdf", "pdf"),
    Source("anthropic_safeguards",    "anthropic", "Building Safeguards for Claude","constitution",  "https://www.anthropic.com/news/building-safeguards-for-claude",                   "html"),

    # ── OpenAI ────────────────────────────────────────────────────────────────
    Source("openai_model_spec",        "openai", "Model Spec",                    "constitution",  "https://cdn.openai.com/spec/model-spec-2024-05-08.html",                          "html"),
    Source("openai_gpt4_system_card",  "openai", "GPT-4 System Card",             "model_card",    "https://cdn.openai.com/papers/gpt-4-system-card.pdf",                             "pdf"),
    Source("openai_preparedness",      "openai", "Preparedness Framework",        "constitution",  "https://cdn.openai.com/openai-preparedness-framework-beta.pdf",                   "pdf"),
    Source("openai_gpt4o_system_card",  "openai", "GPT-4o System Card",            "model_card",    "https://cdn.openai.com/gpt-4o-system-card.pdf",                                   "pdf"),
    Source("openai_agentic_governance", "openai", "Practices for Governing Agentic AI", "constitution", "https://cdn.openai.com/papers/practices-for-governing-agentic-ai-systems.pdf", "pdf"),
    Source("openai_political_bias",     "openai", "Political Bias Evaluation",        "constitution", "https://openai.com/index/defining-and-evaluating-political-bias-in-llms/",     "html"),
    Source("openai_mental_health",      "openai", "Mental Health Safety Update",       "usage_policy", "https://openai.com/index/update-on-mental-health-related-work/",               "html"),
    Source("openai_gpt5_system_card",   "openai", "GPT-5 System Card",                "model_card",   "https://cdn.openai.com/gpt-5-system-card.pdf",                                  "pdf"),
    Source("openai_gpt45_system_card",  "openai", "GPT-4.5 System Card",              "model_card",   "https://cdn.openai.com/gpt-4-5-system-card-2272025.pdf",                        "pdf"),
    Source("openai_o1_system_card",     "openai", "o1 System Card",                   "model_card",   "https://cdn.openai.com/o1-system-card-20241205.pdf",                             "pdf"),
    Source("openai_o3_system_card",     "openai", "o3 System Card",                   "model_card",   "https://cdn.openai.com/pdf/2221c875-02dc-4789-800b-e7758f3722c1/o3-and-o4-mini-system-card.pdf", "pdf"),
    Source("openai_o3mini_card",        "openai", "o3-mini System Card",              "model_card",   "https://cdn.openai.com/o3-mini-system-card-feb10.pdf",                           "pdf"),
    Source("openai_operator_card",      "openai", "Operator System Card",             "model_card",   "https://cdn.openai.com/operator_system_card.pdf",                               "pdf"),
    Source("openai_gpt51_system_card",  "openai", "GPT-5.1 System Card",              "model_card",   "https://cdn.openai.com/pdf/4173ec8d-1229-47db-96de-06d87147e07e/5_1_system_card.pdf", "pdf"),
    Source("openai_gpt52_system_card",  "openai", "GPT-5.2 System Card",              "model_card",   "https://cdn.openai.com/pdf/3a4153c8-c748-4b71-8e31-aecbde944f8d/oai_5_2_system-card.pdf", "pdf"),
    Source("openai_gpt53_codex_card",   "openai", "GPT-5.3 Codex System Card",        "model_card",   "https://cdn.openai.com/pdf/23eca107-a9b1-4d2c-b156-7deb4fbc697c/GPT-5-3-Codex-System-Card-02.pdf", "pdf"),

    # ── Google DeepMind ───────────────────────────────────────────────────────
    Source("google_ai_principles",     "google", "AI Principles",                 "constitution",  "https://ai.google/responsibility/principles/",                                    "html"),
    Source("google_responsible_ai",    "google", "Responsible AI Practices",      "usage_policy",  "https://ai.google/responsibility/responsible-ai-practices/",                      "html"),
    Source("google_gemini_report",     "google", "Gemini Technical Report",       "model_card",    "https://arxiv.org/abs/2312.11805",                                                "html"),
    Source("google_gemini_1_5_report", "google", "Gemini 1.5 Technical Report",   "model_card",    "https://arxiv.org/abs/2403.05530",                                                "html"),
    Source("google_gemini_2_card",     "google", "Gemini 2.0 Flash Model Card",  "model_card",    "https://storage.googleapis.com/deepmind-media/Model-Cards/Gemini-2-0-Flash-Model-Card.pdf", "pdf"),
    Source("google_gemini_25_card",    "google", "Gemini 2.5 Flash Model Card",  "model_card",    "https://storage.googleapis.com/deepmind-media/Model-Cards/Gemini-2-5-Flash-Model-Card.pdf", "pdf"),
    Source("google_gemini_25_pro_card","google", "Gemini 2.5 Pro Model Card",   "model_card",    "https://storage.googleapis.com/deepmind-media/Model-Cards/Gemini-2-5-Pro-Model-Card.pdf", "pdf"),
    Source("google_gemini_3_card",     "google", "Gemini 3 Flash Model Card",   "model_card",    "https://storage.googleapis.com/deepmind-media/Model-Cards/Gemini-3-Flash-Model-Card.pdf", "pdf"),
    Source("google_gemini_3_pro_card", "google", "Gemini 3 Pro Model Card",     "model_card",    "https://storage.googleapis.com/deepmind-media/Model-Cards/Gemini-3-Pro-Model-Card.pdf", "pdf"),
    Source("google_gemini_25dt_card",  "google", "Gemini 2.5 Deep Think Card",  "model_card",    "https://storage.googleapis.com/deepmind-media/Model-Cards/Gemini-2-5-Deep-Think-Model-Card.pdf", "pdf"),
    Source("google_gemini_31_pro_card","google", "Gemini 3.1 Pro Model Card",   "model_card",    "https://storage.googleapis.com/deepmind-media/Model-Cards/Gemini-3-1-Pro-Model-Card.pdf", "pdf"),
    Source("google_prohibited_use",    "google", "Generative AI Prohibited Use", "usage_policy",  "https://policies.google.com/terms/generative-ai/use-policy",                      "html"),
    Source("google_frontier_safety",   "google", "Frontier Safety Framework",    "constitution",  "https://deepmind.google/blog/updating-the-frontier-safety-framework/",            "html"),
    Source("google_responsibility",    "google", "Responsibility & Safety",      "constitution",  "https://deepmind.google/responsibility-and-safety/",                              "html"),

    # ── Meta AI ───────────────────────────────────────────────────────────────
    Source("meta_llama2_card",          "meta", "Llama 2 Model Card",              "model_card",    "https://raw.githubusercontent.com/meta-llama/llama/main/MODEL_CARD.md",           "raw"),
    Source("meta_llama_use_policy",    "meta", "Llama 3.3 Use Policy",            "usage_policy",  "https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_3/USE_POLICY.md", "raw"),
    Source("meta_responsible_use",     "meta", "Llama 3.3 Model Card",           "model_card",    "https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_3/MODEL_CARD.md", "raw"),
    Source("meta_purple_llama",        "meta", "Purple Llama (Safety Tools)",     "constitution",  "https://raw.githubusercontent.com/meta-llama/PurpleLlama/main/README.md",         "raw"),
    Source("meta_llama3_paper",        "meta", "Llama 3.1 Technical Paper",       "model_card",    "https://arxiv.org/abs/2407.21783",                                                "html"),
    Source("meta_llama_guard",         "meta", "Llama Guard Paper",               "model_card",    "https://arxiv.org/abs/2312.06674",                                                "html"),
    Source("meta_llama3_model_card",   "meta", "Llama 3 Model Card (GitHub)",    "model_card",    "https://raw.githubusercontent.com/meta-llama/llama3/main/README.md",             "raw"),
    Source("meta_llama31_card",        "meta", "Llama 3.1 Model Card",           "model_card",    "https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_1/MODEL_CARD.md", "raw"),
    Source("meta_llama32_card",        "meta", "Llama 3.2 Model Card",           "model_card",    "https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_2/MODEL_CARD.md", "raw"),
    Source("meta_llamaguard_card",     "meta", "Llama Guard Model Card",         "model_card",    "https://raw.githubusercontent.com/meta-llama/PurpleLlama/main/Llama-Guard/MODEL_CARD.md",     "raw"),
    Source("meta_llamaguard3_card",    "meta", "Llama Guard 3 Vision Card",      "model_card",    "https://raw.githubusercontent.com/meta-llama/PurpleLlama/main/Llama-Guard3/11B-vision/MODEL_CARD.md", "raw"),
    Source("meta_llama4_card",         "meta", "Llama 4 Model Card",             "model_card",    "https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama4/MODEL_CARD.md", "raw"),

    # ── Mistral ───────────────────────────────────────────────────────────────
    Source("mistral_guardrailing",     "mistral", "Guardrailing Docs",            "usage_policy",  "https://docs.mistral.ai/capabilities/guardrailing/",                              "html"),
    Source("mistral_mixtral_model_card","mistral","Mixtral 8x22B Model Card",     "model_card",    "https://huggingface.co/mistralai/Mixtral-8x22B-Instruct-v0.1/raw/main/README.md", "raw"),
    Source("mistral_7b_model_card",    "mistral", "Mistral 7B Model Card",        "model_card",    "https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3/raw/main/README.md",    "raw"),
    Source("mistral_usage_policy",     "mistral", "Usage Policy",                 "usage_policy",  "https://legal.mistral.ai/terms/usage-policy",                                      "html"),
    Source("mistral_moderation",       "mistral", "Moderation API",               "constitution",  "https://mistral.ai/news/mistral-moderation",                                       "html"),

    # ── xAI ───────────────────────────────────────────────────────────────────
    Source("xai_grok_docs",            "xai", "Grok Documentation",               "model_card",    "https://docs.x.ai/docs",                                                          "html"),
    Source("xai_api_docs",             "xai", "xAI API Documentation",            "usage_policy",  "https://docs.x.ai/docs/api-reference",                                            "html"),
    Source("xai_aup",                  "xai", "Acceptable Use Policy",            "usage_policy",  "https://x.ai/legal/acceptable-use-policy",                                        "html"),
    Source("xai_grok4_card",           "xai", "Grok 4 Model Card",               "model_card",    "https://data.x.ai/2025-08-20-grok-4-model-card.pdf",                              "pdf"),
    Source("xai_grok4_fast_card",     "xai", "Grok 4 Fast Model Card",          "model_card",    "https://data.x.ai/2025-09-19-grok-4-fast-model-card.pdf",                         "pdf"),
    Source("xai_grok41_card",         "xai", "Grok 4.1 Model Card",             "model_card",    "https://data.x.ai/2025-11-17-grok-4-1-model-card.pdf",                            "pdf"),
    Source("xai_risk_framework",       "xai", "Risk Management Framework",        "constitution",  "https://data.x.ai/2025-08-20-xai-risk-management-framework.pdf",                  "pdf"),

    # ── Cohere ────────────────────────────────────────────────────────────────
    Source("cohere_responsibility",    "cohere", "Responsible Use",               "constitution",  "https://docs.cohere.com/docs/responsible-use",                                    "html"),
    Source("cohere_terms",             "cohere", "Terms of Use",                  "usage_policy",  "https://cohere.com/terms-of-use",                                                 "html"),
    Source("cohere_command_r_card",    "cohere", "Command R+ Model Card",        "model_card",    "https://docs.cohere.com/docs/command-r-plus",                                     "html"),

    # ── Amazon (AWS Bedrock) ──────────────────────────────────────────────────
    Source("amazon_bedrock_aup",       "amazon", "Bedrock Acceptable Use",       "usage_policy",  "https://aws.amazon.com/machine-learning/responsible-machine-learning/",            "html"),
    Source("amazon_bedrock_docs",      "amazon", "Bedrock Documentation",        "model_card",    "https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html",       "html"),

    # ── AI21 Labs ─────────────────────────────────────────────────────────────
    Source("ai21_terms",               "ai21", "AI21 Terms of Service",         "usage_policy",  "https://www.ai21.com/terms-of-use",                                               "html"),
    Source("ai21_jamba_card",          "ai21", "Jamba Model Overview",          "model_card",    "https://www.ai21.com/jamba",                                                      "html"),
]
