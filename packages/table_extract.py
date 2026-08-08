"""Read benchmark tables out of a model card by column.

Why this exists
---------------
The extractor reads PDFs through pypdf, which drops column geometry. A Gemini
1.5 table comes out as "39.9% 0-shot 55.8% 0-shot 53.6% 0-shot" with the model
names detached from their numbers, and Claude 3's Table 1 loses the header that
says which of 86.8 / 79.0 / 75.2 is Opus, Sonnet and Haiku.

Two failures follow, and both are in the shipped corpus today:

* **Wrong model.** Every row of a family report is attributed to one model, so
  `anthropic_model_card` has 22 rows all tagged "Claude 3 Opus" and Sonnet and
  Haiku inherit Opus's GPQA of 50.4 (real: 40.4 and 33.3).
* **Wrong benchmark.** Claude 3's *Multilingual* MMLU row (79.1) is stored as
  plain `MMLU`. The real MMLU is 86.8.

`pdftotext -layout` keeps the columns. This module turns that text into rows
that know which model each number belongs to.

The column is a property of the individual table, not of the document. In
`google_gemini_1_5_report` one table is headed `Gemini 1.5 Pro | 1.5 Flash` and
another `1.0 Pro | 1.5 Pro | 1.5 Flash`, so Gemini 1.5 Pro is column 0 in one
and column 1 in the other. Anything that assumes one offset per document is
wrong about half the time. Headers are therefore resolved per table.

Validated against five values read by hand off the source tables:
Claude 3 Opus/Sonnet/Haiku MMLU (86.8 / 79.0 / 75.2) and Claude Fable 5
SWE-bench Verified and Pro (95 / 80, column 1 -- column 0 is Mythos 5, and the
prose confirms it: "Mythos 5 achieved 95.5% and Fable 5 achieved 95%").

    from packages.table_extract import extract_tables, score_for
    score_for(text, model="Claude 3 Haiku", benchmark="MMLU")   -> "75.2"
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# A cell gap in a layout table. Keeping it as a placeholder matters: dropping it
# shifts every column to its right.
GAP = {"-", "--", "—", "–", "n/a", "N/A", ""}

_SPLIT = re.compile(r"\s{2,}")
_SHOTS = re.compile(r"^\d+-shot|^\d+\s*shot|^pass@|^maj@", re.I)


def cells(line: str) -> list[str]:
    return [c.strip() for c in _SPLIT.split(line.strip()) if c.strip()]


def as_number(cell: str) -> str | None:
    t = cell.replace("%", "").replace(",", "").replace("*", "").strip()
    t = re.sub(r"\s*\(.*\)$", "", t)          # "88.0 (single-agent)" -> "88.0"
    if not t or _SHOTS.match(cell):
        return None
    try:
        float(t)
    except ValueError:
        return None
    return t


@dataclass
class Table:
    """One benchmark table: model names across the top, benchmarks down the side."""
    models: list[str] = field(default_factory=list)
    rows: dict[str, list[str | None]] = field(default_factory=dict)
    line_no: int = 0

    def value(self, model: str, benchmark: str) -> str | None:
        col = self.column_of(model)
        if col is None:
            return None
        for name, vals in self.rows.items():
            if _same(name, benchmark) and col < len(vals):
                return vals[col]
        return None

    def column_of(self, model: str) -> int | None:
        want = _norm(model)
        best, best_len = None, 0
        for i, m in enumerate(self.models):
            n = _norm(m)
            if not n:
                continue
            if n == want or (len(n) > 3 and (n in want or want in n)):
                if len(n) > best_len:
                    best, best_len = i, len(n)
        return best


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _same(a: str, b: str) -> bool:
    na, nb_ = _norm(a), _norm(b)
    return bool(na and nb_) and (na == nb_ or na.startswith(nb_) or nb_.startswith(na))


def _tokens(line: str):
    """(text, start_offset) for every whitespace-run-separated cell."""
    return [(m.group().strip(), m.start()) for m in re.finditer(r"\S+(?: \S+)*", line)]


def _numeric_cells(line: str):
    """(value, offset) for numeric cells, skipping shot-counts and row labels."""
    out = []
    for txt, off in _tokens(line):
        v = as_number(txt)
        if v is not None:
            out.append((v, off))
    return out


def extract_tables(text: str, min_cols: int = 2) -> list[Table]:
    """Group numeric rows into tables and name their columns by x-position.

    Header rows in real cards wrap over two or three ragged lines ("Mythos" above
    "5"), so matching them by cell count fails. pdftotext -layout preserves the
    x-offset of every cell, so a column is identified by where it sits on the
    page and a wrapped header is just two tokens at the same offset.
    """
    lines = text.splitlines()
    tables: list[Table] = []
    i = 0
    while i < len(lines):
        nums = _numeric_cells(lines[i])
        if len(nums) < min_cols:
            i += 1
            continue
        block_start = i
        rows_raw = []
        blanks = 0
        while i < len(lines) and blanks < 3:
            nc = _numeric_cells(lines[i])
            if len(nc) >= min_cols:
                label = _tokens(lines[i])[0][0] if _tokens(lines[i]) else ""
                if as_number(label) is None:
                    rows_raw.append((label, nc))
                blanks = 0
            elif not lines[i].strip():
                blanks += 1
            i += 1
        if not rows_raw:
            continue

        offsets = sorted({off for _, nc in rows_raw for _, off in nc})
        merged: list[int] = []
        for o in offsets:
            if merged and o - merged[-1] <= 3:
                continue
            merged.append(o)

        names = ["" for _ in merged]
        for back in range(1, 7):
            ln = block_start - back
            if ln < 0:
                break
            toks = _tokens(lines[ln])
            # Skip span labels. Real cards group columns under a heading that
            # covers several of them at once:
            #     Evaluation   Claude family models      Other models
            #                  Mythos  Fable 5  Mythos   Opus  GPT-5.  Gemini
            # Gluing the span onto the column below produced the model name
            # "Claude family models Fable 5". A span row has far fewer cells
            # than the table has columns, so require it to be nearly as wide.
            if len(toks) < max(2, len(merged) * 0.6):
                continue
            for txt, off in toks:
                if as_number(txt) is not None and len(txt) > 3:
                    continue
                k = min(range(len(merged)), key=lambda x: abs(merged[x] - off))
                if abs(merged[k] - off) <= 12:
                    names[k] = (txt + " " + names[k]).strip()

        rows: dict[str, list[str | None]] = {}
        for label, nc in rows_raw:
            vals: list[str | None] = [None] * len(merged)
            for v, off in nc:
                k = min(range(len(merged)), key=lambda x: abs(merged[x] - off))
                if abs(merged[k] - off) <= 12:
                    vals[k] = v
            rows.setdefault(label, vals)
        if any(n for n in names):
            tables.append(Table(models=names, rows=rows, line_no=block_start))
    return tables


def score_for(text: str, model: str, benchmark: str) -> str | None:
    """The value this model scores on this benchmark, or None if not reported.

    Prefers the table that names the model most specifically, so a card listing
    both "Gemini 1.5 Pro" and "Gemini 1.5 Flash" does not hand back the wrong one.
    """
    for t in extract_tables(text):
        v = t.value(model, benchmark)
        if v is not None:
            return v
    return None


def benchmarks_for(text: str, model: str) -> dict[str, str]:
    """Everything this document reports for this model, by benchmark name."""
    out: dict[str, str] = {}
    for t in extract_tables(text):
        col = t.column_of(model)
        if col is None:
            continue
        for name, vals in t.rows.items():
            if col < len(vals) and vals[col] is not None:
                out.setdefault(name, vals[col])
    return out
