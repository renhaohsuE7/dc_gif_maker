## Why

Preparing a whole sticker/emoji pack today means running `dcmaker` once per
file by hand. There is no way to point at a folder of sources and fan out. This
is the single most common real workflow (a directory of GIFs → a directory of
Discord-ready outputs) and it is entirely manual.

## What Changes

- `dcmaker` accepts a **directory** (or a shell glob) as `input`, converting
  every supported source file under it with the chosen preset/format/options.
- Each result is written through the existing `derive_out` logic (so an
  `original/` folder still routes outputs to a sibling `output/`), or all into
  `--out-dir` when given.
- Add `--recursive` to descend into subdirectories (default: top level only).
- Add `--on-error {stop,skip}` (default `skip`): one bad file does not abort the
  whole run; failures are collected and reported.
- Print a **per-file summary** at the end (converted / skipped / failed with
  reason) and exit non-zero if any file failed under `--on-error skip`.
- `--out FILE` (single-file output) is rejected when the input is a directory.

Non-goals:

- No parallelism across CPU cores — conversions run sequentially first.
- No web/API batch upload; this is CLI-only.
- No archive/zip packaging of the outputs.
- No new output format or Preset; batch reuses the existing single-file pipeline.

## Capabilities

### New Capabilities

- `batch-conversion`: converting every supported source file in a directory (or
  glob) in one invocation, with per-file error isolation and a summary report.

### Modified Capabilities

<!-- None: no existing spec's requirements change; single-file behaviour is unchanged. -->

## Impact

- **Transport layer only** (`src/dcmaker/cli.py`): directory/glob detection,
  the per-file loop, error handling, and the summary print. A thin
  `core/service.py` helper (`convert_many`) may host the loop so the CLI stays
  declarative — no business logic in transport.
- **No `adapters/` changes** and **no `core/budget.py` / geometry changes**:
  each file goes through the unchanged single-file `convert()`. Output geometry
  and the size budget are untouched, so the Discord spec constraints (sticker
  exactly 320x320 ≤512KB; emoji 128x128 <256KB) still hold per file by
  construction.
- Docs: README CLI section gains a batch example; roadmap item removed.
