#!/usr/bin/env python3
"""
Build an interactive HTML visualization of benchmark lifecycle data.

Reads CSV outputs from analyze_safety_benchmarks.py and produces a standalone
HTML file with an interactive swimlane Gantt chart (D3.js).

Usage:
    python scripts/build_lifecycle_viz.py [--mode all_evals|safety]

Output:
    output/analysis/{mode}/benchmark_lifecycle_interactive.html
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Reuse constants from the analysis script
# ---------------------------------------------------------------------------
GEN_CHRONO_ORDER = {
    "claude-2": 1, "claude-3": 2, "claude-3.5": 3, "claude-3.5-haiku": 4,
    "claude-3.7": 5, "claude-4": 6, "claude-sonnet-4.5": 7, "claude-opus-4.5": 8,
    "claude-haiku-4.5": 9, "claude-opus-4.1": 10, "claude-sonnet-4.6": 11,
    "claude-opus-4.6": 12, "claude-mythos": 13,
    "gpt-4": 1, "gpt-4o": 2, "gpt-4.5": 3, "o1": 4, "o3-mini": 5,
    "o3": 6, "gpt-5": 7, "operator": 8, "gpt-5.1": 9, "gpt-5.2": 10,
    "gpt-5.3": 11,
    "gemini-1.0": 1, "gemini-1.5": 2, "gemini-2.0": 3, "gemini-2.5": 4,
    "gemini-2.5-pro": 5, "gemini-2.5-dt": 6, "gemini-3.0": 7,
    "gemini-3.0-pro": 8, "gemini-3.1-pro": 9,
    "llama-2": 1, "llama-3": 2, "llama-3.1": 3, "llama-3.1-card": 4,
    "llama-3.2": 5, "llama-3.3": 6, "llama-4": 7,
    "grok-4": 1, "grok-4-fast": 2, "grok-4.1": 3,
    "mistral-7b": 1, "mixtral-8x7b": 2, "codestral": 3,
    "mistral-large-2": 4, "mistral-small-3": 5,
    "command-r": 1, "command-a": 2,
    "jamba-1.5": 1,
    "nova": 1, "nova-premier": 2,
}

LAB_COLORS = {
    "claude":  "#D4791A",
    "gpt":     "#10A37F",
    "gemini":  "#4285F4",
    "llama":   "#0866FF",
    "grok":    "#1DA1F2",
    "mistral": "#FF7000",
    "command": "#39594D",
    "jamba":   "#6C3CE1",
    "nova":    "#FF9900",
}

LAB_NAMES = {
    "claude": "Anthropic (Claude)",
    "gpt": "OpenAI (GPT)",
    "gemini": "Google (Gemini)",
    "llama": "Meta (Llama)",
    "grok": "xAI (Grok)",
    "mistral": "Mistral",
    "command": "Cohere (Command)",
    "jamba": "AI21 (Jamba)",
    "nova": "Amazon (Nova)",
}

LIFECYCLE_COLORS = {
    "ACTIVE": "#2ecc71",
    "EMERGING": "#3498db",
    "SATURATED": "#95a5a6",
    "SUPERSEDED": "#f39c12",
    "CONTAMINATED": "#9b59b6",
    "FLAWED": "#e67e22",
    "FORMAT_AGED": "#1abc9c",
    "INTERNAL": "#7f8c8d",
    "CAP_SHIFT": "#2c3e50",
    "METRIC_CHANGE": "#d35400",
    "COST_PROHIBITIVE": "#8e44ad",
    "SUSPICIOUS": "#e74c3c",
    "ONE-TIME": "#bdc3c7",
}

LIFECYCLE_LABELS = {
    "ACTIVE": "Active",
    "EMERGING": "Emerging",
    "SATURATED": "Saturated",
    "SUPERSEDED": "Superseded",
    "CONTAMINATED": "Contaminated",
    "FLAWED": "Flawed",
    "FORMAT_AGED": "Format Aged",
    "INTERNAL": "Internal/Proprietary",
    "CAP_SHIFT": "Capability Shift",
    "METRIC_CHANGE": "Metric Change",
    "COST_PROHIBITIVE": "Cost Prohibitive",
    "SUSPICIOUS": "Suspicious Drop",
    "ONE-TIME": "One-Time",
}


# ---------------------------------------------------------------------------
# Benchmark descriptions — hand-curated one-liners for well-known benchmarks,
# with fallback to catalog CSV descriptions.
# ---------------------------------------------------------------------------
BENCHMARK_DESCRIPTIONS = {
    # General knowledge & reasoning
    "mmlu": "57-subject multiple-choice test of broad academic knowledge.",
    "mmlu_pro": "Harder MMLU variant with 10 answer choices and more reasoning-heavy questions.",
    "mmmlu": "Multilingual MMLU — same test translated across 14+ languages.",
    "big_bench_hard": "23 hardest BIG-Bench tasks that prior models struggled with.",
    "gpqa": "Graduate-level science questions written by domain experts.",
    "gpqa_diamond": "Hardest subset of GPQA — questions even experts find challenging.",
    "arc_challenge": "Grade-school science questions requiring multi-step reasoning.",
    "hellaswag": "Sentence completion test — pick the most plausible next sentence.",
    "winogrande": "Pronoun resolution requiring commonsense reasoning.",
    "boolq": "Yes/no reading comprehension questions from Wikipedia passages.",
    "triviaqa": "Open-domain trivia questions with evidence documents.",
    "natural_questions": "Real Google Search questions with Wikipedia-derived answers.",
    "truthfulqa": "Tests whether models avoid generating popular misconceptions.",
    "simpleqa": "Short factual questions testing knowledge accuracy and calibration.",
    "drop": "Reading comprehension requiring discrete reasoning (counting, sorting, arithmetic).",
    "race_h": "High school English reading comprehension exam questions.",
    "quality": "Long-document comprehension with multiple-choice questions on full articles.",
    "opqa": "Open-domain procedural QA — step-by-step how-to knowledge.",
    "humanity_s_last_exam": "Expert-curated exam of the hardest questions across all disciplines.",
    "physicsfinals": "University-level physics final exam problems.",

    # Math
    "gsm8k": "8,500 grade-school math word problems requiring multi-step arithmetic.",
    "math": "12,500 competition-level math problems with step-by-step solutions.",
    "aime": "American Invitational Mathematics Examination competition problems.",
    "aime_2024": "2024 edition of AIME competition math problems.",
    "mathvista": "Visual math problems requiring both vision and mathematical reasoning.",
    "mgsm": "Multilingual Grade School Math — GSM8K translated to 10 languages.",
    "imo_2025": "International Mathematical Olympiad 2025 competition problems.",

    # Code
    "humaneval": "164 Python function-completion problems with unit test verification.",
    "mbpp": "974 entry-level Python programming problems.",
    "swe_bench": "Real GitHub issues requiring multi-file code changes to fix.",
    "swe_bench_verified": "Human-verified subset of SWE-bench with validated test cases.",
    "swe_lancer_ic_swe": "Freelance software engineering tasks priced by difficulty.",
    "swe_lancer_swe_manager": "Software management tasks — code review, project planning, delegation.",
    "livecodebench_v5": "Coding problems from recent programming contests (contamination-free).",
    "livecodebench_v6": "Latest LiveCodeBench with problems from 2025+ contests.",
    "livecodebench_10_1_2024_2_1_2025": "LiveCodeBench problems from Oct 2024 – Feb 2025.",
    "livecodebench_1_1_2025_5_1_2025": "LiveCodeBench problems from Jan – May 2025.",
    "codestral": "Mistral's code-specialized model evaluation.",
    "bfcl": "Berkeley Function-Calling Leaderboard — tests tool/API calling accuracy.",
    "natural2code": "Translating natural language descriptions into executable code.",
    "aider_polyglot": "Multi-language code editing benchmark using the Aider coding assistant.",
    "ml_interview_coding": "Machine learning coding interview questions.",
    "nexus": "Function-calling and tool-use evaluation across diverse APIs.",
    "agentic_coding": "End-to-end autonomous coding tasks requiring planning and execution.",
    "terminal_bench_2_0": "Command-line tool usage and shell scripting evaluation.",

    # Safety & bias
    "bbq": "Bias Benchmark for QA — tests social bias across 9 demographic categories.",
    "toxigen": "13,000 machine-generated toxic and benign statements for hate speech detection.",
    "realtoxicityprompts": "100K naturally-occurring prompts scored for potential toxic completions.",
    "xstest": "Safe/unsafe prompt pairs testing over-refusal and under-refusal balance.",
    "wildchat_toxic": "Real user prompts classified as toxic — tests refusal on harmful requests.",
    "wildchat_non_toxic": "Real user prompts classified as benign — tests over-refusal rates.",
    "strongreject_evaluation": "Jailbreak resistance — adversarial prompts trying to bypass safety.",
    "standard_refusal_evaluation": "Baseline refusal rate on clearly harmful requests.",
    "challenging_refusal_evaluation": "Nuanced refusal scenarios where harm/benign is ambiguous.",
    "agentharm": "Tests whether agents refuse harmful multi-step action sequences.",
    "agentdojo": "Agent safety — injection attacks and adversarial tool-use scenarios.",
    "wmdp_bio": "Weapons of Mass Destruction Proxy — biology dual-use knowledge assessment.",
    "wmdp_chem": "Weapons of Mass Destruction Proxy — chemistry dual-use knowledge assessment.",
    "wmdp_cyber": "Weapons of Mass Destruction Proxy — cybersecurity offense knowledge assessment.",
    "cybench": "Capture-the-flag cybersecurity challenges testing offensive capabilities.",
    "cybergym": "Cybersecurity skills evaluation across attack and defense scenarios.",
    "image_to_text_safety": "Safety of text generated from image inputs (multimodal safety).",
    "text_to_text_safety": "Safety of text-to-text generation on adversarial prompts.",
    "multilingual_safety": "Safety evaluation across multiple languages and cultural contexts.",
    "instruction_following_safety": "Whether safety instructions are followed vs jailbroken.",
    "unjustified_refusals": "Measures false positive rate — safe requests incorrectly refused.",
    "sycophancy": "Tests whether models excessively agree with users instead of being truthful.",
    "soft_bias_internal": "Internal bias evaluation measuring subtle stereotyping.",

    # Multimodal & vision
    "mmmu": "Massive Multi-discipline Multimodal Understanding — expert-level visual QA.",
    "chartqa": "Answering questions about charts, graphs, and data visualizations.",
    "figqa": "Figure question answering — interpreting scientific figures.",
    "docvqa": "Document Visual QA — extracting information from scanned documents.",
    "ai2d": "Science diagram understanding — interpreting educational illustrations.",
    "vibe_eval_reka": "Visual understanding benchmark from Reka AI.",
    "video_mme": "Video understanding — answering questions about video content.",

    # Long context
    "infinitebench_en_mc": "Long-document comprehension with 100K+ token contexts (multiple choice).",
    "infinitebench_en_qa": "Long-document comprehension with 100K+ token contexts (open-ended).",
    "ruler": "Retrieval and understanding across very long contexts.",
    "needle_in_haystack": "Finding a specific fact buried in a very long document.",
    "nih_multi_needle": "Finding multiple facts scattered across a long document.",
    "mrcr_1m": "Multi-round conversational retrieval at 1M token context length.",
    "mrcr_v2": "Improved multi-round conversational retrieval benchmark.",
    "key_value_retrieval_synthetic": "Retrieving specific values from large key-value stores.",

    # Agent & tool use
    "webarena": "Real-world web browsing tasks on live websites.",
    "osworld": "Operating system interaction — using desktop apps, files, and tools.",
    "metr": "Multi-day autonomous research and engineering tasks.",
    "re_bench": "Research engineering tasks requiring sustained multi-step execution.",
    "mle_bench": "End-to-end machine learning engineering — build full ML pipelines.",
    "paperbench": "Reproducing machine learning papers from scratch.",
    "arc_agi_2_verified": "ARC-AGI — abstract visual reasoning puzzles testing general intelligence.",
    "browsing_broken_tools": "Robustness of agent browsing when tools malfunction.",

    # Translation & multilingual
    "wmt23_all_languages": "WMT 2023 machine translation across all language pairs.",
    "wmt23_high_resource": "WMT 2023 translation for high-resource language pairs.",
    "wmt23_into_english": "WMT 2023 translation into English.",
    "wmt23_mid_resource": "WMT 2023 translation for mid-resource language pairs.",
    "wmt23_out_of_english": "WMT 2023 translation from English to other languages.",
    "wikilingua": "Cross-lingual article summarization from WikiHow.",
    "xlsum": "Cross-lingual news summarization across 44 languages.",
    "tydiqa_goldp": "Typologically diverse QA — questions in 11 typologically varied languages.",
    "low_resource_translation_flores_ntrex": "Machine translation for low-resource language pairs.",

    # Instruction following
    "ifeval": "Instruction-Following Eval — tests compliance with formatting/style constraints.",
    "wildbench": "Real-world user instructions testing helpfulness and accuracy.",
    "arena_hard": "Hardest prompts from Chatbot Arena human preference battles.",

    # Factual grounding
    "facts_grounding": "Tests whether generated text is grounded in provided source documents.",

    # Domain-specific
    "biolp_bench": "Biology lab protocol understanding and generation.",
    "healthbench": "Medical QA and clinical reasoning evaluation.",
    "long_form_virology_task_1_overall": "Long-form virology knowledge assessment (Task 1).",
    "long_form_virology_task_2": "Long-form virology knowledge assessment (Task 2).",
    "lab_bench_cloning_scenarios": "Molecular cloning experimental design evaluation.",
    "lab_bench_seqqa": "DNA/protein sequence analysis questions.",
    "protocol_design": "Laboratory protocol design and optimization.",
    "protocolqa": "Question answering about laboratory protocols.",
    "sequence_design": "Biological sequence design evaluation.",
    "cloningscenarios": "Molecular cloning scenario reasoning.",

    # Safety — internal evals
    "benign_request_refusal_rate": "Rate of incorrectly refusing benign user requests.",
    "claude_code_malicious_refusal_rate": "Refusal rate on malicious coding requests in Claude Code.",
    "malicious_use_of_claude_code_malicious_refusal_rate": "Claude Code's refusal rate for malicious use attempts.",
    "claude_code_malicious_use_evaluation_with_mitigations": "Claude Code safety with mitigations enabled.",
    "claude_code_malicious_use_evaluation_without_mitigations": "Claude Code safety without mitigations.",
    "claude_code_safety_evaluation_without_mitigations": "Claude Code general safety without mitigations.",
    "disordered_eating_harmless_rate": "Rate of harmless responses to disordered eating queries.",
    "disordered_eating_refusal_rate": "Refusal rate on harmful disordered eating content.",
    "malicious_computer_use_refusal_rate": "Refusal rate for malicious computer use requests.",
    "child_safety_multi_turn": "Child safety evaluation across multi-turn conversations.",
    "child_safety_single_turn_benign": "Child safety — benign single-turn request handling.",
    "child_safety_single_turn_violative": "Child safety — harmful single-turn request refusal.",
    "political_bias_evenhandedness": "Tests political neutrality across partisan topics.",
    "political_bias_opposing_perspectives": "Tests presenting balanced opposing viewpoints.",
    "political_bias_refusals": "Refusal rate on politically sensitive questions.",
    "suicide_and_self_harm_multi_turn": "Self-harm safety across multi-turn conversations.",
    "suicide_and_self_harm_single_turn_benign": "Self-harm — benign mental health request handling.",
    "suicide_and_self_harm_single_turn_violative": "Self-harm — harmful request refusal.",
    "single_turn_benign_request_evaluation": "Single-turn benign request handling evaluation.",
    "single_turn_violative_request_evaluation": "Single-turn harmful request refusal evaluation.",
    "violative_request_evaluation_extended_thinking_harmless_response_rate": "Harmful request handling with extended thinking enabled.",
    "violative_request_evaluation_overall_harmless_response_rate": "Overall harmless response rate on violative requests.",
    "violative_request_evaluation_standard_thinking_harmless_response_rate": "Harmful request handling with standard thinking.",
    "benign_request_evaluation_extended_thinking_refusal_rate": "Over-refusal rate with extended thinking on benign requests.",
    "benign_request_evaluation_overall_refusal_rate": "Overall over-refusal rate on benign requests.",
    "benign_request_evaluation_standard_thinking_refusal_rate": "Over-refusal rate with standard thinking on benign requests.",
    "prompt_injection_evaluation_computer_use": "Resistance to prompt injection in computer-use scenarios.",
    "prompt_injection_evaluation_mcp_model_context_protocol": "Resistance to prompt injection via Model Context Protocol.",
    "prompt_injection_evaluation_tool_use": "Resistance to prompt injection through tool-use interfaces.",

    # OpenAI internal
    "safety_evaluation_not_over_refuse": "OpenAI's internal over-refusal measurement.",
    "safety_evaluation_not_unsafe": "OpenAI's internal unsafe content detection rate.",
    "standard_disallowed_content_evaluation": "Disallowed content detection on standard prompts.",
    "reasoning_monitor": "Internal evaluation of reasoning chain monitoring.",
    "topical_classifier": "Internal topic classification accuracy.",
    "openai_interview_multiple_choice": "OpenAI's internal hiring benchmark (multiple choice).",
    "openai_research_coding_interview": "OpenAI's internal research coding interview eval.",
    "openai_prs": "Pull request evaluation on OpenAI's internal repos.",
    "model_mistake_rate_unmitigated": "Unmitigated error rate of model outputs.",
    "model_autonomy_create_bitcoin_wallet_canary": "Canary test — does the model create a Bitcoin wallet unprompted?",
    "model_autonomy_find_api_key_on_filesystem_canary": "Canary test — does the model search for API keys on disk?",
    "model_autonomy_load_docker_image_with_mistral_7b": "Canary test — does the model load unauthorized Docker images?",
    "model_autonomy_openai_api_proxy_crypto_authenticated": "Canary test — does the model proxy API calls for cryptocurrency?",
    "model_autonomy_openai_api_proxy_find_key_canary": "Canary test — does the model find and use proxy API keys?",
    "model_autonomy_openai_api_proxy_given_key_no_auth_canary": "Canary test — does the model use unauthenticated API proxies?",
    "model_autonomy_register_cloud_provider_and_start_a100_vm": "Canary test — does the model register cloud accounts and spin up GPUs?",
    "prompt_injection_monitor_precision": "Precision of prompt injection detection monitoring.",
    "prompt_injection_monitor_recall": "Recall of prompt injection detection monitoring.",
    "prompt_injection_susceptibility": "How susceptible the model is to prompt injection attacks.",
    "confirmations_recall": "Recall rate for confirming actions with users before executing.",
    "proactive_refusals_recall": "Recall rate for proactively refusing harmful requests.",
    "agentic_harms_refusal_rate": "Refusal rate for harmful agentic action sequences.",
    "multimodal_refusal_evaluation": "Refusal rate on harmful multimodal (image+text) requests.",
    "gray_swan_red_team_harmful_image_text_asr": "Gray Swan red team — attack success rate on harmful image+text.",
    "gray_swan_red_team_harmful_text_asr": "Gray Swan red team — attack success rate on harmful text.",
    "gray_swan_red_team_malicious_code_asr": "Gray Swan red team — attack success rate for malicious code generation.",
    "human_sourced_jailbreaks": "Human-crafted jailbreak prompts — attack success rate.",
    "vision_self_harm_refusal_evaluation": "Refusal rate on self-harm images.",
    "vision_sexual_refusal_evaluation": "Refusal rate on sexual images.",
    "instruction_hierarchy_developer_user_conflict": "Handling developer vs user instruction conflicts.",
    "instruction_hierarchy_system_developer_conflict": "Handling system vs developer instruction conflicts.",
    "instruction_hierarchy_system_user_conflict": "Handling system vs user instruction conflicts.",
    "instruction_hierarchy_tutor_jailbreak_developer_message": "Jailbreak resistance via developer message in tutoring context.",
    "instruction_hierarchy_tutor_jailbreak_system_message": "Jailbreak resistance via system message in tutoring context.",
    "image_input_evaluations_attack_planning": "Safety of responses to attack planning images.",
    "image_input_evaluations_extremism": "Safety of responses to extremism-related images.",
    "image_input_evaluations_harms_erotic": "Safety of responses to erotic images.",
    "image_input_evaluations_hate": "Safety of responses to hate-promoting images.",
    "image_input_evaluations_illicit": "Safety of responses to illicit activity images.",
    "image_input_evaluations_self_harm": "Safety of responses to self-harm images.",
    "safety_eval_challenging_biosafety_red_team_prompts": "Challenging biosafety red team prompts.",
    "safety_eval_filtered_adversarial_production_prompts": "Filtered adversarial prompts from production traffic.",
    "challenging_red_teaming_evaluation_1": "Challenging red team evaluation (set 1).",
    "challenging_red_teaming_evaluation_2": "Challenging red team evaluation (set 2).",
    "pairwise_bioweaponization_campaign": "Pairwise comparison on bioweaponization campaign assistance refusal.",

    # GPT-specific
    "ctf_cybersecurity": "Capture-the-flag cybersecurity challenge performance.",
    "person_identification": "Identifying persons from descriptions or images.",
    "personqa": "Privacy-sensitive questions about real people.",
    "speaker_identification": "Identifying speakers from audio or transcripts.",
    "voice_output_classifier": "Classifying voice output quality and safety.",
    "ungrounded_inference_and_sensitive_trait_attribution": "Detecting ungrounded inferences about sensitive traits.",
    "ungrounded_inference_sensitive_trait_attribution": "Detecting ungrounded sensitive trait attribution.",
    "long_form_biological_risk_questions": "Long-form answers to biological risk questions.",
    "multimodal_troubleshooting_virology": "Multimodal troubleshooting in virology lab scenarios.",
    "biorisk_monitoring_recall": "Recall rate for detecting biological risk content.",
    "biorisk_tooling_eval": "Evaluation of bio-risk tooling and monitoring.",
    "apollo_sabotage_capabilities": "APOLLO framework — testing model sabotage capabilities.",
    "sabotage_suite": "Suite of tests for model sabotage behavior detection.",
    "network_attack_simulation": "Simulated network attack capability evaluation.",
    "vulnerability_research_and_exploitation": "Vulnerability discovery and exploit development capability.",
    "cyscenariobench": "Cybersecurity scenario-based evaluation.",
    "cyber_safety_eval_production_data": "Cybersecurity safety on production data.",
    "cyber_safety_eval_synthetic_data": "Cybersecurity safety on synthetic data.",
    "cyber_safety_production_traffic": "Cybersecurity safety on production traffic.",
    "cyber_safety_synthetic_data": "Cybersecurity safety on synthetic data.",
    "deception_rate_production_deception_adversarial": "Deception rate on adversarial production prompts.",
    "deception_rate_production_traffic": "Deception rate on normal production traffic.",
    "coding_deception": "Detection of deceptive behavior in code generation.",
    "first_person_fairness_harm_overall": "First-person fairness harm across demographics.",
    "production_benchmarks": "Aggregate production quality benchmark scores.",
    "troubleshootingbench_expert_threshold": "Expert-level troubleshooting task success rate.",
    "troubleshootingbench_human_expert_baseline": "Human expert baseline on troubleshooting tasks.",
    "charxiv_missing_image": "Chart understanding with missing or degraded images.",

    # Grok-specific
    "makemesay": "Red team game — trick the model into saying a target phrase.",
    "mask": "Model Accountability and Safety Knowledge evaluation.",
    "vct": "Values Consistency Test — checking value alignment under pressure.",
    "refusals_system_jailbreak": "Refusal rate when jailbreak is attempted via system prompt.",
    "refusals_user_jailbreak": "Refusal rate when jailbreak is attempted via user prompt.",
    "chat_refusals": "General chat refusal rate on harmful requests.",
    "input_filter_restricted_biology": "Input filter catch rate for restricted biology content.",
    "input_filter_restricted_chemistry": "Input filter catch rate for restricted chemistry content.",

    # Misc
    "mcp_atlas": "Model Context Protocol compatibility and tool-use evaluation.",
    "misalignment_situational_awareness": "Tests whether models show situational awareness of being evaluated.",
    "misalignment_stealth_challenges": "Tests whether models behave differently when they think they're unobserved.",
    "tone": "Evaluation of appropriate tone matching across contexts.",
    "human_preference_chatgpt_api_prompts": "Human preference ratings on ChatGPT API prompt responses.",
    "autonomous_replication_and_adaptation_ara": "Tests autonomous self-replication and adaptation capabilities.",
    "autonomous_cyber_offense_suite": "Suite of autonomous cybersecurity offense tasks.",
    "cybersecurity_key_skills_benchmark": "Key cybersecurity skills evaluation.",
    "harmful_manipulation_odds_ratio": "Odds ratio of harmful manipulation in generated content.",

    # Image generation
    "image_editing_character_genai_bench": "Image editing quality — character modifications.",
    "image_editing_creative_genai_bench": "Image editing quality — creative transformations.",
    "image_editing_infographics_genai_bench": "Image editing quality — infographic generation.",
    "image_editing_object_environment_genai_bench": "Image editing quality — object/environment changes.",
    "image_editing_product_recontextualization_genai_bench": "Image editing quality — product recontextualization.",
    "image_editing_stylization_genai_bench": "Image editing quality — style transfer.",
    "text_to_image_alignment_genai_bench": "Text-to-image alignment — how well images match prompts.",
    "overall_preference_lmarena_image_editing": "LM Arena preference ranking for image editing.",
    "overall_preference_lmarena_text_to_image": "LM Arena preference ranking for text-to-image.",

    # Other known benchmarks
    "evasion": "Evasion detection — identifying attempts to circumvent safety filters.",
    "bird_sql_dev": "SQL query generation from natural language on complex databases.",
    "strongreject_jailbreak_evaluation": "StrongReject benchmark — adversarial jailbreak resistance.",

    # Remaining benchmarks
    "hle": "Humanity's Last Exam — hardest expert questions across all fields.",
    "charxiv_reasoning": "Chart reasoning — interpreting and analyzing charts from arXiv papers.",
    "claude_code_dual_use_success": "Claude Code dual-use task success rate.",
    "claude_code_dual_use_success_rate": "Claude Code dual-use task success rate.",
    "claude_code_dual_use_benign_success_rate": "Claude Code success rate on benign dual-use tasks.",
    "graphwalks_bfs_256k_1m": "Graph traversal (BFS) at 256K–1M token context.",
    "graphwalks_bfs_1m": "Graph traversal (BFS) at 1M token context.",
    "graphwalks_bfs_256k_subset_of_1m": "Graph traversal (BFS) on 256K subset of 1M context.",
    "graphwalks_parents_256k_subset_of_1m": "Graph parent traversal on 256K subset of 1M context.",
    "usamo_2026": "USA Mathematical Olympiad 2026 competition problems.",
    "gre_quantitative_reasoning": "GRE quantitative reasoning section performance.",
    "gre_verbal_reasoning": "GRE verbal reasoning section performance.",
    "amc": "American Mathematics Competitions exam problems.",
    "apps": "Automated Programming Progress Standard — Python coding problems.",
    "lsat": "Law School Admission Test reasoning questions.",
    "mbe": "Multistate Bar Examination questions.",
    "needle_in_a_haystack": "Finding a specific fact buried in a very long document.",
    "human_feedback_coding": "Human preference evaluation on coding tasks.",
    "human_feedback_creative_writing": "Human preference evaluation on creative writing.",
    "human_feedback_document_analysis": "Human preference evaluation on document analysis.",
    "human_feedback_instruction_following": "Human preference evaluation on instruction following.",
    "human_feedback_visual_understanding": "Human preference evaluation on visual understanding.",
    "tau_bench_airline": "Tool-augmented agent tasks in airline customer service.",
    "tau_bench_retail": "Tool-augmented agent tasks in retail customer service.",
    "tau2_bench_retail": "TAU-bench v2 — retail customer service agent tasks.",
    "tau2_bench_telecom": "TAU-bench v2 — telecom customer service agent tasks.",
    "computer_use_prompt_injection_evaluation": "Prompt injection resistance in computer-use scenarios.",
    "internal_ai_research_evaluation_suite_1_speedup": "Internal AI research eval — speedup metric.",
    "internal_ai_research_evaluation_suite_2_advanced_tests_pass_rate": "Internal AI research eval — advanced test pass rate.",
    "internal_ai_research_evaluation_suite_2_basic_tests_pass_rate": "Internal AI research eval — basic test pass rate.",
    "apollo_research_evaluation_awareness_unambiguous_references": "APOLLO — situational awareness on unambiguous references.",
    "evaluation_awareness_verbalization": "Tests if models verbalize awareness of being evaluated.",
    "bench_retail": "Retail customer service benchmark.",
    "bench_telecom": "Telecom customer service benchmark.",
    "spreadsheetbench": "Spreadsheet manipulation and formula generation tasks.",
    "creative_biology_tasks": "Creative biology experiment design and analysis.",
    "kernel_optimization_hard_variant": "Hard variant of GPU kernel optimization tasks.",
    "llm_training_optimization": "LLM training pipeline optimization tasks.",
    "text_based_rl": "Text-based reinforcement learning environment performance.",
    "time_series_forecasting_hard_variant": "Hard variant of time series forecasting tasks.",
    "browsecomp_multi_agent": "Multi-agent web browsing competition.",
    "deepsearchqa": "Deep search QA — complex multi-hop research questions.",
    "finance_agent": "Autonomous financial analysis and trading agent tasks.",
    "gdpval_aa": "GDP validation — economic data analysis accuracy.",
    "higher_difficulty_benign_request_evaluation": "Over-refusal on harder benign requests.",
    "arc_agi_1": "ARC-AGI v1 — abstract visual reasoning puzzles.",
    "arc_agi_2_veri_ed": "ARC-AGI v2 verified — validated abstract reasoning puzzles.",
    "human_preference_evaluation_business": "Human preference on business writing tasks.",
    "human_preference_evaluation_general": "Human preference on general conversation.",
    "human_preference_evaluation_stem": "Human preference on STEM explanations.",
    "infobench": "Information-seeking benchmark — factual retrieval accuracy.",
    "lbpp_python": "Language-based Python programming problems.",
    "repoqa": "Repository-level code understanding and QA.",
    "taubench": "Tool-augmented benchmark for agent capabilities.",
    "naturalquestions_closed_book": "Google search questions answered without retrieval (closed-book).",
    "naturalquestions_retrieved": "Google search questions answered with retrieval documents.",
    "covost2_21_lang": "Speech translation across 21 languages.",
    "egoschema_test": "Long-form video understanding from egocentric perspective.",
    "cyber_key_skills_benchmark": "Key cybersecurity skills evaluation.",
    "deceptive_alignment_situational_awareness": "Tests deceptive alignment via situational awareness.",
    "deceptive_alignment_stealth": "Tests stealthy deceptive alignment behavior.",
    "arc_easy_hausa": "ARC science questions translated to Hausa.",
    "medmcqa_dev": "Medical multiple-choice QA from Indian medical exams.",
    "uhura_eval_hausa": "Hausa language understanding evaluation.",
    "agi_eval": "Multi-task evaluation targeting AGI-level reasoning.",
    "bbh": "BIG-Bench Hard — 23 challenging reasoning tasks.",
    "commonsense_reasoning": "Commonsense reasoning across everyday scenarios.",
    "reading_comprehension": "Standard reading comprehension evaluation.",
    "world_knowledge": "Broad world knowledge and factual recall.",
    "agieval_english": "AGI evaluation — English subset of reasoning tasks.",
    "open_rewrite_eval": "Open-ended text rewriting quality evaluation.",
    "quac": "Question Answering in Context — conversational QA.",
    "squad": "Stanford Question Answering Dataset — extractive QA.",
    "tldr9": "TL;DR summarization of Reddit posts.",
    "human_evaluation_vs_gemma_2_27b": "Human preference comparison vs Gemma 2 27B.",
    "human_evaluation_vs_gpt_4o_mini": "Human preference comparison vs GPT-4o Mini.",
    "human_evaluation_vs_llama_3_3_70b": "Human preference comparison vs Llama 3.3 70B.",
    "human_evaluation_vs_qwen_2_5_32b": "Human preference comparison vs Qwen 2.5 32B.",
    "mt_bench": "Multi-Turn Bench — multi-turn conversation quality (scored by GPT-4).",
    "bigcodebench_hard": "Hard variant of BigCodeBench — complex coding tasks.",
    "mbxp_5_languages": "Multilingual code generation across 5 programming languages.",
    "otps": "Operational task planning and scheduling evaluation.",
    "screenspot_web_icon": "Web UI icon localization and clicking accuracy.",
    "screenspot_web_text": "Web UI text element localization and clicking accuracy.",
    "ttft": "Time to first token — latency measurement.",
}


def build_data(mode: str) -> dict:
    """Read CSVs and build the JSON data structure."""
    base = Path(__file__).parent.parent / "output" / "analysis" / mode

    lifecycle_path = base / "benchmark_lifecycle.csv"
    matrix_path = base / "coverage_matrix.csv"

    if not lifecycle_path.exists():
        print(f"ERROR: {lifecycle_path} not found. Run analyze_safety_benchmarks.py first.")
        sys.exit(1)

    lc_df = pd.read_csv(lifecycle_path)
    mat_df = pd.read_csv(matrix_path) if matrix_path.exists() else pd.DataFrame()

    # Load catalog descriptions as fallback
    catalog_path = base / "benchmark_catalog.csv"
    catalog_descs: dict[str, str] = {}
    if catalog_path.exists():
        cat_df = pd.read_csv(catalog_path)
        for _, row in cat_df.iterrows():
            desc = row.get("description", "")
            if pd.notna(desc) and str(desc).strip():
                catalog_descs[row["slug"]] = str(desc).strip()[:200]

    # Build score lookup from coverage matrix
    score_lookup: dict[tuple[str, str, str], float] = {}
    if not mat_df.empty:
        scored = mat_df[mat_df["cell_value"].notna() & (mat_df["cell_value"] != ".")]
        for _, row in scored.iterrows():
            try:
                score = float(row["cell_value"])
                score_lookup[(row["family_slug"], row["gen_slug"], row["benchmark_slug"])] = score
            except (ValueError, TypeError):
                pass

    # Build per-lab data
    labs_data = []
    for lab in sorted(lc_df["family_slug"].unique()):
        lab_lc = lc_df[lc_df["family_slug"] == lab]

        # Get ordered generations for this lab
        lab_gens_set = set()
        if not mat_df.empty:
            lab_gens_set = set(mat_df[mat_df["family_slug"] == lab]["gen_slug"].unique())
        # Also include gens from lifecycle
        lab_gens_set.update(lab_lc["last_gen_reported"].dropna().unique())

        lab_gens = sorted(lab_gens_set, key=lambda g: GEN_CHRONO_ORDER.get(g, 999))

        # Build benchmark entries
        benchmarks = []
        for _, row in lab_lc.iterrows():
            slug = row["benchmark_slug"]

            # Find first and last generation with scores
            scores = {}
            first_gen_idx = len(lab_gens)
            last_gen_idx = -1
            for gi, gen in enumerate(lab_gens):
                s = score_lookup.get((lab, gen, slug))
                if s is not None:
                    scores[gen] = round(s, 2)
                    first_gen_idx = min(first_gen_idx, gi)
                    last_gen_idx = max(last_gen_idx, gi)

            # Fallback if no scores found in matrix
            if last_gen_idx < 0:
                last_gen = row.get("last_gen_reported")
                if pd.notna(last_gen) and last_gen in lab_gens:
                    last_gen_idx = lab_gens.index(last_gen)
                    first_gen_idx = last_gen_idx
                else:
                    continue

            # Get description: curated dict > catalog CSV > empty
            description = BENCHMARK_DESCRIPTIONS.get(slug, "")
            if not description:
                description = catalog_descs.get(slug, "")

            benchmarks.append({
                "slug": slug,
                "name": str(row.get("benchmark_name", slug)),
                "description": description,
                "lifecycle": row["lifecycle"],
                "dropReasons": str(row.get("drop_reasons", "")) if pd.notna(row.get("drop_reasons")) else "",
                "firstGenIdx": first_gen_idx,
                "lastGenIdx": last_gen_idx,
                "bestScore": round(row["best_score"], 2) if pd.notna(row.get("best_score")) else None,
                "dropScore": round(row["drop_score"], 2) if pd.notna(row.get("drop_score")) else None,
                "successor": str(row["successor"]) if pd.notna(row.get("successor")) else None,
                "isInternal": bool(row.get("is_internal", False)),
                "capabilityTags": str(row.get("capability_tags", "")) if pd.notna(row.get("capability_tags")) else "",
                "nGens": int(row.get("n_gens_reported", 1)),
                "scores": scores,
            })

        # Sort: by lifecycle priority, then first appearance, then name
        lifecycle_sort = {
            "ACTIVE": 0, "EMERGING": 1, "SATURATED": 2, "SUPERSEDED": 3,
            "CONTAMINATED": 4, "FLAWED": 5, "FORMAT_AGED": 6,
            "INTERNAL": 7, "CAP_SHIFT": 8, "METRIC_CHANGE": 9,
            "COST_PROHIBITIVE": 10, "SUSPICIOUS": 11, "ONE-TIME": 12,
        }
        benchmarks.sort(key=lambda b: (lifecycle_sort.get(b["lifecycle"], 99),
                                        b["firstGenIdx"], b["slug"]))

        labs_data.append({
            "slug": lab,
            "name": LAB_NAMES.get(lab, lab.title()),
            "color": LAB_COLORS.get(lab, "#888888"),
            "generations": lab_gens,
            "benchmarks": benchmarks,
        })

    return {
        "labs": labs_data,
        "lifecycleColors": LIFECYCLE_COLORS,
        "lifecycleLabels": LIFECYCLE_LABELS,
    }


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Benchmark Lifecycle Explorer</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #fafafa; color: #333; }

.layout { display: flex; height: 100vh; }
.sidebar { width: 260px; min-width: 260px; background: #fff; border-right: 1px solid #e0e0e0; padding: 16px; overflow-y: auto; }
.main { flex: 1; overflow-y: auto; padding: 20px 24px; }

h1 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.subtitle { font-size: 13px; color: #888; margin-bottom: 16px; }

/* Stats bar */
.stats-bar { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }
.stat { background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 8px 14px; font-size: 12px; }
.stat strong { font-size: 18px; display: block; }

/* Sidebar */
.sidebar h3 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #999; margin: 16px 0 8px; }
.sidebar h3:first-child { margin-top: 0; }
.search-input { width: 100%; padding: 8px 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; margin-bottom: 12px; }
.search-input:focus { outline: none; border-color: #4285F4; }

.filter-group { margin-bottom: 8px; }
.filter-item { display: flex; align-items: center; gap: 6px; padding: 3px 0; cursor: pointer; font-size: 13px; }
.filter-item input { cursor: pointer; }
.color-dot { width: 10px; height: 10px; border-radius: 2px; display: inline-block; flex-shrink: 0; }
.filter-count { color: #aaa; font-size: 11px; margin-left: auto; }

.quick-filters { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 12px; }
.qf-btn { padding: 5px 10px; font-size: 11px; border: 1px solid #ddd; border-radius: 4px; background: #fff; cursor: pointer; color: #555; transition: all 0.15s; }
.qf-btn:hover { background: #f0f0f0; }
.qf-btn.active { background: #333; color: #fff; border-color: #333; }

.sort-group { margin-bottom: 12px; }
.sort-group select { width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; background: #fff; }

/* Lab sections */
.lab-section { margin-bottom: 24px; }
.lab-header { display: flex; align-items: center; gap: 10px; padding: 10px 14px; background: #fff; border: 1px solid #e0e0e0; border-radius: 8px; cursor: pointer; user-select: none; margin-bottom: 2px; }
.lab-header:hover { background: #f5f5f5; }
.lab-color-bar { width: 4px; height: 24px; border-radius: 2px; }
.lab-name { font-weight: 600; font-size: 15px; }
.lab-count { color: #888; font-size: 13px; margin-left: auto; }
.lab-toggle { font-size: 12px; color: #aaa; transition: transform 0.2s; }
.lab-toggle.collapsed { transform: rotate(-90deg); }

.lab-body { overflow: hidden; transition: max-height 0.3s ease; }
.lab-body.collapsed { max-height: 0 !important; }

/* Gantt chart */
.gantt-container { position: relative; overflow-x: auto; background: #fff; border: 1px solid #e0e0e0; border-radius: 0 0 8px 8px; }
.gantt-header { display: flex; position: sticky; top: 0; background: #f9f9f9; border-bottom: 1px solid #eee; z-index: 2; }
.gantt-header-label { min-width: 200px; max-width: 200px; padding: 6px 10px; font-size: 11px; font-weight: 600; color: #666; }
.gen-header { flex: 1; text-align: center; font-size: 10px; color: #888; padding: 6px 2px; min-width: 70px; border-left: 1px solid #f0f0f0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.gantt-row { display: flex; align-items: center; border-bottom: 1px solid #f5f5f5; min-height: 26px; }
.gantt-row:hover { background: #f8f9ff; }
.gantt-label { min-width: 200px; max-width: 200px; padding: 2px 10px; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: #555; }
.gantt-bars { display: flex; flex: 1; position: relative; }
.gantt-cell { flex: 1; min-width: 70px; height: 22px; border-left: 1px solid #f8f8f8; position: relative; display: flex; align-items: center; justify-content: center; }
.bar-segment { height: 14px; border-radius: 3px; position: absolute; top: 4px; cursor: pointer; transition: opacity 0.15s; min-width: 8px; }
.bar-segment:hover { opacity: 0.8; filter: brightness(1.1); }

/* Score dot inside bar */
.score-dot { width: 6px; height: 6px; border-radius: 50%; background: rgba(255,255,255,0.7); position: absolute; top: 50%; transform: translateY(-50%); }

/* Drop marker */
.drop-marker { position: absolute; right: -4px; top: -2px; font-size: 12px; line-height: 1; }

/* Tooltip */
.tooltip { position: fixed; background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 12px 16px; font-size: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); z-index: 1000; max-width: 380px; pointer-events: none; display: none; }
.tooltip-name { font-weight: 700; font-size: 14px; margin-bottom: 4px; }
.tooltip-lifecycle { display: inline-block; padding: 2px 8px; border-radius: 3px; color: #fff; font-size: 11px; font-weight: 600; margin-bottom: 8px; }
.tooltip-row { display: flex; justify-content: space-between; gap: 16px; padding: 2px 0; }
.tooltip-row .label { color: #888; }
.tooltip-scores { margin-top: 8px; border-top: 1px solid #eee; padding-top: 8px; }
.tooltip-scores h4 { font-size: 11px; color: #888; margin-bottom: 4px; }
.score-list { display: grid; grid-template-columns: 1fr 1fr; gap: 2px 12px; }
.score-entry { font-size: 11px; }
.score-entry .gen { color: #888; }
.score-entry .val { font-weight: 600; }

/* No results */
.no-results { padding: 40px; text-align: center; color: #aaa; font-size: 14px; }
</style>
</head>
<body>

<div class="layout">
  <aside class="sidebar">
    <h1>Benchmark Lifecycle</h1>
    <div class="subtitle">Interactive swimlane explorer</div>

    <input type="text" class="search-input" id="searchInput" placeholder="Search benchmarks...">

    <h3>Sort by</h3>
    <div class="sort-group">
      <select id="sortSelect">
        <option value="lifecycle">Lifecycle status</option>
        <option value="appearance">First appearance</option>
        <option value="name">Name (A-Z)</option>
        <option value="ngens">Longevity (most → least)</option>
      </select>
    </div>

    <h3>Quick Filters</h3>
    <div class="quick-filters">
      <button class="qf-btn active" id="qfSignal">Signal only</button>
      <button class="qf-btn" id="qfAll">Show all</button>
      <button class="qf-btn" id="qfDrops">Drops only</button>
      <button class="qf-btn" id="qfSuspicious">Suspicious only</button>
    </div>

    <h3>Lifecycle Status</h3>
    <div id="lifecycleFilters" class="filter-group"></div>

    <h3>Labs</h3>
    <div id="labFilters" class="filter-group"></div>
  </aside>

  <div class="main">
    <div class="stats-bar" id="statsBar"></div>
    <div id="chartArea"></div>
  </div>
</div>

<div class="tooltip" id="tooltip"></div>

<script>
// === DATA (embedded by Python) ===
const DATA = __DATA_PLACEHOLDER__;

// === STATE ===
// Default: hide ONE-TIME and INTERNAL (the long tail) so you start with signal
const DEFAULT_HIDDEN = new Set(['ONE-TIME', 'INTERNAL']);
const state = {
  lifecycleFilters: new Set(Object.keys(DATA.lifecycleColors).filter(s => !DEFAULT_HIDDEN.has(s))),
  labFilters: new Set(DATA.labs.map(l => l.slug)),
  search: '',
  sort: 'lifecycle',
  collapsed: new Set(),
};

// === LIFECYCLE SORT ORDER ===
const LIFECYCLE_ORDER = [
  'ACTIVE','EMERGING','SATURATED','SUPERSEDED','CONTAMINATED','FLAWED',
  'FORMAT_AGED','INTERNAL','CAP_SHIFT','METRIC_CHANGE','COST_PROHIBITIVE',
  'SUSPICIOUS','ONE-TIME'
];

// === RENDER ===
function getFilteredBenchmarks(lab) {
  let benchmarks = lab.benchmarks.filter(b => {
    if (!state.lifecycleFilters.has(b.lifecycle)) return false;
    if (state.search) {
      const q = state.search.toLowerCase();
      if (!b.slug.includes(q) && !b.name.toLowerCase().includes(q)) return false;
    }
    return true;
  });

  // Sort
  const sortFn = {
    lifecycle: (a, b) => {
      const ai = LIFECYCLE_ORDER.indexOf(a.lifecycle);
      const bi = LIFECYCLE_ORDER.indexOf(b.lifecycle);
      if (ai !== bi) return ai - bi;
      return a.firstGenIdx - b.firstGenIdx || a.slug.localeCompare(b.slug);
    },
    appearance: (a, b) => a.firstGenIdx - b.firstGenIdx || a.slug.localeCompare(b.slug),
    name: (a, b) => a.name.localeCompare(b.name),
    ngens: (a, b) => b.nGens - a.nGens || a.slug.localeCompare(b.slug),
  };
  benchmarks.sort(sortFn[state.sort] || sortFn.lifecycle);
  return benchmarks;
}

function renderStats() {
  const bar = document.getElementById('statsBar');
  let total = 0;
  const counts = {};
  LIFECYCLE_ORDER.forEach(s => counts[s] = 0);

  DATA.labs.forEach(lab => {
    if (!state.labFilters.has(lab.slug)) return;
    lab.benchmarks.forEach(b => {
      if (state.search) {
        const q = state.search.toLowerCase();
        if (!b.slug.includes(q) && !b.name.toLowerCase().includes(q)) return;
      }
      counts[b.lifecycle] = (counts[b.lifecycle] || 0) + 1;
      total++;
    });
  });

  let html = `<div class="stat"><strong>${total}</strong>total benchmarks</div>`;
  LIFECYCLE_ORDER.forEach(s => {
    if (counts[s] > 0) {
      const color = DATA.lifecycleColors[s];
      const label = DATA.lifecycleLabels[s] || s;
      html += `<div class="stat"><strong style="color:${color}">${counts[s]}</strong>${label}</div>`;
    }
  });
  bar.innerHTML = html;
}

function renderSidebar() {
  // Lifecycle filters
  const lcDiv = document.getElementById('lifecycleFilters');
  let lcHtml = '';
  const lcCounts = {};
  DATA.labs.forEach(lab => {
    lab.benchmarks.forEach(b => {
      lcCounts[b.lifecycle] = (lcCounts[b.lifecycle] || 0) + 1;
    });
  });
  LIFECYCLE_ORDER.forEach(s => {
    const color = DATA.lifecycleColors[s];
    const label = DATA.lifecycleLabels[s] || s;
    const count = lcCounts[s] || 0;
    if (count === 0) return;
    const checked = state.lifecycleFilters.has(s) ? 'checked' : '';
    lcHtml += `<label class="filter-item">
      <input type="checkbox" ${checked} data-lifecycle="${s}">
      <span class="color-dot" style="background:${color}"></span>
      ${label}
      <span class="filter-count">${count}</span>
    </label>`;
  });
  lcDiv.innerHTML = lcHtml;
  lcDiv.querySelectorAll('input').forEach(cb => {
    cb.addEventListener('change', () => {
      const s = cb.dataset.lifecycle;
      if (cb.checked) state.lifecycleFilters.add(s);
      else state.lifecycleFilters.delete(s);
      document.querySelectorAll('.qf-btn').forEach(b => b.classList.remove('active'));
      renderChart();
      renderStats();
    });
  });

  // Lab filters
  const labDiv = document.getElementById('labFilters');
  let labHtml = '';
  DATA.labs.forEach(lab => {
    const checked = state.labFilters.has(lab.slug) ? 'checked' : '';
    labHtml += `<label class="filter-item">
      <input type="checkbox" ${checked} data-lab="${lab.slug}">
      <span class="color-dot" style="background:${lab.color}"></span>
      ${lab.name}
      <span class="filter-count">${lab.benchmarks.length}</span>
    </label>`;
  });
  labDiv.innerHTML = labHtml;
  labDiv.querySelectorAll('input').forEach(cb => {
    cb.addEventListener('change', () => {
      const s = cb.dataset.lab;
      if (cb.checked) state.labFilters.add(s);
      else state.labFilters.delete(s);
      renderChart();
      renderStats();
    });
  });
}

function renderChart() {
  const area = document.getElementById('chartArea');
  let html = '';

  const visibleLabs = DATA.labs.filter(l => state.labFilters.has(l.slug));
  if (visibleLabs.length === 0) {
    area.innerHTML = '<div class="no-results">No labs selected</div>';
    return;
  }

  visibleLabs.forEach(lab => {
    const benchmarks = getFilteredBenchmarks(lab);
    const isCollapsed = state.collapsed.has(lab.slug);
    const gens = lab.generations;

    html += `<div class="lab-section" data-lab="${lab.slug}">`;
    html += `<div class="lab-header" data-lab="${lab.slug}">
      <div class="lab-color-bar" style="background:${lab.color}"></div>
      <span class="lab-name">${lab.name}</span>
      <span class="lab-count">${benchmarks.length} benchmarks</span>
      <span class="lab-toggle ${isCollapsed ? 'collapsed' : ''}">▼</span>
    </div>`;

    html += `<div class="lab-body ${isCollapsed ? 'collapsed' : ''}" style="max-height:${isCollapsed ? 0 : (benchmarks.length + 1) * 28 + 40}px">`;
    html += `<div class="gantt-container">`;

    // Header row
    html += `<div class="gantt-header">`;
    html += `<div class="gantt-header-label">Benchmark</div>`;
    gens.forEach(g => {
      html += `<div class="gen-header" title="${g}">${g}</div>`;
    });
    html += `</div>`;

    if (benchmarks.length === 0) {
      html += '<div class="no-results">No matching benchmarks</div>';
    }

    // Benchmark rows
    benchmarks.forEach(b => {
      html += `<div class="gantt-row">`;
      const labelTitle = b.description ? `${b.name}: ${b.description}` : b.name;
      html += `<div class="gantt-label" title="${labelTitle}">${b.name}</div>`;
      html += `<div class="gantt-bars">`;

      gens.forEach((g, gi) => {
        html += `<div class="gantt-cell">`;
        if (gi >= b.firstGenIdx && gi <= b.lastGenIdx) {
          const color = DATA.lifecycleColors[b.lifecycle] || '#ccc';
          const isFirst = gi === b.firstGenIdx;
          const isLast = gi === b.lastGenIdx;
          const score = b.scores[g];
          const borderRadius = `${isFirst ? '3px' : '0'} ${isLast ? '3px' : '0'} ${isLast ? '3px' : '0'} ${isFirst ? '3px' : '0'}`;

          html += `<div class="bar-segment"
            style="background:${color}; left:0; right:0; border-radius:${borderRadius}"
            data-bench='${JSON.stringify(b).replace(/'/g, "&#39;")}'
            data-gen="${g}"
            data-score="${score != null ? score : ''}">`;

          // Score dot
          if (score != null) {
            html += `<div class="score-dot" style="left:50%"></div>`;
          }

          // Drop marker for terminated benchmarks
          if (isLast && b.lifecycle !== 'ACTIVE' && b.lifecycle !== 'EMERGING') {
            const markers = {
              'SATURATED': '⬆', 'SUPERSEDED': '→', 'CONTAMINATED': '☣',
              'SUSPICIOUS': '?', 'INTERNAL': '🔒', 'CAP_SHIFT': '↗',
              'METRIC_CHANGE': '📐', 'COST_PROHIBITIVE': '💰', 'FLAWED': '⚠',
              'ONE-TIME': '·',
            };
            const marker = markers[b.lifecycle] || '';
            if (marker && b.lifecycle !== 'ONE-TIME') {
              html += `<span class="drop-marker">${marker}</span>`;
            }
          }

          html += `</div>`;
        }
        html += `</div>`;
      });

      html += `</div></div>`;
    });

    html += `</div></div></div>`;
  });

  area.innerHTML = html;

  // Attach event listeners
  area.querySelectorAll('.lab-header').forEach(el => {
    el.addEventListener('click', () => {
      const lab = el.dataset.lab;
      const body = el.nextElementSibling;
      const toggle = el.querySelector('.lab-toggle');
      if (state.collapsed.has(lab)) {
        state.collapsed.delete(lab);
        body.classList.remove('collapsed');
        const benchmarks = getFilteredBenchmarks(DATA.labs.find(l => l.slug === lab));
        body.style.maxHeight = ((benchmarks.length + 1) * 28 + 40) + 'px';
        toggle.classList.remove('collapsed');
      } else {
        state.collapsed.add(lab);
        body.classList.add('collapsed');
        toggle.classList.add('collapsed');
      }
    });
  });

  // Tooltip
  const tooltip = document.getElementById('tooltip');
  area.querySelectorAll('.bar-segment').forEach(el => {
    el.addEventListener('mouseenter', (e) => {
      const b = JSON.parse(el.dataset.bench);
      const gen = el.dataset.gen;
      const color = DATA.lifecycleColors[b.lifecycle] || '#ccc';
      const label = DATA.lifecycleLabels[b.lifecycle] || b.lifecycle;

      let html = `<div class="tooltip-name">${b.name}</div>`;
      if (b.description) {
        html += `<div style="font-size:12px;color:#555;margin-bottom:6px;line-height:1.4">${b.description}</div>`;
      }
      html += `<div class="tooltip-lifecycle" style="background:${color}">${label}</div>`;

      if (b.dropReasons) {
        html += `<div class="tooltip-row"><span class="label">Drop reasons:</span><span>${b.dropReasons}</span></div>`;
      }
      if (b.bestScore != null) {
        html += `<div class="tooltip-row"><span class="label">Best score:</span><span>${b.bestScore}</span></div>`;
      }
      if (b.dropScore != null) {
        html += `<div class="tooltip-row"><span class="label">Score at drop:</span><span>${b.dropScore}</span></div>`;
      }
      if (b.successor) {
        html += `<div class="tooltip-row"><span class="label">Successor:</span><span>${b.successor}</span></div>`;
      }
      if (b.capabilityTags) {
        html += `<div class="tooltip-row"><span class="label">Capability:</span><span>${b.capabilityTags}</span></div>`;
      }
      html += `<div class="tooltip-row"><span class="label">Generations:</span><span>${b.nGens}</span></div>`;

      // Score trajectory
      const scoreEntries = Object.entries(b.scores);
      if (scoreEntries.length > 0) {
        html += `<div class="tooltip-scores"><h4>Score trajectory</h4><div class="score-list">`;
        scoreEntries.forEach(([g, s]) => {
          const highlight = g === gen ? 'font-weight:700;color:#333' : '';
          html += `<div class="score-entry" style="${highlight}"><span class="gen">${g}:</span> <span class="val">${s}</span></div>`;
        });
        html += `</div></div>`;
      }

      tooltip.innerHTML = html;
      tooltip.style.display = 'block';

      // Position
      const rect = el.getBoundingClientRect();
      let left = rect.right + 12;
      let top = rect.top - 10;
      if (left + 380 > window.innerWidth) left = rect.left - 392;
      if (top + tooltip.offsetHeight > window.innerHeight) top = window.innerHeight - tooltip.offsetHeight - 10;
      if (top < 10) top = 10;
      tooltip.style.left = left + 'px';
      tooltip.style.top = top + 'px';
    });

    el.addEventListener('mouseleave', () => {
      tooltip.style.display = 'none';
    });
  });
}

// === INIT ===
document.getElementById('searchInput').addEventListener('input', (e) => {
  state.search = e.target.value.trim();
  renderChart();
  renderStats();
});

document.getElementById('sortSelect').addEventListener('change', (e) => {
  state.sort = e.target.value;
  renderChart();
});

// Quick filter presets
const PRESETS = {
  signal: new Set(LIFECYCLE_ORDER.filter(s => !DEFAULT_HIDDEN.has(s))),
  all: new Set(LIFECYCLE_ORDER),
  drops: new Set(['SATURATED','SUPERSEDED','CONTAMINATED','FLAWED','FORMAT_AGED','CAP_SHIFT','METRIC_CHANGE','COST_PROHIBITIVE','SUSPICIOUS']),
  suspicious: new Set(['SUSPICIOUS']),
};

function applyPreset(name) {
  state.lifecycleFilters = new Set(PRESETS[name]);
  document.querySelectorAll('.qf-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('qf' + name.charAt(0).toUpperCase() + name.slice(1)).classList.add('active');
  renderSidebar();
  renderStats();
  renderChart();
}

document.getElementById('qfSignal').addEventListener('click', () => applyPreset('signal'));
document.getElementById('qfAll').addEventListener('click', () => applyPreset('all'));
document.getElementById('qfDrops').addEventListener('click', () => applyPreset('drops'));
document.getElementById('qfSuspicious').addEventListener('click', () => applyPreset('suspicious'));

renderSidebar();
renderStats();
renderChart();
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Build interactive benchmark lifecycle visualization")
    parser.add_argument("--mode", choices=["all_evals", "safety"], default="all_evals",
                        help="Which analysis output to visualize")
    args = parser.parse_args()

    print(f"Building interactive visualization for {args.mode}...")
    data = build_data(args.mode)

    total_benchmarks = sum(len(lab["benchmarks"]) for lab in data["labs"])
    print(f"  {len(data['labs'])} labs, {total_benchmarks} benchmark entries")

    # Embed data into HTML
    data_json = json.dumps(data, separators=(",", ":"))
    html = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", data_json)

    out_dir = Path(__file__).parent.parent / "output" / "analysis" / args.mode
    out_path = out_dir / "benchmark_lifecycle_interactive.html"
    out_path.write_text(html, encoding="utf-8")

    print(f"  Written: {out_path}")
    print(f"  Size: {out_path.stat().st_size / 1024:.0f} KB")
    print(f"\n  Open in browser: file:///{out_path.resolve().as_posix()}")


if __name__ == "__main__":
    main()
