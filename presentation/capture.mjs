// Real screens for the presentation, from the DMA live-like instance (Arabic UI, DMA theme).
// node capture.mjs [name ...]   -> captures/final/NAME.png (@2x) + NAME.markers.json (CSS px in the crop)
import { createRequire } from "module";
import fs from "node:fs";
import path from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("C:/Users/Lenovo/Documents/odoo19/qr_anu/node_modules/playwright");
const HERE = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1"));
const OUT = path.join(HERE, "captures", "final");
fs.mkdirSync(OUT, { recursive: true });
const BASE = "http://127.0.0.1:8078";
const A = 42, B = 43;
const want = process.argv.slice(2);

const browser = await chromium.launch();

async function session(w, h) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 2, locale: "ar" });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/web/login`);
  const ok = await page.evaluate(async () => {
    const r = await fetch("/web/session/authenticate", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", params: { db: "dma_fr_livelike", login: "admin", password: "admin" } }) });
    return (await r.json()).result?.uid;
  });
  if (!ok) throw new Error("login failed");
  return { ctx, page };
}

async function settle(page, text) {
  if (text) await page.getByText(text).first().waitFor({ state: "visible", timeout: 60000 });
  await page.evaluate(async () => { await document.fonts.ready; });
  await page.waitForTimeout(900);
}

// markers: [[n, selector, nth?, pad?]] boxes relative to the clip
async function shoot(page, name, clip, marks) {
  const markers = [];
  for (const [n, sel, nth = 0, pad = 4] of marks) {
    const box = await page.evaluate(([sel, nth]) => {
      const els = [...document.querySelectorAll(sel)].filter((e) => e.offsetParent || e.getClientRects().length);
      const e = els[nth]; if (!e) return null;
      const r = e.getBoundingClientRect(); return [r.x, r.y, r.width, r.height];
    }, [sel, nth]);
    if (!box) { console.log(`  ! ${name}:${n} no element for ${sel}`); continue; }
    markers.push({ n, box: [box[0] - clip.x - pad, box[1] - clip.y - pad, box[2] + 2 * pad, box[3] + 2 * pad].map(Math.round) });
  }
  await page.screenshot({ path: path.join(OUT, `${name}.png`), clip });
  fs.writeFileSync(path.join(OUT, `${name}.markers.json`),
    JSON.stringify({ crop_css: { width: clip.width, height: clip.height }, markers }, null, 1));
  console.log(`${name}: ${clip.width}x${clip.height}, ${markers.length} markers`);
}

const jobs = {
  async batch_form() {
    const { ctx, page } = await session(1060, 640);
    await page.goto(`${BASE}/odoo/action-dma_field_reports.dma_fr_batch_action/${A}`);
    await settle(page, "FRB/2026/0042");
    await shoot(page, "batch_form", { x: 0, y: 0, width: 1060, height: 640 }, [
      [1, ".o_statusbar_buttons"], [2, ".o_statusbar_status"], [3, ".o-form-buttonbox"], [4, "div[name=next_step]"],
      [5, "div[name=attachment_ids]"]]);
    await ctx.close();
  },
  async problems() {
    const { ctx, page } = await session(1060, 600);
    await page.goto(`${BASE}/odoo/action-dma_field_reports.dma_fr_batch_action/${A}`);
    await settle(page, "FRB/2026/0042");
    await page.locator("button[name=action_open_problems].btn-primary").first().click();
    await settle(page, null);
    for (const h of await page.locator(".o_group_header").all()) { await h.click(); await page.waitForTimeout(350); }
    await page.evaluate(() => {   // hide the task-dossier group (warnings) to keep the screen on the must-fix ones
      const hs = [...document.querySelectorAll(".o_group_header")];
      const g = hs.find((h) => /معرّف ملف المهمة|ملف المهمة|Task/.test(h.innerText));
      if (g) g.click();
    });
    await settle(page, null);
    await shoot(page, "problems", { x: 0, y: 0, width: 1060, height: 600 }, [
      [1, ".o_group_header", 0, 2], [2, "td[name=raw]", 0, 2], [3, "td[name=suggestion]", 0, 2],
      [4, "button[name=action_fix]", 0, 3]]);
    await ctx.close();
  },
  async fix_dialog() {
    const { ctx, page } = await session(1060, 760);
    await page.goto(`${BASE}/odoo/action-dma_field_reports.dma_fr_batch_action/${A}`);
    await settle(page, "FRB/2026/0042");
    await page.locator("button[name=action_open_problems].btn-primary").first().click();
    await settle(page, null);
    for (const h of await page.locator(".o_group_header").all()) { await h.click(); await page.waitForTimeout(350); }
    await page.locator(".o_data_row", { hasText: "Alkasarah" }).locator("button[name=action_fix]").first().click();
    await page.locator(".modal div[name=location_pick_id] input").waitFor();
    await settle(page, null);
    const r = await page.locator(".modal-content").boundingBox();
    const clip = { x: Math.floor(r.x), y: Math.floor(r.y), width: Math.ceil(r.width), height: Math.ceil(r.height) };
    await shoot(page, "fix_dialog", clip, [
      [1, ".modal div.alert-danger"], [2, ".modal div[name=nearby_html]"], [3, ".modal div[name=place_choice]"],
      [4, ".modal div[name=location_pick_id]"], [5, ".modal div[name=apply_all]"]]);
    await ctx.close();
  },
  async exported() {
    const { ctx, page } = await session(1060, 640);
    await page.goto(`${BASE}/odoo/action-dma_field_reports.dma_fr_batch_action/${B}`);
    await settle(page, "FRB/2026/0043");
    const tab = page.locator(".o_notebook .nav-link", { hasText: /التصدير|Exports|عمليات التصدير/ }).first();
    if (await tab.count()) { await tab.click(); await page.waitForTimeout(600); }
    await page.evaluate(() => document.querySelector(".o_notebook")?.scrollIntoView({ block: "end" }));
    await settle(page, null);
    await shoot(page, "exported", { x: 0, y: 0, width: 1060, height: 640 }, [
      [1, ".o_statusbar_status"], [2, ".o_notebook .tab-pane.active .o_list_renderer"], [3, ".o-form-buttonbox"]]);
    await ctx.close();
  },
  async source() {
    const { ctx, page } = await session(1060, 700);
    await page.goto(`${BASE}/odoo/action-dma_field_reports.dma_fr_source_action/2`);
    await settle(page, "IMSMA backup 2025-03-02");
    await shoot(page, "source", { x: 0, y: 0, width: 1060, height: 700 }, [
      [1, "div[name=mode]"], [2, "button[name=action_refresh]"], [3, "div[name=dump_date]"], [4, "div[name=stats]"]]);
    await ctx.close();
  },
};

for (const [name, fn] of Object.entries(jobs)) {
  if (want.length && !want.includes(name)) continue;
  try { await fn(); } catch (e) { console.log(`${name} FAILED: ${e.message.split("\n")[0]}`); }
}
await browser.close();
