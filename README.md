# dc_emoji_sticker_maker(dcmaker)

> 📦 **Release(latest)**:<https://github.com/renhaohsuE7/dc_gif_maker/releases/latest>

把 **GIF / SVG / PNG** 變成符合 Discord 規格的**貼圖**(正好 320×320、≤512KB)
或**表情符號**(128×128、<256KB),透明背景全程保留。

## 快速開始(uv)

系統需先有 `ffmpeg` + `gifsicle`(SVG 另需 `librsvg`;動畫 SVG 另需
Chromium)。不想自備工具 → 用下方 **Docker Compose**,工具全在 image 裡。

```bash
git clone https://github.com/renhaohsuE7/dc_gif_maker.git && cd dc_gif_maker
uv run dcmaker samples/original/hajime_todoroki_02.gif                  # 貼圖:320×320、≤512KB
uv run dcmaker samples/original/hajime_todoroki_02.gif --preset emoji   # 表情:128×128、<256KB
```

## 一句指令、雙產出 + 瘦身策略

**`--preset all`** 一次同時產出兩種 Discord 素材:**512KB 貼圖**(320×320)與
**256KB 表情**(128×128);動畫 SVG 只做一次 Chromium 截圖、兩條路線共用。

**`--strategy`** 決定 GIF 路線「靠什麼」把體積壓進預算:

| 策略 | 作法 | 狀態 |
|------|------|------|
| **抽幀 frames**(預設) | 主要靠降 fps;解析度與色彩(256 色)盡量保留 | ✅ 已實作 |
| **色彩減少 colors** | 保住源幀率,走色階梯 256→192→128→96→64→48→32;梯底仍不行才降 fps | ✅ 已實作(實測 hajime 貼圖:123 幀/256 色 → **190 幀**/32 色) |
| **均衡 balanced** | 抽幀 + 減色並用 —— 前身 gif_compressor 實測肉眼效果最好的方向 | 🧪 實驗中:`scripts/strategy_matrix.py` 產出對照表,由肉眼排名決定組合後升為預設 |

> `--priority`(frames / balanced / resolution)管「幀數 vs 畫面大小」;
> `--strategy` 管「幀數 vs 色彩」,兩軸可組合。`--colors N` 可釘死色數
> (策略階梯不會動它)。

## 未來目標

其他排程中:海報幀 PNG、靜態 WebP。(批次模式已實作:INPUT 給資料夾或 glob
即批次轉換,見 CLI 用法。)

## 特色

- **GIF 路線**:承襲前身專案 gif_compressor 的
  「ffmpeg 最佳化調色盤 + gifsicle lossy + 大小預算搜尋」管線。
- **SVG 靜態路線**:向量 → 透明 PNG,天生遠低於預算、畫質最佳。
- **SVG 動畫路線(crazy 的部分)**:headless Chromium 載入 SVG,把 SMIL 與
  CSS/WAAPI 動畫**暫停後逐幀定格截圖**(透明背景),再餵進同一套壓縮管線 →
  GIF 或 APNG。
- **APNG**:全 8-bit alpha(半透明邊緣比 GIF 的 1-bit 透明漂亮),Discord 貼圖官方推薦。
- **WebP**:動畫 WebP,真彩 + 全 8-bit alpha(無 GIF 調色盤與抖動),體積卻只有
  APNG 的零頭 —— 在同一預算內填進**接近 APNG 的畫質**而非 GIF 的調色盤觀感
  (幀數與 GIF 相當)。Discord **表情官方支援 WebP**;貼圖官方格式為
  APNG/PNG/GIF,WebP 貼圖上傳未保證接受(表情用最穩)。

Discord 規格(2026-07-02 依官方文件查證):貼圖須**正好 320×320**、≤512KB
(PNG/APNG 推薦、GIF 可);表情 <256KB、建議 128×128。

---

## 快速開始(Docker Compose,建議)

```bash
cp .env.example .env        # 需要時調整
docker compose up --build -d
# 開 http://localhost:8000 → 拖檔案、選路線、下載
```

容器內建 ffmpeg、gifsicle、librsvg、pngquant、Noto CJK/emoji 字型與 Chromium,
`mem_limit: 2g`。

### 容器內跑 CLI

```bash
docker compose run --rm -v ./samples:/work dcmaker \
  dcmaker /work/original/star_spin.svg --preset sticker --out-dir /work/output
```

### 本機直接跑(uv,需自備媒體工具)

```bash
sudo apt install -y ffmpeg gifsicle librsvg2-bin pngquant
uv run playwright install chromium      # 動畫 SVG 截圖才需要
uv run dcmaker samples/original/star_spin.svg
```

`uv run` 會自動依 `pyproject.toml` 建立虛擬環境並安裝套件,不需手動 pip。

---

## CLI 用法

```bash
dcmaker INPUT [--preset sticker|emoji|all] [--format auto|gif|apng|webp|png]
              [--strategy frames|colors|balanced]  # GIF 瘦身策略(見上表)
              [--priority frames|balanced|resolution]
              [--ss T --to T]            # 裁短(體積最大的槓桿)
              [--duration N]             # 動畫 SVG:截取秒數(預設自動偵測)
              [--lossy N]                # GIF gifsicle lossy 強度
              [--quality N]              # WebP libwebp 品質 0-100(越高越好越大)
              [--colors N --dither D --min-fps F]
              [--recursive] [--on-error stop|skip]   # 批次(INPUT 為資料夾/glob)
              [--out FILE | --out-dir DIR]
```

路由規則:輸入是動畫(GIF / 動畫 SVG)→ 預設 GIF,可選 APNG 或 WebP;輸入是
靜態(SVG / PNG / JPG / WebP)→ PNG。輸入放 `samples/original/` 時產出自動寫到
`samples/output/`。

**批次**:INPUT 給資料夾或 glob 就逐檔轉換(每檔各自路由)——預設只掃頂層
(`--recursive` 進子目錄);單一檔案失敗不會中斷整批(`--on-error stop` 改為
遇錯即停),結尾印 converted/skipped/failed 摘要,有失敗時以非零碼退出。

範例:

```bash
dcmaker x.gif                                  # 貼圖 GIF(320×320 ≤512KB)
dcmaker x.gif --preset emoji                   # 表情 GIF(128×128 <256KB)
dcmaker x.gif --preset all                     # 一句指令、貼圖+表情雙產出
dcmaker x.gif --strategy colors                # 保幀率,靠減色塞進預算
dcmaker x.gif --format apng                    # 貼圖 APNG(8-bit alpha)
dcmaker x.gif --preset emoji --format webp     # 表情 WebP(真彩+8-bit 透明)
dcmaker x.gif --ss 0 --to 5 --priority resolution   # 裁短 → 又大又順
dcmaker logo.svg --preset emoji                # 靜態 SVG → 透明 PNG
dcmaker anim.svg --duration 4                  # 動畫 SVG → GIF
dcmaker ./pack --preset emoji --out-dir out/   # 批次:整個資料夾一次轉
dcmaker './pack/**/*.gif' --recursive          # 批次:glob + 子目錄
```

---

## 運作原理

### 動畫路線(GIF 或 動畫 SVG)

1. **來源展開**
   - GIF:直接作為 ffmpeg 輸入。
   - 動畫 SVG:Chromium 開一個透明頁面,`svg.pauseAnimations()` +
     `document.getAnimations().pause()` 把時間軸凍結,再用
     `setCurrentTime(t)` / `Animation.currentTime = t` 逐幀定格、
     `omit_background` 截圖 → PNG 序列(以 2× 畫布解析度、預設 24fps 擷取;
     迴圈長度自動偵測,`--duration` 可覆寫)。
2. **候選 × 預算搜尋**:對每個候選內容尺寸(貼圖 44%~100% 畫布),用比例搜尋
   找出「塞得進預算的最高 fps」;等比縮放 + 透明補邊到正好畫布大小。
3. **編碼**
   - GIF:ffmpeg `palettegen`(保留透明)→ `paletteuse`(`dither=none` +
     `diff_mode=rectangle`)→ `gifsicle -O3 --lossy`。
   - APNG:ffmpeg `-f apng -plays 0 -pred mixed`(rgba,全 alpha)。
   - WebP:ffmpeg `libwebp_anim`(rgba,`-preset drawing -compression_level 6`,
     `-q:v` 品質;塞不進預算時自動降品質)。
4. **取向挑選**:`frames`(最順)/ `balanced` / `resolution`(角色最大)。

### 靜態路線(SVG / 點陣圖)

rsvg-convert(或 cairosvg)向量輸出 → 等比縮放 + 透明補邊成正方形 →
幾乎必然遠低於預算;超標(如照片)才啟動 pngquant 量化。

**核心通則**(沿襲 gif_compressor 實測):體積 ≈ 幀數 × 解析度;顏色留 256
幾乎不影響體積;`dither=none` 對平塗圖最省;**裁短片長是最大的槓桿**。

---

## Web 服務

- `GET /` 上傳頁(拖放、路線/格式/取向、進階裁剪)。
- `POST /api/convert`(multipart:`file`, `preset`, `fmt`, `priority`,
  `ss`, `to`, `duration`)→ JSON(結果檔連結與 metadata)。
- `GET /files/{name}` 下載產出。

上傳大小上限 `DCM_MAX_UPLOAD_MB`(預設 32MB);SVG 截圖上限
`DCM_CAPTURE_MAX_SECONDS`(預設 15s)。設定全部走環境變數(見
`.env.example`),transport 層只驗證與委派,業務邏輯在 `core/`,外部工具
(ffmpeg/gifsicle/librsvg/Chromium/pngquant)全部封裝在 `adapters/`。

---

## 專案結構

```
├─ docker-compose.yml / Dockerfile   ← 執行站(含全部工具與字型)
├─ src/dcmaker/
│  ├─ presets.py        ← sticker / emoji 兩條固定路線
│  ├─ config.py         ← DCM_* 環境變數
│  ├─ adapters/         ← ffmpeg、gifsicle、svg 渲染、Chromium 截圖、pngquant
│  ├─ core/             ← budget 搜尋、幾何、GIF/APNG/靜態管線、convert() facade
│  ├─ cli.py            ← 薄 CLI
│  └─ web/              ← FastAPI + 上傳 UI(薄 transport)
├─ samples/original/    ← 示範素材(產出自動進 samples/output/,gitignore)
├─ tests/               ← 單元恆跑;整合測試缺工具自動 skip、容器內全跑
└─ docs/references/     ← 外部查證摘要 + 參考 repo(local-only)
```

## 測試

```bash
docker compose build
docker compose run --rm dcmaker python -m pytest -v   # 容器內全套(含 e2e)
python -m pytest tests/test_unit.py -v                # 本機純函式單元測試
```

## 規格驅動開發(OpenSpec)

本 repo 導入了 [OpenSpec](https://github.com/Fission-AI/OpenSpec):把「提案 →
規格 → 任務」留在 repo 裡再動手。專案脈絡與規則寫在 `openspec/config.yaml`
(技術棧、分層原則、Discord 規格不變量、慣例)。Claude Code 整合在 `.claude/`
(5 個 skills + `/opsx:*` slash commands)。

```bash
# 在 Claude Code 內:
/opsx:propose "為 emoji 加 WebP 靜態輸出"   # 開一個 change proposal
/opsx:apply                                  # 依 proposal 實作
/opsx:archive                                # 完成後歸檔並更新 specs

# CLI(無全域安裝,走 npx):
npx @fission-ai/openspec@1.5.0 list          # 列出進行中的 change / specs
npx @fission-ai/openspec@1.5.0 validate      # 驗證 change/spec 格式
```

## 發佈 Release(自動)

git tag 是版本的事實來源;**GitHub Release** 是疊在 tag 上的公告頁(release
notes + 附件)。發版只要打 tag:

```bash
git tag -a v0.3.0 -m "dcmaker v0.3.0 — …" && git push origin v0.3.0
```

push tag 後 `.github/workflows/release.yml` 會自動建立 Release(notes = tag
訊息 + 自動 changelog),用 Actions 內建的 `GITHUB_TOKEN`,本機零 token 管理。
補建舊 tag:GitHub → Actions → release → **Run workflow** 填 tag 名。

**本地備援**(Actions 不可用時):`scripts/release.sh` 用容器內建的 `gh` 建
Release,冪等(已存在就跳過)。需要一顆能 push 本 repo 的 token(既有 git 憑證
即可;或 fine-grained PAT 給 **Contents: Read and write**),只在發佈當下注入:

```bash
GITHUB_TOKEN=github_pat_xxx \
  docker compose --profile release run --rm release v0.3.0
#   ...--draft 先存草稿、--latest=false 不標記為最新,皆會轉傳給 gh
```

token 從 `$GITHUB_TOKEN` 讀取,只留在 shell 變數、不會被 log 或 echo。repo 位址
取自 `DCM_RELEASE_REPO`(見 `.env.example`),留空則自 git remote 推導。

## 已知限制

- 依賴 JavaScript 驅動(rAF)的 SVG 動畫無法定格重現,截圖結果可能不符預期。
- WebP:Discord 表情官方支援;貼圖上傳未保證接受(貼圖用 APNG/GIF 最穩)。
- 其餘待辦見上方「[未來目標](#未來目標)」。
