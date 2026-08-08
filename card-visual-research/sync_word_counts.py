#!/usr/bin/env python3
"""Correct each card's word count against the corpus.

The deck's `words` values were authored by hand and most of them are wrong:
Claude Opus 4.8's card face read 475,000 words against a measured 61,922, Llama
2 read 15,000 against 956, and GPT-4 *understated* itself at 8,000 against
27,859. On a set whose whole argument is about disclosure accuracy, the numbers
on the cards have to match the corpus.

Source of truth is `data/dataset/documents.csv` (`word_count_latest`), which is
measured from the fetched document rather than typed in.

The card-to-document pairing is written out by hand below. Fuzzy matching is not
safe here: normalising "GPT-5" to "gpt5" makes it a substring of
"gpt51systemcard", which silently paired GPT-5 with GPT-5.1's card and produced
a bogus 134x discrepancy. Cards with no unambiguous corpus document are listed
in UNMAPPED and left untouched.

    python3 sync_word_counts.py            # dry run
    python3 sync_word_counts.py --apply
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
CARDS = ROOT / "cards"
DOCS_CSV = REPO / "data/dataset/documents.csv"

# card dir -> corpus document slug. Hand-checked, one line at a time.
PAIR = {
    # Anthropic. The Claude 3 family and the Claude 4 family each share one
    # document across several cards, so those cards share a word count too.
    "claude-2": "anthropic_claude2_card",
    "claude-3-haiku": "anthropic_model_card",
    "claude-3-sonnet": "anthropic_model_card",
    "claude-3-opus": "anthropic_model_card",
    "claude-3-5-sonnet": "anthropic_35_addendum",
    "claude-3-5-haiku": "anthropic_35h_addendum",
    "claude-3-7-sonnet": "anthropic_37_card",
    "claude-4-sonnet": "anthropic_claude4_card",
    "claude-4-opus": "anthropic_claude4_card",
    "claude-4-1": "anthropic_opus41_card",
    "claude-4-5": "anthropic_sonnet45_card",   # card.json meta says Sep 2025 = Sonnet 4.5
    "claude-4-6": "anthropic_opus46_card",
    "claude-opus-4-7": "anthropic_opus47_card",
    "claude-opus-4-8": "anthropic_opus48_card",
    "claude-sonnet-4-6": "anthropic_sonnet46_card",
    "claude-mythos-preview": "anthropic_mythos_card",
    # Fable 5 shares one document with Mythos 5, and at 66,211 words it is the
    # longest card in the corpus.
    "claude-fable-5": "anthropic_fable5_card",
    "claude-sonnet-5": "anthropic_sonnet5_card",
    "claude-opus-5": "anthropic_opus5_card",
    # OpenAI
    "gpt-4": "openai_gpt4_system_card",
    "gpt-4o": "openai_gpt4o_system_card",
    "gpt-4-5": "openai_gpt45_system_card",
    "o1": "openai_o1_system_card",
    "o3": "openai_o3_system_card",
    "o3-mini": "openai_o3mini_card",
    "gpt-5": "openai_gpt5_system_card",
    "gpt-5-1": "openai_gpt51_system_card",
    "gpt-5-2": "openai_gpt52_system_card",
    "gpt-5-3": "openai_gpt53_codex_card",
    # Both of these have a decoy in the corpus: GPT-5.5 also ships an "Instant"
    # card (6,446) and GPT-5.6 a "Preview" (19,590). The cards document the full
    # models, so they pair with the full documents.
    "gpt-5-5": "openai_gpt55_system_card",
    "gpt-5-6-sol": "openai_gpt56_full_card",
    # Google. Gemini 1.5 Pro and Flash are both documented by the one report.
    "gemini-1-0-pro": "google_gemini_report",
    "gemini-1-5-pro": "google_gemini_1_5_report",
    "gemini-1-5-flash": "google_gemini_1_5_report",
    "gemini-2-0-flash": "google_gemini_2_card",
    "gemini-2-5-pro": "google_gemini_25_pro_card",
    "gemini-2-5-deep-think": "google_gemini_25dt_card",
    "gemini-3-flash": "google_gemini_3_card",
    "gemini-3-pro": "google_gemini_3_pro_card",
    "gemini-3-1-pro": "google_gemini_31_pro_card",
    # Meta
    "llama-2": "meta_llama2_card",
    "llama-3": "meta_llama3_model_card",
    "llama-3-1": "meta_llama31_card",
    "llama-3-2": "meta_llama32_card",
    "llama-3-3": "meta_responsible_use",
    "llama-4": "meta_llama4_card",
    # Mistral
    "mistral-7b": "mistral_7b_model_card",
    "mistral-large-2": "mistral_large_2_blog",
    # xAI
    "grok-4": "xai_grok4_card",
    "grok-4-fast": "xai_grok4_fast_card",
    "grok-4-1": "xai_grok41_card",
}

# Deliberately not paired. Each would need a guess, and a wrong word count is
# worse than a stale one on a set that argues about disclosure accuracy.
UNMAPPED = {
    "o1-mini": "corpus has no o1-mini card",
    "mixtral-8-7b": "corpus has Mixtral 8x22B, the card is 8x7B",
    "mistral-large": "corpus has Large 2 only, not Large",
    "mistral-3-1": "corpus has Small 3, not 3.1",
}


def fmt(n: int) -> str:
    """Match the existing card style: 475k, 750, 62.8k."""
    if n < 1000:
        return str(n)
    k = n / 1000
    return f"{k:.1f}k".replace(".0k", "k")


def load_corpus() -> dict[str, int]:
    out = {}
    for r in csv.DictReader(open(DOCS_CSV)):
        out[r["slug"]] = int(r["word_count_latest"] or 0)
    return out


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--apply", action="store_true")
    a = p.parse_args(argv)

    corpus = load_corpus()
    changed, same, prose = 0, 0, []
    for cj in sorted(CARDS.glob("*/*/card.json")):
        d = cj.parent
        doc = PAIR.get(d.name)
        if not doc:
            continue
        real = corpus.get(doc)
        if not real:
            print(f"  ?? {d.name}: corpus has no word count for {doc}")
            continue

        card = json.loads(cj.read_text())
        old, new = str(card.get("words", "")), fmt(real)
        if old == new:
            same += 1
            continue

        hp = d / (card.get("html") or f"{d.name}.html")
        card["words"] = new
        if a.apply:
            cj.write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n")

        # The dex strip renders "NO. 012 · 475k words · 18 evals · 73% lab-unique"
        if hp.exists():
            doc_html = hp.read_text()
            fixed = re.sub(r"(<div class=\"dex\">[^<]*?)\b" + re.escape(old) + r"\s+words",
                           lambda m: m.group(1) + new + " words", doc_html, count=1)
            if fixed != doc_html and a.apply:
                hp.write_text(fixed)
            # Flavour prose that cites a length has to be rewritten by a human.
            if re.search(re.escape(old) + r"\s*(k)?\s*(words|characters|-word|-character)",
                         doc_html.split('class="flavor"')[-1][:600], re.I):
                prose.append((d.name, old, new))

        changed += 1
        print(f"  {d.name:24s} {old:>8s} -> {new:>8s}   ({doc}, {real:,} words)")

    print(f"\n  {changed} card(s) corrected, {same} already correct, "
          f"{len(UNMAPPED)} left alone (no safe corpus match)")
    for slug, why in UNMAPPED.items():
        print(f"    skipped {slug:16s} {why}")
    if prose:
        print("\n  flavour text still cites the old figure, rewrite by hand:")
        for slug, old, new in prose:
            print(f"    {slug:24s} mentions {old}, should be {new}")
    if not a.apply:
        print("\n  dry run — re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
