# gifsicle 1.96 `--lossy` 在平塗動漫幀上失效(實測)

- **日期**:2026-07-03
- **目的**:hajime 表情回歸(舊工具 240KB)在新容器內「nothing fits 256KB」,
  追查哪個階段退步。
- **方法**:同一輸入(hajime_todoroki_02.gif, 300×328, 278f, 20fps)、同一
  ffmpeg 管線(palettegen stats_mode=diff → paletteuse dither=none +
  diff_mode=rectangle),在 4.75fps/128×128 產出相同的 raw(434,071 bytes,
  66 幀),分別餵給兩個 gifsicle。

| gifsicle | 平台 | `-O3 --lossy=60` 結果 | 壓縮率 |
|---|---|---|---|
| **1.95**(官方 Windows build,舊工具內建) | Windows | **245,802** | **-43%** |
| **1.96**(Debian trixie apt) | 容器 | 433,790 | -0.06% |

其他資料點(1.96):`--lossy=200` 也只 -3.3%;`--lossy=60` 對已由 ffmpeg
最佳化過的 raw 甚至**變大**(368,016 → 368,910)。

## 結論與對策

- Debian trixie 的 gifsicle 1.96 對這類 flat-colour 動漫幀的 lossy LZW 幾乎
  無效,是行為回歸(或建置差異);1.95 是已驗證有效的版本。
- **對策**:Dockerfile 以 multi-stage 從 lcdf.org 原始碼編譯並釘住
  `gifsicle 1.95`,COPY 到 `/usr/local/bin` 蓋過 apt 版。apt 的 1.96 仍保留
  (層快取考量),但 PATH 順序保證 1.95 生效。
- 驗證方式:容器內 `gifsicle --version` 應顯示 1.95;hajime emoji 回歸應
  回到 ~240KB 且塞進 256KB 預算。
