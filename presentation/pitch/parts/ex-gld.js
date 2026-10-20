// ---------------------------------------------------------------- gold edition (30 Sep): the thread, the set, karat bars, the loss bar, the scale
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const mk = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };
  const num = (v) => Number(String(v).replace(/[^\d.\-]/g, ""));
  const J = (el, k) => { try { return JSON.parse(el.dataset[k] || "null"); } catch (e) { return null; } };
  const g1 = (v) => (Math.round(num(v) * 10) / 10).toFixed(1);
  let uid = 0;
  // a metal gradient in this svg (userSpace, horizontal by default)
  function metal(svg, x1, y1, x2, y2) {
    const id = "gm" + ++uid, defs = svg.querySelector("defs") || mk("defs", {}, svg);
    const lg = mk("linearGradient", { id, gradientUnits: "userSpaceOnUse", x1, y1, x2, y2 }, defs);
    const ink = !!(svg.closest && svg.closest(".cover,.dark,.close2"));   // on paper the highlight stays deeper, so the line holds on white
    (ink ? [[0, "#8A6A22"], [0.22, "#B8923C"], [0.44, "#F1D78A"], [0.56, "#D8B866"], [0.72, "#C9A44C"], [1, "#8A6A22"]]
         : [[0, "#6E5214"], [0.25, "#A5822C"], [0.45, "#D6B45A"], [0.6, "#B8923C"], [1, "#7A5C12"]]).forEach(([o, c]) => mk("stop", { offset: o, "stop-color": c }, lg));
    return `url(#${id})`;
  }
  // the same metal on every shape (objectBoundingBox), for bars that must look alike
  function metalBox(svg) {
    const id = "gmb" + ++uid, defs = svg.querySelector("defs") || mk("defs", {}, svg);
    const lg = mk("linearGradient", { id, x1: 0, y1: 0, x2: 1, y2: 0 }, defs);
    [[0, "#6E5214"], [0.3, "#A5822C"], [0.5, "#D6B45A"], [0.7, "#B8923C"], [1, "#7A5C12"]].forEach(([o, c]) => mk("stop", { offset: o, "stop-color": c }, lg));
    return `url(#${id})`;
  }
  function blurF(svg, sd) {
    const id = "gb" + ++uid, defs = svg.querySelector("defs") || mk("defs", {}, svg);
    const f = mk("filter", { id, x: "-50%", y: "-50%", width: "200%", height: "200%" }, defs); mk("feGaussianBlur", { stdDeviation: sd }, f);
    return `url(#${id})`;
  }
  // Catmull-Rom through points → cubic path segments [[p0,c1,c2,p1]]
  function spline(P, k = 0.5) {
    const seg = [];
    for (let i = 0; i < P.length - 1; i++) {
      const p0 = P[i - 1] || P[i], p1 = P[i], p2 = P[i + 1], p3 = P[i + 2] || p2;
      const c1 = [p1[0] + (p2[0] - p0[0]) * k / 3, p1[1] + (p2[1] - p0[1]) * k / 3];
      const c2 = [p2[0] - (p3[0] - p1[0]) * k / 3, p2[1] - (p3[1] - p1[1]) * k / 3];
      seg.push([p1, c1, c2, p2]);
    }
    return seg;
  }
  const d1 = (s) => `M${s[0][0]},${s[0][1]} C${s[1][0]},${s[1][1]} ${s[2][0]},${s[2][1]} ${s[3][0]},${s[3][1]}`;
  // the thread: tapering metal line through P; dust under the points listed in `dust`; glow on ink
  function thread(svg, P, o) {
    const segs = spline(P), n = segs.length, w0 = o.w0 || 7, w1 = o.w1 || 3.5;
    const xs = P.map((p) => p[0]), grad = metal(svg, Math.min(...xs), 0, Math.max(...xs), 0);
    if (o.ink) {
      const glow = mk("g", { filter: blurF(svg, 7), opacity: 0.55 }, svg);
      segs.forEach((s, i) => mk("path", { d: d1(s), fill: "none", stroke: "#F1D78A", "stroke-width": w0 + 8 - (i / n) * 4, "stroke-linecap": "round" }, glow));
    }
    segs.forEach((s, i) => {
      const w = w0 - (w0 - w1) * (i / Math.max(1, n - 1));
      mk("path", { d: d1(s), fill: "none", stroke: grad, "stroke-width": w, "stroke-linecap": "round" }, svg);
      mk("path", { d: d1(s), fill: "none", stroke: "#FFF4CF", "stroke-width": Math.max(0.8, w * 0.18), opacity: o.ink ? 0.7 : 0.55, "stroke-linecap": "round", transform: `translate(0,${-w * 0.22})` }, svg);
    });
    (o.dust || []).forEach((k, j) => {
      const p = P[k]; if (!p) return;
      const rnd = (a) => { const x = Math.sin((k + 1) * 12.9898 + a * 78.233) * 43758.5453; return x - Math.floor(x); };
      for (let q = 0; q < (o.dustN || 7); q++) {
        const dx = (rnd(q) - 0.5) * 26, dy = 10 + q * 7 + rnd(q + 9) * 6, r = 1.1 + rnd(q + 3) * 1.6;
        mk("circle", { cx: p[0] + dx, cy: p[1] + dy, r, class: "gdust", opacity: (1 - q / (o.dustN || 7)) * 0.9 }, svg);
      }
    });
    return grad;
  }

  // .gthr[data-pts='[[x,y],…]'][data-w0][data-w1][data-dust="i j"][data-ink]  (an absolutely placed <svg>)
  document.querySelectorAll("svg.gthr[data-pts]").forEach((svg) => {
    const P = J(svg, "pts") || [];
    thread(svg, P, { w0: num(svg.dataset.w0 || 7), w1: num(svg.dataset.w1 || 3.5), ink: svg.dataset.ink != null, dust: (svg.dataset.dust || "").split(" ").filter(Boolean).map(Number), dustN: num(svg.dataset.dustn || 7) });
  });

  // the cover map: .map[data-thread="k1 k2 …"] draws the thread through those sites (after the base .map renderer placed them)
  document.querySelectorAll(".map[data-thread]").forEach((map) => {
    const svg = map.querySelector("svg.lines"), pos = {};
    map.querySelectorAll(".site").forEach((s) => (pos[s.dataset.k] = [num(s.dataset.x), num(s.dataset.y)]));
    const P = map.dataset.thread.split(" ").map((k) => pos[k]).filter(Boolean);
    thread(svg, P, { w0: 7, w1: 3, ink: true, dust: (map.dataset.dust || "").split(" ").filter(Boolean).map(Number), dustN: 8 });
    if (map.dataset.thread2) {
      const Q = map.dataset.thread2.split(" ").map((k) => pos[k]).filter(Boolean);
      if (Q.length === 2) {
        const g2 = metal(svg, Math.min(Q[0][0], Q[1][0]), 0, Math.max(Q[0][0], Q[1][0]), 0);
        mk("path", { d: `M${Q[0][0]},${Q[0][1]} Q${(Q[0][0] + Q[1][0]) / 2},${Math.max(Q[0][1], Q[1][1]) + 46} ${Q[1][0]},${Q[1][1]}`, fill: "none", stroke: g2, "stroke-width": 3.2, "stroke-dasharray": "1 7", "stroke-linecap": "round" }, svg);
      }
    }
    map.querySelectorAll(".glab[data-at]").forEach((l) => {
      const [a, b] = l.dataset.at.split("-").map((k) => pos[k]); const t = num(l.dataset.f || 0.5);
      const x = a[0] + (b[0] - a[0]) * t, y = a[1] + (b[1] - a[1]) * t;
      l.style.left = x + num(l.dataset.dx || 0) + "px"; l.style.top = y + num(l.dataset.dy || 0) + "px";
    });
  });

  // the route in gold: .tangle.gt[data-dust="6 7 8"] : the done part becomes a thinning metal line, dust under the workshop stations
  document.querySelectorAll(".tangle.gt").forEach((tg) => {
    const svg = tg.querySelector("svg"), D = JSON.parse(tg.querySelector(".tdata").textContent);
    const pl = svg && svg.querySelector("polyline"); if (!pl) return; pl.remove();
    const P = D.st.slice(0, D.now).map((st) => [st[0], st[1]]), n = P.length - 1, w0 = 6.5, w1 = 2.6;
    const xs = P.map((q) => q[0]), grad = metal(svg, Math.min(...xs), 0, Math.max(...xs), 0);
    for (let i = 0; i < n; i++) {
      const w = w0 - (w0 - w1) * (i / Math.max(1, n - 1));
      mk("line", { x1: P[i][0], y1: P[i][1], x2: P[i + 1][0], y2: P[i + 1][1], stroke: grad, "stroke-width": w, "stroke-linecap": "round" }, svg);
    }
    (tg.dataset.dust || "").split(" ").filter(Boolean).map((k) => Number(k) - 1).forEach((k) => {
      const q = P[k]; if (!q) return;
      for (let j = 0; j < 7; j++) mk("circle", { cx: q[0] + ((j * 23) % 34) - 17, cy: q[1] + (q[1] > 450 ? -1 : 1) * (26 + j * 8), r: 1.4 + (j % 3) * 0.5, class: "gdust", opacity: 0.9 - j * 0.1 }, svg);
    });
  });

  // the bride's set in gold line art: .set4[data-pieces='[{k:necklace|bracelet|ring|earrings, name, w}]'][data-size]
  const PIECE = {
    necklace(g, s, grad) {
      mk("path", { d: `M${-0.42 * s},${-0.36 * s} C${-0.40 * s},${0.20 * s} ${0.40 * s},${0.20 * s} ${0.42 * s},${-0.36 * s}`, fill: "none", stroke: grad, "stroke-width": s * 0.035, "stroke-dasharray": `${s * 0.05} ${s * 0.018}` }, g);
      mk("path", { d: `M${-0.30 * s},${-0.30 * s} C${-0.28 * s},${0.08 * s} ${0.28 * s},${0.08 * s} ${0.30 * s},${-0.30 * s}`, fill: "none", stroke: grad, "stroke-width": s * 0.02 }, g);
      const py = 0.05 * s;
      mk("path", { d: `M0,${py} l${-0.09 * s},${0.13 * s} l${0.09 * s},${0.17 * s} l${0.09 * s},${-0.17 * s} z`, fill: "none", stroke: grad, "stroke-width": s * 0.03, "stroke-linejoin": "miter" }, g);
      mk("path", { d: `M0,${py} v${0.30 * s} M${-0.09 * s},${py + 0.13 * s} h${0.18 * s}`, fill: "none", stroke: grad, "stroke-width": s * 0.012, opacity: 0.8 }, g);
      [-0.19, 0.19].forEach((x) => mk("path", { d: `M${x * s},${-0.02 * s} l${-0.03 * s},${0.07 * s} l${0.03 * s},${0.05 * s} l${0.03 * s},${-0.05 * s} z`, fill: "none", stroke: grad, "stroke-width": s * 0.02 }, g));
    },
    bracelet(g, s, grad) {
      mk("ellipse", { cx: 0, cy: 0, rx: 0.40 * s, ry: 0.26 * s, fill: "none", stroke: grad, "stroke-width": s * 0.05 }, g);
      mk("ellipse", { cx: 0, cy: 0.04 * s, rx: 0.40 * s, ry: 0.26 * s, fill: "none", stroke: grad, "stroke-width": s * 0.015, opacity: 0.7 }, g);
      for (let i = 0; i < 14; i++) { const a = Math.PI * (0.08 + (i / 13) * 0.84); const x = -Math.cos(a) * 0.40 * s, y = Math.sin(a) * 0.26 * s; mk("line", { x1: x - 0.012 * s, y1: y - 0.03 * s, x2: x + 0.012 * s, y2: y + 0.03 * s, stroke: "#8A6A22", "stroke-width": s * 0.01 }, g); }
    },
    ring(g, s, grad) {
      mk("ellipse", { cx: 0, cy: 0.06 * s, rx: 0.26 * s, ry: 0.28 * s, fill: "none", stroke: grad, "stroke-width": s * 0.07 }, g);
      mk("ellipse", { cx: 0, cy: 0.06 * s, rx: 0.19 * s, ry: 0.21 * s, fill: "none", stroke: "#8A6A22", "stroke-width": s * 0.012, opacity: 0.7 }, g);
      mk("path", { d: `M${-0.10 * s},${-0.26 * s} h${0.20 * s} l${0.04 * s},${0.06 * s} h${-0.28 * s} z`, fill: "none", stroke: grad, "stroke-width": s * 0.03, "stroke-linejoin": "miter" }, g);
      mk("path", { d: `M${-0.05 * s},${0.30 * s} q${0.05 * s},${-0.03 * s} ${0.10 * s},0`, fill: "none", stroke: "#8A6A22", "stroke-width": s * 0.012 }, g);
    },
    earrings(g, s, grad) {
      [-0.17, 0.17].forEach((x) => {
        mk("path", { d: `M${x * s},${-0.36 * s} q${0.07 * s},0 ${0.05 * s},${0.09 * s}`, fill: "none", stroke: grad, "stroke-width": s * 0.02 }, g);
        mk("circle", { cx: x * s, cy: -0.19 * s, r: 0.05 * s, fill: "none", stroke: grad, "stroke-width": s * 0.025 }, g);
        mk("path", { d: `M${x * s},${-0.13 * s} c${-0.11 * s},${0.13 * s} ${-0.09 * s},${0.30 * s} 0,${0.33 * s} c${0.09 * s},${-0.03 * s} ${0.11 * s},${-0.20 * s} 0,${-0.33 * s} z`, fill: "none", stroke: grad, "stroke-width": s * 0.03 }, g);
        mk("path", { d: `M${x * s},${-0.07 * s} v${0.22 * s}`, fill: "none", stroke: "#8A6A22", "stroke-width": s * 0.01, opacity: 0.7 }, g);
      });
    },
  };
  document.querySelectorAll(".set4[data-pieces]").forEach((box) => {
    const P = J(box, "pieces") || [], W = box.offsetWidth, H = box.offsetHeight, s = num(box.dataset.size || 120);
    const svg = mk("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}` }); box.prepend(svg);
    const dark = !!box.closest(".cover,.dark,.close2");
    const grad = metal(svg, 0, 0, W, H * 0.4);
    const gap = W / P.length, cy = num(box.dataset.cy || s * 0.55);
    if (dark) { const glow = mk("g", { filter: blurF(svg, 9), opacity: 0.5 }, svg); P.forEach((p, i) => { const g = mk("g", { transform: `translate(${W - gap * (i + 0.5)},${cy})` }, glow); (PIECE[p.k] || PIECE.ring)(g, s, "#F1D78A"); }); }
    P.forEach((p, i) => {
      const cx = W - gap * (i + 0.5), g = mk("g", { transform: `translate(${cx},${cy})` }, svg);
      (PIECE[p.k] || PIECE.ring)(g, s, grad);
      if (p.name) {
        const l = document.createElement("p"); l.className = "pl"; l.style.left = cx + "px"; l.style.top = cy + s * 0.46 + "px";
        l.innerHTML = `<b>${p.name}</b>` + (p.w != null ? `<span class="num">${g1(p.w)}</span> غرام` : ""); box.appendChild(l);
      }
    });
  });

  // karat bars: .kbar[data-k='{"a":{"k":18,"g":28.4,"lb":"…"},"b":{"k":21,"g":24.34,"lb":"…"}}'] > .br.a, .br.b (filled here) + .same
  document.querySelectorAll(".kbar[data-k]").forEach((box) => {
    const D = J(box, "k"); if (!D) return;
    const maxG = Math.max(D.a.g, D.b.g), tw = box.querySelector(".br .tr").offsetWidth;
    ["a", "b"].forEach((key) => {
      const r = D[key], br = box.querySelector(".br." + key), tr = br.querySelector(".tr"), fine = r.g * r.k / 24;
      const wf = (fine / maxG) * tw, wa = ((r.g - fine) / maxG) * tw;
      tr.innerHTML = `<span class="fn" style="width:${wf}px"><span class="fl">ذهب صافي <span class="num">${g1(fine)}</span> غرام</span></span><span class="al" style="width:${wa}px"></span>`;
    });
    const same = box.querySelector(".same");
    if (same) { const fine = D.a.g * D.a.k / 24, x = (fine / maxG) * tw; same.innerHTML = `<i style="right:0"></i><i style="right:${x}px"></i><span class="sm" style="right:${x + 10}px">نفس الذهب الصافي بالكسر</span>`; }
  });

  // the workshop's loss per stage: .lbar[data-d='{"issued","stages":[{"n","out","tol"}],"returned","dust"}'][data-top][data-h]
  document.querySelectorAll(".lbar[data-d]").forEach((box) => {
    const D = J(box, "d"); if (!D) return;
    const W = box.offsetWidth, top = num(box.dataset.top || 44), H = num(box.dataset.h || 140), M = 170;
    const svg = mk("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, style: `top:${top}px` }); box.appendChild(svg);
    const n = D.stages.length, xR = W - M, xL = M, col = (xR - xL) / n, ty = 14, base = H - 12;
    const grad = metal(svg, xL, 0, xR, 0), gbox = metalBox(svg);
    let prev = D.issued;
    const rows = D.stages.map((st) => { const lost = prev - st.out, allowed = prev * (st.tol || 0) / 100; prev = st.out; return { n: st.n, lost, allowed, over: lost > allowed + 1e-9 }; });
    const mx = Math.max(...rows.map((r) => Math.max(r.lost, r.allowed))) * 1.15, sc = (base - 40) / mx;
    rows.forEach((r, i) => {
      const x1 = xR - col * i, x0 = xR - col * (i + 1), cx = (x0 + x1) / 2, w = 11 - i * 1.4;
      mk("line", { x1: x1, y1: ty, x2: x0, y2: ty, stroke: grad, "stroke-width": w, "stroke-linecap": "butt" }, svg);
      for (let j = 0; j < 5; j++) mk("circle", { cx: x0 + 4 + ((j * 13) % 22), cy: ty + 12 + j * 4, r: 1.5, class: "gdust", opacity: 0.85 - j * 0.14 }, svg);
      const ha = r.allowed * sc, hl = r.lost * sc;
      mk("rect", { x: cx - 30, y: base - ha, width: 60, height: ha, fill: "none", stroke: "#090B11", "stroke-width": 1.4, "stroke-dasharray": "4 4" }, svg);
      mk("rect", { x: cx - 16, y: base - hl, width: 32, height: hl, fill: r.over ? "#C81E1E" : gbox }, svg);
      const lab = document.createElement("p"); lab.className = "stg";
      lab.style.cssText = `left:${x0}px;width:${col}px;top:${top + H + 6}px`;
      lab.innerHTML = `<b>${r.n}</b><span class="v num${r.over ? " al" : ""}">−${r.lost.toFixed(2)}</span><small>المسموح <span class="num">${r.allowed.toFixed(2)}</span></small>`;
      box.appendChild(lab);
    });
    mk("line", { x1: xL - 10, y1: base, x2: xR + 10, y2: base, stroke: "#94A3B8", "stroke-width": 1 }, svg);
    const eR = document.createElement("p"); eR.className = "ends"; eR.style.cssText = `right:0;top:${top + ty - 12}px`;
    eR.innerHTML = `طلع <b class="num">${g1(D.issued)}</b> غرام`; box.appendChild(eR);
    const eL = document.createElement("p"); eL.className = "ends"; eL.style.cssText = `left:0;top:${top + ty - 12}px`;
    eL.innerHTML = `رجع <b class="num">${g1(D.returned)}</b>` + (num(D.dust) > 0 ? `، وتراب <b class="num">${g1(D.dust)}</b>` : ""); box.appendChild(eL);
  });

  // the balance scale: .scl[data-tilt="deg"] > .pan.l, .pan.r (labels), .dif  (beam 0..W, pivot centre)
  document.querySelectorAll(".scl").forEach((box) => {
    const W = box.offsetWidth, H = box.offsetHeight, t = (num(box.dataset.tilt || 0) * Math.PI) / 180, dark = !!box.closest(".cover,.dark,.close2");
    const svg = mk("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}` }); box.prepend(svg);
    const ink = dark ? "#BFDBFE" : "#090B11", cx = W / 2, py = 40, L = W / 2 - 40;
    const grad = metal(svg, 0, 0, W, 0);
    mk("path", { d: `M${cx},${py} V${H - 16} M${cx - 60},${H - 16} H${cx + 60} M${cx - 30},${H - 16} l12,-14 h36 l12,14`, fill: "none", stroke: ink, "stroke-width": 2.5 }, svg);
    mk("rect", { x: cx - 7, y: py - 7, width: 14, height: 14, fill: ink }, svg);
    const ex = Math.cos(t) * L, ey = Math.sin(t) * L;
    const lx = cx - ex, ly = py + ey, rx = cx + ex, ry = py - ey;       // positive tilt: left pan down
    mk("line", { x1: lx, y1: ly, x2: rx, y2: ry, stroke: grad, "stroke-width": 6, "stroke-linecap": "square" }, svg);
    [[lx, ly], [rx, ry]].forEach(([x, y]) => {
      mk("path", { d: `M${x},${y} L${x - 46},${y + 70} M${x},${y} L${x + 46},${y + 70}`, stroke: ink, "stroke-width": 1.5, fill: "none", opacity: 0.8 }, svg);
      mk("path", { d: `M${x - 58},${y + 70} H${x + 58} Q${x},${y + 104} ${x - 58},${y + 70} Z`, fill: dark ? "rgba(241,215,138,.10)" : "#FBF6E8", stroke: grad, "stroke-width": 3 }, svg);
    });
    const pl = box.querySelector(".pan.l"), pr = box.querySelector(".pan.r"), df = box.querySelector(".dif");
    if (pl) { pl.style.left = lx + "px"; pl.style.top = ly + 110 + "px"; }
    if (pr) { pr.style.left = rx + "px"; pr.style.top = ry + 110 + "px"; }
    if (df) { df.style.left = cx + "px"; df.style.top = "0px"; }
  });

  // the repair bag: .rbag (zip bag outline drawn here; the label is HTML)
  document.querySelectorAll(".rbag").forEach((b) => {
    const W = b.offsetWidth, H = b.offsetHeight, svg = mk("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}` }); b.prepend(svg);
    mk("rect", { x: 6, y: 20, width: W - 12, height: H - 26, fill: "rgba(241,245,249,.55)", stroke: "#1E293B", "stroke-width": 1.8 }, svg);
    mk("path", { d: `M6,40 H${W - 6} M6,46 H${W - 6}`, stroke: "#1E293B", "stroke-width": 1.4 }, svg);
    mk("rect", { x: W / 2 - 10, y: 12, width: 20, height: 12, fill: "#fff", stroke: "#1E293B", "stroke-width": 1.4 }, svg);
    const g = mk("g", { transform: `translate(${W / 2},${H - 50})` }, svg), grad = metal(svg, 0, 0, W, 0);
    mk("ellipse", { cx: 0, cy: 0, rx: 44, ry: 18, fill: "none", stroke: grad, "stroke-width": 5 }, g);
    if (b.dataset.clean == null) mk("path", { d: "M-8,-19 l6,6 M4,-18 l-5,7", stroke: "#C81E1E", "stroke-width": 2 }, g);
  });

  // gram dots: .gdots[data-n][data-au][data-red][data-cols] : n squares; the first `au` metal (kept), the last `red` red (lost)
  document.querySelectorAll(".gdots[data-n]").forEach((g) => {
    const n = num(g.dataset.n), au = num(g.dataset.au || 0), red = num(g.dataset.red || 0), cols = num(g.dataset.cols || 25);
    g.style.gridTemplateColumns = `repeat(${cols}, max-content)`;
    for (let i = 0; i < n; i++) { const i2 = document.createElement("i"); if (i < au) i2.className = "au"; if (i >= n - red) i2.className = "r"; g.appendChild(i2); }
  });

  // the gram ledger strip: .gled[data-rows='[{name, g, late}]'][data-max] : + owed to us (left of the axis), − we owe (right)
  document.querySelectorAll(".gled[data-rows]").forEach((b) => {
    const R = J(b, "rows") || [], max = num(b.dataset.max || Math.max(...R.map((r) => Math.abs(num(r.g))))), ol = b.querySelector("ol");
    R.forEach((r) => {
      const v = num(r.g), w = (Math.abs(v) / max) * 50;
      const li = document.createElement("li");
      li.innerHTML = `<span>${r.name}</span><span class="bar"><i class="${v < 0 ? "neg" : ""} ${r.late ? "late" : ""}" style="${v < 0 ? `left:50%;width:${w}%` : `right:50%;width:${w}%`}"></i></span><b class="${r.late ? "al" : ""}">${v > 0 ? "+" : ""}${(b.dataset.int != null || Math.abs(v) >= 100) ? Math.round(v).toLocaleString("en-US") : g1(v)}</b>`;
      ol.appendChild(li);
    });
  });

  // the order slip's sketch: .oslip .sk (a pen drawing of the set; wobbly on purpose)
  document.querySelectorAll(".oslip .sk").forEach((sk) => {
    const W = sk.offsetWidth, H = sk.offsetHeight, svg = mk("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}` }); sk.appendChild(svg);
    const pen = { fill: "none", stroke: "#8A6A22", "stroke-width": 1.9, "stroke-linecap": "round" };   // the set in gold; the hand stays ink
    const cx = W * 0.62;
    mk("path", Object.assign({ d: `M${cx - 70},8 C${cx - 66},${H - 20} ${cx + 64},${H - 22} ${cx + 70},10` }, pen), svg);
    mk("path", Object.assign({ d: `M${cx - 2},${H - 34} l-9,13 l10,15 l9,-14 z` }, pen), svg);
    mk("path", Object.assign({ d: `M${cx - 40},${H - 46} l-5,8 l5,6 l5,-7 z M${cx + 38},${H - 47} l-4,8 l5,6 l4,-7 z` }, pen), svg);
    mk("ellipse", Object.assign({ cx: W * 0.16, cy: H * 0.46, rx: 22, ry: 23 }, pen), svg);
    mk("path", Object.assign({ d: `M${W * 0.16 - 8},${H * 0.46 - 24} l8,-7 l8,7` }, pen), svg);
    mk("path", Object.assign({ d: `M${W * 0.30},${H * 0.18} l-10,14 M${W * 0.30},${H * 0.18} l6,16`, opacity: 0.6 }, pen), svg);
  });

  // the gold route on the wholesale map: .zmap[data-bal='[{city, name, g, late, dx, dy}]'] (after the base zmap renderer)
  if (window.IRQ) document.querySelectorAll(".zmap[data-bal]").forEach((box) => {
    const B = J(box, "bal") || [], IRQ = window.IRQ, W = num(box.dataset.w), s = W / IRQ.w, svg = box.querySelector("svg.geo"), top = 34;
    if (!B.length) return;
    const grad = metal(svg, 0, 0, W, 0), gbox = metalBox(svg), mx = Math.max(...B.map((b) => Math.abs(num(b.g))));
    const bx = IRQ.cities.baghdad[0] * s, by = IRQ.cities.baghdad[1] * s, g = mk("g", {}, svg);
    B.forEach((b) => {
      const c = IRQ.cities[b.city]; if (!c) return;
      const x = c[0] * s, y = c[1] * s, v = Math.abs(num(b.g)), r = 4 + 8 * Math.sqrt(v / mx);
      mk("line", { x1: bx, y1: by, x2: x, y2: y, stroke: grad, "stroke-width": 1.2 + 2.6 * (v / mx), "stroke-linecap": "round" }, g);
      const lx = x + num(b.dx || 0), ly = y + num(b.dy || 0);
      if (b.dx || b.dy) mk("line", { x1: x, y1: y, x2: lx, y2: ly, stroke: "#64748B", "stroke-width": 1 }, g);
      mk("circle", { cx: x, cy: y, r, fill: gbox, stroke: b.late ? "#C81E1E" : "#6E5214", "stroke-width": b.late ? 2.6 : 1.2 }, g);
      if (!b.name) return;                         // a dot only
      const l = document.createElement("span"); l.className = "zlab" + (b.late ? " al" : "");
      l.style.left = lx + "px"; l.style.top = ly + top + "px";
      l.innerHTML = `${b.name} <span class="num">${Math.round(v).toLocaleString("en-US")}</span> غ`;
      box.appendChild(l);
    });
  });

  // the provinces on the ladder's small map in gold (.minimap.au)
  document.querySelectorAll(".minimap.au svg line").forEach((l) => { l.setAttribute("stroke", "#A5822C"); l.setAttribute("stroke-width", 2.6); });

  // money bars on the cost cards: .gbar[data-total][data-part] : the lost part in red at the end
  document.querySelectorAll(".gbar[data-total]").forEach((b) => {
    const t = Math.abs(num(b.dataset.total)), p = Math.abs(num(b.dataset.part));
    const i = document.createElement("i"); i.style.width = (t ? Math.min(100, (p / t) * 100) : 0) + "%"; b.appendChild(i);
  });

  // the week's workshop orders as a routing slip: .dueslip[data-rows='[{n, w, g, due, late, now}]']
  document.querySelectorAll(".dueslip[data-rows]").forEach((sl) => {
    const R = J(sl, "rows") || [], ol = sl.querySelector("ol");
    R.forEach((r) => {
      const li = document.createElement("li"); li.className = r.late ? "late" : r.now ? "now" : r.next ? "next" : "";
      li.innerHTML = `<b class="nd"></b><span class="rl">${r.n}<small class="ar">${r.w}، <span class="num">${g1(r.g)}</span> غ، ${r.due}</small></span>`;
      ol.appendChild(li);
    });
  });
})();
