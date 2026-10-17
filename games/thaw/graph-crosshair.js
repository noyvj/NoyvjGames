// G-16: the mini-graph crosshair. game.py gives every named graph its points as data-pts
// ([x, y, "Round 3: +3.0°, dampening 8%"]) plus a hidden cross line and dot. Hovering (or touching)
// moves them and fills a small readout above the graph; focusing a graph and using the left and right
// arrow keys (Home and End jump to the ends) does the same, and the readout is a status region so a
// screen reader announces it. Plain JS because the graph is re-drawn on every render.
(function () {
  const SELECTOR = ".mini-temp-graph-svg[data-pts]";
  function points(svg) {
    try { return JSON.parse(svg.getAttribute("data-pts") || "[]"); } catch (e) { return []; }
  }
  function readoutFor(svg) {
    const host = svg.parentElement;
    let out = host.querySelector(".graph-readout");
    if (!out) {
      out = document.createElement("p");
      out.className = "graph-readout";
      out.setAttribute("role", "status");
      host.appendChild(out);
    }
    return out;
  }
  function show(svg, index) {
    const pts = points(svg);
    if (!pts.length) return;
    const i = Math.max(0, Math.min(pts.length - 1, index));
    svg.setAttribute("data-sel", String(i));
    const p = pts[i];
    const line = svg.querySelector(".mini-cross");
    const dot = svg.querySelector(".mini-dot");
    if (line) { line.setAttribute("x1", p[0]); line.setAttribute("x2", p[0]); line.style.display = "block"; }
    if (dot) { dot.setAttribute("cx", p[0]); dot.setAttribute("cy", p[1]); dot.style.display = "block"; }
    readoutFor(svg).textContent = p[2];
  }
  function hide(svg) {
    const line = svg.querySelector(".mini-cross");
    const dot = svg.querySelector(".mini-dot");
    if (line) line.style.display = "none";
    if (dot) dot.style.display = "none";
    svg.removeAttribute("data-sel");
    const out = svg.parentElement && svg.parentElement.querySelector(".graph-readout");
    if (out) out.remove();
  }
  function nearest(svg, clientX, clientY) {
    const pts = points(svg);
    if (!pts.length || !svg.getScreenCTM) return -1;
    const pt = svg.createSVGPoint();
    pt.x = clientX; pt.y = clientY;
    const local = pt.matrixTransform(svg.getScreenCTM().inverse());
    let best = 0, bestGap = Infinity;
    pts.forEach(function (p, i) {
      const gap = Math.abs(p[0] - local.x);
      if (gap < bestGap) { bestGap = gap; best = i; }
    });
    return best;
  }
  document.addEventListener("pointermove", function (e) {
    const svg = e.target.closest && e.target.closest(SELECTOR);
    if (!svg) return;
    const i = nearest(svg, e.clientX, e.clientY);
    if (i >= 0) show(svg, i);
  });
  document.addEventListener("pointerout", function (e) {
    const svg = e.target.closest && e.target.closest(SELECTOR);
    if (svg && !svg.contains(e.relatedTarget) && document.activeElement !== svg) hide(svg);
  });
  document.addEventListener("focusin", function (e) {
    const svg = e.target.matches && e.target.matches(SELECTOR) ? e.target : null;
    if (svg) show(svg, points(svg).length - 1);
  });
  document.addEventListener("focusout", function (e) {
    if (e.target.matches && e.target.matches(SELECTOR)) hide(e.target);
  });
  document.addEventListener("keydown", function (e) {
    const svg = e.target.matches && e.target.matches(SELECTOR) ? e.target : null;
    if (!svg) return;
    const count = points(svg).length;
    const now = parseInt(svg.getAttribute("data-sel") || String(count - 1), 10);
    let next = null;
    if (e.key === "ArrowLeft") next = now - 1;
    else if (e.key === "ArrowRight") next = now + 1;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = count - 1;
    if (next === null) return;
    e.preventDefault();
    show(svg, next);
  });
})();
