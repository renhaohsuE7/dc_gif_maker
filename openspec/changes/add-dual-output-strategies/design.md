## Context

The budget search today is one-dimensional: for each candidate artwork size,
`fit_fps()` finds the highest fps that fits, always at 256 colours, with a
gifsicle-lossy escalation as the last resort. `--priority` then picks among
candidates on the "frames vs artwork size" axis. Colour reduction — the other
big GIF size lever — exists only as a manual `--colors` flag nobody drives
automatically. gif_compressor-era outputs that mixed frame-dropping with
colour-cutting looked best to the user's eye, but the combination was never
systematized. Separately, producing a sticker *and* an emoji means two runs,
including two Chromium captures for animated SVG.

## Goals / Non-Goals

**Goals:**

- One invocation → both presets, with animated-SVG capture done once.
- An explicit strategy axis (frames / colors / balanced) on the GIF route.
- A `balanced` definition backed by a recorded human-eye experiment, then made
  the default strategy.
- Zero behaviour change for user-pinned knobs (`--colors`, `--lossy`,
  `--min-fps` still win over any ladder).

**Non-Goals:**

- APNG/WebP strategy variants; parallelism; touching budgets/geometry or the
  `--priority` axis semantics.

## Decisions

- **Strategy = an ordered degradation ladder over (fps, colours).**
  - `frames`: colours fixed at 256; existing `fit_fps` proportional search.
  - `colors`: fps fixed at source fps; walk the palette ladder
    256→192→128→96→64→48→32, encoding once per rung, stop at first fit
    (≤7 encodes, comparable cost to today's fps search). If 32 still misses,
    fall back to `fit_fps` at 32 colours — colour-first spirit preserved.
  - `balanced`: hypothesis form "colours = C\* then fps search" (C\* expected
    around 96–128 from gif_compressor experience); the experiment decides C\*
    and whether an interleaved ladder beats the fixed-C\* form.
  *Alternative rejected:* full 2-D search per candidate — encode count
  explodes (fps trials × colour rungs × content sizes) for marginal gain.
- **Plumbing: encoder factory, not a fatter interface.** `compress_animated`
  accepts the existing single-shot `Encoder`; the strategy loop lives one
  level up in `core/service.py`/`budget.py`, recreating `GifEncoder` per
  colour rung (constructor already takes `colors`). `Encoder.encode(chain,
  out)` stays untouched, so APNG/WebP paths don't change shape.
- **Ladder order vs lossy escalation.** Per strategy: `frames` = fps search →
  lossy escalate (unchanged today); `colors` = colour ladder → fps fallback →
  lossy escalate last; `balanced` = per experiment outcome. A user-pinned
  `--colors`/`--lossy` freezes that rung of the ladder.
- **Dual output lives in core, not the CLI.** `convert_all(req) ->
  list[ConvertResult]` in `service.py` loops presets `[sticker, emoji]`;
  the CLI just prints N results (same rule as batch: thin transport). `--out`
  with `all` raises before any work; `derive_out`'s per-preset suffixes
  already prevent collisions.
- **Shared SVG capture at the largest canvas.** Capture once at 2×320 = 640px;
  emoji trials downscale from it (the per-trial fps/scale filters already do
  this). One Chromium run instead of two; more downscale headroom for emoji.
  Guard: compare emoji-from-640 vs emoji-from-256 on `star_spin.svg` — if
  quality/size regresses, fall back to per-preset capture.
- **The balanced experiment (the validation the user asked for).**
  - Harness: `scripts/strategy_matrix.py`, runs inside the image only.
  - Matrix: fixtures {hajime_todoroki_02.gif, star_spin.svg} × presets
    {sticker, emoji} × colours {256, 128, 96, 64, 32}; for each cell run the
    fps search so **every cell already fits its budget**; record fps, frames,
    bytes.
  - Deliverable: a contact-sheet HTML (cells side by side, looping, labelled
    with colours/fps/frames/KB) written to `samples/output/strategy_matrix/`.
  - Protocol: the **user ranks cells by eye** (they are the judge — 肉眼效果
    is the stated criterion); optional SSIM numbers are secondary reference
    only, never the decider.
  - Record: findings + ranking land in `docs/experiments/<date>-strategy-
    matrix.md` (committed); `balanced`'s C\*/form and the default-strategy
    switch cite that file.

## Risks / Trade-offs

- [Colour ladder adds encodes] → capped at 7 rungs, GIF route only; each rung
  is a seconds-scale encode. Acceptable; no change to APNG/WebP cost.
- [Experiment is subjective] → intentional: the acceptance criterion *is* the
  user's eye. The contact sheet forces same-budget, side-by-side comparison;
  the ranking is recorded so the decision is auditable.
- [Merge conflict with add-batch-mode] → both touch `cli.py`/`service.py`;
  land batch first or rebase; loops compose (batch outer × presets inner).
- [Shared 640px capture shifts emoji-from-SVG output] → explicit guard task
  compares against per-preset capture before adopting.
- [Low palettes + `dither=none` can band on gradients] → keep `dither=none`
  (flat-art default); note in docs that photographic sources should prefer
  `frames`. Revisit only if the experiment shows banding dominating.

## Open Questions

- The experiment's outcome itself: C\* value, fixed-C\* vs interleaved ladder,
  and whether sticker and emoji want different C\*.
- Should `--strategy colors` relax `min_fps` (it never drops frames until the
  ladder is exhausted, so `min_fps` rarely binds)? Leaning: leave `min_fps`
  semantics untouched.
