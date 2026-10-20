// ANU pitch v2: place every callout from its capture's markers (crop CSS px), then level each note with its outline.
//   <img class="cap" data-cap="board" data-w="1060" [data-crop-y="40"]>   the capture, shown at any scale
//   <div class="hl" data-mk="board:1" [data-n="2"] [data-pad="5"] [class alarm|pin-l|pin-b]>   outline + pin
//   <p class="note" data-for="board:1" [data-col="r"] [data-dy="0"] [data-min="230"]>   note, same height
// window.MARKERS = {name: {w, h, markers: [{n, box: [x, y, w, h]}]}} is written by build.py.
(function () {
  const M = window.MARKERS || {};
  function place() {
    const report = [];
    // loupes: <figure class="lp" data-lp="cap:n" data-scale="1" data-pad="8"> shows one marker's region of a capture
    document.querySelectorAll(".lp[data-lp]").forEach((lp) => {
      const [cap, n] = lp.dataset.lp.split(":");
      const m = ((M[cap] || {}).markers || []).find((x) => String(x.n) === n);
      const img = lp.querySelector("img.cap"), win = lp.querySelector(".lp__win");
      if (!m || !img || !win) { lp.dataset.missing = "1"; report.push(`loupe ${lp.dataset.lp}: no marker`); return; }
      const s = Number(lp.dataset.scale || 1), pad = Number(lp.dataset.pad || 8), W = (M[cap] || {}).w || 1060;
      const [x, y, w, h] = m.box;
      win.style.width = (w + 2 * pad) * s + "px"; win.style.height = (h + 2 * pad) * s + "px";
      Object.assign(img.style, { width: W * s + "px", left: -(x - pad) * s + "px", top: -(y - pad) * s + "px" });
    });
    document.querySelectorAll(".pg").forEach((pg, pi) => {
      const pr = pg.getBoundingClientRect();
      pg.querySelectorAll(".hl[data-mk]").forEach((hl) => {
        const [cap, n] = hl.dataset.mk.split(":");
        const img = pg.querySelector(`img.cap[data-cap="${cap}"]`);
        const m = ((M[cap] || {}).markers || []).find((x) => String(x.n) === n);
        if (!img || !m) { hl.style.display = "none"; hl.dataset.missing = "1"; report.push(`p${pi + 1} ${hl.dataset.mk}: no marker`); return; }
        const ir = img.getBoundingClientRect();
        const s = ir.width / Number(img.dataset.w || (M[cap] || {}).w || img.naturalWidth);
        const cy = Number(img.dataset.cropY || 0);
        const pad = Number(hl.dataset.pad || 5);
        let [x, y, w, h] = m.box;
        if (hl.dataset.adj) { const [al, at, ar, ab] = hl.dataset.adj.split(",").map(Number); x -= al; y -= at; w += al + ar; h += at + ab; }
        let L = ir.left - pr.left + x * s - pad, T = ir.top - pr.top + (y - cy) * s - pad;
        let R = L + w * s + 2 * pad, B = T + h * s + 2 * pad;
        const clip = img.closest(".win__scr,.phone__scr,.loupe__scr,.paper,.scr");
        if (clip) {
          const c = clip.getBoundingClientRect();
          const cl = c.left - pr.left, ct = c.top - pr.top, cr = cl + c.width, cb = ct + c.height;
          if (T > cb - 8 || B < ct + 8) report.push(`p${pi + 1} ${hl.dataset.mk}: outside its slot`);
          L = Math.max(L, cl + 2); T = Math.max(T, ct + 2); R = Math.min(R, cr - 2); B = Math.min(B, cb - 2);
        }
        Object.assign(hl.style, { left: L + "px", top: T + "px", width: R - L + "px", height: B - T + "px" });
        if (!hl.querySelector(".pin") && !hl.hasAttribute("data-nopin")) {
          const p = document.createElement("b"); p.className = "pin"; p.textContent = hl.dataset.n || n; hl.appendChild(p);
          // pin-gl / pin-gr: the badge in the outer gutter beside the screen, level with the box (never on a label)
          const gl = hl.classList.contains("pin-gl"), gr = hl.classList.contains("pin-gr");
          if ((gl || gr) && clip) {
            const c = clip.getBoundingClientRect(), cl = c.left - pr.left, cr = cl + c.width;
            Object.assign(p.style, { top: (B - T) / 2 - 14 + "px", bottom: "auto", right: "auto", left: (gl ? cl - L - 34 : cr - L + 6) + "px" });
          }
        }
      });
      const cols = {};
      pg.querySelectorAll(".note[data-for]").forEach((el, k) => {
        const hl = pg.querySelector(`.hl[data-mk="${el.dataset.for}"]`);
        const lost = !hl || hl.dataset.missing;   // no marker yet: keep the note in its column, in order
        (cols[el.dataset.col || "r"] = cols[el.dataset.col || "r"] || []).push({ el, hl, lost, k });
      });
      Object.values(cols).forEach((list) => {
        list.forEach((o) => { o.want = o.lost ? 300 + o.k : parseFloat(o.hl.style.top) + Number(o.el.dataset.dy || 0) - 1; });
        list.sort((a, b) => a.want - b.want);
        let floor = Number(list[0].el.dataset.min || 232);
        list.forEach((o) => {
          const top = Math.max(o.want, floor);
          o.el.style.top = top + "px";
          floor = top + o.el.getBoundingClientRect().height + 18;
          if (top + o.el.getBoundingClientRect().height > 842) report.push(`p${pi + 1} note ${o.el.dataset.for}: below the content area`);
        });
      });
    });
    window.__placeReport = report;
    document.documentElement.dataset.placed = "1";
  }
  window.anuPlace = place;
  const go = () => document.fonts.ready.then(() => requestAnimationFrame(place));
  if (document.readyState === "complete") go(); else window.addEventListener("load", go);
})();
