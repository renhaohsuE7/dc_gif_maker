# dc_emoji_sticker_maker(dcmaker)

把 **GIF / SVG / PNG** 變成符合 Discord 規格的**貼圖**(正好 320×320、≤512KB)
或**表情符號**(128×128、<256KB),透明背景全程保留。

- **GIF 路線**:承襲 [gif_compressor](docs/references/external_repos/README.md) 的
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

Discord 規格(2026-07-02 查證,詳見
[reference note](docs/references/external_sites/2026-07-02-discord-sticker-emoji-specs.md)):
貼圖須**正好 320×320**、≤512KB(PNG/APNG 推薦、GIF 可);表情 <256KB、建議 128×128。

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

### 本機直接跑(不建議,需自備工具)

```bash
sudo apt install -y ffmpeg gifsicle librsvg2-bin pngquant
pip install -e .[dev] && playwright install --with-deps chromium
dcmaker samples/original/star_spin.svg
```

---

## CLI 用法

```bash
dcmaker INPUT [--preset sticker|emoji] [--format auto|gif|apng|webp|png]
              [--priority frames|balanced|resolution]
              [--ss T --to T]            # 裁短(體積最大的槓桿)
              [--duration N]             # 動畫 SVG:截取秒數(預設自動偵測)
              [--lossy N]                # GIF gifsicle lossy 強度
              [--quality N]              # WebP libwebp 品質 0-100(越高越好越大)
              [--colors N --dither D --min-fps F]
              [--out FILE | --out-dir DIR]
```

路由規則:輸入是動畫(GIF / 動畫 SVG)→ 預設 GIF,可選 APNG 或 WebP;輸入是
靜態(SVG / PNG / JPG / WebP)→ PNG。輸入放 `samples/original/` 時產出自動寫到
`samples/output/`。

範例:

```bash
dcmaker x.gif                                  # 貼圖 GIF(320×320 ≤512KB)
dcmaker x.gif --preset emoji                   # 表情 GIF(128×128 <256KB)
dcmaker x.gif --format apng                    # 貼圖 APNG(8-bit alpha)
dcmaker x.gif --preset emoji --format webp     # 表情 WebP(真彩+8-bit 透明)
dcmaker x.gif --ss 0 --to 5 --priority resolution   # 裁短 → 又大又順
dcmaker logo.svg --preset emoji                # 靜態 SVG → 透明 PNG
dcmaker anim.svg --duration 4                  # 動畫 SVG → GIF
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

## 發佈 Release(半自動)

git tag 是版本的事實來源;**GitHub Release** 是疊在 tag 上的公告頁(release
notes + 附件)。`scripts/release.sh` 用容器內建的 `gh` 為「已 push 的 tag」建立
Release,冪等(已存在就跳過)、自動產生 changelog。

**先設定一次 token**:到 GitHub → Settings → Developer settings → **Fine-grained
personal access token**,對本 repo 給 **Contents: Read and write**(或用 classic
token 的 `repo` scope)。**不要**寫進 `.env`;只在發佈當下用環境變數提供:

```bash
# 1) 打 tag 並 push(SemVer,annotated)
git tag -a v0.3.0 -m "dcmaker v0.3.0 — …" && git push origin v0.3.0

# 2) 建 Release(token 只在這一次注入,不進長跑的 web 容器)
GITHUB_TOKEN=github_pat_xxx \
  docker compose --profile release run --rm release v0.3.0
#   ...--draft 先存草稿、--latest=false 不標記為最新,皆會轉傳給 gh
```

token 從 `$GITHUB_TOKEN` 讀取,只留在 shell 變數、不會被 log 或 echo。repo 位址
取自 `DCM_RELEASE_REPO`(見 `.env.example`),留空則自 git remote 推導。

## 已知限制 / 路線圖

- 依賴 JavaScript 驅動(rAF)的 SVG 動畫無法定格重現,截圖結果可能不符預期。
- 批次模式尚未實作。
- 動畫輸入想取單幀 PNG(海報幀)尚未支援 —— 先自行裁剪。
- WebP 目前僅動畫輸出(靜態輸入仍走 PNG);靜態 WebP 尚未實作。
