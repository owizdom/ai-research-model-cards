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

Deck folders are matched on card **name**, never on `card.json`'s `num`. The
deck is numbered 01 to 47 over the cards that were actually exported, while
`num` numbers a 52-card set that also counts the three xAI cards. The two
sequences drift apart from 013 onward, so number-matching pairs GPT-5 (022) with
the folder `22 o3` and silently overwrites 35 of the 47 folders.

## Known state

- 50 cards exist in `cards/`. 47 are in the exported deck. The three xAI cards
  (`grok-4`, `grok-4-1`, `grok-4-fast`) render to `print/` but have no deck
  folder, so they are not in the 47-card print order.
- `check_bleed.py` reads PNG only. The jpgs are converted from the same pngs by
  `sips` at quality 92 and are not re-checked.
