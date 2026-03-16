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
    Source("anthropic_model_card",     "anthropic", "Claude 3 Model Card",        "model_card",    "https://www-cdn.anthropic.com/de8ba9b01c9ab7cbabf5c33b80b7bbc618857627/Model_Card_Claude_3.pdf", "pdf"),
    Source("anthropic_rsp",            "anthropic", "Responsible Scaling Policy", "constitution",  "https://www.anthropic.com/responsible-scaling-policy",                            "html"),
    Source("anthropic_core_views",     "anthropic", "Core Views on AI Safety",    "constitution",  "https://www.anthropic.com/news/core-views-on-ai-safety",                          "html"),
    Source("anthropic_claude_character","anthropic","Claude's Character",         "constitution",  "https://www.anthropic.com/research/claude-character",                             "html"),
    Source("anthropic_constitutional_ai","anthropic","Constitutional AI Paper",   "constitution",  "https://arxiv.org/abs/2212.08073",                                                "html"),

    # ── OpenAI ────────────────────────────────────────────────────────────────
    Source("openai_model_spec",        "openai", "Model Spec",                    "constitution",  "https://cdn.openai.com/spec/model-spec-2024-05-08.html",                          "html"),
    Source("openai_gpt4_system_card",  "openai", "GPT-4 System Card",             "model_card",    "https://cdn.openai.com/papers/gpt-4-system-card.pdf",                             "pdf"),
    Source("openai_preparedness",      "openai", "Preparedness Framework",        "constitution",  "https://cdn.openai.com/openai-preparedness-framework-beta.pdf",                   "pdf"),
    Source("openai_gpt4o_system_card",  "openai", "GPT-4o System Card",            "model_card",    "https://cdn.openai.com/gpt-4o-system-card.pdf",                                   "pdf"),
    Source("openai_agentic_governance", "openai", "Practices for Governing Agentic AI", "constitution", "https://cdn.openai.com/papers/practices-for-governing-agentic-ai-systems.pdf", "pdf"),

    # ── Google DeepMind ───────────────────────────────────────────────────────
    Source("google_ai_principles",     "google", "AI Principles",                 "constitution",  "https://ai.google/responsibility/principles/",                                    "html"),
    Source("google_responsible_ai",    "google", "Responsible AI Practices",      "usage_policy",  "https://ai.google/responsibility/responsible-ai-practices/",                      "html"),
    Source("google_gemini_report",     "google", "Gemini Technical Report",       "model_card",    "https://arxiv.org/abs/2312.11805",                                                "html"),
    Source("google_gemini_1_5_report", "google", "Gemini 1.5 Technical Report",   "model_card",    "https://arxiv.org/abs/2403.05530",                                                "html"),
    Source("google_prohibited_use",    "google", "Generative AI Prohibited Use", "usage_policy",  "https://policies.google.com/terms/generative-ai/use-policy",                      "html"),

    # ── Meta AI ───────────────────────────────────────────────────────────────
    Source("meta_llama_use_policy",    "meta", "Llama 3.3 Use Policy",            "usage_policy",  "https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_3/USE_POLICY.md", "raw"),
    Source("meta_responsible_use",     "meta", "Llama 3.3 Model Card",           "model_card",    "https://raw.githubusercontent.com/meta-llama/llama-models/main/models/llama3_3/MODEL_CARD.md", "raw"),
    Source("meta_purple_llama",        "meta", "Purple Llama (Safety Tools)",     "constitution",  "https://raw.githubusercontent.com/meta-llama/PurpleLlama/main/README.md",         "raw"),
    Source("meta_llama3_paper",        "meta", "Llama 3.1 Technical Paper",       "model_card",    "https://arxiv.org/abs/2407.21783",                                                "html"),
    Source("meta_llama_guard",         "meta", "Llama Guard Paper",               "model_card",    "https://arxiv.org/abs/2312.06674",                                                "html"),
    Source("meta_llama3_model_card",   "meta", "Llama 3 Model Card (GitHub)",    "model_card",    "https://raw.githubusercontent.com/meta-llama/llama3/main/README.md",             "raw"),

    # ── Mistral ───────────────────────────────────────────────────────────────
    Source("mistral_guardrailing",     "mistral", "Guardrailing Docs",            "usage_policy",  "https://docs.mistral.ai/capabilities/guardrailing/",                              "html"),
    Source("mistral_mixtral_model_card","mistral","Mixtral 8x22B Model Card",     "model_card",    "https://huggingface.co/mistralai/Mixtral-8x22B-Instruct-v0.1/raw/main/README.md", "raw"),
    Source("mistral_7b_model_card",    "mistral", "Mistral 7B Model Card",        "model_card",    "https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3/raw/main/README.md",    "raw"),

    # ── xAI ───────────────────────────────────────────────────────────────────
    Source("xai_grok_docs",            "xai", "Grok Documentation",               "model_card",    "https://docs.x.ai/docs",                                                          "html"),
    Source("xai_api_docs",             "xai", "xAI API Documentation",            "usage_policy",  "https://docs.x.ai/docs/api-reference",                                            "html"),

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
