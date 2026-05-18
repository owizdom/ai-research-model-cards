#!/usr/bin/env python3
"""Grep raw card text from the Railway API and rewrite the estimated CSVs
(B, F, J, H, V) with real counts.

Pipeline:
  1. Read C_card_timeline.csv -> 50 (slug, lab, release_date) rows.
  2. Resolve slug -> document_id via /api/v1/documents.
  3. For each id, fetch /api/v1/documents/{id}/content -> content_md.
     Cache to charts/data/article data/_card_text_cache/{slug}.md.
  4. Run phrase greps on each card (case-insensitive). Build a per-card
     master table with flags + counts.
  5. Aggregate into chart CSVs:
        B_language_register.csv (rewrite, per-card classification)
        F_limitations_vocabulary.csv (rewrite, per-year counts)
        J_hedging_signal.csv (rewrite, per-year counts)
        H_category_coverage.csv (rewrite, per-lab pct mentioning)
        V_risk_level_escalation.csv (rewrite, with regex-extracted levels)
        master_card_grep.csv (new — auditable per-card flags)

Run:
    python3 charts/grep_card_text.py
"""
import csv
import json
import re
import sys
import time
import urllib.request
from collections import defaultdict, Counter
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data" / "article data"
CACHE = DATA_DIR / "_card_text_cache"
API = "https://modest-playfulness-production.up.railway.app/api/v1"

CACHE.mkdir(parents=True, exist_ok=True)

# ============================================================
# 1. Read the 50 cards from C_card_timeline.csv
# ============================================================
def load_card_index():
    rows = []
    with open(DATA_DIR / "C_card_timeline.csv") as f:
        for r in csv.DictReader(f):
            rows.append({
                "slug": r["document_slug"],
                "lab":  r["lab"],
                "release_date": r["release_date"],
                "word_count":   r["word_count"],
            })
    return rows

# ============================================================
# 2. Slug -> document_id via /api/v1/documents
# ============================================================
def fetch_json(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())

def resolve_slug_to_id(slugs):
    docs = fetch_json(f"{API}/documents?limit=200")
    by_slug = {d["slug"]: d["id"] for d in docs}
    out = {}
    for s in slugs:
        if s in by_slug:
            out[s] = by_slug[s]
    return out, by_slug

# ============================================================
# 3. Fetch + cache content_md
# ============================================================
def fetch_card_text(slug, doc_id):
    cache_path = CACHE / f"{slug}.md"
    if cache_path.exists() and cache_path.stat().st_size > 0:
        return cache_path.read_text()
    print(f"  fetching {slug} (id={doc_id})...", flush=True)
    data = fetch_json(f"{API}/documents/{doc_id}/content")
    text = data.get("content_md") or ""
    cache_path.write_text(text)
    time.sleep(0.05)
    return text

# ============================================================
# 4. Phrase grep — patterns
# ============================================================
# Hedging phrases for J. case-insensitive.
HEDGING_PHRASES = [
    r"cannot rule out",
    r"can ?not rule out",
    r"could not verify",
    r"could not confirm",
    r"increasingly difficult",
    r"no longer able to",
    r"cannot confidently",
    r"we are uncertain",
    r"unable to (?:verify|confirm|rule out)",
    r"saturated",
]
# Reassurance phrases (used for register classification, B)
REASSURANCE_PHRASES = [
    r"we do not believe",
    r"we are confident",
    r"does not pose",
    r"no evidence (?:that|of)",
    r"no significant risk",
    r"poses (?:no|minimal) risk",
    r"\brule(?:s|d)? out\b(?! ASL| catastrophic)",  # plain "rule out" not "cannot rule out"
]
# Threshold-style language (B)
THRESHOLD_PHRASES = [
    r"\bASL[- ]?[1-4]\b",
    r"preparedness framework",
    r"frontier safety framework",
    r"\bCCL[- ]?[1-4]\b",
    r"acceptable[- ]risk bound",
    r"\d+\.\d+\s*[x×]",         # numeric uplift like 2.1x
    r"below the .{0,30}? threshold",
    r"\b(?:Low|Medium|High|Critical)\b risk",
]

# F — limitations vocabulary (term -> regex)
F_TERMS = {
    "hallucination":         r"hallucinat",
    "bias":                  r"\bbias(?:es|ed)?\b",
    "cot_unfaithfulness":    r"(?:chain[- ]of[- ]thought|\bCoT\b).{0,120}?(?:faithful|unfaith|reliab|insufficient|monitor|illegib)|(?:faithful|unfaith)[^.]{0,40}(?:chain[- ]of[- ]thought|\bCoT\b)",
    "reward_hacking":        r"reward[- ]hack",
    "deception":             r"\bdecept(?:ion|ive)|sycophan|sandbag",
    "benchmark_saturation":  r"\bsaturat(?:ed|ion|ing)\b",
}

# H — category coverage (key -> regex)
H_CATS = {
    "hallucination":     r"hallucinat",
    "bias_fairness":     r"\bbias(?:es|ed)?\b|\bfairness\b",
    "cyber":             r"\bcyber|\bcybersecurity\b|\bexploit(?:ation)?\b|\bhacking\b",
    "cbrn_weapons":      r"\bCBRN\b|biolog(?:ical)? weapon|chemical weapon|\bbioweapon|\bbiorisk|\bnuclear\b|radiological",
    "child_safety":      r"child safety|\bCSAM\b|child sexual|minors?\b",
    "mental_health":     r"mental health|self[- ]harm|\bsuicid",
    "agentic_autonomy":  r"\bagentic\b|\bautonom(?:ous|y)\b|long[- ]horizon|\btool use\b",
    "deception":         r"\bdecept(?:ion|ive)|sycophan|sandbag|scheming",
    "reward_hacking":    r"reward[- ]hack",
    "cot_faithfulness":  r"(?:chain[- ]of[- ]thought|CoT)[^.]{0,60}?(?:faithful|unfaith)",
}

# V — risk-level extraction
V_PATTERNS = {
    "ASL": re.compile(r"\bASL[- ]?([1-4])\b", re.I),
    "PF":  re.compile(r"(?:preparedness[^.]{0,80}?)\b(Low|Medium|High|Critical)\b|\b(Low|Medium|High|Critical)\b[^.]{0,40}?(?:risk|preparedness)", re.I),
    "FSF": re.compile(r"\bCCL[- ]?([1-4])\b|critical capability level[^.]{0,30}?([1-4])", re.I),
}
V_LEVEL_NAME = {
    "ASL": ["pre-RSP", "ASL-1", "ASL-2", "ASL-3", "ASL-4"],
    "PF":  ["pre-PF",  "Low",   "Medium", "High",  "Critical"],
    "FSF": ["pre-FSF", "CCL-1", "CCL-2", "CCL-3", "CCL-4"],
}
PF_LEVEL = {"low": 1, "medium": 2, "high": 3, "critical": 4}

def grep_card(text):
    """Return a dict of all flags + counts for one card."""
    t = text.lower()
    flags = {}

    # Hedging (J, also for B's hedging signal)
    hedging_hits = {}
    for pat in HEDGING_PHRASES:
        m = re.findall(pat, t, re.I)
        if m:
            hedging_hits[pat] = len(m)
    flags["hedging_total_hits"]   = sum(hedging_hits.values())
    flags["hedging_distinct_phrases"] = len(hedging_hits)
    flags["hedging_phrases_matched"] = "; ".join(hedging_hits.keys())
    flags["has_hedging"]          = int(bool(hedging_hits))

    # Reassurance (for B)
    reassurance_hits = {}
    for pat in REASSURANCE_PHRASES:
        m = re.findall(pat, t, re.I)
        if m:
            reassurance_hits[pat] = len(m)
    flags["reassurance_total_hits"] = sum(reassurance_hits.values())
    flags["reassurance_distinct"]   = len(reassurance_hits)

    # Threshold (for B)
    threshold_hits = {}
    for pat in THRESHOLD_PHRASES:
        m = re.findall(pat, t, re.I)
        if m:
            threshold_hits[pat] = len(m)
    flags["threshold_total_hits"]   = sum(threshold_hits.values())
    flags["threshold_distinct"]     = len(threshold_hits)

    # F terms
    for term, pat in F_TERMS.items():
        flags[f"F_{term}"] = int(bool(re.search(pat, t, re.I)))

    # H categories
    for cat, pat in H_CATS.items():
        flags[f"H_{cat}"] = int(bool(re.search(pat, t, re.I)))

    # V — extract MAX risk level by framework
    for fw, pat in V_PATTERNS.items():
        max_level = 0
        if fw == "ASL":
            for m in pat.finditer(text):
                lvl = int(m.group(1))
                if lvl > max_level:
                    max_level = lvl
        elif fw == "FSF":
            for m in pat.finditer(text):
                lvl = m.group(1) or m.group(2)
                if lvl:
                    lvl = int(lvl)
                    if lvl > max_level:
                        max_level = lvl
        elif fw == "PF":
            for m in pat.finditer(text):
                level_str = (m.group(1) or m.group(2) or "").lower()
                lvl = PF_LEVEL.get(level_str, 0)
                if lvl > max_level:
                    max_level = lvl
        flags[f"V_{fw}_level"] = max_level
    return flags

# ============================================================
# 5. Register classifier (B)
# ============================================================
def classify_register(flags):
    """Three buckets — based on which signal type DOMINATES.
    Tie-break: hedging > threshold > reassurance (chronologically newer = more
    "evolved" register; we keep the most-evolved label when tied)."""
    h = flags["hedging_total_hits"]
    t = flags["threshold_total_hits"]
    r = flags["reassurance_total_hits"]
    if h == 0 and t == 0 and r == 0:
        return "reassurance", "no signals — defaulting to reassurance"
    # Strong hedging = hedging present at all
    if h >= 2:
        return "hedging", f"hedging={h} hits"
    # Threshold dominant if more threshold than reassurance
    if t > r:
        return "threshold", f"threshold={t} > reassurance={r}"
    # Hedging beats reassurance with even 1 hit
    if h >= 1 and r == 0:
        return "hedging", f"hedging={h}, no reassurance"
    return "reassurance", f"reassurance={r} >= threshold={t}, hedging={h}"

# ============================================================
# 6. Run pipeline
# ============================================================
def main():
    cards = load_card_index()
    print(f"loaded {len(cards)} cards from C_card_timeline.csv")

    print("resolving slugs to IDs...")
    slugs = [c["slug"] for c in cards]
    slug_to_id, _ = resolve_slug_to_id(slugs)
    missing = [s for s in slugs if s not in slug_to_id]
    if missing:
        print(f"  WARN: {len(missing)} slugs not found: {missing[:5]}...")
    print(f"  resolved {len(slug_to_id)}/{len(slugs)}")

    print("fetching card content (cache-aware)...")
    fetched = 0
    for c in cards:
        s = c["slug"]
        if s not in slug_to_id:
            c["content_md"] = ""
            continue
        try:
            c["content_md"] = fetch_card_text(s, slug_to_id[s])
            fetched += 1
        except Exception as e:
            print(f"  ERROR fetching {s}: {e}")
            c["content_md"] = ""
    print(f"  {fetched} cards fetched/loaded")

    print("running greps...")
    for c in cards:
        c.update(grep_card(c["content_md"]))
        reg, why = classify_register(c)
        c["register"] = reg
        c["register_evidence"] = why
        c["year"] = int(c["release_date"][:4]) if c["release_date"] else None

    # ====== Write master per-card grep CSV ======
    out = DATA_DIR / "master_card_grep.csv"
    cols = ["slug", "lab", "release_date", "year", "word_count",
            "register", "register_evidence",
            "has_hedging", "hedging_total_hits", "hedging_distinct_phrases",
            "hedging_phrases_matched",
            "reassurance_total_hits", "reassurance_distinct",
            "threshold_total_hits",   "threshold_distinct"]
    cols += [f"F_{k}" for k in F_TERMS]
    cols += [f"H_{k}" for k in H_CATS]
    cols += [f"V_{fw}_level" for fw in V_PATTERNS]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for c in cards:
            row = {**c}
            row["slug"] = c["slug"]
            w.writerow(row)
    print(f"[OK] {out.name}")

    # ====== B — register classification ======
    out = DATA_DIR / "B_language_register.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "document_slug", "lab", "release_date", "year",
            "register", "evidence_phrase", "confidence",
        ])
        for c in cards:
            w.writerow([c["slug"], c["lab"], c["release_date"], c["year"],
                         c["register"], c["register_evidence"],
                         "real (phrase-list classifier on raw card text)"])
    print(f"[OK] {out.name}")

    # ====== F — limitations vocabulary by year × term ======
    out = DATA_DIR / "F_limitations_vocabulary.csv"
    by_year = defaultdict(list)
    for c in cards:
        if c["year"]:
            by_year[c["year"]].append(c)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "limitation_term", "year",
            "n_cards_mentioning", "n_total_cards", "pct_mentioning",
            "example_card_slugs", "confidence",
        ])
        for term in F_TERMS:
            for year in sorted(by_year):
                pool = by_year[year]
                key = f"F_{term}"
                hits = [c for c in pool if c.get(key)]
                pct = round(100 * len(hits) / max(len(pool), 1), 1)
                examples = ", ".join(c["slug"] for c in hits[:3])
                w.writerow([term, year, len(hits), len(pool), pct,
                             examples, "real (regex on raw card text)"])
    print(f"[OK] {out.name}")

    # ====== J — hedging signal by year ======
    out = DATA_DIR / "J_hedging_signal.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "year", "n_cards_with_hedging", "n_total_cards", "pct_hedging",
            "example_card_slugs", "example_phrase", "phrases_searched",
            "confidence",
        ])
        for year in sorted(by_year):
            pool = by_year[year]
            hits = [c for c in pool if c.get("has_hedging")]
            pct = round(100 * len(hits) / max(len(pool), 1), 1)
            slugs_str = ", ".join(c["slug"] for c in hits[:4])
            phrase = ""
            for c in hits:
                if c.get("hedging_phrases_matched"):
                    phrase = c["hedging_phrases_matched"].split(";")[0].strip()
                    break
            w.writerow([year, len(hits), len(pool), pct,
                         slugs_str, phrase,
                         "; ".join(HEDGING_PHRASES),
                         "real (regex on raw card text)"])
    print(f"[OK] {out.name}")

    # ====== H — category coverage by lab × category ======
    out = DATA_DIR / "H_category_coverage.csv"
    by_lab = defaultdict(list)
    for c in cards:
        by_lab[c["lab"]].append(c)
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "lab", "category", "category_label",
            "pct_mentioning", "n_cards_mentioning", "n_total_lab_cards",
            "confidence",
        ])
        cat_labels = {
            "hallucination":     "Hallucination",
            "bias_fairness":     "Bias / fairness",
            "cyber":             "Cyber",
            "cbrn_weapons":      "CBRN / weapons",
            "child_safety":      "Child safety",
            "mental_health":     "Mental health",
            "agentic_autonomy":  "Agentic autonomy",
            "deception":         "Deception / scheming",
            "reward_hacking":    "Reward hacking",
            "cot_faithfulness":  "CoT faithfulness",
        }
        for cat in H_CATS:
            for lab in ["anthropic", "openai", "google", "meta", "mistral", "xai"]:
                pool = by_lab.get(lab, [])
                hits = [c for c in pool if c.get(f"H_{cat}")]
                pct = round(100 * len(hits) / max(len(pool), 1), 1)
                w.writerow([lab, cat, cat_labels[cat], pct,
                             len(hits), len(pool),
                             "real (regex on raw card text)"])
    print(f"[OK] {out.name}")

    # ====== V — risk-level escalation per card ======
    out = DATA_DIR / "V_risk_level_escalation.csv"
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "lab", "document_slug", "release_date", "framework",
            "declared_level", "declared_level_numeric",
            "source_quote", "confidence",
        ])
        for c in cards:
            for fw, lab_for_fw in [("ASL","anthropic"),
                                    ("PF","openai"),
                                    ("FSF","google")]:
                if c["lab"] != lab_for_fw:
                    continue
                lvl = c.get(f"V_{fw}_level", 0)
                w.writerow([
                    c["lab"], c["slug"], c["release_date"], fw,
                    V_LEVEL_NAME[fw][lvl], lvl,
                    f"max {fw} level matched in card text",
                    "real (regex on raw card text)"
                    if lvl > 0 else "real (no match found)",
                ])
    print(f"[OK] {out.name}")

    # Summary stats so we can sanity-check before re-rendering
    print("\n=== SANITY CHECKS ===")
    print(f"\nB register distribution:")
    reg_count = Counter(c["register"] for c in cards)
    for r, n in reg_count.most_common():
        print(f"  {r}: {n}")
    print(f"\nB by year × register:")
    for year in sorted(by_year):
        rs = Counter(c["register"] for c in by_year[year])
        print(f"  {year}: {dict(rs)}")
    print(f"\nJ hedging by year:")
    for year in sorted(by_year):
        pool = by_year[year]
        hits = sum(1 for c in pool if c.get("has_hedging"))
        print(f"  {year}: {hits}/{len(pool)} = {100*hits/len(pool):.0f}%")
    print(f"\nF terms by year (cards mentioning):")
    for term in F_TERMS:
        by_yr = []
        for year in sorted(by_year):
            pool = by_year[year]
            hits = sum(1 for c in pool if c.get(f"F_{term}"))
            by_yr.append(f"{year}={hits}/{len(pool)}")
        print(f"  {term}: {' '.join(by_yr)}")
    print(f"\nH category coverage by lab (mean across cats):")
    for lab in ["anthropic", "openai", "google", "meta", "mistral", "xai"]:
        pool = by_lab.get(lab, [])
        if not pool: continue
        means = []
        for cat in H_CATS:
            hits = sum(1 for c in pool if c.get(f"H_{cat}"))
            means.append(hits / len(pool))
        print(f"  {lab}: mean coverage {100*sum(means)/len(means):.0f}% across {len(pool)} cards")
    print(f"\nV max levels:")
    for fw, lab_for_fw in [("ASL","anthropic"),
                             ("PF","openai"),
                             ("FSF","google")]:
        cards_lab = [c for c in cards if c["lab"] == lab_for_fw]
        levels = sorted(set(c.get(f"V_{fw}_level", 0) for c in cards_lab))
        print(f"  {fw} ({lab_for_fw}): levels seen = {levels}")

if __name__ == "__main__":
    main()
