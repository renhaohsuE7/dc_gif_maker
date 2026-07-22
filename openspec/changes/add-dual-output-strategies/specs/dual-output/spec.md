## ADDED Requirements

### Requirement: One command produces both Discord assets

`dcmaker <input> --preset all` SHALL produce both a sticker output (exactly
320×320, ≤512KB) and an emoji output (128×128, <256KB) in a single invocation,
each written through the existing per-preset naming (`…-dc_sticker_<fmt>` /
`…-dc_emoji_<fmt>`). All other options (format, strategy, priority, trim)
SHALL apply to both outputs. `--out` (a single explicit file) SHALL be
rejected before any conversion when the run produces more than one output;
`--out-dir` SHALL apply to every output.

#### Scenario: GIF in, two spec-compliant files out

- **WHEN** the user runs `dcmaker x.gif --preset all --out-dir out/`
- **THEN** `out/` contains one 320×320 sticker ≤512KB and one 128×128 emoji
  <256KB, and the run reports both results

#### Scenario: --out rejected for dual output

- **WHEN** the user runs `dcmaker x.gif --preset all --out one.gif`
- **THEN** the command fails with an error explaining `--out` cannot target
  multiple outputs, and no file is converted

### Requirement: Animated-SVG capture is shared

For an animated-SVG source, `--preset all` SHALL run the Chromium frame
capture once (at the largest canvas any selected preset needs) and reuse the
captured frames for every preset, rather than capturing per preset.

#### Scenario: One capture, two outputs

- **WHEN** the user runs `dcmaker anim.svg --preset all`
- **THEN** the run performs exactly one frame capture and still produces both
  the sticker and the emoji outputs

### Requirement: Each output honours its own budget

Every file produced by a multi-preset run SHALL individually satisfy its
preset's Discord constraint — the run SHALL NOT trade one output's budget
against the other's.

#### Scenario: Budgets verified per file

- **WHEN** a `--preset all` run completes
- **THEN** the sticker file is ≤ the 512KB byte ceiling and the emoji file is
  ≤ the 256KB byte ceiling, verified independently
