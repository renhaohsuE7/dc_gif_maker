"use strict";

/* icon registry — single source of truth; hand-drawn line icons
   (24px grid, 2px stroke, round caps, currentColor) */
const ICONS = {
  sticker: '<path d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8l-6 6H6a2 2 0 0 1-2-2z"/><path d="M14 20v-4a2 2 0 0 1 2-2h4"/>',
  smile: '<circle cx="12" cy="12" r="9"/><path d="M9 14.5a4 4 0 0 0 6 0"/><path d="M9.5 9.5v.01M14.5 9.5v.01"/>',
  upload: '<path d="M12 16V5"/><path d="m7 9 5-4.5L17 9"/><path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>',
  wand: '<path d="m5 19 9.5-9.5"/><path d="M16 3.5v3M14.5 5h3M19 9.5v3M17.5 11h3M8.5 3.5 9.3 5.6 11.4 6.4 9.3 7.2 8.5 9.3 7.7 7.2 5.6 6.4 7.7 5.6z"/>',
  download: '<path d="M12 4v11"/><path d="m7 11 5 4.5L17 11"/><path d="M4 17v1a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-1"/>',
  alert: '<path d="M12 3 2.5 20h19z"/><path d="M12 9.5V14M12 17v.01"/>',
  spinner: '<path d="M12 3a9 9 0 1 0 9 9"/>',
};
const svgIcon = (name, cls = "icon") =>
  `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor"
     stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
     aria-hidden="true">${ICONS[name]}</svg>`;
document.querySelectorAll("[data-icon]").forEach(el => {
  el.outerHTML = svgIcon(el.dataset.icon, el.className);
});

const $ = (sel) => document.querySelector(sel);
const form = $("#form"), drop = $("#drop"), fileInput = $("#file"),
      go = $("#go"), errBox = $("#error"), result = $("#result");
let picked = null;

function setFile(f) {
  picked = f || null;
  go.disabled = !picked;
  drop.classList.toggle("hasfile", !!picked);
  $("#dropText").textContent = picked
    ? `${picked.name}(${(picked.size / 1024).toFixed(0)} KB)`
    : "拖放檔案到這裡,或點擊選擇(.gif .svg .png .jpg .webp)";
}
drop.addEventListener("click", () => fileInput.click());
drop.addEventListener("keydown", e => {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); }
});
fileInput.addEventListener("change", () => setFile(fileInput.files[0]));
["dragover", "dragleave", "drop"].forEach(ev =>
  drop.addEventListener(ev, e => {
    e.preventDefault();
    drop.classList.toggle("drag", ev === "dragover");
    if (ev === "drop") setFile(e.dataTransfer.files[0]);
  }));

function showError(msg) {
  errBox.classList.toggle("hide", !msg);
  errBox.lastElementChild.textContent = msg || "";
}

form.addEventListener("submit", async e => {
  e.preventDefault();
  if (!picked) return;
  showError("");
  result.classList.add("hide");
  go.disabled = true;
  $("#goText").textContent = "轉換中…(動畫 SVG 需要截圖,可能要一兩分鐘)";
  go.firstElementChild.outerHTML = svgIcon("spinner", "icon spin");

  const fd = new FormData(form);
  fd.set("file", picked);
  try {
    const resp = await fetch("/api/convert", { method: "POST", body: fd });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || resp.statusText);
    render(data.results);
  } catch (err) {
    showError(err.message);
  } finally {
    go.disabled = false;
    $("#goText").textContent = "開始轉換";
    go.firstElementChild.outerHTML = svgIcon("wand");
  }
});

function render(list) {
  result.innerHTML = "";
  for (const d of list) {
    const item = document.createElement("div");
    item.className = "result-item";
    const kb = d.size / 1024, budget = d.budget_kb;
    const rows = [
      ["路線", d.preset === "sticker" ? "貼圖" : "表情"],
      ["格式", d.format.toUpperCase()],
      ["尺寸", `${d.width}×${d.height}`],
      ["大小", `${kb.toFixed(0)} KB / ${budget} KB`],
    ];
    if (d.frames > 1) rows.push(["幀數", d.frames], ["幀率", `${d.fps} fps`],
                                ["內容", `${d.artwork_px}px`],
                                ["色數", d.colors]);
    item.innerHTML = `
      <img alt="轉換結果預覽">
      <div class="budget"><div></div></div>
      <div class="meta"></div>
      <a class="dl" download><span data-icon="download" class="icon"></span>下載</a>`;
    const img = item.querySelector("img");
    img.src = d.file;
    img.width = d.width;
    const bar = item.querySelector(".budget > div");
    bar.style.width = Math.min(100, (kb / budget) * 100) + "%";
    bar.classList.toggle("over", kb > budget);
    item.querySelector(".meta").innerHTML = rows
      .map(([k, v]) => `<span>${k} <b>${v}</b></span>`).join("");
    const a = item.querySelector("a.dl");
    a.href = d.file;
    a.download = d.filename;
    a.querySelector("[data-icon]").outerHTML = svgIcon("download");
    result.appendChild(item);
  }
  result.classList.remove("hide");
}
