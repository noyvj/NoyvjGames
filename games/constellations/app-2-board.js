/* Constellations, part 2 of 4: the chart head, the SVG board, pointer input, the keyboard ring and zoom. Glue only; every rule is
   in the engine. */
(function () {
  "use strict";

  var A = window.ConstellationsApp;
  var $ = A.$, announce = A.announce, BADGE = A.BADGE, el = A.el, GRID = A.GRID, lsSet = A.lsSet,
      pairKey = A.pairKey, plural = A.plural, send = A.send, setText = A.setText, STAR_HIT = A.STAR_HIT,
      svgEl = A.svgEl, ZOOMS = A.ZOOMS;

  // ---- the chart ---------------------------------------------------------------------------------------
  function starOf(i) { return A.view.chart.stars[i]; }
  function editable() { return A.view && A.view.editable; }
  function canJoin(a, b) { return Boolean(A.allowed[pairKey(a, b)]); }
  function starRadius(star) { return Math.max(22, Math.min(44, 22 + (4.6 - star.mag) * 3.6)); }

  function renderChartHead() {
    var c = A.view.chart;
    var solved = c.status === "solved";
    setText($("chart-kicker"), c.season + " - chart " + c.number + " of " + c.of);
    setText($("chart-heading"), solved ? c.name : "Chart " + c.number);
    setText($("chart-caption"), solved ? c.meaning + ". " + plural(c.stars.length, "star", "stars") + "." :
      plural(c.stars.length, "star", "stars") + ". Its name appears when you finish it.");
    $("done-button").disabled = !A.view.valid;
    $("done-button").hidden = solved;
    $("undo-button").disabled = !A.view.can_undo;
    $("redo-button").disabled = !A.view.can_redo;
    $("clear-button").disabled = !A.view.can_clear;
    $("clear-button").hidden = solved;
    $("undo-button").hidden = solved;
    $("redo-button").hidden = solved;
    setText($("status-line"), solved ? "" : A.view.problems);
    var card = $("done-card");
    card.hidden = !solved;
    if (solved) {
      setText($("done-title"), c.name + " is in your atlas");
      setText($("done-text"), c.note + " Brightest star: " + c.brightest.name + " (magnitude " + c.brightest.mag + "). " +
        c.best_time.charAt(0).toUpperCase() + c.best_time.slice(1) + ".");
    }
    var words = $("chart-text-body");
    words.textContent = "";
    A.view.words.forEach(function (line) { words.appendChild(el("p", null, line)); });
  }

  function intersection(a, b, c, d) {
    var den = (a.x - b.x) * (c.y - d.y) - (a.y - b.y) * (c.x - d.x);
    if (!den) return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
    var t = ((a.x - c.x) * (c.y - d.y) - (a.y - c.y) * (c.x - d.x)) / den;
    return { x: a.x + t * (b.x - a.x), y: a.y + t * (b.y - a.y) };
  }

  function drawStar(g, s, solved) {
    var r = starRadius(s);
    var x = s.x, y = s.y;
    svgEl("circle", { cx: x, cy: y, r: r * 1.45, "class": "b-glow" }, g);
    var pts = [[0, -r], [r * 0.22, -r * 0.22], [r, 0], [r * 0.22, r * 0.22], [0, r], [-r * 0.22, r * 0.22], [-r, 0], [-r * 0.22, -r * 0.22]]
      .map(function (p) { return (x + p[0]) + "," + (y + p[1]); }).join(" ");
    svgEl("polygon", { points: pts, "class": "b-star" + (s.state === "over" && s.need === null ? " over-ring" : "") }, g);
    svgEl("polygon", { points: (x) + "," + (y - r) + " " + (x + r * 0.22) + "," + (y - r * 0.22) + " " + x + "," + y + " " + (x - r * 0.22) + "," + (y - r * 0.22), "class": "b-star-facet" }, g);
    if (s.need !== null) {
      if (s.state === "met") svgEl("circle", { cx: x, cy: y, r: BADGE + 8, "class": "b-badge-outer" }, g);
      svgEl("circle", { cx: x, cy: y, r: BADGE, "class": "b-badge " + s.state }, g);
      svgEl("text", { x: x, y: y + 2, "class": "b-num" }, g).textContent = String(s.need);
      if (s.state === "met") svgEl("text", { x: x + BADGE + 4, y: y - BADGE - 2, "class": "b-flag met" }, g).textContent = "✓";
      if (s.state === "over") svgEl("text", { x: x + BADGE + 4, y: y - BADGE - 2, "class": "b-flag over" }, g).textContent = "!";
    }
    svgEl("text", { x: x + BADGE - 2, y: y + BADGE + 22, "class": "b-letter" }, g).textContent = s.letter;
    if (solved && s.name) svgEl("text", { x: x + BADGE + 6, y: y - BADGE - 8, "class": "b-name" }, g).textContent = s.label || s.name;
  }

  function drawBoard() {
    var c = A.view.chart;
    var svg = $("board");
    var solved = c.status === "solved";
    svg.textContent = "";
    svg.setAttribute("viewBox", "0 0 " + c.w + " " + c.h);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    var defs = svgEl("defs", null, svg);
    var grad = svgEl("radialGradient", { id: "sky-grad", cx: "50%", cy: "40%", r: "80%" }, defs);
    svgEl("stop", { offset: "0", "class": "b-sky-a" }, grad);
    svgEl("stop", { offset: "1", "class": "b-sky-b" }, grad);
    svgEl("rect", { x: 0, y: 0, width: c.w, height: c.h, fill: "url(#sky-grad)" }, svg);
    for (var gx = GRID; gx < c.w; gx += GRID) svgEl("line", { x1: gx, y1: 0, x2: gx, y2: c.h, "class": "b-grid" }, svg);
    for (var gy = GRID; gy < c.h; gy += GRID) svgEl("line", { x1: 0, y1: gy, x2: c.w, y2: gy, "class": "b-grid" }, svg);

    c.never.forEach(function (pair) {
      var a = starOf(pair[0]), b = starOf(pair[1]);
      svgEl("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, "class": "b-never" }, svg);
      var mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      svgEl("circle", { cx: mx, cy: my, r: 17, "class": "b-never-mark" }, svg);
      svgEl("line", { x1: mx - 8, y1: my - 8, x2: mx + 8, y2: my + 8, "class": "b-never-x" }, svg);
      svgEl("line", { x1: mx - 8, y1: my + 8, x2: mx + 8, y2: my - 8, "class": "b-never-x" }, svg);
    });

    var from = A.ghostFrom !== null ? A.ghostFrom : A.held;
    if (from !== null && editable()) {
      c.allowed.forEach(function (pair) {
        var other = pair[0] === from ? pair[1] : pair[1] === from ? pair[0] : null;
        if (other === null) return;
        var a = starOf(from), b = starOf(other);
        svgEl("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, "class": "b-ghost" }, svg);
      });
    }

    var drawn = {};
    c.lines.forEach(function (l) {
      var a = starOf(l.a), b = starOf(l.b);
      drawn[l.a + "-" + l.b] = true;
      if (l.given) {
        svgEl("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, "class": "b-line given" }, svg);
        svgEl("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, "class": "b-line-core" }, svg);
      } else {
        svgEl("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, "class": "b-line" + (l.cross ? " cross" : "") + (solved ? " done" : "") }, svg);
      }
    });
    // crossing marks
    var crossing = c.lines.filter(function (l) { return l.cross; });
    for (var i = 0; i < crossing.length; i++) {
      for (var j = i + 1; j < crossing.length; j++) {
        var p = crossing[i], q = crossing[j];
        if (p.a === q.a || p.a === q.b || p.b === q.a || p.b === q.b) continue;
        var pt = intersection(starOf(p.a), starOf(p.b), starOf(q.a), starOf(q.b));
        var onP = Math.min(starOf(p.a).x, starOf(p.b).x) - 1 <= pt.x && pt.x <= Math.max(starOf(p.a).x, starOf(p.b).x) + 1;
        var onQ = Math.min(starOf(q.a).x, starOf(q.b).x) - 1 <= pt.x && pt.x <= Math.max(starOf(q.a).x, starOf(q.b).x) + 1;
        if (!onP || !onQ) continue;
        svgEl("line", { x1: pt.x - 12, y1: pt.y - 12, x2: pt.x + 12, y2: pt.y + 12, "class": "b-cross-mark" }, svg);
        svgEl("line", { x1: pt.x - 12, y1: pt.y + 12, x2: pt.x + 12, y2: pt.y - 12, "class": "b-cross-mark" }, svg);
      }
    }
    // lines that cross where this chart allows it (the Southern Cross): a small ring where they meet, never a warning
    (c.joined || []).forEach(function (pair) {
      var pt = intersection(starOf(pair[0][0]), starOf(pair[0][1]), starOf(pair[1][0]), starOf(pair[1][1]));
      svgEl("circle", { cx: pt.x, cy: pt.y, r: 13, "class": "b-joined" }, svg);
    });
    // the suggestion ladder: dotted guide lines with a plus (draw) or a minus (erase) in a small plate, so it is never told by colour alone
    var hint = A.view.hint;
    if (hint && !solved) {
      var guide = function (pair, sign) {
        var ga = starOf(pair[0]), gb = starOf(pair[1]);
        svgEl("line", { x1: ga.x, y1: ga.y, x2: gb.x, y2: gb.y, "class": "b-hintline" }, svg);
        var mx = (ga.x + gb.x) / 2, my = (ga.y + gb.y) / 2;
        svgEl("circle", { cx: mx, cy: my, r: 17, "class": "b-hintplate" }, svg);
        svgEl("text", { x: mx, y: my + 1, "class": "b-hintsign" }, svg).textContent = sign;
      };
      if (hint.rung >= 3) {
        hint.ghost.forEach(function (pair) { guide(pair, "+"); });
        hint.erase.forEach(function (pair) { guide(pair, "\u2212"); });
      } else if (hint.rung >= 2 && hint.line) {
        guide(hint.line, hint.kind === "remove" ? "\u2212" : "+");
      }
    }
    // tap targets for the lines the player drew
    if (!solved) {
      c.lines.forEach(function (l) {
        if (l.given) return;
        var a = starOf(l.a), b = starOf(l.b);
        var hit = svgEl("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, "class": "b-hit" }, svg);
        hit.setAttribute("data-a", l.a);
        hit.setAttribute("data-b", l.b);
      });
    }

    c.stars.forEach(function (s) {
      var g = svgEl("g", { "data-star": s.i }, svg);
      drawStar(g, s, solved);
    });

    if (hint && !solved && hint.star !== null && hint.star !== undefined && starOf(hint.star)) {
      var hs0 = starOf(hint.star);
      svgEl("circle", { cx: hs0.x, cy: hs0.y, r: BADGE + 24, "class": "b-hintstar" }, svg);
    }
    if (!solved) {
      if (A.ghostFrom !== null || A.held !== null) {
        var hs = starOf(A.ghostFrom !== null ? A.ghostFrom : A.held);
        svgEl("circle", { cx: hs.x, cy: hs.y, r: BADGE + 16, "class": "b-held" }, svg);
        svgEl("circle", { cx: hs.x, cy: hs.y, r: BADGE + 26, "class": "b-held2" }, svg);
        c.allowed.forEach(function (pair) {
          var f = A.ghostFrom !== null ? A.ghostFrom : A.held;
          var other = pair[0] === f ? pair[1] : pair[1] === f ? pair[0] : null;
          if (other === null) return;
          var o = starOf(other);
          svgEl("circle", { cx: o.x, cy: o.y, r: BADGE + 14, "class": "b-near" }, svg);
        });
      }
      svgEl("line", { id: "rubber", x1: 0, y1: 0, x2: 0, y2: 0, "class": "b-rubber", visibility: "hidden" }, svg);
    }
    if (A.showCursor && c.stars[A.cursor]) {
      var cs = c.stars[A.cursor];
      svgEl("circle", { cx: cs.x, cy: cs.y, r: BADGE + 11, "class": "b-cursor-under" }, svg);
      svgEl("circle", { cx: cs.x, cy: cs.y, r: BADGE + 11, "class": "b-cursor" }, svg);
    }
    svg.setAttribute("aria-label", "Chart " + c.number + " of " + c.of + " in " + c.season + ", " + plural(c.stars.length, "star", "stars"));
    svg.classList.toggle("found", Boolean(A.view.just) && A.foundShown === (A.view.just.id + ":" + A.view.totals.done));
  }

  function describeStar(i) {
    var s = starOf(i);
    var text = "Star " + s.letter + (s.need === null ? ", no number, " : ", needs " + plural(s.need, "line", "lines") + ", ") + "has " + s.have;
    if (s.name) text = s.name + " (star " + s.letter + ")" + text.slice(text.indexOf(","));
    return text;
  }
  function neighboursOf(i) {
    var out = [];
    A.view.chart.allowed.forEach(function (pair) {
      if (pair[0] === i) out.push(starOf(pair[1]).letter);
      else if (pair[1] === i) out.push(starOf(pair[0]).letter);
    });
    return out.sort();
  }
  function renderCursorLine() {
    var line = $("cursor-line");
    if (!A.view || A.view.chart.status === "solved") { setText(line, ""); return; }
    if (A.held !== null) setText(line, "Holding " + describeStar(A.held).replace(/^Star/, "star") + ". It can join " + neighboursOf(A.held).join(", ") + ". Press the star to join, or Escape to put it down.");
    else if (A.showCursor) setText(line, describeStar(A.cursor) + ". Can join " + neighboursOf(A.cursor).join(", ") + ".");
    else setText(line, "");
  }

  // ---- pointer ---------------------------------------------------------------------------------------------
  function svgPoint(e) {
    var svg = $("board");
    var pt = svg.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    var m = svg.getScreenCTM();
    return m ? pt.matrixTransform(m.inverse()) : { x: 0, y: 0 };
  }
  function starAt(p) {
    var best = null, bestD = STAR_HIT * STAR_HIT;
    A.view.chart.stars.forEach(function (s) {
      var d = (s.x - p.x) * (s.x - p.x) + (s.y - p.y) * (s.y - p.y);
      if (d < bestD) { bestD = d; best = s.i; }
    });
    return best;
  }
  function onPointerDown(e) {
    if (!A.view || !editable()) return;
    if (e.pointerType === "mouse" && e.button !== 0) return;
    A.showCursor = false;
    var p = svgPoint(e);
    var s = starAt(p);
    if (s !== null) {
      A.stroke = { from: s, moved: false, id: e.pointerId, line: false };
      A.cursor = s;
      A.ghostFrom = s;
      try { $("board").setPointerCapture(e.pointerId); } catch (err) { /* older browsers */ }
      drawBoard();
      e.preventDefault();
      return;
    }
    var target = e.target;
    if (target && target.getAttribute && target.getAttribute("data-a") !== null) {
      A.stroke = { line: true, a: Number(target.getAttribute("data-a")), b: Number(target.getAttribute("data-b")), id: e.pointerId };
      e.preventDefault();
      return;
    }
    if (A.held !== null) { A.held = null; drawBoard(); renderCursorLine(); }
  }
  function onPointerMove(e) {
    if (!A.stroke || A.stroke.line || !A.view) return;
    var p = svgPoint(e);
    var a = starOf(A.stroke.from);
    if (!A.stroke.moved && Math.hypot(p.x - a.x, p.y - a.y) > 18) A.stroke.moved = true;
    var rubber = $("rubber");
    if (rubber && A.stroke.moved) {
      rubber.setAttribute("x1", a.x); rubber.setAttribute("y1", a.y);
      rubber.setAttribute("x2", p.x); rubber.setAttribute("y2", p.y);
      rubber.setAttribute("visibility", "visible");
    }
  }
  function onPointerUp(e) {
    if (!A.stroke) return;
    var st = A.stroke;
    A.stroke = null;
    A.ghostFrom = null;
    var rubber = $("rubber");
    if (rubber) rubber.setAttribute("visibility", "hidden");
    if (!A.view || !editable()) return;
    var p = svgPoint(e);
    if (st.line) {
      var near = e.target && e.target.getAttribute && e.target.getAttribute("data-a") !== null &&
        Number(e.target.getAttribute("data-a")) === st.a && Number(e.target.getAttribute("data-b")) === st.b;
      if (near && starAt(p) === null) send({ action: "toggle", a: st.a, b: st.b });
      return;
    }
    var to = starAt(p);
    if (to !== null && to !== st.from) {
      A.held = null;
      send({ action: "toggle", a: st.from, b: to });
      return;
    }
    if (to === st.from && !st.moved) {                      // a tap
      if (A.held === st.from) A.held = null;
      else if (A.held !== null && canJoin(A.held, st.from)) { var h = A.held; A.held = st.from; send({ action: "toggle", a: h, b: st.from }); return; }
      else A.held = st.from;
    } else if (st.moved) {
      A.held = null;                                          // a drag that ended on nothing lets go
    }
    drawBoard();
    renderCursorLine();
    if (A.held !== null) announce("Holding star " + starOf(A.held).letter + ". It can join " + neighboursOf(A.held).join(", ") + ".");
  }
  function onPointerCancel() {
    A.stroke = null; A.ghostFrom = null;
    if (A.view) { drawBoard(); }
  }

  // ---- keyboard --------------------------------------------------------------------------------------------
  function moveCursor(dx, dy) {
    var stars = A.view.chart.stars;
    var me = stars[A.cursor];
    var best = null, bestScore = Infinity, fallback = null, fallbackScore = Infinity;
    stars.forEach(function (s) {
      if (s.i === A.cursor) return;
      var vx = s.x - me.x, vy = s.y - me.y;
      var dist = Math.hypot(vx, vy);
      var cos = (vx * dx + vy * dy) / dist;
      if (cos <= 0) return;
      var score = dist * (1 + 2.5 * (1 - cos));
      if (cos > 0.45 && score < bestScore) { bestScore = score; best = s.i; }
      if (score < fallbackScore) { fallbackScore = score; fallback = s.i; }
    });
    var pick = best !== null ? best : fallback;
    if (pick !== null) A.cursor = pick;
  }
  function activateCursor() {
    if (A.held === null) {
      A.held = A.cursor;
      announce("Picked up star " + starOf(A.cursor).letter + ". It can join " + neighboursOf(A.cursor).join(", ") + ".");
    } else if (A.held === A.cursor) {
      A.held = null;
      announce("Put down star " + starOf(A.cursor).letter + ".");
    } else if (canJoin(A.held, A.cursor)) {
      var h = A.held;
      A.held = A.cursor;
      send({ action: "toggle", a: h, b: A.cursor });
      return;
    } else {
      announce("Stars " + starOf(A.held).letter + " and " + starOf(A.cursor).letter + " cannot be joined. Move to one of " + neighboursOf(A.held).join(", ") + ".");
    }
    drawBoard();
    renderCursorLine();
  }
  function onBoardKey(e) {
    if (!A.view) return;
    var mod = e.ctrlKey || e.metaKey;
    if (mod && (e.key === "z" || e.key === "Z")) { e.preventDefault(); send({ action: e.shiftKey ? "redo" : "undo" }); return; }
    if (mod && (e.key === "y" || e.key === "Y")) { e.preventDefault(); send({ action: "redo" }); return; }
    if (e.altKey && !mod && e.code === "KeyH") { e.preventDefault(); if (A.view.hint_ui.available && !$("hint-box").hidden) A.pressHint(false); return; }
    if (mod || e.altKey) return;
    var solved = A.view.chart.status === "solved";
    var handled = true;
    switch (e.key) {
      case "ArrowLeft": moveCursor(-1, 0); break;
      case "ArrowRight": moveCursor(1, 0); break;
      case "ArrowUp": moveCursor(0, -1); break;
      case "ArrowDown": moveCursor(0, 1); break;
      case "Enter": case " ":
        if (solved) { handled = false; break; }
        A.showCursor = true;
        activateCursor();
        e.preventDefault();
        return;
      case "Escape":
        if (A.held !== null) { A.held = null; announce("Put the star down."); } else handled = false;
        break;
      case "Home": A.cursor = 0; break;
      case "End": A.cursor = A.view.chart.stars.length - 1; break;
      default: {
        var idx = e.key.length === 1 ? "abcdefghijklmnopqrstuvwxyz".indexOf(e.key.toLowerCase()) : -1;
        if (idx >= 0 && idx < A.view.chart.stars.length) A.cursor = idx; else handled = false;
      }
    }
    if (!handled) return;
    e.preventDefault();
    A.showCursor = true;
    revealStar(A.cursor);
    drawBoard();
    renderCursorLine();
    if (e.key !== "Escape") announce(describeStar(A.cursor) + ". Can join " + neighboursOf(A.cursor).join(", ") + ".");
  }

  // ---- zoom: a larger board for small screens (it scrolls sideways) ---------------------------------------------
  function applyZoom() {
    var pc = document.documentElement.getAttribute("data-layout") === "pc";      // the Desktop board fills the stage (a window with room), so it never needs the larger sizes
    var z = pc ? 1 : ZOOMS[A.zoomIdx];
    var svg = $("board");
    svg.style.width = z === 1 ? "" : Math.round(z * 100) + "%";
    svg.style.maxHeight = z === 1 ? "" : "none";
    svg.style.touchAction = z === 1 ? "" : "pan-x pan-y";
    $("board-wrap").classList.toggle("zoomed", z > 1);
    $("zoom-out-button").disabled = A.zoomIdx === 0;
    $("zoom-in-button").disabled = A.zoomIdx === ZOOMS.length - 1;
    $("zoom-reset-button").setAttribute("aria-pressed", String(z === 1));
    setText($("zoom-note"), z === 1 ? "Stars close together? Press + for a larger board." : "Board at " + Math.round(z * 100) + "%. Scroll the board sideways. On a touch screen, drag scrolls; tap one star, then the next, to draw.");
  }
  function setZoom(index) {
    A.zoomIdx = Math.max(0, Math.min(ZOOMS.length - 1, index));
    lsSet("constellations:zoom", String(A.zoomIdx));
    applyZoom();
    if (A.view) revealStar(A.cursor);
  }
  function revealStar(i) {
    var wrap = $("board-wrap");
    if (!A.view || !A.view.chart.stars[i] || wrap.scrollWidth <= wrap.clientWidth + 1) return;
    var svg = $("board");
    var m = svg.getScreenCTM();
    if (!m) return;
    var s = A.view.chart.stars[i];
    var sx = s.x * m.a + m.e;
    var box = wrap.getBoundingClientRect();
    if (sx < box.left + 50) wrap.scrollLeft -= box.left + 50 - sx;
    else if (sx > box.right - 50) wrap.scrollLeft += sx - (box.right - 50);
  }

  // what the other parts use
  A.applyZoom = applyZoom;
  A.drawBoard = drawBoard;
  A.onBoardKey = onBoardKey;
  A.onPointerCancel = onPointerCancel;
  A.onPointerDown = onPointerDown;
  A.onPointerMove = onPointerMove;
  A.onPointerUp = onPointerUp;
  A.renderChartHead = renderChartHead;
  A.renderCursorLine = renderCursorLine;
  A.setZoom = setZoom;
})();
