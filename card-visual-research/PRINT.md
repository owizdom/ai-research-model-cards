# Print pipeline for the card deck

How the 816x1110 print files are produced, and why the layout is built the way
it is. Run `build_print.py` to regenerate, `check_bleed.py` to verify.

## The three zones (MPC American poker size, 300DPI)

Taken from MPC's own template, `American-poker-size.pdf`:

| zone  | pixels @300DPI | inches       | rule                                  |
|-------|----------------|--------------|---------------------------------------|
| bleed | 816 x 1110     | 2.72 x 3.70  | the full file; design must fill to here |
| cut   | 744 x 1038     | 2.48 x 3.46  | where the blade lands, plus drift     |
| safe  | 684 x  981     | 2.28 x 3.27  | all text stays inside                 |

Inset from the file edge: cut is 36px in, safe is 66px in horizontally and 64px
vertically. Everything between the bleed edge and the cut line is expected to be
thrown away, so it has to be filled with something you are happy to lose.

## What was wrong with the first set of renders

Production flagged a white or coloured strip risk on the trimmed edge. Measured
on the files that were sent out (`check_bleed.py` on the pre-fix renders):

- 192 of the 3,852 border pixels were flat backdrop rather than design, on every
  card. The scaled card frame carried `border-radius: 20px`, so at each of the
  four corners the flat `.pcard` colour showed through: `#0e0b06` on Anthropic,
  `#050a18` on Google, `#04110e` on OpenAI, `#140703` on Mistral. The flat run
  measured 24px along each edge from each corner.
- The frame sat exactly on the bleed boundary. Any outward blade drift cut
  outside the frame and exposed backdrop; any inward drift shaved the frame.

A second defect turned up while fixing this. `.gold` and `.inner` never
stretched to the fixed `.tcg` height, so every card had a dead band of bare
frame at the bottom, roughly 100px on the front and more on the back. That is
visible in the deck as printed.

## The layer model

Three layers, which is what the production note asked for:

1. **Parchment base**, `.pcard` background. Absolutely fills 816x1110, so every
   pixel of the file is design by construction and no gap is possible.
2. **Dark illustration panel**, `.pbleed`. Pinned to `top/left/right: 0`, 520px
   tall, so it runs off the top edge and both side edges. The card art is
   reused here, scaled slightly past its box, darkened and softly blurred so it
   reads as an extension of the artwork rather than a second copy of it. It
   fades into the parchment over the last 150px.
3. **Gold frame**, `.pframe`. Floats 54px in from the file edge with background
   behind it on all four sides. It never touches the bleed boundary.

54px is 1.5mm inside the cut line. MPC drift is about plus or minus 1mm (12px at
300DPI), so the frame survives the blade landing anywhere in its range, in both
directions. Inward drift is the case that matters here, since that is the one
that would shave the frame instead of just widening the margin.

## Type size and the fit pass

The card is authored in CSS pixels and scaled by `ZOOM` at print time. `ZOOM`
stays at 1.581, the value the approved proofs used, so every type size keeps the
physical size it already had. Floating the frame inside the cut line was paid
for by authoring the card narrower (455.4 x 641.4 CSS px) rather than by scaling
it down, and by trimming the frame chrome from 20px to 12px.

That costs 108px of height, which is enough to push the densest backs past the
bottom of the card. GPT-5 carries five benchmark rows and its validation footer
was being clipped. `fitCard()` handles this: it walks four levels of
progressively tighter vertical rhythm and only scales type as a last resort,
2% at a time. The build prints the level each card needed, and warns if any card
still overflows or puts text outside the safe zone.

## Running it

```bash
python3 build_print.py                      # all cards: png, jpg, deck copy
python3 build_print.py claude-4-6            # one card
python3 build_print.py --guides claude-4-6   # proof with trim/safe overlay
python3 build_print.py --no-deck             # skip writing the exported deck
python3 check_bleed.py                       # QA gate over every print png
```

Source of truth is each card's committed `<slug>.html`. The builder re-wraps
those two faces; it never edits card content. Outputs land in three places:
`cards/<lab>/<slug>/print_{front,back}.png`, `print/<slug>_{front,back}.jpg`,
and `~/Desktop/docs/stanford/model-cards-deck/<NN Name>/{front,back}.jpg`.

Order and numbering come from `cards/_roster.yaml`. Position in that file is the
card number and the file's length is the set size, so `card.json`'s `num`, the
number printed on the face, the deck folder and the cover count are all the same
sequence by construction.

Use `build_export.py`, not `build_print.py`, to write the deck. `build_print.py`
only copies a card into a deck folder that already exists, which made the export
a hand-maintained list: for a long time the three xAI cards sat in an `_extras`
folder and every newly added card silently landed nowhere.

```bash
python3 sync_roster.py --check   # what would renumber
python3 sync_roster.py           # renumber every card from the roster
python3 build_export.py          # write both export targets and the zip
```

Renumbering rewrites the four places a card prints its number (dex strip, front
footer, back head, back set-line) **by position, never by matching the old
value** — the two legacy cards write theirs as `011 / 052` with spaces, which is
why value-matching passes used to skip them.

## Known state

- **55 cards, numbered 001/055 to 055/055.** The eight cards added in Aug 2026
  are 048–055.
- **The three xAI cards are not in the set.** `grok-4`, `grok-4-fast` and
  `grok-4-1` still exist under `cards/xai/` but are listed in `DROPPED` in
  `sync_roster.py` and are absent from the roster, so they are off the deck, off
  the cover and off the gallery. The old `_extras` folder is gone too. Adding
  them back means adding three lines to the roster, nothing else.
- The exported folder that ships is `~/Desktop/model-cards-print-FIXED/`: the
  cover as `00 Free Systems Cover` plus all 55 numbered cards, 112 jpgs.
  `~/Desktop/docs/stanford/model-cards-deck/` holds the same 55 without a cover.
- `check_bleed.py` reads PNG only. The jpgs are converted from the same pngs by
  `sips` at quality 92 and are not re-checked.
