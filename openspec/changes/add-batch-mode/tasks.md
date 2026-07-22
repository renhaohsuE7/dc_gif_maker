## 1. Core: batch facade

- [x] 1.1 Add `iter_inputs(path_or_glob, recursive, supported_exts)` to
      `core/service.py` (or a small helper module): resolve a directory/glob to
      a sorted list of supported files; classify others as `unsupported`.
- [x] 1.2 Add `convert_many(inputs, base_request, on_error, progress)` yielding
      a per-file record `{path, result | error}`; honour `stop` vs `skip`.
- [x] 1.3 Guard: raise a clear error if `base_request.out` is set with >1 input.
- [x] 1.4 Verify: `docker compose run --rm dcmaker python -m pytest tests -q`
      (new unit tests for `iter_inputs`/`convert_many` green).

## 2. Transport: CLI wiring

- [x] 2.1 In `cli.py`, detect directory/glob input; add `--recursive` and
      `--on-error {stop,skip}` (default `skip`) arguments.
- [x] 2.2 Call `convert_many`, print a per-file line and an end-of-run summary
      (converted / skipped / failed with reason); exit non-zero if any failed.
- [x] 2.3 Keep single-file behaviour byte-identical when `input` is one file.
- [x] 2.4 Verify: run `docker run --rm -v $PWD:/w -w /w ... dcmaker \
      dcmaker samples/original --preset emoji --out-dir /tmp/out` and confirm
      all supported samples convert and the summary/exit code are correct.

## 3. Tests

- [x] 3.1 Unit: `iter_inputs` (top-level vs `--recursive`, unsupported
      classification, glob) — pure-function, no tools.
- [x] 3.2 Integration (ffmpeg-gated): a temp dir of small generated GIFs →
      batch emoji conversion produces one output each; a deliberately corrupt
      file is isolated under `skip` and aborts under `stop`.
- [x] 3.3 Verify: full suite green in the image
      (`docker compose run --rm dcmaker python -m pytest -q`).

## 4. Docs

- [x] 4.1 README CLI section: add a batch example and document `--recursive` /
      `--on-error`.
- [x] 4.2 Remove "批次模式尚未實作" from the README roadmap.
- [x] 4.3 Verify: `npx @fission-ai/openspec@1.5.0 validate --strict` passes for
      this change before archiving.
