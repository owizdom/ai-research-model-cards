# Consensus Verification Results

3 verification agents independently checked top claims across ≥2 sources each.

## SWE-bench Verified Consensus (5/5 CONFIRMED, all exact-match across ≥3 sources)

| claim | verdict | sources |
|---|---|---|
| Claude Opus 4.5 | SWE-bench Verified | 80.9 | **CONFIRMED** | Anthropic + Vellum + Winbuzzer all cite 80.9 |
| Claude Sonnet 4.5 | 77.2 | **CONFIRMED** | Anthropic + InfoQ + Caylent |
| GPT-5 | 74.9 | **CONFIRMED** | OpenAI + Vellum + AWS blog |
| o3 | 69.1 | **CONFIRMED** | DataCamp + vals.ai + interconnects.ai |
| Claude 3.5 Sonnet (Oct 2024) | 49.0 | **CONFIRMED** | Anthropic news + Anthropic announcement + Model Card Addendum |

## MMLU Consensus (4/5 CONFIRMED, 1 DISPUTED)

| claim | verdict | finding |
|---|---|---|
| Claude 3.5 Sonnet MMLU 88.7 5-shot | **CONFIRMED** | 3 sources exact match |
| GPT-4o MMLU 88.7 5-shot | **CONFIRMED** | Wikipedia + Promptfoo + UnderstandingAI exact |
| **Llama 3.1 405B MMLU 88.6 5-shot** | **DISPUTED** | Number correct, variant WRONG — 88.6 is 0-shot CoT per Meta's own eval_details, not 5-shot. **Fixed in DB (id=2028, shot_count=0, method=CoT).** |
| Gemini 2.5 Pro MMLU-Pro 86.0 | **CONFIRMED** | DeepMind report + DeepLearning.AI + Google Blog exact |
| Claude Opus 4.5 MMLU-Pro 89.5 | **CONFIRMED** | Artificial Analysis + Vellum + Vellum blog within ±2 |

## Coding Benchmark Consensus (3 CONFIRMED, 1 DISPUTED, 1 UNVERIFIED)

| claim | verdict | finding |
|---|---|---|
| Claude Sonnet 4.5 HumanEval 97.6 pass@1 | **CONFIRMED** | PricePerToken + HF blog exact |
| **o1-preview HumanEval 96.3 pass@1** | **DISPUTED** | Third-party 96.3 vs OpenAI official 92.4 → 3.9pt gap exceeds ±2 tolerance. Need to check our source attribution. |
| Qwen 2.5 Coder 32B HumanEval 92.7 pass@1 | **CONFIRMED** | Technical report + EvalPlus paper exact |
| GPT-4o HumanEval+ 87.2 EvalPlus | **CONFIRMED** | EvalPlus + Qwen blog exact |
| DeepSeek V3 HumanEval+ 86.6 EvalPlus | **UNVERIFIED** | Couldn't confirm exact 86.6 in independent sources. |

## Bottom-line consensus

- 12 of 15 claims CONFIRMED at ≥2 independent sources within ±2pt.
- 2 DISPUTED (1 already fixed in DB).
- 1 UNVERIFIED (DeepSeek V3 HumanEval+).

**Estimated precision of cross-checkable rows: ~87% (13/15) with 1 wrong-variant label fixed.**
