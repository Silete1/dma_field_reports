// Social images: screenshot every <section class="so" data-name> of social.html at its own size.
// node social.mjs [--only=name,name]   → business_intel/output/<slug>/social/<name>.png (+ out/social-sheet.png via sheet)
import { createRequire } from "module";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require("playwright")); } catch { ({ chromium } = require("C:/Users/Lenovo/Documents/odoo19/qr_anu/node_modules/playwright")); }
const HERE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"));
const ROOT = path.dirname(HERE);
// the edition's own output folder: pitch.json publish_dir output/<slug>/pdf -> output/<slug>/social
const CFG = JSON.parse(fs.readFileSync(path.join(HERE, "pitch.json"), "utf8"));
const OUT = path.resolve(ROOT, "../..", CFG.publish_dir.replace(/\/pdf$/, "/social"));
fs.mkdirSync(OUT, { recursive: true });
const only = ((process.argv.find((a) => a.startsWith("--only=")) || "").split("=")[1] || "").split(",").filter(Boolean);
const types = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".woff2": "font/woff2", ".svg": "image/svg+xml", ".png": "image/png" };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname));
  fs.readFile(p, (e, d) => { if (e) { res.writeHead(404); res.end(); return; } res.writeHead(200, { "content-type": types[path.extname(p)] || "application/octet-stream" }); res.end(d); });
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const browser = await chromium.launch();
const page = await (await browser.newContext({ viewport: { width: 1300, height: 2000 }, deviceScaleFactor: 1 })).newPage();
const log = [];
page.on("pageerror", (e) => log.push(`pageerror: ${e.message}`));
page.on("response", (r) => { if (r.status() >= 400) log.push(`http ${r.status()}: ${r.url()}`); });
await page.goto(`http://127.0.0.1:${server.address().port}/pitch/social.html`);
await page.evaluate(async () => { await document.fonts.ready; });
await page.waitForTimeout(600);
const names = await page.$$eval("section.so[data-name]", (s) => s.map((x) => x.dataset.name));
const report = [];
for (const n of names) {
  if (only.length && !only.includes(n)) continue;
  const el = await page.$(`section.so[data-name="${n}"]`);
  // gates: text leaving its image or overlapping the call to action
  const fails = await el.evaluate((sec) => {
    const R = (e) => e.getBoundingClientRect(), s = R(sec), out = [];
    sec.querySelectorAll("h1,h2,h3,p,li,span,b,small").forEach((e) => {
      const r = R(e); if (!r.width || !r.height) return;
      if (r.left < s.left - 1 || r.right > s.right + 1 || r.top < s.top - 1 || r.bottom > s.bottom + 1) out.push(`leaves: ${e.textContent.trim().slice(0, 30)}`);
    });
    const cta = sec.querySelector(".so-cta");
    if (cta) { const c = R(cta); sec.querySelectorAll("h1,.so-s,.so-foot,.gmap,.zleg,.am,.so-costs,.exh,.tg").forEach((e) => { const r = R(e);
      if (Math.min(r.bottom, c.bottom) - Math.max(r.top, c.top) > 2 && Math.min(r.right, c.right) - Math.max(r.left, c.left) > 2) out.push(`over the CTA: ${e.className}`); }); }
    return out;
  });
  const file = path.join(OUT, `${n}.png`);
  await el.screenshot({ path: file });
  report.push({ name: n, file, fails });
}
await browser.close(); server.close();
console.log(JSON.stringify({ images: report, log }, null, 1));
process.exit(report.some((r) => r.fails.length) || log.length ? 2 : 0);
