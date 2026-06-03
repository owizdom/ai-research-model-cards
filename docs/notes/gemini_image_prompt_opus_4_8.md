# Claude prompt — design the Claude Opus 4.8 evaluation card

Paste the block between `---START---` and `---END---` into a fresh Claude
chat (claude.ai or Claude Code). Claude produces a single HTML artifact you
can render in the artifact pane and screenshot. This is design-quality, not
photographic — it ships as crisp typography, geometric SVG hero art, and
real CSS layout, which is what you want for the v1 mockup of modelcards.net.

---START---

You are a senior product designer with three layered specializations:

1. Editorial design for scientific publications (MIT Press, Phaidon, Edward
   Tufte aesthetics).
2. Trading-card systems (the visual grammar of Pokémon TCG, Magic: The
   Gathering, and modern boutique TCG art books like the Sushi Go! series).
3. Information density for technical readers (research dashboard
   typography, ratio-driven layout grids, restrained color systems).

You output **one single self-contained HTML file** that renders a static
design mockup. No external dependencies — all CSS inline, all imagery as
inline SVG. The deliverable goes in an artifact and I will screenshot it.

## What we're making

A **two-faced** trading-card-style "evaluation card" for the AI model
**Claude Opus 4.8** (Anthropic, released 2026-05-28). This is the v1
design for modelcards.net, a Stanford GSB Free Systems Lab project
building an interpretive transparency layer over AI model evaluations.
The thesis paper is *EvalCards 2: An Interpretive Layer for AI
Evaluation Reporting* (NeurIPS 2026 submission).

The artifact should render both faces side by side on the same page
(front on the left, back on the right), as if photographed together on a
designer's reference table. Both faces share the exact same dimensions,
frame, palette, and typography — they're two sides of the same physical
object, not two different posters.

- **Front face** = the EvalCards "policy mode": glanceable, headline,
  decision-ready. Designed to be readable in three seconds.
- **Back face** = the EvalCards "research mode": dense, methodological,
  provenance-explicit. Designed to be readable in three minutes.

The card has the visual grammar of a Pokémon TCG card — identity strip on
top, hero illustration, capability "moves", weakness/resistance row — but
the aesthetic is **prestige scientific monograph**, not toy. Imagine the
card pulled out of a slim Phaidon-published volume titled *The Evaluation
Cards Catalogue, 2026 Edition*. It should look like an artifact a
researcher would frame above their desk and a designer would post to
Are.na.

Why these design constraints exist (so you can make judgment calls when
the spec is ambiguous):

- Our user survey (n=4) found 75% of respondents use model cards for
  **research and benchmarking**, not vendor selection. The card is for a
  technically literate reader who wants information density.
- The top reported gaps in current model cards were training-data
  provenance and failure modes. The EvalCards 2 paper's central
  finding is that 98.2% of (model, benchmark) pairs are reported by only
  one party, and 96.5% lack at least one reproducibility field. The card
  must signal these conditions honestly — visible reliability flags, not
  smoothed averages.
- Anthropic's brand identity is warm, scholarly, restrained. Cream paper,
  copper-orange accent, serif typography. The card must look like
  Anthropic, not generic AI-startup aesthetic.

## Card dimensions and frame

- Aspect ratio **2.5 : 3.5** (Pokémon TCG standard). Render at 500px ×
  700px in the HTML for the mockup; the design must remain readable at
  half-size.
- Centered on a soft neutral page background, color around `#EDE7DA`, so
  the card photographs well.
- Drop shadow under the card: `0 24px 48px rgba(58, 40, 23, 0.18)`. Slight
  realistic perspective tilt is fine (transform-rotate-y of about 2deg)
  but make sure the card is fully readable.
- Card frame: 4px copper-gold foil border. Build the foil look in CSS with
  a linear gradient between `#B87B3A`, `#E8B86F`, and `#8C5A28`, animated
  if you want, static if cleaner.
- 24px outer corner radius. 16px inner content radius.
- 28px internal padding all around.
- Subtle paper-grain noise on the card surface (CSS `filter: url(#grain)`
  with an SVG turbulence filter, or a base64 noise PNG).

## Color palette (use these and only these)

```
--ink            #3A2817   primary text (espresso)
--ink-soft       #6B4F35   secondary text
--paper          #F5F1E8   card body background (warm cream)
--paper-shadow   #E8E0CE   card inner shadow color
--accent         #C66A2B   rust orange, used sparingly for emphasis
--accent-deep    #8C4A1A   accent shadow / hover
--copper-light   #E8B86F   foil highlight
--copper-mid     #B87B3A   foil base
--copper-dark    #8C5A28   foil shadow
--neutral-stroke #D9CFB8   thin dividers
--success        #4F7A4A   reliability flag green
--warn           #B07B2B   reliability flag amber
--alert          #A4452E   reliability flag red
```

White (#FFFFFF) is forbidden anywhere on the card. The eye should never
hit a pure white surface — that's what kills the prestige aesthetic.

## Typography

Use Google Fonts with `@import`. Three families only:

- Display (model name, card title, big numbers): **Cormorant Garamond** —
  weight 600, slight letter-spacing. This is the serif that makes the
  card feel like a monograph.
- Body and stats: **Inter** — weights 400, 500, 600.
- Slug / monospaced details (generation_slug, release date): **JetBrains
  Mono** — weight 500, slightly tighter tracking.

Type scale:

- Model name title: 32px Cormorant Garamond 600, tracking 0.01em
- Capability badge label "CAP": 9px Inter 600 caps, tracking 0.12em
- Capability badge number: 36px Cormorant Garamond 600
- Hero subtitle: 11px JetBrains Mono 500, tracking 0.04em
- Move row label (e.g. "SWE-BENCH VERIFIED"): 12px Inter 600 caps,
  tracking 0.08em
- Move row score: 24px Cormorant Garamond 600, tabular-nums
- Move row split: 9px Inter 500 italic, color `--ink-soft`
- Reliability flag label: 9px Inter 600 caps
- Reliability flag value: 14px Inter 600 tabular-nums
- Bottom strip: 8px JetBrains Mono 400, color `--copper-mid`,
  tracking 0.08em

## FRONT FACE — zone-by-zone layout

Top to bottom, with vertical gaps of 14px between zones unless noted.

### Zone 1 — Identity strip (height ~64px)

Three-column row.

- **Left** (60% width): model name "Claude Opus 4.8" as the title.
  Beneath it on a second line in 9px JetBrains Mono caps with 0.08em
  tracking: `ANTHROPIC · OPUS GENERATION`.
- **Right** (40% width): a circular badge, 56px diameter, with copper
  gradient stroke at 2px and cream interior. Inside: top line
  "CAP" in 9px Inter caps, bottom line a large numeral. Use the
  number **96** for Claude Opus 4.8. The capability index here is a
  designed composite, not pulled from a single benchmark.

The strip ends with a thin neutral divider line (1px, `--neutral-stroke`).

### Zone 2 — Hero art (height ~210px, full card width minus padding)

A recessed window with `--paper-shadow` inner shadow at the corners (8px
inset) and soft inner glow from the center.

Inside, render an **abstract crystalline geometric sculpture in SVG**.
Form language: a stack of three to five faceted prisms or hexagonal
lattices, nested and offset, in warm copper-orange gradients. The piece
should suggest layered reasoning and structured knowledge. Lighting from
top-left. No anthropomorphism. No face. No creature. No actual logos.

The SVG should be sophisticated — at least 30 path elements, with subtle
gradient stops and small geometric details (thin construction lines,
faint inner facets, a few small accent circles). Think Sol LeWitt drawing
× a polished mineral specimen.

The hero window has a single tiny annotation in the bottom-right corner
of the window, in 8px JetBrains Mono: `obj_001`. Like a museum catalog
number. This sells the prestige feel.

### Zone 3 — Subtitle strip (height ~22px)

Single line of 11px JetBrains Mono, color `--ink-soft`, centered:
`RELEASED · 2026-05-28 · 200K CONTEXT · 244-PAGE SYSTEM CARD`

### Zone 4 — Type tag row (height ~30px)

Three pill-shaped chips, evenly spaced, centered. Each chip is 4px
vertical padding, 12px horizontal padding, 999px border radius, 1px solid
`--accent` border, cream interior, 10px Inter 600 caps in `--accent`:

- `AGENTIC`
- `REASONING`
- `MULTIMODAL`

### Zone 5 — Move boxes (height ~180px total, three stacked)

Three horizontal rows separated by thin 1px `--neutral-stroke` dividers.
Each row is 60px tall, three columns:

1. **Left** (~36px): a colored circular "energy" bullet, 18px diameter.
2. **Middle** (flex grow): move label in 12px Inter 600 caps, with a
   smaller italic split line beneath in 9px Inter 500.
3. **Right** (~80px, right-aligned): score in 24px Cormorant Garamond
   600 with tabular-nums, plus a tiny 8px JetBrains Mono line beneath
   showing the metric path.

The three rows:

- Bullet color `--accent` (orange) · **SWE-BENCH VERIFIED** · split
  *verified, n=500, 5-trial average* · score **88.6** · metric
  *resolve_rate*
- Bullet color `--copper-mid` (gold) · **USAMO 2026** · split
  *6-problem, 10-attempt average* · score **96.7** · metric *accuracy*
- Bullet color `#6B5A8C` (muted indigo, not in palette but allowed for
  one of the three to vary) · **TERMINAL-BENCH 2.1** · split *Harbor /
  Terminus-2 harness, 89 tasks, 5-attempt mean* · score **74.6** ·
  metric *mean_reward*

### Zone 6 — Reliability flag row (height ~52px)

Four small badge cards in a row, evenly spaced. Each badge is 70px wide,
44px tall, cream interior, 1px `--neutral-stroke` border, 8px corner
radius. Internal layout: top line label, middle line a 0–100 number,
bottom thin color bar.

Use these values for Opus 4.8 (chosen to make the design demonstrate the
EvalCards interpretive-signal idea — real-data versions can swap in):

- **REPROD.** value 24, bar color `--alert` red — reflects the paper's
  finding that 96.5% of triples miss reproducibility fields
- **COMPL.** value 41, bar color `--warn` amber
- **PROV.** value 100, bar color `--success` green — first-party card
- **COMPAR.** value 38, bar color `--warn` amber — competitor scores
  reported but spread is moderate

Hovering or focusing a badge should expand a small caption beneath (in
the static design just show one in the expanded state for Reprod.,
with caption text: *"95% of this card's eval rows lack at least one
required reproducibility field — temperature, max_tokens, prompt
template, eval_plan, or eval_limits."*).

### Zone 7 — Weakness / Resistance / Retreat row (height ~22px)

Single horizontal strip with three labels separated by 1px vertical
hairlines, 8px Inter 600 caps:

- `WEAKNESS · single-source evals (98.2% of corpus)`
- `RESISTANCE · extended thinking, adaptive budget`
- `RETREAT · 1M tokens`

Color the labels in `--ink-soft`, the values in `--ink`.

### Zone 8 — Bottom foil strip (height ~24px)

Full-width strip at the bottom of the card with a subtle copper gradient
background. Single line, centered, 8px JetBrains Mono 400 caps in
`--paper`:

`MODELCARDS.NET · EVALUATION CARD V1 · SOURCED FROM ANTHROPIC CLAUDE OPUS 4.8 SYSTEM CARD · MAY 2026`

## BACK FACE — zone-by-zone layout

Same dimensions as the front (500px × 700px, 2.5:3.5 ratio, copper foil
border, cream paper, etc.). The back is the **research mode** face. Type
scale is slightly compressed because the back is information-dense by
design — drop body sizes by 1px from the front-side scale where it helps
fit. Vertical gaps between zones drop from 14px to 10px.

The back's central principle (from the EvalCards 2 paper): **make
absence visible**. Anywhere a field is empty or undisclosed, render an
explicit "Not disclosed" pill in `--warn` or `--alert` rather than
hiding the row. The back exists to expose what's missing as much as
what's present.

### Back zone 1 — Compressed identity strip (height ~40px)

Same model name and lab as the front, but smaller:
- Model name "Claude Opus 4.8" in 20px Cormorant Garamond 600
- Beneath: `ANTHROPIC · OPUS GENERATION · METHODOLOGY VIEW` in 9px
  JetBrains Mono caps with 0.08em tracking, color `--ink-soft`
- Right side: a small `back face` watermark in 8px JetBrains Mono caps,
  rotated -90deg vertically along the right edge — like the spine
  imprint on a book

Thin neutral divider line below.

### Back zone 2 — Evaluation table (height ~180px)

A compact table of the model's top six benchmark rows, rendered at full
EvalCards 5-level rollout: Family → Composite → Benchmark → Split →
Metric. Six rows, 24px row height each.

Header row (12px Inter 600 caps, color `--ink-soft`, tracking 0.08em):
`BENCHMARK` · `SPLIT` · `SCORE` · `METRIC` · `SETUP`

Use these exact rows (real Opus 4.8 data from our extraction):

| benchmark | split | score | metric | setup |
|---|---|---|---|---|
| SWE-bench | verified | 88.6 | resolve_rate | ext-thinking, 5-trial avg |
| SWE-bench | pro | 69.2 | resolve_rate | ext-thinking, 5-trial avg |
| GPQA | diamond | 93.6 | accuracy | 25-trial avg |
| USAMO | 2026 | 96.7 | accuracy | 10-attempt avg, batch API |
| Terminal-Bench | 2.1 | 74.6 | mean_reward | Terminus-2 harness |
| HLE | with-tools | 57.9 | accuracy | web+code+fetch |

Body type: 10px Inter 500 for benchmark and split, 10px JetBrains Mono
500 tabular-nums for score, 9px Inter 400 italic for setup.

Each benchmark name is underlined with a 1px dotted `--ink-soft` line to
hint at the BenchmarkPopover behavior in the real product. Each row ends
with a tiny self-reported badge: small filled circle in `--accent` with
8px caps "SR" inside (since all Opus 4.8 rows are self-reported).

### Back zone 3 — Training data provenance (height ~64px)

Section header "TRAINING DATA PROVENANCE" in 9px Inter 600 caps with
tracking 0.12em, color `--ink-soft`. A 1px `--neutral-stroke` line below.

Inside, four labeled fields in a 2-column grid, each field with a 9px
caps label and 11px value:

- **CUTOFF** — `Not disclosed` (warn pill)
- **SOURCES** — `Not disclosed` (warn pill)
- **EXCLUSIONS** — `Not disclosed` (warn pill)
- **CONTAMINATION NOTE** — `2026 USAMO collected after most training data`
  *(the one Opus 4.8 explicitly addresses)*

Anthropic's system cards intentionally publish very little provenance.
The empty-state pills here are not a bug — they're the point. Show them
in `--warn` amber so the reader sees the gap.

### Back zone 4 — Failure modes (height ~60px)

Section header "FAILURE MODES · DISCLOSED" with the same caps treatment.
Three bullet rows, 10px Inter 500, color `--ink`. Use these placeholders
(Anthropic's card does discuss these in prose):

- Low chain-of-thought controllability vs prior Opus models
- 1M-token context subset not reproducible via public API
- HLE no-tools results require >1hr sampling, exceed Public API limits

### Back zone 5 — Threshold assessments (height ~52px)

Section header "THRESHOLD ASSESSMENTS · LOAD-BEARING". Two items in 10px
Inter 500:

- **ASL-3 safeguards** — passed (Anthropic's responsible-scaling framework)
- **CBRN uplift threshold** — not crossed per internal red-team

Each item has a small `--success` green dot at the left.

### Back zone 6 — Reproducibility recipe (height ~48px)

Section header "REPRODUCIBILITY". Four mono fields stacked:

- `harness` — `Not disclosed` (warn pill)
- `container` — `Not disclosed` (warn pill)
- `seed` — `Not disclosed` (warn pill)
- `prompt template` — `system card §8, partial` (warn pill)

This zone exists precisely to show the paper's 96.5% reproducibility-gap
finding rendered concretely on a real card.

### Back zone 7 — Cross-source comparison (height ~80px)

Section header "CROSS-SOURCE · SWE-BENCH VERIFIED". A small comparison
table, three rows, showing where this card's SWE-bench Verified score
sits against other sources:

| source | score | divergence |
|---|---|---|
| Anthropic Opus 4.8 card (this card) | 88.6 | — |
| Anthropic Opus 4.7 card (competitor row) | 87.6 | +1.0 |
| OpenAI GPT-5.5 card (competitor row) | n/a | — |

Color the divergence column in `--warn` amber if absolute value ≥ 5%
(per EvalCards 2 threshold), else `--ink-soft`. Here +1.0 is under
threshold so use `--ink-soft`.

### Back zone 8 — Citations + back foil strip (height ~36px)

Two-line block. Top line, 9px JetBrains Mono caps with `--copper-mid`:

`SYSTEM CARD · anthropic.com/claude-opus-4-8-system-card`

Bottom line, full-width copper-gradient foil strip identical to the
front's:

`MODELCARDS.NET · EVALUATION CARD V1 · METHODOLOGY VIEW · MAY 2026`

## Side-by-side artifact layout

Both faces render in the same HTML page, centered with 40px horizontal
gap between them. Background of the page is `#EDE7DA` (the soft-neutral
moodboard color). Tiny credit line *below* both cards: `design mockup ·
modelcards.net · v1 · front + back`, 9px Inter, `--ink-soft`.

The two faces should photograph together as a unit. Don't tilt one and
not the other — either both flat or both with the same 2deg perspective
tilt.

## Microcopy and content lock

Use the exact numbers and labels above. Do not modify or invent
benchmark scores. Do not add scores I haven't given you. These come
from the actual Opus 4.8 extraction in our database.

## Technical constraints

- One HTML file, complete and self-contained.
- All CSS in a single `<style>` block in the `<head>`. No external CSS,
  no Tailwind, no frameworks.
- Hero art is inline `<svg>` in the body.
- All fonts loaded via single `@import` at the top of the CSS, from
  Google Fonts. Allow ~200ms for font load — handle FOUT gracefully with
  `font-display: swap`.
- The card itself sits in a centered flex container on the page so it
  reads as a presentation mockup.
- Include a tiny credit line *outside* the card at the very bottom of
  the page in 9px Inter, color `--ink-soft`: *"design mockup · modelcards.net · v1"*.
- Do not include any JavaScript. Static only.

## What I care about, ranked

1. The **two faces must feel like one object**. Same frame, same palette,
   same type system. If you have to choose between making the front more
   ornate and making the front+back feel like a coherent pair, choose
   the pair.
2. Typography. Get the type scale and the spacing right — that's what
   sells the prestige on both faces.
3. The hero SVG (front). A weak hero art sinks the whole thing. Spend
   detail here.
4. The **reliability flag row (front) and the "Not disclosed" pills
   (back)**. These are the load-bearing zones for the research thesis
   — together they communicate the EvalCards 2 "absence as content"
   principle. Don't soften either one in service of visual prettiness.
5. Information density on the back. Six eval rows in 180px is tight —
   make it readable through type scale and rhythm, not by reducing rows.
6. Foil details. The copper border, the bottom strips, the small
   typographic flourishes. Trading cards earn their tradability through
   these details.

## Output format

Produce one HTML artifact in your response, nothing else outside the
artifact tags. The artifact should render immediately in Claude's
artifact pane.

If you have a single significant design judgment you want to flag (e.g.
"I deviated from the prismatic hero in favor of a hexagonal lattice
because it photographed better"), put that as a one-line HTML comment
inside the file. No prose response outside the artifact.

---END---

## After the first render, you'll probably want to iterate

Save the screenshot. Then in the same chat:

> The hero SVG reads as too small / too busy / too cartoonish. Make it
> bigger, simpler, more sculptural. Fewer paths, larger facets, more
> dramatic light gradient. The form should feel monumental, not
> intricate.

Or:

> Push the copper foil more. Right now the border looks flat. Add a
> stronger highlight band along the top edge and a subtle inner bevel.
> The card should photograph like it has texture.

Or, when you want to spin variants for the rest of the corpus:

> Generate the same card for **GPT-5.5** (OpenAI, released 2026, GPT
> generation). Keep the exact layout, palette, and typography. Move
> scores: MMLU 91.4, ArxivMath 71.48, BrowseComp 85.9. Reliability flags:
> REPROD 18, COMPL 38, PROV 92, COMPAR 44.
