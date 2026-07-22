## Why

Making a Discord pack today takes one command per preset, and the pipeline has
exactly one slimming behaviour (fps-first at 256 colours). The real per-source
goal is "**both assets, best-looking, one command**": produce the sticker and
the emoji together, and let the user pick **what gets sacrificed** to reach the
budget — frames, colours, or a validated best-of-both blend. Experience from
the gif_compressor era says the visually best output combined frame-dropping
*and* colour reduction, but that combo was hand-tuned and never systematically
validated.

## What Changes

- **`--preset all`(一句指令、雙產出)**: one invocation emits both the
  sticker (exactly 320×320, ≤512KB) and the emoji (128×128, <256KB), using the
  existing per-preset output naming. `--out` (single file) is rejected for
  multi-output runs; `--out-dir` applies to both. Animated-SVG sources are
  captured **once** (at the largest needed canvas) and shared across presets.
- **`--strategy {balanced,frames,colors}`**(GIF 路線)— the slimming axis:
  - `frames`(抽幀): today's behaviour formalized — colours stay 256, fit by
    lowering fps.
  - `colors`(色彩減少): fps stays at source; fit by shrinking the palette
    (256 → 192 → 128 → 96 → 64 → 48 → 32); only start dropping fps if even 32
    colours cannot fit.
  - `balanced`(均衡): frame-drop + colour-cut together. The exact combination
    is **decided by a recorded experiment** (see design), not guessed.
- **Validation experiment** for `balanced`: a dev-only matrix harness renders
  fps×colours candidates on real fixtures into a contact sheet; the user ranks
  them by eye; the winning combination is recorded in-repo and becomes
  `balanced`'s definition — and `balanced` then becomes the default strategy.
- Web/API: `preset=all` and `strategy` accepted as thin passthrough fields.

Non-goals:

- No change to Discord budgets or geometry — every output still individually
  satisfies its preset constraint (sticker exactly 320×320 ≤512KB; emoji
  128×128 <256KB).
- Strategies target the **GIF route only**. APNG has no colour knob in our
  pipeline; WebP already has its own quality ladder. `--strategy` with
  `--format apng|webp` is a clear error, not a silent no-op.
- No parallel conversion; no changes to the `--priority` axis (it stays the
  "frames vs artwork size" selector and composes with strategies).

## Capabilities

### New Capabilities

- `dual-output`: one command producing both Discord assets (sticker + emoji)
  from a single source, capture shared, outputs individually spec-compliant.
- `slimming-strategies`: the frames / colors / balanced slimming axis on the
  GIF route, with `balanced` empirically validated and made the default.

### Modified Capabilities

<!-- None. batch-conversion (pending change) is orthogonal: batch = many
     inputs; all = many presets per input. Single-preset runs keep today's
     behaviour until balanced is validated and promoted. -->

## Impact

- **transport**: `cli.py` (`--preset all`, `--strategy`), `web/app.py` + static
  UI (two thin form fields). No business logic added to transport.
- **core**: `service.py` (multi-preset loop + shared SVG capture),
  `budget.py` (strategy-driven search: colour ladder around the existing
  fps search), `presets.py` (strategy definitions/defaults), `animate.py`
  (per-trial colours plumbing to the GIF encoder).
- **adapters**: none — `GifEncoder` already takes `colors`.
- **Sequencing**: the pending `add-batch-mode` change also touches
  `cli.py`/`service.py`; land batch first (or rebase this one) — the two loops
  compose (batch outer × presets inner).
