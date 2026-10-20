// ANU sector-pitch kit: render ed.html -> out/pages/pNN.png and out/<name>.pdf, with the layout gates.
// node render.mjs [--pdf] [--scale=1] [--only=3,4]
// Serves business_intel/tmp/<slug> (pages at /pitch/, captures at /captures/<caps>/). Name from pitch.json.
// Playwright: a local node_modules if present, else the repo's qr_anu install (see references/08-lessons.md).
import { createRequire } from "module";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require("playwright")); } catch { ({ chromium } = require("C:/Users/Lenovo/Documents/odoo19/qr_anu/node_modules/playwright")); }
const HERE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"));
const ROOT = path.dirname(HERE);
const pdf = process.argv.includes("--pdf");
const scale = Number((process.argv.find((a) => a.startsWith("--scale=")) || "--scale=1").split("=")[1]);
const only = (process.argv.find((a) => a.startsWith("--only=")) || "").split("=")[1];
const OUT = path.join(HERE, "out");
fs.mkdirSync(path.join(OUT, "pages"), { recursive: true });
const NAME = JSON.parse(fs.readFileSync(path.join(HERE, "pitch.json"), "utf8")).name;

const types = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".json": "application/json",
  ".woff2": "font/woff2", ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg" };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname));
  fs.readFile(p, (e, d) => {
    if (e) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { "content-type": types[path.extname(p)] || "application/octet-stream" }); res.end(d);
  });
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: scale });
const page = await ctx.newPage();
const log = [];
page.on("console", (m) => { if (m.type() === "error" || m.type() === "warning") log.push(`console.${m.type()}: ${m.text()}`); });
page.on("pageerror", (e) => log.push(`pageerror: ${e.message}`));
page.on("response", (r) => { if (r.status() >= 400) log.push(`http ${r.status()}: ${r.url()}`); });
await page.goto(`${base}/pitch/ed.html`);
await page.evaluate(async () => { await document.fonts.ready; });
await page.waitForFunction(() => document.documentElement.dataset.placed === "1", null, { timeout: 15000 });
await page.waitForTimeout(250);

const checks = await page.evaluate(() => {
  const fails = [], warns = [];
  const R = (el) => el.getBoundingClientRect();
  const inter = (a, b) => Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left)) * Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
  document.querySelectorAll(".pg").forEach((pg, i) => {
    const P = `p${i + 1}`, pr = R(pg);
    const bleed = pg.classList.contains("pg--bleed");
    // 1. text leaving the page / below the content area
    pg.querySelectorAll("h1,h2,h3,p,li,span,b,small,.note").forEach((el) => {
      if (el.closest(".phone,.cv-phone,.win__scr,.scr,.paper")) return;
      const r = R(el); if (!r.width || !r.height) return;
      if (r.left < pr.left - 1 || r.right > pr.right + 1 || r.top < pr.top - 1 || r.bottom > pr.bottom + 1)
        fails.push(`${P}: "${el.textContent.trim().slice(0, 36)}" leaves the page`);
      if (el.matches(".note") && r.bottom > pr.top + 846) fails.push(`${P}: note "${el.textContent.trim().slice(0, 30)}" below 846`);
    });
    // 2. type size: nothing under 14px outside captures (small tags 13)
    const walker = document.createTreeWalker(pg, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const t = walker.currentNode; if (!t.textContent.trim()) continue;
      const el = t.parentElement; if (el.closest(".phone,.cv-phone,.cv-win,.win__scr,.scr,.paper,.obj,svg")) continue;
      const fs = parseFloat(getComputedStyle(el).fontSize);
      const min = el.closest(".tg--sm,.phone__bar") ? 12.5 : 14;
      if (fs < min) fails.push(`${P}: ${fs}px text "${t.textContent.trim().slice(0, 30)}"`);
    }
    // 3. overlaps: band words, notes against notes and against the screens
    const band = [...pg.querySelectorAll(".strip .q,.strip .tabs,.strip .pno")];
    for (let a = 0; a < band.length; a++) for (let b = a + 1; b < band.length; b++)
      if (inter(R(band[a]), R(band[b])) > 4) fails.push(`${P}: band overlap ${band[a].className} × ${band[b].className}`);
    const notes = [...pg.querySelectorAll(".note")];
    const solids = [...pg.querySelectorAll(".win,.att,.phone,.paper,.loupe,.lp,.flow,.ix,.slip,.stamp")];
    notes.forEach((n, a) => {
      notes.slice(a + 1).forEach((m) => { if (inter(R(n), R(m)) > 4) fails.push(`${P}: notes overlap "${n.textContent.trim().slice(0, 20)}" × "${m.textContent.trim().slice(0, 20)}"`); });
      solids.forEach((s) => { if (inter(R(n), R(s)) > 4 && !s.contains(n)) fails.push(`${P}: note "${n.textContent.trim().slice(0, 24)}" over ${s.className}`); });
    });
    // 3b. any text outside a screen hidden behind a screen, phone or paper
    const walls = [...pg.querySelectorAll(".win,.att,.phone,.paper,.lp,.cv-phone,.cv-win")];
    pg.querySelectorAll("p,h1,h2,h3,li,.tg").forEach((el) => {
      if (walls.some((w) => w.contains(el)) || el.closest(".band")) return;
      const r = R(el); if (!r.width) return;
      walls.forEach((w) => {
        if (inter(r, R(w)) > 6) fails.push(`${P}: "${el.textContent.trim().slice(0, 30)}" is under ${w.className}`);
      });
    });
    // 4. the strip's blue edge never covered; content never above y 180
    pg.querySelectorAll(".win,.att,.phone,.paper,.note,.flow,.ix,.nrow,.slip").forEach((el) => {
      if (R(el).top < pr.top + 180 && !pg.classList.contains("inkpg")) fails.push(`${P}: ${el.className} starts above 180`);
    });
    // 5. screens that end past the content area (bleeding phones allowed)
    pg.querySelectorAll(".win,.att,.lp").forEach((el) => { if (R(el).bottom > pr.top + 862) fails.push(`${P}: ${el.className} ends at ${Math.round(R(el).bottom - pr.top)}`); });
    // 6. one-line rules: title, sub, idx questions stay on one line
    pg.querySelectorAll(".q,.slip .rl > small:not(.ar)").forEach((el) => {
      const lh = parseFloat(getComputedStyle(el).lineHeight); if (R(el).height > lh * 1.5) fails.push(`${P}: "${el.textContent.trim().slice(0, 30)}" wraps`);
    });
    // 5b. phones and papers end on the content floor too (y 862)
    pg.querySelectorAll(".phone,.paper").forEach((el) => { if (!pg.classList.contains("inkpg") && R(el).bottom > pr.top + 870) fails.push(`${P}: ${el.className} ends at ${Math.round(R(el).bottom - pr.top)}`); });
    // 5c. reserved kit classes reused inside content (they carry absolute positions: .pg .q .t .band .s .foot)
    pg.querySelectorAll(".pg,.band,.t,.s,.foot").forEach((el) => { fails.push(`${P}: reserved class on <${el.tagName.toLowerCase()} class="${el.className}">`); });
    pg.querySelectorAll(".q").forEach((el) => { if (!el.closest(".strip")) fails.push(`${P}: reserved class .q outside the strip ("${el.textContent.trim().slice(0, 20)}")`); });
    // 7. notes: at most 3 lines each
    notes.forEach((n) => { const span = n.querySelector("span"); if (span && R(span).height > 3.2 * 28) warns.push(`${P}: note "${n.textContent.trim().slice(0, 24)}" is ${Math.round(R(span).height)}px tall`); });
  });
  // 8. every numbered outline sits inside its capture (layout.js reports the ones that do not)
  (window.__placeReport || []).forEach((r) => fails.push(`marker: ${r}`));
  return { fails, warns, place: window.__placeReport || [] };
});

const sections = await page.$$(".pg");
const want = only ? only.split(",").map(Number) : null;
for (let i = 0; i < sections.length; i++) {
  if (want && !want.includes(i + 1)) continue;
  await sections[i].screenshot({ path: path.join(OUT, "pages", `p${String(i + 1).padStart(2, "0")}.png`) });
}
let pdfPath = null;
if (pdf) {
  pdfPath = path.join(OUT, `${NAME}.pdf`);
  await page.emulateMedia({ media: "print" });
  await page.pdf({ path: pdfPath, width: "1600px", height: "900px", printBackground: true, preferCSSPageSize: true });
}
await browser.close();
server.close();
const res = { pages: sections.length, pdf: pdfPath, fails: checks.fails, warns: checks.warns, place: checks.place, log };
fs.writeFileSync(path.join(OUT, "render.json"), JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, null, 1));
process.exit(checks.fails.length ? 2 : 0);
