# Stanford HELM External Capture

Source: limited — `crfm.stanford.edu` domain consistently refused all WebFetch + Wayback + Google cache attempts. Data below is what could be recovered from secondary coverage via WebSearch.

| model | benchmark | score | variant | source_url |
|---|---|---:|---|---|
| Claude 3 Opus | MMLU | 84.6 | 5-shot (HELM-measured) | medium.com |
| Claude 3 Sonnet | MMLU | 75.9 | 5-shot (HELM-measured) | medium.com |
| GPT-4 (2023-06) | MMLU | 82.4 | 5-shot (HELM-measured) | medium.com |
| Llama 2 70B | MMLU | 69.5 | 5-shot (HELM-measured) | medium.com |
| Claude 3.7 Sonnet | HELM Capabilities mean | 0.674 | aggregate of MMLU-Pro+GPQA+IFEval+WildBench+Omni-MATH | https://crfm.stanford.edu/2025/03/20/helm-capabilities.html |
| Gemini 2.0 Flash | HELM Capabilities mean | 0.679 | aggregate | https://crfm.stanford.edu/2025/03/20/helm-capabilities.html |
| DeepSeek v3 | HELM Capabilities mean | 0.665 | aggregate | https://crfm.stanford.edu/2025/03/20/helm-capabilities.html |

## Access status

HELM data requires direct access to `crfm.stanford.edu/helm/<project>/<version>/groups/latest.json` (client-side rendered tables). The WebFetch tool blocked all `crfm.stanford.edu` URLs + all Wayback / Google cache mirrors. For a rigorous HELM cross-check, the correct next step is running `helm-summarize` locally from the benchmark repo against a pinned HELM release, or having a human fetch the JSON endpoints directly.

**Honest read:** We have 0 cross-validated (frontier model × MMLU) from HELM. HELM remains the gold-standard cross-validation source; this gap is flagged in METHODOLOGY.md as a known limitation until direct access is obtained.
