# batch-conversion Specification

## Purpose
TBD - created by archiving change add-batch-mode. Update Purpose after archive.
## Requirements
### Requirement: Directory and glob input

`dcmaker` SHALL accept a directory or a shell glob as its `input` and convert
every supported source file it resolves, using the same preset, format, and
options as a single-file run. A directory SHALL be scanned at its top level
only, unless `--recursive` is given, in which case subdirectories SHALL be
scanned as well. Supported files are those recognised by input detection
(`.gif`, `.svg`, `.png`, `.jpg`, `.jpeg`, `.webp`); other files SHALL be
reported as skipped, not converted.

#### Scenario: Directory of GIFs

- **WHEN** the user runs `dcmaker ./pack --preset emoji` and `./pack` holds
  three `.gif` files
- **THEN** three emoji outputs are produced, one per GIF, and the run reports
  three conversions

#### Scenario: Recursive is opt-in

- **WHEN** `./pack` contains `a.gif` and `sub/b.gif` and the user runs
  `dcmaker ./pack` without `--recursive`
- **THEN** only `a.gif` is converted and `sub/b.gif` is left untouched

#### Scenario: Unsupported files are surfaced, not converted

- **WHEN** the input directory contains a `readme.txt`
- **THEN** `readme.txt` is listed as skipped (unsupported) in the summary and no
  output is written for it

### Requirement: Per-file output routing preserved

Each converted file SHALL be written through the existing single-file output
routing: a source inside an `original/` folder routes to a sibling `output/`
folder, and `--out-dir` overrides the destination for every file. An explicit
single-file `--out` SHALL be rejected for a multi-file run before any conversion
begins.

#### Scenario: original/ routes to output/

- **WHEN** the user batch-converts `samples/original/` without `--out-dir`
- **THEN** every result is written into `samples/output/` with its derived name

#### Scenario: --out rejected for many inputs

- **WHEN** the user runs `dcmaker ./pack --out one.gif` and `./pack` resolves to
  more than one file
- **THEN** the command fails with an error explaining `--out` cannot target
  multiple inputs, and no file is converted

### Requirement: Error isolation and summary

A batch run SHALL isolate per-file failures. With `--on-error skip` (the
default) a failing file SHALL be recorded and the run SHALL continue; with
`--on-error stop` the run SHALL abort on the first failure. At the end the
command SHALL print a summary of converted, skipped, and failed files (each
failure naming the file and reason), and SHALL exit non-zero if any file failed.

#### Scenario: One bad file does not abort the run

- **WHEN** a batch of five files includes one corrupt GIF and `--on-error skip`
  is in effect
- **THEN** the other four are converted, the corrupt file is listed as failed
  with its reason, and the process exits non-zero

#### Scenario: Stop on first error

- **WHEN** the same batch is run with `--on-error stop`
- **THEN** the run aborts at the corrupt file and reports it, without converting
  the remaining files

