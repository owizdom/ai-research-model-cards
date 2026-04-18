-- Industry-domain classification for benchmark_definitions
-- Source of truth:
--   (1) packages/db/seed/benchmark_ontology.py (56 curated slugs)
--   (2) data/exports/groq_baseline_20260408_224114.csv (209 extracted eval rows
--       covering every benchmark NAME the extractor has minted through 2026-04-08)
--   (3) user's 8-domain taxonomy (general_academic default)
-- Slug derivation: lowercase -> [^a-z0-9]+ collapsed to "_" -> strip leading/trailing _
-- (matches apps/worker/src/extractor/eval_extractor.py::_slugify)

BEGIN;

ALTER TABLE benchmark_definitions ADD COLUMN IF NOT EXISTS industry_domain VARCHAR;

-- =========================================================================
-- software_engineering  (code gen, patching, function calling, swe-agent)
-- =========================================================================
UPDATE benchmark_definitions SET industry_domain = 'software_engineering' WHERE slug IN (
  'humaneval', 'humaneval_', 'humaneval_python',
  'mbpp', 'mbpp_',
  'swe_bench', 'swe_bench_verified', 'swe_bench_lite',
  'swe_lancer', 'swe_lancer_diamond',
  'livecodebench', 'live_code_bench',
  'bfcl', 'berkeley_function_calling',
  'agentic_coding',
  'multipl_e', 'multipl_e_aggregate',
  'apps',
  'natural2code',
  'codeforces', 'codecontests', 'mercury',
  'mle_bench',
  'coding_deception',
  'nexus',
  'ds_1000', 'ds1000',
  'paperbench'  -- ML-engineering research replication, closest to SWE
);

-- =========================================================================
-- healthcare_medical
-- =========================================================================
UPDATE benchmark_definitions SET industry_domain = 'healthcare_medical' WHERE slug IN (
  'medqa', 'medqa_usmle',
  'pubmedqa',
  'medmcqa',
  'healthbench',
  'usmle',
  'mmlu_med', 'mmlu_medical',
  'medbullets', 'medexpqa', 'mediq', 'multimedqa',
  'biolp_bench',                   -- Grok 4 biology protocols
  'lab_bench_subset', 'lab_bench', -- wet-lab research QA
  'long_form_virology_task_2',
  'protocol_design',
  'sequence_design',
  'short_horizon_computational_biology_tasks',
  'creative_biology_tasks',
  'wmdp_bio',                      -- biosecurity hazardous-knowledge (see report)
  'wmdp_chem'                      -- chemistry hazardous-knowledge (see report)
);

-- =========================================================================
-- education_exams  (competition / standardized exam benchmarks)
-- =========================================================================
UPDATE benchmark_definitions SET industry_domain = 'education_exams' WHERE slug IN (
  'aime', 'aime_2024', 'aime_2025', 'aime24', 'aime25',
  'amc', 'amc_10', 'amc_12',
  'gpqa', 'gpqa_diamond', 'gpqa_main',
  'math', 'math_500',
  'hmmt',
  'physicsfinals', 'physics_finals',
  'race_h', 'race_m',
  'agi_eval', 'agieval',
  'sat', 'gre', 'lsat',
  'olympiad_bench', 'olympiadbench'
);

-- =========================================================================
-- crm_enterprise  (customer-service, sales, business-workflow agents)
-- =========================================================================
UPDATE benchmark_definitions SET industry_domain = 'crm_enterprise' WHERE slug IN (
  'tau_bench', 'tau_2_bench', '_bench_telecom', 'tau_bench_telecom',
  'tau_bench_retail', 'tau_bench_airline',
  'crmarena', 'crm_arena',
  'sales_bench',
  'productionbenchmarks',          -- OpenAI prod-traffic safety suite (enterprise prod)
  'mcp_atlas'                      -- Anthropic enterprise tool-use suite
);

-- =========================================================================
-- cybersecurity
-- =========================================================================
UPDATE benchmark_definitions SET industry_domain = 'cybersecurity' WHERE slug IN (
  'cybench', 'cy_bench',
  'cybergym', 'cyber_gym',
  'agentdojo', 'agent_dojo',
  'wmdp_cyber',
  'ctf_challenges',
  'computer_use_prompt_injection_evaluation',
  'human_sourced_jailbreaks',
  'browsing_broken_tools',         -- tool-use deception; judgment call (see report)
  'vct'                            -- vulnerability/CVE triage — Grok 4
);

-- =========================================================================
-- legal
-- =========================================================================
UPDATE benchmark_definitions SET industry_domain = 'legal' WHERE slug IN (
  'legalbench', 'legal_bench',
  'cuad',
  'casehold', 'case_hold',
  'lex_glue', 'lexglue'
);

-- =========================================================================
-- finance_tax
-- =========================================================================
UPDATE benchmark_definitions SET industry_domain = 'finance_tax' WHERE slug IN (
  'finqa', 'fin_qa',
  'financebench',
  'bizbench', 'biz_bench',
  'convfinqa', 'conv_fin_qa',
  'tatqa', 'tat_qa',
  'mmlu_finance'
);

-- =========================================================================
-- general_academic  (default — knowledge, reasoning, safety, multimodal,
--                   multilingual, long-context, agent/web, arena/elo)
-- Explicit list makes intent auditable; the trailing `WHERE industry_domain
-- IS NULL` clause is the actual default catch-all.
-- =========================================================================
UPDATE benchmark_definitions SET industry_domain = 'general_academic' WHERE slug IN (
  -- Knowledge / academic
  'mmlu', 'mmlu_pro', 'mmmlu',
  'arc_challenge', 'arc_easy', 'arc_easy_hausa',
  'hellaswag', 'winogrande',
  'triviaqa', 'natural_questions', 'naturalquestions_closed_book', 'naturalquestions_retrieved',
  'fever', 'boolq', 'drop',
  'big_bench_hard', 'bbh', 'big_bench_hard_3_shot',
  'common_sense_reasoning', 'commonsense_reasoning', 'reading_comprehension', 'world_knowledge',
  'ai2d',                                   -- science diagrams; general academic KB
  -- Reasoning / math (general)
  'gsm8k', 'mgsm',
  'arc_agi', 'arc_agi_2', 'arc_agi_2_verified',
  'ifeval',
  'maj_64',
  'time_horizon_score',
  -- Multimodal (non-domain-specific)
  'mmmu', 'mmmu_pro', 'mathvista', 'chartqa', 'docvqa', 'charxiv_missing_image',
  -- Multilingual / translation
  'flores', 'xnli', 'tydiqa', 'tydiqa_goldp', 'wmt_23', 'xlsum', 'wikilingua',
  'multilingual_safety', 'image_to_text_safety', 'text_to_text_safety',
  'mtob', 'mtob_full_book_eng_kgv_kgv_eng',
  -- Long context
  'infinitebench', 'infinitebench_en_mc', 'nih_multi_needle',
  'quality',
  -- Agent / web / OS (general)
  'webarena', 'osworld', 'osworld_verified', 'browsecomp',
  -- Arena / elo
  'chatbot_arena_elo',
  -- Safety (cross-cutting — see report)
  'truthfulqa', 'bbq', 'toxigen', 'xstest', 'realtoxicityprompts',
  'bias_benchmark_for_question_answering',
  'agentharm',
  'abstention_bench',
  'strongreject_evaluation',
  'standard_disallowed_content_evaluation',
  'single_turn_benign_request_evaluation', 'single_turn_violative_request_evaluation',
  'wildchat_non_toxic', 'wildchat_toxic',
  'vision_self_harm_refusal_evaluation', 'vision_sexual_refusal_evaluation',
  'unjustified_refusals', 'tone', 'reasoning_monitor', 'topical_classifier',
  'safety_evaluations', 'speaker_identification',
  'ungrounded_inference_and_sensitive_trait_attribution',
  'makemesay', 'make_me_say',               -- persuasion
  -- Moderation classifiers
  'openai_mod', 'toxicchat', 'our_test_set_prompt', 'our_test_set_response', 'internal_test',
  -- Misc
  'metr', 'chatgpt_and_openai_api_prompts'
);

-- Default: anything we didn't explicitly classify falls back to general_academic.
UPDATE benchmark_definitions SET industry_domain = 'general_academic' WHERE industry_domain IS NULL;

COMMIT;

-- To inspect after running:
-- SELECT industry_domain, COUNT(*) FROM benchmark_definitions GROUP BY 1 ORDER BY 2 DESC;
