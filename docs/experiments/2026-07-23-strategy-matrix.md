# 策略矩陣實驗:balanced 的定義(2026-07-23)

- **目的**:決定 `--strategy balanced` 的「fps × 色數」組合(OpenSpec change
  `add-dual-output-strategies` tasks 4.2–4.4)。
- **方法**:`scripts/strategy_matrix.py` —— fixtures × presets × 色數
  {256,128,96,64,32},每格用既有 fps 預算搜尋把**每一格都塞進同一個 Discord
  預算**,產出 contact sheet(`samples/output/strategy_matrix/index.html`),
  由使用者**肉眼排名**(這是唯一裁決;SSIM 未使用)。
- **裁決者**:使用者本人,2026-07-23。

## 數據

**hajime_todoroki_02.gif × sticker(512KB 預算,320×320)**

| 色數 | fps | 幀數 | KB |
|-----:|----:|-----:|---:|
| 256 | 8.82 | 123 | 484 |
| 128 | 10.13 | 141 | 483 |
| **96** | **10.66** | **148** | **479** |
| 64 | 11.68 | 162 | 475 |
| 32 | 13.69 | 190 | 487 |

**hajime_todoroki_02.gif × emoji(256KB 預算,128×128,實際顯示 32px)**

| 色數 | fps | 幀數 | KB |
|-----:|----:|-----:|---:|
| 256 | 4.72 | 66 | 239 |
| 128 | 5.38 | 75 | 238 |
| 96 | 5.67 | 79 | 238 |
| 64 | 6.26 | 87 | 239 |
| **32** | **7.07** | **98** | **238** |

**star_spin.svg(對照組,兩個 preset)**:五格全為 48 幀 / 24fps,只有位元組
遞減 —— 來源太簡單,預算與色彩軸都沒綁到。追查發現它在 c256 格實際只用了
**128 色**(內容色 ~2 色,其餘全是抗鋸齒邊緣過渡色)→ 證明 colors 策略對
平塗素材是無害的 no-op。

## 排名結果(使用者肉眼)

| Preset | 勝出 | 理由(事後詮釋) |
|--------|------|------|
| sticker | **96 色**(10.66fps / 148 幀 / 479KB) | 320×320 大圖近看,色帶露餡的成本高;96 色是「色彩幾乎無損 + 幀數 +25」的甜蜜點 |
| emoji | **32 色**(7.07fps / 98 幀 / 238KB) | Discord 實際顯示 32px,色彩細節不可見;全部預算換流暢度(66→98 幀) |

## 決策

- `balanced` = **每個 preset 釘住實驗勝出的色數,再跑既有 fps 預算搜尋**:
  - sticker → `balanced_colors = 96`
  - emoji → `balanced_colors = 32`
- `DEFAULT_STRATEGY` 由 `frames` 切換為 **`balanced`**(spec:
  `slimming-strategies` / "balanced strategy is empirically validated")。
- 舊行為仍可用 `--strategy frames` 取回;`--colors N` 依規格凍結色數維度。

## 重跑方式

```bash
docker run --rm --memory=2g -v "$PWD":/work:ro -v "$PWD/samples/output":/outdir \
  -w /work -e PYTHONPATH=/work/src --entrypoint python dcmaker:latest \
  scripts/strategy_matrix.py --out-dir /outdir/strategy_matrix
```

樣本注意:本輪只有 hajime 一個「色彩豐富且預算綁定」的素材;未來若加入更多
彩色動畫 fixtures,重跑矩陣並複核 96/32 是否仍是甜蜜點。
