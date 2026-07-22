## Context

`convert()` in `core/service.py` is a clean single-file facade; the CLI
(`cli.py`) builds one `ConvertRequest` and prints one result. Nothing today
handles more than one input. Users preparing a pack run the command N times by
hand. The change is small in surface area but needs deliberate decisions about
routing, error isolation, and exit codes so the batch behaves predictably in
scripts.

## Goals / Non-Goals

**Goals:**

- One invocation converts every supported source file under a directory/glob.
- Per-file error isolation with a clear end-of-run summary and a script-friendly
  exit code.
- Zero change to single-file behaviour or to the conversion pipeline itself.

**Non-Goals:**

- Parallel/concurrent conversion (sequential first; revisit if too slow).
- Web/API batch; archive packaging; recursive-by-default.

## Decisions

- **Where the loop lives.** Add `convert_many()` to `core/service.py` that takes
  a resolved list of input paths + a base `ConvertRequest` and yields per-file
  results/errors. The CLI stays thin: it resolves the file list, calls
  `convert_many`, prints the summary. *Alternative rejected:* looping inside
  `cli.py` — would put iteration/error policy (business logic) in transport.

- **Input resolution.** If `input` is a directory → glob supported extensions
  (`detect.py`'s known set) at top level, or recursively with `--recursive`. If
  `input` contains glob metacharacters → expand it. A plain file keeps today's
  path. *Alternative rejected:* a separate `--batch` flag — detecting a
  directory is unambiguous and needs no new mode switch.

- **Output routing.** Reuse `derive_out` per file unchanged, so `original/` →
  `output/` routing and `--out-dir` both keep working. `--out` (single explicit
  file) is invalid for a multi-file run and raises before any work.

- **Error isolation & exit code.** `--on-error skip` (default) records failures
  and continues; `--on-error stop` re-raises on the first failure. After a skip
  run with ≥1 failure, exit non-zero so CI/scripts notice.

- **Ordering & determinism.** Process files in sorted path order for a stable,
  reproducible summary.

## Risks / Trade-offs

- [A huge directory blocks for a long time] → sequential is acceptable for pack
  sizes (tens of files); parallelism is a later, separate change. Print
  progress per file so it is visibly working.
- [Mixed static + animated sources in one folder with an explicit `--format`
  that only suits one kind] → per-file `resolve_format` already raises a clear
  error; `--on-error skip` isolates it and the summary names the file.
- [Accidental huge recursive sweep] → `--recursive` is opt-in; default is top
  level only.

## Open Questions

- Should unsupported files in the directory be silently ignored or listed as
  "skipped (unsupported)"? Leaning: list them in the summary so nothing is
  silently dropped.
