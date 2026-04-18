# External Cross-Check Summary

**Sample size:** 76 of 1417 DB rows had a matching external-source score.

| Verdict | Count | Share |
|---|---:|---:|
| MATCH (within ±2pt of external) | 50 | 65.8% |
| DISPUTE (>2pt gap) | 26 | 34.2% |
| No external source available | 1341 | — |

## Agreement rate: **65.8%** across 76 cross-checkable rows.

## Top 10 largest deltas (for manual review)

- `gpt-5-thinking` | `mmlu` | ours=0.903 external=92.5 **Δ=91.6** (source: 02_mmlu.md)
- `GPT-4o` | `mmlu` | ours=0.8311 external=88.7 **Δ=87.9** (source: 02_mmlu.md)
- `Claude Sonnet 4.6` | `swe_bench` | ours=0.9 external=79.6 **Δ=78.7** (source: 01_swebench.md)
- `Llama 3.3 70B` | `mmlu_pro` | ours=0.666 external=68.9 **Δ=68.2** (source: 15_vellum_aggregate.md)
- `Claude Sonnet 4` | `swe_bench` | ours=15.4 external=72.7 **Δ=57.3** (source: 01_swebench.md)
- `Claude Opus 4.1` | `swe_bench` | ours=18.4 external=74.5 **Δ=56.1** (source: 01_swebench.md)
- `Claude 3.7 Sonnet` | `swe_bench` | ours=23.0 external=62.3 **Δ=39.3** (source: 01_swebench.md)
- `Claude Opus 4.6` | `swe_bench` | ours=53.4 external=80.8 **Δ=27.4** (source: 01_swebench.md)
- `GPT-4o` | `swe_bench` | ours=19.0 external=33.2 **Δ=14.2** (source: 01_swebench.md)
- `GPT-4o` | `taubench` | ours=51.2 external=61.2 **Δ=10.0** (source: 13_tau_bench.md)

## What counts as cross-checkable

A DB row was compared against external data when:
- Our `model_name` normalized (case-insensitive, punctuation stripped) matched an external model's normalized form
- Our benchmark slug OR display name matched an external benchmark's normalized form

## Limitations
- Variant mismatches cause spurious disputes (e.g. our "0-shot CoT" vs external "cons@64")
- Some benchmarks have legitimate score drift across reporting dates (SWE-bench Verified rankings shift)
- External sources are themselves mostly aggregators of vendor-reported numbers (not independent re-runs). True independence requires HELM/vals.ai direct API runs.
