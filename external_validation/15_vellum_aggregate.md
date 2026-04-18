# Vellum LLM Leaderboard Aggregate External Capture

Captured 2026-04-18. Vellum DELIBERATELY excludes MMLU (saturated); uses MMLU-Pro, GPQA-Diamond, AIME 2025, SWE-bench Verified, ARC-AGI-2, HLE, Terminal-Bench.

Representative sample (60+ data points compiled in agent output):

| model | benchmark | score | variant | source |
|---|---|---:|---|---|
| Claude Opus 4.7 | GPQA Diamond | 94.2 | thinking | vellum.ai/blog/opus-4-7 |
| Claude Opus 4.7 | AIME 2025 | 99.8 | thinking | vellum.ai |
| Claude Opus 4.7 | SWE-bench Verified | 87.6 | agentic | vellum.ai |
| Claude Opus 4.7 | SWE-bench Pro | 64.3 | agentic | vellum.ai |
| Claude Opus 4.5 | GPQA Diamond | 87.0 | thinking | vellum.ai |
| Claude Opus 4.5 | AIME 2025 | 100 | with Python | vellum.ai |
| Claude Opus 4.5 | SWE-bench Verified | 80.9 | agentic | vellum.ai |
| Claude Opus 4.5 | ARC-AGI-2 | 37.6 | thinking | vellum.ai |
| Claude Opus 4.5 | HLE (w/ search) | 43.2 | web search | vellum.ai |
| Claude Sonnet 4.5 | SWE-bench Verified | 77.2 | agentic | vellum.ai |
| Claude Sonnet 4.5 | HumanEval | 97.6 | default | vellum.ai |
| Claude Sonnet 4.5 | AIME 2025 | 87.0 | no tools | vellum.ai |
| GPT-5.2 Thinking | GPQA Diamond | 92.4 | thinking | vellum.ai |
| GPT-5.2 Thinking | AIME 2025 | 100 | thinking, no tools | vellum.ai |
| GPT-5.2 Thinking | SWE-bench Verified | 80.0 | thinking | vellum.ai |
| GPT-5.2 Thinking | ARC-AGI-2 | 52.9 | thinking | vellum.ai |
| GPT-5.1 | SWE-bench Verified | 76.3 | thinking | vellum.ai |
| GPT-5 | GPQA Diamond | 85.7 | thinking | vellum.ai |
| GPT-5 | SWE-bench Verified | 74.9 | thinking | vellum.ai |
| GPT-5 | Aider Polyglot | 88.0 | thinking | vellum.ai |
| Gemini 3 Pro | GPQA Diamond | 91.9 | default | vellum.ai |
| Gemini 3 Pro | GPQA Diamond | 93.8 | Deep Think | vellum.ai |
| Gemini 3 Pro | AIME 2025 | 100 | with code exec | vellum.ai |
| Gemini 3 Pro | SWE-bench Verified | 76.2 | default | vellum.ai |
| Gemini 3.1 Pro | GPQA Diamond | 94.3 | default | vellum.ai |
| Gemini 3.1 Pro | SWE-bench Verified | 80.6 | default | vellum.ai |
| o4-mini | GPQA Diamond | 94.2 | reasoning | vellum.ai |
| o4-mini | SWE-bench Verified | 87.6 | reasoning | vellum.ai |
| o3 | GPQA Diamond | 91.3 | reasoning | vellum.ai |
| o3 | SWE-bench Verified | 80.8 | reasoning | vellum.ai |
| Grok 4 | GPQA Diamond | 94.2 | default | vellum.ai |
| Grok 4 | AIME 2025 | 99.8 | default | vellum.ai |
| Grok 4 | SWE-bench Verified | 87.6 | default | vellum.ai |
| DeepSeek R1 | GPQA Diamond | 87.6 | reasoning | vellum.ai |
| DeepSeek R1 | AIME 2025 | 96.1 | reasoning | vellum.ai |
| DeepSeek R1 | MATH-500 | 97.3 | reasoning | vellum.ai |
| Llama 3.1 405B | MMLU | 87.3 | 5-shot legacy | vellum.ai |
| Llama 3.1 405B | HumanEval | 89.0 | 0-shot | vellum.ai |
| Llama 3.1 405B | GPQA | 50.7 | 0-shot non-Diamond | vellum.ai |
| Llama 3.3 70B | MMLU-Pro | 68.9 | 5-shot CoT | vellum.ai |
| Llama 3.3 70B | GPQA Diamond | 50.5 | 0-shot CoT | vellum.ai |

**Note:** Mistral Large 2 is NOT featured on current Vellum leaderboard (shifted to frontier-only 2025+).
