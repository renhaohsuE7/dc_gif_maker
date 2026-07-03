# dcmaker UI 色彩 token 與對比度紀錄

- **日期**:2026-07-03
- **工具**:WCAG 2.x 相對亮度公式(自寫 Python 腳本,對比 = (L1+0.05)/(L2+0.05))
- **標準**:內文 ≥4.5:1;大字/UI 邊框/圖示 ≥3:1(user rules)

## Light

| token | 值 | 對地色 | 對比 | 用途 |
|---|---|---|---|---|
| `--ink` | `#1c2333` | surface `#ffffff` | 15.70:1 | 內文 |
| `--ink-soft` | `#4b5468` | surface | 7.59:1 | 次要文字 |
| `--line` | `#8089a0` | surface | 3.50:1 | 邊框 |
| `--accent` | `#3b5bdb` | surface | 5.67:1 | 連結/焦點/圖示 |
| `--accent-ink` | `#ffffff` | accent | 5.67:1 | accent 上的文字 |
| `--ok` / `--err` | `#2b7a3d` / `#b3261e` | surface | 5.31 / 6.54:1 | 狀態 |

## Dark

| token | 值 | 對地色 | 對比 | 用途 |
|---|---|---|---|---|
| `--ink` | `#e8eaf1` | surface `#1b2029` | 13.59:1 | 內文 |
| `--ink-soft` | `#a8b0c0` | surface | 7.50:1 | 次要文字 |
| `--line` | `#65718f` | surface | 3.36:1 | 邊框 |
| `--accent` | `#8da4ff` | surface | 6.91:1 | 連結/焦點/圖示 |
| `--accent-ink` | `#10131b` | accent | 7.86:1 | accent 上的文字 |
| `--ok` / `--err` | `#7bd48e` / `#ffb4ab` | surface | 9.06 / 9.62:1 | 狀態 |

初版 `--line`(light `#c7cdd9` 1.60:1、dark `#3d4657` 1.72:1)未達 3:1,
已於 2026-07-03 調整為上表值。
