# slimming-strategies Specification

## Purpose
TBD - created by archiving change add-dual-output-strategies. Update Purpose after archive.
## Requirements
### Requirement: Strategy selection on the GIF route

`dcmaker` SHALL accept `--strategy {balanced,frames,colors}` for GIF outputs,
selecting which lever reaches the size budget. With `--format apng` or
`--format webp` an explicit `--strategy` SHALL fail with a clear error (those
routes have no palette axis). The web API SHALL accept the same field as thin
passthrough.

#### Scenario: Strategy rejected off the GIF route

- **WHEN** the user runs `dcmaker x.gif --format webp --strategy colors`
- **THEN** the command fails explaining strategies apply to the GIF route only

### Requirement: frames strategy preserves colours

Under `--strategy frames` the encoder SHALL keep the 256-colour palette and
reach the budget by lowering fps (today's behaviour, formalized). Resolution
and colours SHALL only degrade if the budget is unreachable otherwise.

#### Scenario: Fits by dropping fps alone

- **WHEN** a 20fps source misses the 256KB emoji budget and `--strategy
  frames` is in effect
- **THEN** the output uses a 256-colour palette at a reduced fps that fits

### Requirement: colors strategy preserves frames

Under `--strategy colors` the encoder SHALL keep fps at the source rate and
reach the budget by shrinking the palette down a fixed ladder
(256→192→128→96→64→48→32), stopping at the first fit. Only if the smallest
rung still misses SHALL it start lowering fps (at that smallest palette).

#### Scenario: Fits by shrinking the palette alone

- **WHEN** a source misses its budget at 256 colours but fits at 96 under
  `--strategy colors`
- **THEN** the output keeps the source fps and uses a ≤96-colour palette

#### Scenario: fps falls back only after the ladder is exhausted

- **WHEN** a source still misses the budget at 32 colours and full fps
- **THEN** the encoder lowers fps at 32 colours until the output fits

### Requirement: balanced strategy is empirically validated

The `balanced` combination of frame-dropping and colour reduction SHALL be
derived from a recorded fixture experiment (fps×colours contact sheet ranked
by human eye), with the ranking and the chosen combination committed under
`docs/experiments/`. Once validated, `balanced` SHALL become the default
strategy, and its definition SHALL cite the experiment record.

#### Scenario: Experiment decides the default

- **WHEN** the strategy-matrix experiment concludes and the user ranks a
  winning fps×colours combination
- **THEN** `docs/experiments/` records the ranking, `balanced` implements that
  combination, and a bare `dcmaker x.gif` uses it by default

### Requirement: Explicit knobs override ladders

A user-supplied `--colors`, `--lossy`, or `--min-fps` SHALL pin that dimension
for every strategy — ladders never move a value the user set explicitly.

#### Scenario: Pinned colours freeze the ladder

- **WHEN** the user runs `dcmaker x.gif --strategy colors --colors 64`
- **THEN** every trial uses exactly 64 colours; only fps may vary to fit

