// ANU pitch v4: lay out the drawn exhibits from their data (maps, the tangled route, dials, the day ruler).
// Runs deferred, before layout.js places the callouts.
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const mk = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };
  const num = (v) => Number(String(v).replace(/[^\d.\-]/g, ""));

  // the night map: .site[data-k][data-x][data-y] around .site.hq; .fl[data-on][data-f] files on the lines
  document.querySelectorAll(".map").forEach((map) => {
    const svg = map.querySelector("svg.lines");
    const pos = (s) => [num(s.dataset.x), num(s.dataset.y)];
    const hq = map.querySelector(".site.hq");
    const [hx, hy] = pos(hq);
    map.querySelectorAll(".site").forEach((s) => {
      const [x, y] = pos(s), half = s.classList.contains("hq") ? 46 : 38;
      s.style.left = x + "px"; s.style.top = y - half + "px";
    });
    (map.dataset.mesh || "").split(" ").filter(Boolean).forEach((pair) => {
      const [a, b] = pair.split("-").map((k) => pos(map.querySelector(`.site[data-k="${k}"]`)));
      mk("line", { x1: a[0], y1: a[1], x2: b[0], y2: b[1], stroke: "#3B82F6", "stroke-width": 1, opacity: 0.35, "stroke-dasharray": "2 6" }, svg);
    });
    map.querySelectorAll(".site:not(.hq)").forEach((s) => {
      const [x, y] = pos(s);
      mk("line", { x1: hx, y1: hy, x2: x, y2: y, stroke: map.dataset.calm ? "#60A5FA" : "#3B82F6", "stroke-width": 2, opacity: 0.8 }, svg);
    });
    map.querySelectorAll(".fl").forEach((f) => {
      const [x, y] = pos(map.querySelector(`.site[data-k="${f.dataset.on}"]`)), t = num(f.dataset.f);
      const fx = hx + (x - hx) * t, fy = hy + (y - hy) * t;
      f.style.left = fx + "px"; f.style.top = fy + "px";
      const lab = f.nextElementSibling;
      if (lab && lab.classList.contains("flab")) { if (lab.dataset.side === "l") { lab.style.right = (map.offsetWidth || 700) - fx + 16 + "px"; } else { lab.style.left = fx + num(lab.dataset.dx || 16) + "px"; } lab.style.top = fy + num(lab.dataset.dy || -16) + "px"; }
    });
  });

  // rings: .dial[data-v][data-of] (one arc) or [data-days][data-term][data-full] (term + overrun + reminder ticks)
  document.querySelectorAll(".dial[data-v],.dial[data-days]").forEach((d) => {
    const sz = 300, r = 128, C = 2 * Math.PI * r, w = Number(d.dataset.w || 18);
    const svg = mk("svg", { viewBox: `0 0 ${sz} ${sz}` }); d.prepend(svg);
    const g = mk("g", { transform: `rotate(-90 ${sz / 2} ${sz / 2})`, fill: "none", "stroke-width": w }, svg);
    mk("circle", { cx: sz / 2, cy: sz / 2, r, stroke: d.dataset.track || "#E2E8F0" }, g);
    if (d.dataset.v) {
      const f = Math.min(1, num(d.dataset.v) / num(d.dataset.of));
      mk("circle", { cx: sz / 2, cy: sz / 2, r, stroke: d.dataset.color || "#2563EB", "stroke-dasharray": `${f * C} ${C}` }, g);
    } else {
      const full = num(d.dataset.full), term = num(d.dataset.term), days = Math.min(num(d.dataset.days), full);
      const a = (term / full) * C, b = ((days - term) / full) * C;
      mk("circle", { cx: sz / 2, cy: sz / 2, r, stroke: "#2563EB", "stroke-dasharray": `${a} ${C}` }, g);
      mk("circle", { cx: sz / 2, cy: sz / 2, r, stroke: "#C81E1E", "stroke-dasharray": `0 ${a} ${b} ${C}` }, g);
      (d.dataset.ticks || "").split(" ").filter(Boolean).forEach((t) => {
        const ang = (num(t) / full) * 2 * Math.PI;
        const x1 = sz / 2 + (r - w / 2 - 6) * Math.cos(ang), y1 = sz / 2 + (r - w / 2 - 6) * Math.sin(ang);
        const x2 = sz / 2 + (r + w / 2 + 6) * Math.cos(ang), y2 = sz / 2 + (r + w / 2 + 6) * Math.sin(ang);
        mk("line", { x1, y1, x2, y2, stroke: "#090B11", "stroke-width": 3 }, g);
      });
    }
  });

  // the tangled route: <script type="application/json" class="tdata"> {st:[[x,y,label,small,side,cls]], now, hand:[[a,b]]}
  document.querySelectorAll(".tangle").forEach((tg) => {
    const D = JSON.parse(tg.querySelector(".tdata").textContent);
    const svg = mk("svg", {}); tg.prepend(svg);
    const P = D.st.map((s) => [s[0], s[1]]), now = D.now;
    const line = (from, to, attrs) => mk("polyline", Object.assign({ points: P.slice(from - 1, to).map((p) => p.join(",")).join(" "), fill: "none" }, attrs), svg);
    line(1, now, { stroke: "#090B11", "stroke-width": 2.5, "stroke-linejoin": "miter" });
    line(now, P.length, { stroke: "#94A3B8", "stroke-width": 2, "stroke-dasharray": "6 6" });
    D.hand.forEach(([a, b]) => {
      const i = document.createElement("i"); i.className = "hdia";
      i.style.left = (P[a - 1][0] + P[b - 1][0]) / 2 + "px"; i.style.top = (P[a - 1][1] + P[b - 1][1]) / 2 + "px"; tg.appendChild(i);
    });
    D.st.forEach(([x, y, lab, sm, side, cls], k) => {
      const n = document.createElement("b"); n.className = "stn " + (cls || ""); n.textContent = k + 1;
      n.style.left = x + "px"; n.style.top = y + "px"; tg.appendChild(n);
      const l = document.createElement("p"); l.className = "stl " + (cls || "");
      l.innerHTML = lab + (sm ? `<small>${sm}</small>` : "");
      const W = 1600, gap = 26;
      if (side === "l") Object.assign(l.style, { right: W - (x - gap) + "px", top: y + "px", transform: "translateY(-50%)", textAlign: "right" });
      else if (side === "r") Object.assign(l.style, { left: x + gap + "px", top: y + "px", transform: "translateY(-50%)", textAlign: "left" });
      else if (side === "u") Object.assign(l.style, { left: x + "px", top: y - gap + "px", transform: "translate(-50%,-100%)", textAlign: "center" });
      else Object.assign(l.style, { left: x + "px", top: y + gap + "px", transform: "translateX(-50%)", textAlign: "center" });
      tg.appendChild(l);
    });
    const f = tg.querySelector(".filex");
    if (f) { f.style.left = P[now - 1][0] + 26 + "px"; f.style.top = P[now - 1][1] + 8 + "px"; }
    const fl = tg.querySelector(".filel");
    if (fl) { fl.style.left = P[now - 1][0] + 80 + "px"; fl.style.top = P[now - 1][1] + 24 + "px"; }
  });

  // the rotation strip: .rot[data-crews='[[name, phase today]]'], 28 days (14 back, 14 ahead), on site while phase < 28 of 56
  document.querySelectorAll(".rot[data-crews]").forEach((r) => {
    const crews = JSON.parse(r.dataset.crews), rows = r.querySelector(".rows");
    crews.forEach(([name, ph]) => {
      const rw = document.createElement("div"); rw.className = "rw";
      const cl = document.createElement("div"); cl.className = "cl";
      for (let d = -14; d < 14; d++) {
        const on = (((ph + d) % 56) + 56) % 56 < 28, onNext = (((ph + d + 1) % 56) + 56) % 56 < 28;
        const i = document.createElement("i"); i.className = (on ? "on" : "") + (d === 0 && on !== onNext ? " flip" : ""); cl.appendChild(i);
      }
      rw.innerHTML = `<b>${name}</b>`; rw.appendChild(cl); rows.appendChild(rw);
    });
    const first = rows.querySelector(".cl"), today = document.createElement("i"); today.className = "today";
    const cells = first.children, a = cells[14].getBoundingClientRect(), base = rows.getBoundingClientRect();
    today.style.left = (a.left + a.right) / 2 - base.left - 1 + "px"; rows.appendChild(today);
  });


  // ---------------------------------------------------------------- furniture edition
  const J = (el, k) => { try { return JSON.parse(el.dataset[k] || "null"); } catch (e) { return null; } };
  const usd = (v) => "$" + Math.round(v).toLocaleString("en-US");
  const txt = (tag, attrs, s, parent) => { const e = mk(tag, attrs, parent); e.textContent = s; return e; };

  // board waste bar: .cells[data-pct] = 20 squares, one per 5%, the waste red
  document.querySelectorAll(".cells[data-pct]").forEach((c) => {
    const over = Math.round(num(c.dataset.pct) / 5);
    for (let i = 0; i < 20; i++) { const s = document.createElement("i"); s.className = i >= 20 - over ? "over" : "on"; c.appendChild(s); }
  });

  // the room set, exploded: .roomset[data-pieces] = [{k, name, share, state, doors}] ; drawn on a clear grid
  document.querySelectorAll(".roomset[data-pieces]").forEach((box) => {
    const P = J(box, "pieces") || [];
    const svg = mk("svg", { width: 448, height: 610, viewBox: "0 0 448 610", style: "position:absolute;left:0;top:34px;overflow:visible" }); box.appendChild(svg);
    // wardrobe top-left, bed top-right; mirror over dresser bottom-left; two nightstands bottom-right
    const pos = { wardrobe: [8, 30, 176, 250], bed: [218, 120, 222, 150], stand: [[232, 478, 88, 70], [344, 478, 88, 70]], mirror: [34, 364, 124, 92], dresser: [16, 470, 160, 90] };
    let si = 0;
    const lab = (x, y, name, share, cls, anchorRight) => {
      const l = document.createElement("span"); l.className = "lab" + (cls ? " " + cls : "");
      l.style.top = y + 34 + "px";
      if (anchorRight) l.style.right = 448 - anchorRight + "px"; else l.style.left = x + "px";
      l.innerHTML = name + (share != null ? "<small>" + share + "%</small>" : ""); box.appendChild(l);
    };
    P.forEach((p) => {
      let r = pos[p.k]; if (p.k === "stand") r = pos.stand[si++ % 2];
      if (!r) return;
      const [x, y, w, h] = r;
      const col = p.state === "swap" ? "#2563EB" : p.state === "short" ? "#C81E1E" : "#090B11";
      const g = mk("g", { fill: "none", stroke: col, "stroke-width": p.state === "swap" ? 3.2 : 2.4, "stroke-linejoin": "miter" }, svg);
      if (p.state === "short") g.setAttribute("stroke-dasharray", "8 6");
      const L = (d) => mk("path", { d }, g), R = (a1, b1, c1, d1) => mk("rect", { x: a1, y: b1, width: c1, height: d1 }, g);
      if (p.k === "wardrobe") {
        R(x, y, w, h); const n = p.doors || 4;
        for (let i = 1; i < n; i++) L("M" + (x + (w * i) / n) + " " + y + " V" + (y + h));
        for (let i = 0; i < n; i += 2) { const hx = x + (w * (i + 1)) / n; L("M" + (hx - 5) + " " + (y + h * 0.45) + " v22 M" + (hx + 5) + " " + (y + h * 0.45) + " v22"); }
        L("M" + (x + 6) + " " + (y + h) + " v12 M" + (x + w - 6) + " " + (y + h) + " v12");
      } else if (p.k === "bed") {
        R(x + 12, y - 50, w - 24, 110);                     // headboard
        R(x, y + 60, w, 34);                                 // mattress
        R(x, y + 94, w, 46);                                 // base
        L("M" + (x + 26) + " " + (y + 60) + " q" + (w / 4 - 20) + " -26 " + (w / 2 - 36) + " 0 M" + (x + w / 2 + 10) + " " + (y + 60) + " q" + (w / 4 - 20) + " -26 " + (w / 2 - 36) + " 0"); // pillows
        L("M" + (x + 8) + " " + (y + 140) + " v12 M" + (x + w - 8) + " " + (y + 140) + " v12");
      } else if (p.k === "stand") {
        R(x, y, w, h); L("M" + x + " " + (y + h / 2) + " H" + (x + w));
        L("M" + (x + w / 2 - 9) + " " + (y + h / 4) + " h18 M" + (x + w / 2 - 9) + " " + (y + (3 * h) / 4) + " h18");
      } else if (p.k === "dresser") {
        R(x, y, w, h); L("M" + x + " " + (y + h / 2) + " H" + (x + w));
        L("M" + (x + w / 2 - 12) + " " + (y + h / 4) + " h24 M" + (x + w / 2 - 12) + " " + (y + (3 * h) / 4) + " h24");
        L("M" + (x + 8) + " " + (y + h) + " v12 M" + (x + w - 8) + " " + (y + h) + " v12");
      } else if (p.k === "mirror") {
        R(x, y, w, h); R(x + 10, y + 10, w - 20, h - 20);
      }
      const cls = p.state === "swap" ? "sig" : p.state === "short" ? "al" : "";
      if (p.k === "mirror") lab(0, y + 26, p.name, p.share, cls, x + w + 170 > 448 ? 448 : x + w + 170);
      else if (p.k === "bed") lab(x, y + 162, p.name, p.share, cls);
      else if (p.k === "wardrobe") lab(x, y + h + 20, p.name, p.share, cls);
      else lab(x, y + h + (p.k === "dresser" ? 18 : 10), p.name, p.share, cls);
    });
  });

  // the kitchen plan from the measurement: .plan[data-plan] = {walls:[a,b], ceiling, window:[from,to] on wall a}
  document.querySelectorAll(".plan[data-plan]").forEach((box) => {
    const D = J(box, "plan"); if (!D) return;
    const BW = box.offsetWidth || 398, BH = (box.offsetHeight || 400) - 30;
    const a = D.walls[0], b = D.walls[1], s = Math.min((BW - 110) / a, (BH - 90) / b), ox = 20, oy = 56;
    const svg = mk("svg", { width: BW, height: BH, viewBox: "0 0 " + BW + " " + BH, style: "position:absolute;left:0;top:30px" }); box.appendChild(svg);
    const g = mk("g", { fill: "none", stroke: "#090B11", "stroke-width": 4 }, svg);
    mk("path", { d: "M" + ox + " " + oy + " H" + (ox + a * s) + " V" + (oy + b * s) }, g);
    const d = 60 * s;
    mk("path", { d: "M" + ox + " " + (oy + d) + " H" + (ox + a * s - d) + " V" + (oy + b * s), fill: "none", "stroke-width": 1.5, stroke: "#475569" }, svg);
    if (D.window) {
      const w0 = D.window[0], w1 = D.window[1];
      mk("path", { d: "M" + (ox + w0 * s) + " " + oy + " H" + (ox + w1 * s), stroke: "#F8FAFC", "stroke-width": 6 }, svg);
      mk("path", { d: "M" + (ox + w0 * s) + " " + (oy - 4) + " H" + (ox + w1 * s) + " M" + (ox + w0 * s) + " " + (oy + 4) + " H" + (ox + w1 * s), stroke: "#090B11", "stroke-width": 1.5 }, svg);
    }
    const dim = mk("g", { stroke: "#2563EB", "stroke-width": 1.5, fill: "none" }, svg);
    mk("path", { d: "M" + ox + " " + (oy - 26) + " H" + (ox + a * s) + " M" + ox + " " + (oy - 32) + " v12 M" + (ox + a * s) + " " + (oy - 32) + " v12" }, dim);
    mk("path", { d: "M" + (ox + a * s + 26) + " " + oy + " V" + (oy + b * s) + " M" + (ox + a * s + 20) + " " + oy + " h12 M" + (ox + a * s + 20) + " " + (oy + b * s) + " h12" }, dim);
    const T = (x, y, s2, anchor) => txt("text", { x, y, "text-anchor": anchor || "middle", "font-family": "Anu Mono, Anu Arabic, monospace", "font-size": 17, fill: "#1D4ED8", "font-weight": 500 }, s2, svg);
    T(ox + (a * s) / 2, oy - 38, a + " سم");
    T(ox + a * s + 34, oy + (b * s) / 2, b + " سم", "end");
    if (D.ceiling) txt("text", { x: ox, y: oy + b * s + 30, "text-anchor": "end", "font-size": 15, fill: "#475569" }, "ارتفاع السقف " + D.ceiling + " سم", svg);
  });

  // a cost stack: .stackx[data-parts] = [{label, v}] ; horizontal bar, or .vert = a column with labels beside it
  document.querySelectorAll(".stackx.ledger[data-parts]").forEach((sx) => {
    const parts = J(sx, "parts") || [], mx = Math.max(...parts.map((p) => num(p.v))) || 1, keys = sx.querySelector(".keys2");
    parts.forEach((p) => {
      const r = document.createElement("div");
      r.className = "lrow" + (/مشتراة/.test(p.label) ? " bought" : /هامش/.test(p.label) ? " margin" : "");
      const note = /مشتراة/.test(p.label) ? "<small>مو من صنع المعمل</small>" : "";
      r.innerHTML = "<span class=\"ll\">" + p.label + note + "</span><span class=\"lb\"><i style=\"width:" + (num(p.v) / mx) * 100 + "%\"></i></span><span class=\"lv\">" + usd(num(p.v)) + "</span>";
      keys.appendChild(r);
    });
  });
  document.querySelectorAll(".stackx:not(.ledger)[data-parts]").forEach((sx) => {
    const parts = J(sx, "parts") || [], tot = parts.reduce((acc, p) => acc + num(p.v), 0) || 1;
    const bar = sx.querySelector(".bar"), keys = sx.querySelector(".keys2"), vert = sx.classList.contains("vert");
    parts.forEach((p) => {
      const f = num(p.v) / tot, seg = document.createElement("i");
      if (vert) seg.style.height = f * 100 + "%"; else seg.style.width = f * 100 + "%";
      if (!vert && f > 0.07) seg.textContent = usd(num(p.v));
      bar.appendChild(seg);
      const kl = document.createElement("span");
      if (vert) { kl.innerHTML = "<b>" + p.label + "</b> <span class=\"num\">" + usd(num(p.v)) + "</span>"; kl.style.flex = "0 0 " + f * 100 + "%"; kl.style.display = "flex"; kl.style.alignItems = "center"; }
      else { kl.style.width = f * 100 + "%"; kl.textContent = f > 0.07 ? p.label : ""; if (f <= 0.07) { const sm = sx.querySelector(".small") || (() => { const e = document.createElement("p"); e.className = "small"; sx.insertBefore(e, sx.querySelector(".eq")); return e; })(); sm.innerHTML += (sm.innerHTML ? " · " : "") + p.label + " <span class=\"num\">" + usd(num(p.v)) + "</span>"; } }
      keys.appendChild(kl);
    });
  });

  // deposits and balances per order: .dbars[data-rows] = [{name, paid, total, late}]
  document.querySelectorAll(".dbars[data-rows]").forEach((b) => {
    (J(b, "rows") || []).slice(0, Number(b.dataset.max || 99)).forEach((r) => {
      const row = document.createElement("div"); row.className = "dbar";
      const f = Math.max(0, Math.min(1, num(r.paid) / num(r.total)));
      row.innerHTML = "<span>" + r.name + "</span><span class=\"b\"><i style=\"width:" + f * 100 + "%\"></i></span><span class=\"v" + (r.late ? " alarm" : "") + "\">" + usd(num(r.total) - num(r.paid)) + "</span>";
      b.appendChild(row);
    });
  });


  // quantity grids: .qgrid[data-n][data-red][data-cols] = n squares, the last `red` in red
  document.querySelectorAll(".qgrid[data-n]").forEach((g) => {
    const n = Math.round(num(g.dataset.n)), red = Math.round(num(g.dataset.red || 0)), cols = Number(g.dataset.cols || 18);
    g.style.gridTemplateColumns = "repeat(" + Math.min(n, cols) + ", 26px)";
    for (let i = 0; i < n; i++) { const c = document.createElement("i"); c.className = i >= n - red ? "over" : "on"; g.appendChild(c); }
  });
  // remade doors: .doors[data-n]
  document.querySelectorAll(".doors[data-n]").forEach((d) => {
    for (let i = 0; i < Math.round(num(d.dataset.n)); i++) {
      const s = mk("svg", { viewBox: "0 0 44 62" }); d.appendChild(s);
      const g = mk("g", { fill: "none", stroke: "#F87171", "stroke-width": 2.2 }, s);
      mk("rect", { x: 2, y: 2, width: 40, height: 58 }, g); mk("rect", { x: 8, y: 8, width: 28, height: 46, "stroke-width": 1.2 }, g); mk("path", { d: "M34 28 v8" }, g);
    }
  });
  // the dollar gap: .gapruler[data-a][data-b] on a line from 125,000 to 160,000 per 100$
  document.querySelectorAll(".gapruler[data-a]").forEach((r) => {
    const A = num(r.dataset.a), B = num(r.dataset.b), W = r.offsetWidth || 600, lo = 125000, hi = 160000;
    const X = (v) => W - ((v - lo) / (hi - lo)) * W; // RTL: low on the right
    const s = mk("svg", { viewBox: "0 0 " + W + " 64" }); r.appendChild(s);
    mk("path", { d: "M0 22 H" + W, stroke: "rgba(255,255,255,.35)", "stroke-width": 2 }, s);
    mk("path", { d: "M" + X(B) + " 22 H" + X(A), stroke: "#F87171", "stroke-width": 6 }, s);
    [[A, "رسمي", "#fff"], [B, "بالسوق", "#F87171"]].forEach(([v, l, col]) => {
      mk("rect", { x: X(v) - 7, y: 15, width: 14, height: 14, fill: col }, s);
      const tx = mk("text", { x: X(v), y: 54, "text-anchor": "middle", "font-size": 16, fill: col, "font-family": "Anu Mono, Anu Arabic, monospace" }, s);
      tx.textContent = v.toLocaleString("en-US") + " " + l;
    });
  });

  // day cells: .grid147[data-n][data-term] one square a day, the term white, past due red
  document.querySelectorAll(".grid147").forEach((g) => {
    const n = num(g.dataset.n), term = num(g.dataset.term);
    for (let i = 0; i < n; i++) { const c = document.createElement("i"); c.className = i < term ? "due" : "over"; g.appendChild(c); }
  });

  // the day ruler: .day[data-from][data-to]; .ev/.hr/.took[data-t="HH:MM"] placed by time (right = start of day)
  document.querySelectorAll(".day").forEach((day) => {
    const hm = (s) => { const m = String(s).match(/(\d{1,2}):(\d{2})/); return m ? Number(m[1]) + Number(m[2]) / 60 : NaN; };
    const t0 = hm(day.dataset.from), t1 = hm(day.dataset.to), W = num(day.dataset.w);
    const X = (t) => ((t - t0) / (t1 - t0)) * W;
    day.querySelectorAll("[data-t]").forEach((e) => { const t = hm(e.dataset.t); if (!isNaN(t)) e.style.right = X(t) + "px"; });
    const took = day.querySelector(".took[data-a][data-b]");
    if (took) {
      const a = hm(took.dataset.a), b = hm(took.dataset.b), mins = Math.round((b - a) * 60);
      took.style.right = X((a + b) / 2) + "px";
      took.querySelector(".m").textContent = mins;
    }
  });
})();
/* PART ex-dlv START (tools_parts.py) */
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
/* PART ex-dlv END */
