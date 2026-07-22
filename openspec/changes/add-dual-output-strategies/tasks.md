## 1. Core: strategy search

- [ ] 1.1 `presets.py`: add strategy definitions (frames / colors / balanced)
      with the colour ladder and per-strategy degradation order.
- [ ] 1.2 `core/budget.py`: strategy-driven search — colour ladder as an outer
      loop around the existing `fit_fps`, plus the colors→fps fallback; pinned
      `--colors`/`--lossy`/`--min-fps` freeze their dimension.
- [ ] 1.3 `core/service.py`/`animate.py`: per-rung `GifEncoder` recreation
      (encoder interface unchanged); `--strategy` + `--format apng|webp` → error.
- [ ] 1.4 Unit tests with a fake encoder asserting ladder order, first-fit
      stop, fps fallback, and pinned-knob freezing.
- [ ] 1.5 Verify: `docker compose run --rm dcmaker python -m pytest tests -q`.

## 2. Core: dual output

- [ ] 2.1 `core/service.py`: `convert_all(req)` looping presets
      [sticker, emoji]; `--out` with multiple outputs raises before work.
- [ ] 2.2 Shared animated-SVG capture at the largest needed canvas (640px);
      guard task — compare emoji-from-640 vs emoji-from-256 on
      `star_spin.svg` (size/frames/visual); fall back to per-preset capture
      if it regresses.
- [ ] 2.3 Integration tests: gif→all produces two spec-compliant files;
      svg→all captures once (assert via notes) and produces two files.
- [ ] 2.4 Verify: full suite green in the image + a real
      `samples/original/hajime_todoroki_02.gif --preset all` run writes both
      files within their byte ceilings.

## 3. Transport: CLI + web

- [ ] 3.1 `cli.py`: `--preset all`, `--strategy`; print one result line per
      output plus a summary; exit non-zero if any output failed.
- [ ] 3.2 `web/app.py` + static UI: accept `preset=all` and `strategy` as thin
      passthrough (radio buttons); `_SAFE_NAME`/media types unchanged.
- [ ] 3.3 Verify: container e2e — `docker compose run --rm dcmaker dcmaker
      samples/original/hajime_todoroki_02.gif --preset all --strategy colors
      --out-dir /tmp/out` produces both files; web POST with preset=all
      returns both results.

## 4. Balanced validation experiment

- [ ] 4.1 `scripts/strategy_matrix.py` (runs in the image): fixtures
      {hajime gif, star_spin.svg} × presets {sticker, emoji} × colours
      {256,128,96,64,32}, fps auto-fitted per cell so every cell meets its
      budget; emit contact-sheet HTML to `samples/output/strategy_matrix/`
      with colours/fps/frames/KB labels.
- [ ] 4.2 User ranks the contact sheet by eye (肉眼效果 is the criterion);
      optional SSIM as secondary reference only.
- [ ] 4.3 Record ranking + chosen combination in
      `docs/experiments/<date>-strategy-matrix.md` (committed).
- [ ] 4.4 Implement the winner as `balanced`; switch the default strategy to
      `balanced`; cite the experiment record in `presets.py` docstring.
- [ ] 4.5 Verify: pytest green; re-run hajime baselines to confirm the new
      default still meets both budgets and matches the ranked winner's
      fps/colours.

## 5. Docs & wrap-up

- [ ] 5.1 README: move 未來目標's dual-output + strategies rows to implemented
      CLI docs (`--preset all`, `--strategy`), keep the experiment link.
- [ ] 5.2 Verify: `npx @fission-ai/openspec@1.5.0 validate
      add-dual-output-strategies --strict` passes; archive the change after
      apply (`/opsx:archive`) so specs/ absorbs the two new capabilities.
