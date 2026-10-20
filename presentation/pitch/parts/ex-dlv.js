
// ---------------------------------------------------------------- delivery edition (29 Sep): Iraq, the parcel, the run, the cash
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const mk = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };
  const num = (v) => Number(String(v).replace(/[^\d.\-]/g, ""));
  const J = (el, k) => { try { return JSON.parse(el.dataset[k] || "null"); } catch (e) { return null; } };
  const iqd = (v) => Math.round(num(v)).toLocaleString("en-US");
  const IRQ = window.IRQ;

  // Iraq as line art in an <svg> W px wide; returns the scale (px per map unit)
  function drawIraq(svg, W, o) {
    const s = W / IRQ.w, H = IRQ.h * s;
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("width", W); svg.setAttribute("height", H);
    const g = mk("g", { transform: `scale(${s})` }, svg);
    if (o.landFill) mk("path", { d: IRQ.outline, fill: o.landFill, stroke: "none" }, g);
    if (o.govs) IRQ.govs.forEach((gv) => mk("path", { d: gv.d, fill: o.fill ? o.fill(gv) : "none", stroke: o.govStroke, "stroke-width": o.govW / s, "stroke-linejoin": "round" }, g));
    mk("path", { d: IRQ.outline, fill: "none", stroke: o.stroke, "stroke-width": o.w / s, "stroke-linejoin": "round" }, g);
    return s;
  }

  // the cover: .gmap > svg.geo + .site[data-k][data-city][data-dx][data-dy] (.hq, .dot); data-links="a-b …", data-main="a-b …";
  // .fl[data-on="a-b"][data-f] files on a link, followed by an optional .flab[data-side][data-dx][data-dy]
  if (IRQ) document.querySelectorAll(".gmap").forEach((map) => {
    const W = map.offsetWidth, svg = map.querySelector("svg.geo");
    const s = drawIraq(svg, W, { stroke: "rgba(147,197,253,.85)", w: 1.8, govs: true, govStroke: "rgba(147,197,253,.28)", govW: 0.9, landFill: "rgba(37,99,235,.08)" });
    const pos = {};
    map.querySelectorAll(".site").forEach((el) => {
      const c = IRQ.cities[el.dataset.city] || [0, 0];
      const x = c[0] * s + num(el.dataset.dx || 0), y = c[1] * s + num(el.dataset.dy || 0);
      pos[el.dataset.k] = [x, y];
      if (el.classList.contains("dot")) { el.style.right = W - x - 6 + "px"; el.style.top = y - 11 + "px"; return; }
      if (el.classList.contains("side")) { el.style.right = W - x - 30 + "px"; el.style.top = y - 30 + "px"; return; }
      const half = el.classList.contains("hq") ? 40 : 31;
      el.style.left = x + "px"; el.style.top = y - half + "px";
    });
    const main = (map.dataset.main || "").split(" ").filter(Boolean);
    const lines = mk("g", {}, svg);
    (map.dataset.links || "").split(" ").filter(Boolean).forEach((pair) => {
      const [a, b] = pair.split("-").map((k) => pos[k]); if (!a || !b) return;
      const on = main.includes(pair);
      mk("line", { x1: a[0], y1: a[1], x2: b[0], y2: b[1], stroke: on ? "#3B82F6" : "#60A5FA", "stroke-width": on ? 2.4 : 1.3, opacity: on ? 0.9 : 0.55, "stroke-dasharray": on ? "" : "3 6" }, lines);
    });
    map.querySelectorAll(".fl").forEach((f) => {
      const [a, b] = f.dataset.on.split("-").map((k) => pos[k]); if (!a || !b) return;
      const t = num(f.dataset.f), fx = a[0] + (b[0] - a[0]) * t, fy = a[1] + (b[1] - a[1]) * t;
      f.style.left = fx + "px"; f.style.top = fy + "px";
      const lab = f.nextElementSibling;
      if (lab && lab.classList.contains("flab")) {
        if (lab.dataset.side === "l") lab.style.right = W - fx + num(lab.dataset.dx || 16) + "px"; else lab.style.left = fx + num(lab.dataset.dx || 16) + "px";
        lab.style.top = fy + num(lab.dataset.dy || -16) + "px";
      }
    });
    map.querySelectorAll(".road[data-city]").forEach((r) => { const c = IRQ.cities[r.dataset.city]; r.style.left = c[0] * s + num(r.dataset.dx || 0) + "px"; r.style.top = c[1] * s + num(r.dataset.dy || 0) + "px"; });
  });

  // the zone-fee map: .zmap[data-zones='{gov_k: 1|2|3}'][data-w] > svg.geo + .zlab[data-city][data-dx][data-dy]; data-route="baghdad-basra"
  if (IRQ) document.querySelectorAll(".zmap[data-zones]").forEach((box) => {
    const Z = J(box, "zones") || {}, W = num(box.dataset.w || box.offsetWidth), svg = box.querySelector("svg.geo");
    const defs = mk("defs", {}, svg), pat = mk("pattern", { id: "zhatch", width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(135)" }, defs);
    mk("rect", { width: 6, height: 6, fill: "#fff" }, pat); mk("line", { x1: 0, y1: 0, x2: 0, y2: 6, stroke: "#94A3B8", "stroke-width": 2 }, pat);
    const fillOf = (gv) => ({ 1: "#60A5FA", 2: "#FFFFFF", 3: "url(#zhatch)" }[Z[gv.k] || 2]);
    const s = drawIraq(svg, W, { stroke: "#090B11", w: 1.8, govs: true, govStroke: "#94A3B8", govW: 0.9, fill: fillOf });
    const top = 34;
    IRQ.govs.filter((gv) => Z[gv.k] === 1).forEach((gv) => mk("path", { d: gv.d, fill: "none", stroke: "#2563EB", "stroke-width": 2.2 / s, transform: `scale(${s})` }, svg));
    (box.dataset.route || "").split(" ").filter(Boolean).forEach((pair) => {
      const [a, b] = pair.split("-").map((k) => IRQ.cities[k]);
      mk("line", { x1: a[0] * s, y1: a[1] * s, x2: b[0] * s, y2: b[1] * s, stroke: "#2563EB", "stroke-width": 3 }, svg);
      [a, b].forEach((c) => mk("rect", { x: c[0] * s - 6, y: c[1] * s - 6, width: 12, height: 12, fill: "#2563EB" }, svg));
    });
    box.querySelectorAll(".zlab[data-city]").forEach((l) => { const c = IRQ.cities[l.dataset.city]; l.style.left = c[0] * s + num(l.dataset.dx || 0) + "px"; l.style.top = top + c[1] * s + num(l.dataset.dy || 0) + "px"; });
  });

  // the line manifest as a sheet: .mfx[data-n][data-miss][data-cols] > .cells2 ; one mini barcode stub per parcel,
  // a Signal tick line under each scanned one, the missing slot dashed red (first stub top-right, RTL)
  document.querySelectorAll(".mfx[data-n]").forEach((m) => {
    const n = Math.round(num(m.dataset.n)), miss = (m.dataset.miss || "").split(" ").filter(Boolean).map(Number), g = m.querySelector(".cells2");
    const cols = Number(m.dataset.cols || 20), cw = 21, ch = 18, gx = 5, gy = 13, rows = Math.ceil(n / cols);
    const W = cols * (cw + gx) - gx, Hh = rows * (ch + gy);
    const svg = mk("svg", { width: W, height: Hh, viewBox: `0 0 ${W} ${Hh}` }); g.appendChild(svg);
    const pat = [2, 1, 1, 2, 3, 1, 1, 2, 1, 1, 2, 1];
    for (let i = 0; i < n; i++) {
      const c = i % cols, r = Math.floor(i / cols), x = W - (c + 1) * (cw + gx) + gx, y = r * (ch + gy);
      if (miss.includes(i + 1)) { mk("rect", { x: x + 0.8, y: y + 0.8, width: cw - 1.6, height: ch + 2, fill: "none", stroke: "#C81E1E", "stroke-width": 1.6, "stroke-dasharray": "3 2" }, svg); continue; }
      let bx = x, k = i % 5;
      while (bx < x + cw - 1) { const w = pat[k++ % pat.length] * 0.9; if (k % 2) mk("rect", { x: bx, y, width: Math.min(w, x + cw - bx), height: ch, fill: "#090B11" }, svg); bx += w + 0.9; }
      mk("rect", { x, y: y + ch + 2, width: cw, height: 2, fill: "#2563EB" }, svg);
    }
  });

  // a small Iraq with the nightly line: .minimap[data-hubs="baghdad basra …"][data-w] > svg (first hub = HQ)
  if (IRQ) document.querySelectorAll(".minimap[data-hubs]").forEach((b) => {
    const W = num(b.dataset.w || 200), svg = b.querySelector("svg"), hubs = b.dataset.hubs.split(" ");
    const s = drawIraq(svg, W, { stroke: "#94A3B8", w: 1.2, landFill: "#F8FAFC" });
    const [hx, hy] = IRQ.cities[hubs[0]];
    hubs.slice(1).forEach((h) => { const c = IRQ.cities[h]; mk("line", { x1: hx * s, y1: hy * s, x2: c[0] * s, y2: c[1] * s, stroke: "#2563EB", "stroke-width": 2 }, svg); });
    hubs.forEach((h, i) => { const c = IRQ.cities[h]; mk("rect", { x: c[0] * s - 5, y: c[1] * s - 5, width: 10, height: 10, fill: i ? "#fff" : "#090B11", stroke: "#090B11", "stroke-width": 1.6 }, svg); });
  });

  // the run on real streets: .runmap[data-run='{n, fail:[k], post:[k], ours:k}'] ; the route leaves the branch (right),
  // runs the three streets as a snake (stops on the streets), and comes back along the lower road; orthogonal segments only
  document.querySelectorAll(".runmap[data-run]").forEach((box) => {
    const D = J(box, "run") || {}, W = box.offsetWidth, H = box.offsetHeight, n = D.n || 34;
    const svg = mk("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}` }); box.prepend(svg);
    const y0 = 76, gap = (H - y0 - 44) / 3, rows = [y0, y0 + gap, y0 + 2 * gap], road = H - 30;
    const xR = W - 96, xL = 64, hubX = W - 40;
    const st = mk("g", { stroke: "#EEF2F7", "stroke-width": 9, fill: "none", "stroke-linecap": "square" }, svg);
    [...rows, road].forEach((y) => mk("path", { d: `M14 ${y} H${W - 14}` }, st));
    for (let k = 0; k <= 11; k++) { const x = xL + ((xR - xL) * k) / 11; mk("path", { d: `M${x} ${y0 - 24} V${H - 12}` }, st); }
    mk("path", { d: `M${hubX} ${y0 - 24} V${H - 12}` }, st);
    mk("path", { d: `M14 ${road} H${W - 14}`, stroke: "#E2E8F0", "stroke-width": 13 }, st);
    const per = [Math.ceil(n / 3), Math.ceil(n / 3), n - 2 * Math.ceil(n / 3)], P = [];
    per.forEach((k, r) => { for (let i = 0; i < k; i++) { const f = k === 1 ? 0 : i / (k - 1); P.push([r % 2 ? xL + (xR - xL) * f : xR - (xR - xL) * f, rows[r]]); } });
    const out = [[hubX, rows[0]], ...P.slice(0, per[0]), [xL, rows[1]], ...P.slice(per[0], per[0] + per[1]), [xR, rows[2]], ...P.slice(per[0] + per[1])];
    mk("polyline", { points: out.map((p) => p.join(",")).join(" "), fill: "none", stroke: "#090B11", "stroke-width": 2.2, "stroke-linejoin": "miter" }, svg);
    const last = P[P.length - 1];
    mk("polyline", { points: [last, [last[0], road], [hubX, road], [hubX, rows[0]]].map((p) => p.join(",")).join(" "), fill: "none", stroke: "#94A3B8", "stroke-width": 2, "stroke-dasharray": "6 5" }, svg);
    const hub = document.createElement("div"); hub.className = "hub"; hub.style.left = hubX + "px"; hub.style.top = rows[0] + "px";
    hub.innerHTML = '<svg class="ic tb"><use href="#i-warehouse"/></svg>'; box.appendChild(hub);
    P.forEach(([x, y], i) => {
      const k = i + 1, e = document.createElement("i");
      e.className = "stp" + ((D.fail || []).includes(k) ? " fail" : (D.post || []).includes(k) ? " post" : "") + (k === D.ours ? " ours" : "");
      e.style.left = x + "px"; e.style.top = y + "px"; box.appendChild(e);
      if (k === D.ours) { const l = box.querySelector(".rlab"); if (l) { l.style.left = x + num(l.dataset.dx || -20) + "px"; l.style.top = y + num(l.dataset.dy || 12) + "px"; } }
    });
    const hl = box.querySelector(".hlab"); if (hl) { hl.style.right = W - hubX - 26 + "px"; hl.style.top = rows[0] + 28 + "px"; }
    const rl = box.querySelector(".roadl"); if (rl) { rl.style.left = (xL + xR) / 2 + "px"; rl.style.top = road - 9 + "px"; }
  });

  // return reasons: .rbars[data-rows='[{r, n}]'] sorted high → low; the top reason in ink, the rest slate
  document.querySelectorAll(".rbars[data-rows]").forEach((b) => {
    const R = (J(b, "rows") || []).slice().sort((x, y) => num(y.n) - num(x.n)), mx = Math.max(...R.map((r) => num(r.n))) || 1, at = b.querySelector(".rsum");
    const fv = b.dataset.dec ? (v) => num(v).toFixed(Number(b.dataset.dec)) : iqd;
    R.forEach((r, i) => {
      const row = document.createElement("div"); row.className = "rrow" + (i === 0 ? " top" : "");
      row.innerHTML = `<span class="rl2">${r.r}</span><span class="rb"><i style="width:${(num(r.n) / mx) * 100}%"></i></span><span class="rv">${fv(r.n)}</span>`;
      b.insertBefore(row, at);
    });
  });

  // per-merchant payouts: .mbars[data-rows='[{name, due, paid, late, note}]'] ; paid ink, owed slate, owed red when late
  document.querySelectorAll(".mbars[data-rows]").forEach((b) => {
    const R = J(b, "rows") || [], mx = Math.max(...R.map((r) => num(r.due))) || 1;
    R.forEach((r) => {
      const due = num(r.due), paid = Math.min(due, num(r.paid)), owed = due - paid;
      const row = document.createElement("div"); row.className = "mrow" + (r.late ? " late" : "");
      row.innerHTML = `<span class="mn">${r.name}</span><span class="mb" style="width:${(due / mx) * 100}%">${paid > 0 ? `<i class="pd" style="flex:${paid}"></i>` : ""}${owed > 0 ? `<i class="${r.late ? "al" : "ow"}" style="flex:${owed}"></i>` : ""}</span><span class="mv">${iqd(due)}</span><span class="ms">${r.note || ""}</span>`;
      b.appendChild(row);
    });
  });

  // vehicles, line art facing left: .vart[data-k=moto|van|truck][data-w]
  const VEH = {
    moto: { vb: "0 0 220 130", d: '<circle cx="46" cy="100" r="24"/><circle cx="46" cy="100" r="12"/><circle cx="174" cy="100" r="24"/><circle cx="174" cy="100" r="12"/><path d="M46 100 L64 42"/><path d="M52 36 H78"/><rect x="34" y="48" width="13" height="11"/><path d="M68 62 Q92 46 122 54 H162"/><path d="M64 62 L86 74"/><rect x="86" y="70" width="38" height="24"/><path d="M124 90 H166 L184 84"/><path d="M124 78 L174 100"/><path d="M148 54 V46 M198 54 V46"/><rect x="138" y="6" width="68" height="40"/><path d="M138 18 H206"/>' },
    van: { vb: "0 0 280 140", d: '<path d="M14 108 V74 L40 46 H70 L80 30 H262 V108 Z"/><path d="M48 52 H76 V74 H30"/><path d="M110 30 V108 M186 30 V108"/><path d="M92 70 H100 M196 70 H204"/><circle cx="64" cy="110" r="18"/><circle cx="64" cy="110" r="5"/><circle cx="216" cy="110" r="18"/><circle cx="216" cy="110" r="5"/><path d="M14 92 H26"/>' },
    truck: { vb: "0 0 340 140", d: '<path d="M14 110 V68 L34 40 H84 V110 Z"/><path d="M40 48 H78 V70 H26"/><rect x="92" y="18" width="236" height="92"/><path d="M92 40 H328 M150 18 V110 M210 18 V110 M270 18 V110"/><circle cx="50" cy="114" r="17"/><circle cx="50" cy="114" r="5"/><circle cx="244" cy="114" r="17"/><circle cx="244" cy="114" r="5"/><circle cx="290" cy="114" r="17"/><circle cx="290" cy="114" r="5"/>' },
  };
  document.querySelectorAll(".vart[data-k]").forEach((v) => {
    const V = VEH[v.dataset.k]; if (!V) return;
    const w = num(v.dataset.w || 200), [, , vw, vh] = V.vb.split(" ").map(Number);
    v.innerHTML = `<svg width="${w}" height="${(w * vh) / vw}" viewBox="${V.vb}" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linejoin="miter" stroke-linecap="square">${V.d}</svg>`;
  });

  // hand tally marks: .tally[data-tally=groups] (four strokes and a slash per group)
  document.querySelectorAll(".tally[data-tally]").forEach((t) => {
    for (let g = 0; g < num(t.dataset.tally); g++) {
      const s = mk("svg", { viewBox: "0 0 34 22" }); t.appendChild(s);
      const G = mk("g", { stroke: "#1E293B", "stroke-width": 1.8, "stroke-linecap": "round" }, s);
      for (let k = 0; k < 4; k++) mk("line", { x1: 5 + k * 6 + (g % 3) * 0.4, y1: 3, x2: 4 + k * 6, y2: 19 }, G);
      mk("line", { x1: 1, y1: 16, x2: 29, y2: 5 }, G);
    }
  });

  // a drawn barcode (not a scannable code): .bcode[data-code][data-w][data-h]
  document.querySelectorAll(".bcode[data-code]").forEach((b) => {
    const code = String(b.dataset.code), w = num(b.dataset.w || 220), h = num(b.dataset.h || 44);
    const bars = [2, 1, 1, 2]; String(code).split("").forEach((c, i) => { const d = Number(c) || 0; bars.push(1 + (d % 3), 1 + ((d + i) % 2), 1 + ((d * 7 + i) % 3), 1 + (i % 2)); }); bars.push(2, 1, 1, 2);
    const tot = bars.reduce((a, c) => a + c, 0), u = w / tot;
    const svg = mk("svg", { width: w, height: h, viewBox: `0 0 ${w} ${h}` }); let x = 0;
    bars.forEach((bw, i) => { if (i % 2 === 0) mk("rect", { x: x, y: 0, width: bw * u, height: h, fill: "#090B11" }, svg); x += bw * u; });
    b.appendChild(svg);
  });
})();
