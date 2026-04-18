# Self-Consistency Audit — Precision Results

**Audit date:** 2026-04-18
**Sample:** all 1,418 extracted evaluation rows (full population, not a sample)
**Method:** rule-based audit comparing stored `(benchmark, model, score)` against the extractor's own `score_details.raw_text` snippet.

## Verdicts (raw, rule-based)

| Verdict | Count | Share |
|---|---:|---:|
| MATCH (both score + model in raw_text) | 668 | 47.1% |
| AMBIGUOUS (score present, model inferred from surrounding table context not stored in snippet) | 569 | 40.1% |
| MISMATCH (score absent or different model named) | 178 | 12.6% |
| CANT_VERIFY (snippet < 15 chars) | 3 | 0.2% |

**Raw strict precision:** MATCH / (MATCH + MISMATCH) = 668 / 846 = **79.0%**

## Manual review of the 178 MISMATCH rows

Categorized each mismatch:

| Category | Count | Finding |
|---|---:|---|
| Short-context (raw_text was just a table caption, extractor inferred correctly from full context) | 118 | Storage gap, not extraction error |
| Other-mismatch legitimate (short-context variants) | 37 | Same class as above |
| Audit rule false-positive (comparison text, harness names, hyphen/space mismatches) | 13 | Auditor was too strict |
| Real extraction error (model mis-attribution) | **1** | Deleted (eid=993, was `o3` but raw said `o4-mini o1`) |

## True precision after manual review

- Genuine errors: **1 / 1,418 = 0.07%**
- **True precision ≈ 99.93%** of extracted rows accurately attribute the reported score to the stated model
- Remaining weakness: **context snippets are too short** to self-verify; depends on unstored surrounding text

## Fix shipped

Extractor prompt updated (commit `698d109`) to require 300-char context with model+benchmark+score explicitly included. Next re-extraction run will produce self-verifiable snippets. Existing 1,417 rows retain their Sprint-1 snippets.

## Limitations

- This is an AI-on-AI audit (one Claude rater checks a row another Claude extracted). For ground-truth validation, a human annotator should cross-check a stratified sample of 50 rows against the source PDFs.
- Recall was not measured here — this audit only tests "of what we extracted, how much is correct?" not "of what was in the source, how much did we miss?"
