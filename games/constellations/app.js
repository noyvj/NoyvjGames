/* Constellations view: glue only. The engine (game.py and its modules) holds every rule; this file draws what handle() returns as an SVG
   sky, turns pointer, touch and keyboard input into `toggle` requests, and shows the charts, the atlas and its cards. It never decides
   whether a number holds or the chart is finished: it asks the engine, and draws the answer. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["sky.py", "charts_s1.py", "charts_s2.py", "charts_s3.py", "charts.py", "info.py"];
  var STORE_KEY = "constellations:state";
  var BACKUP_KEY = "constellations:state-backup";
  var SVG_NS = "http://www.w3.org/2000/svg";
  var BADGE = 28;              // radius of a numbered star's badge, in chart units (a chart is 1000 units wide)
  var STAR_HIT = 54;           // a press within this many units of a star is a press on that star
  var GRID = 100;

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;
  var view = null;
  var boardId = null;          // the chart the board is currently drawn for
  var cursor = 0;              // the star the keyboard ring is on
  var showCursor = false;      // the ring is drawn only after a key was pressed
  var held = null;             // the star picked up (tap, or keyboard): the next star pressed is joined to it
  var stroke = null;           // the pointer gesture in progress
  var ghostFrom = null;        // while a gesture is in progress, the star whose allowed neighbours are shown
  var allowed = {};            // "i-j" -> true for every pair that can be joined on this chart
  var atlasSig = "", cardsSig = "", chartsSig = "";
  var foundShown = "";
  var infoLiveDone = false;    // the live Wikipedia read has been tried for this page load

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }
  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }
  function announce(text) {
    if (!text) return;
    if (window.NoyvjAnnounce) { window.NoyvjAnnounce.say(text); return; }      // the shared announcer when it is on the page, otherwise this page's own region (never both)
    var live = $("announce");
    live.textContent = "";
    setTimeout(function () { live.textContent = text; }, 40);
  }
  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function svgEl(tag, attrs, parent) {
    var node = document.createElementNS(SVG_NS, tag);
    if (attrs) for (var k in attrs) if (Object.prototype.hasOwnProperty.call(attrs, k)) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  }
  function showToast(text) {
    var t = $("toast");
    t.textContent = text;
    t.classList.toggle("on", Boolean(text));
  }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }
  function pairKey(a, b) { return a < b ? a + "-" + b : b + "-" + a; }

  // ---- panels --------------------------------------------------------------------------------------
  function setPanel(panelId, buttonId, open) {
    $(panelId).hidden = !open;
    $(buttonId).setAttribute("aria-expanded", String(open));
  }
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () { setPanel(panelId, buttonId, $(panelId).hidden); });
  }

  // ---- the stats -------------------------------------------------------------------------------------
  function bumpStat(id, value) {
    var node = $(id);
    var next = String(value);
    if (node.textContent === next) return;
    var had = node.dataset.seen === "1";
    node.textContent = next;
    node.dataset.seen = "1";
    if (had) {
      node.classList.remove("bump");
      void node.offsetWidth;
      node.classList.add("bump");
    }
  }
  function renderStats() {
    var t = view.totals;
    bumpStat("stat-done", t.done + "/" + t.charts);
    bumpStat("stat-stars", t.stars);
    bumpStat("stat-pages", t.pages_open + "/" + t.pages);
    bumpStat("stat-seasons", t.seasons_done + "/" + t.pages);
    bumpStat("stat-lines", t.lines);
  }

  // ---- the chart ---------------------------------------------------------------------------------------
  function starOf(i) { return view.chart.stars[i]; }
  function editable() { return view && view.editable; }
  function canJoin(a, b) { return Boolean(allowed[pairKey(a, b)]); }
  function starRadius(star) { return Math.max(22, Math.min(44, 22 + (4.6 - star.mag) * 3.6)); }

  function renderChartHead() {
    var c = view.chart;
    var solved = c.status === "solved";
    setText($("chart-kicker"), c.season + " - chart " + c.number + " of " + c.of);
    setText($("chart-heading"), solved ? c.name : "Chart " + c.number);
    setText($("chart-caption"), solved ? c.meaning + ". " + plural(c.stars.length, "star", "stars") + "." :
      plural(c.stars.length, "star", "stars") + ". Its name appears when you finish it.");
    $("done-button").disabled = !view.valid;
    $("done-button").hidden = solved;
    $("undo-button").disabled = !view.can_undo;
    $("redo-button").disabled = !view.can_redo;
    $("clear-button").disabled = !view.can_clear;
    $("clear-button").hidden = solved;
    $("undo-button").hidden = solved;
    $("redo-button").hidden = solved;
    setText($("status-line"), solved ? "" : view.problems);
    var card = $("done-card");
    card.hidden = !solved;
    if (solved) {
      setText($("done-title"), c.name + " is in your atlas");
      setText($("done-text"), c.note + " Brightest star: " + c.brightest.name + " (magnitude " + c.brightest.mag + "). " +
        c.best_time.charAt(0).toUpperCase() + c.best_time.slice(1) + ".");
    }
    var words = $("chart-text-body");
    words.textContent = "";
    view.words.forEach(function (line) { words.appendChild(el("p", null, line)); });
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
    var c = view.chart;
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

    var from = ghostFrom !== null ? ghostFrom : held;
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

    if (!solved) {
      if (ghostFrom !== null || held !== null) {
        var hs = starOf(ghostFrom !== null ? ghostFrom : held);
        svgEl("circle", { cx: hs.x, cy: hs.y, r: BADGE + 16, "class": "b-held" }, svg);
        svgEl("circle", { cx: hs.x, cy: hs.y, r: BADGE + 26, "class": "b-held2" }, svg);
        c.allowed.forEach(function (pair) {
          var f = ghostFrom !== null ? ghostFrom : held;
          var other = pair[0] === f ? pair[1] : pair[1] === f ? pair[0] : null;
          if (other === null) return;
          var o = starOf(other);
          svgEl("circle", { cx: o.x, cy: o.y, r: BADGE + 14, "class": "b-near" }, svg);
        });
      }
      svgEl("line", { id: "rubber", x1: 0, y1: 0, x2: 0, y2: 0, "class": "b-rubber", visibility: "hidden" }, svg);
    }
    if (showCursor && c.stars[cursor]) {
      var cs = c.stars[cursor];
      svgEl("circle", { cx: cs.x, cy: cs.y, r: BADGE + 11, "class": "b-cursor-under" }, svg);
      svgEl("circle", { cx: cs.x, cy: cs.y, r: BADGE + 11, "class": "b-cursor" }, svg);
    }
    svg.setAttribute("aria-label", "Chart " + c.number + " of " + c.of + " in " + c.season + ", " + plural(c.stars.length, "star", "stars"));
    svg.classList.toggle("found", Boolean(view.just) && foundShown === (view.just.id + ":" + view.totals.done));
  }

  function describeStar(i) {
    var s = starOf(i);
    var text = "Star " + s.letter + (s.need === null ? ", no number, " : ", needs " + plural(s.need, "line", "lines") + ", ") + "has " + s.have;
    if (s.name) text = s.name + " (star " + s.letter + ")" + text.slice(text.indexOf(","));
    return text;
  }
  function neighboursOf(i) {
    var out = [];
    view.chart.allowed.forEach(function (pair) {
      if (pair[0] === i) out.push(starOf(pair[1]).letter);
      else if (pair[1] === i) out.push(starOf(pair[0]).letter);
    });
    return out.sort();
  }
  function renderCursorLine() {
    var line = $("cursor-line");
    if (!view || view.chart.status === "solved") { setText(line, ""); return; }
    if (held !== null) setText(line, "Holding " + describeStar(held).replace(/^Star/, "star") + ". It can join " + neighboursOf(held).join(", ") + ". Press the star to join, or Escape to put it down.");
    else if (showCursor) setText(line, describeStar(cursor) + ". Can join " + neighboursOf(cursor).join(", ") + ".");
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
    view.chart.stars.forEach(function (s) {
      var d = (s.x - p.x) * (s.x - p.x) + (s.y - p.y) * (s.y - p.y);
      if (d < bestD) { bestD = d; best = s.i; }
    });
    return best;
  }
  function onPointerDown(e) {
    if (!view || !editable()) return;
    if (e.pointerType === "mouse" && e.button !== 0) return;
    showCursor = false;
    var p = svgPoint(e);
    var s = starAt(p);
    if (s !== null) {
      stroke = { from: s, moved: false, id: e.pointerId, line: false };
      cursor = s;
      ghostFrom = s;
      try { $("board").setPointerCapture(e.pointerId); } catch (err) { /* older browsers */ }
      drawBoard();
      e.preventDefault();
      return;
    }
    var target = e.target;
    if (target && target.getAttribute && target.getAttribute("data-a") !== null) {
      stroke = { line: true, a: Number(target.getAttribute("data-a")), b: Number(target.getAttribute("data-b")), id: e.pointerId };
      e.preventDefault();
      return;
    }
    if (held !== null) { held = null; drawBoard(); renderCursorLine(); }
  }
  function onPointerMove(e) {
    if (!stroke || stroke.line || !view) return;
    var p = svgPoint(e);
    var a = starOf(stroke.from);
    if (!stroke.moved && Math.hypot(p.x - a.x, p.y - a.y) > 18) stroke.moved = true;
    var rubber = $("rubber");
    if (rubber && stroke.moved) {
      rubber.setAttribute("x1", a.x); rubber.setAttribute("y1", a.y);
      rubber.setAttribute("x2", p.x); rubber.setAttribute("y2", p.y);
      rubber.setAttribute("visibility", "visible");
    }
  }
  function onPointerUp(e) {
    if (!stroke) return;
    var st = stroke;
    stroke = null;
    ghostFrom = null;
    var rubber = $("rubber");
    if (rubber) rubber.setAttribute("visibility", "hidden");
    if (!view || !editable()) return;
    var p = svgPoint(e);
    if (st.line) {
      var near = e.target && e.target.getAttribute && e.target.getAttribute("data-a") !== null &&
        Number(e.target.getAttribute("data-a")) === st.a && Number(e.target.getAttribute("data-b")) === st.b;
      if (near && starAt(p) === null) send({ action: "toggle", a: st.a, b: st.b });
      return;
    }
    var to = starAt(p);
    if (to !== null && to !== st.from) {
      held = null;
      send({ action: "toggle", a: st.from, b: to });
      return;
    }
    if (to === st.from && !st.moved) {                      // a tap
      if (held === st.from) held = null;
      else if (held !== null && canJoin(held, st.from)) { var h = held; held = st.from; send({ action: "toggle", a: h, b: st.from }); return; }
      else held = st.from;
    } else if (st.moved) {
      held = null;                                          // a drag that ended on nothing lets go
    }
    drawBoard();
    renderCursorLine();
    if (held !== null) announce("Holding star " + starOf(held).letter + ". It can join " + neighboursOf(held).join(", ") + ".");
  }
  function onPointerCancel() {
    stroke = null; ghostFrom = null;
    if (view) { drawBoard(); }
  }

  // ---- keyboard --------------------------------------------------------------------------------------------
  function moveCursor(dx, dy) {
    var stars = view.chart.stars;
    var me = stars[cursor];
    var best = null, bestScore = Infinity, fallback = null, fallbackScore = Infinity;
    stars.forEach(function (s) {
      if (s.i === cursor) return;
      var vx = s.x - me.x, vy = s.y - me.y;
      var dist = Math.hypot(vx, vy);
      var cos = (vx * dx + vy * dy) / dist;
      if (cos <= 0) return;
      var score = dist * (1 + 2.5 * (1 - cos));
      if (cos > 0.45 && score < bestScore) { bestScore = score; best = s.i; }
      if (score < fallbackScore) { fallbackScore = score; fallback = s.i; }
    });
    var pick = best !== null ? best : fallback;
    if (pick !== null) cursor = pick;
  }
  function activateCursor() {
    if (held === null) {
      held = cursor;
      announce("Picked up star " + starOf(cursor).letter + ". It can join " + neighboursOf(cursor).join(", ") + ".");
    } else if (held === cursor) {
      held = null;
      announce("Put down star " + starOf(cursor).letter + ".");
    } else if (canJoin(held, cursor)) {
      var h = held;
      held = cursor;
      send({ action: "toggle", a: h, b: cursor });
      return;
    } else {
      announce("Stars " + starOf(held).letter + " and " + starOf(cursor).letter + " cannot be joined. Move to one of " + neighboursOf(held).join(", ") + ".");
    }
    drawBoard();
    renderCursorLine();
  }
  function onBoardKey(e) {
    if (!view) return;
    var mod = e.ctrlKey || e.metaKey;
    if (mod && (e.key === "z" || e.key === "Z")) { e.preventDefault(); send({ action: e.shiftKey ? "redo" : "undo" }); return; }
    if (mod && (e.key === "y" || e.key === "Y")) { e.preventDefault(); send({ action: "redo" }); return; }
    if (mod || e.altKey) return;
    var solved = view.chart.status === "solved";
    var handled = true;
    switch (e.key) {
      case "ArrowLeft": moveCursor(-1, 0); break;
      case "ArrowRight": moveCursor(1, 0); break;
      case "ArrowUp": moveCursor(0, -1); break;
      case "ArrowDown": moveCursor(0, 1); break;
      case "Enter": case " ":
        if (solved) { handled = false; break; }
        showCursor = true;
        activateCursor();
        e.preventDefault();
        return;
      case "Escape":
        if (held !== null) { held = null; announce("Put the star down."); } else handled = false;
        break;
      case "Home": cursor = 0; break;
      case "End": cursor = view.chart.stars.length - 1; break;
      default: {
        var idx = e.key.length === 1 ? "abcdefghijklmnopqrstuvwxyz".indexOf(e.key.toLowerCase()) : -1;
        if (idx >= 0 && idx < view.chart.stars.length) cursor = idx; else handled = false;
      }
    }
    if (!handled) return;
    e.preventDefault();
    showCursor = true;
    drawBoard();
    renderCursorLine();
    if (e.key !== "Escape") announce(describeStar(cursor) + ". Can join " + neighboursOf(cursor).join(", ") + ".");
  }

  // ---- charts panel, atlas and cards -----------------------------------------------------------------------------
  function allCharts() {
    var list = [];
    view.seasons.forEach(function (s) { s.charts.forEach(function (c) { list.push({ id: c.id, open: s.open, solved: c.solved, current: c.current }); }); });
    return list;
  }
  function renderSeasons() {
    var sig = JSON.stringify(view.seasons);
    if (sig === chartsSig) return;
    chartsSig = sig;
    var holder = $("season-list");
    holder.textContent = "";
    view.seasons.forEach(function (season) {
      var block = el("section", "season-block" + (season.open ? "" : " locked"));
      block.setAttribute("aria-label", season.name);
      block.appendChild(el("h3", null, season.name + " - " + season.done + " of " + season.total + " found"));
      block.appendChild(el("p", "note blurb", season.open ? season.blurb : "Opens when " + season.need_total + " charts in " + season.after + " are found (" + season.need + " more)."));
      var list = el("ul", "chart-list");
      season.charts.forEach(function (c) {
        var item = el("li");
        var btn = el("button", "chart-btn" + (c.solved ? " found" : "") + (c.current ? " current" : ""));
        btn.type = "button";
        btn.setAttribute("data-chart", c.id);
        if (!season.open) btn.setAttribute("aria-disabled", "true");
        if (c.current) btn.setAttribute("aria-current", "true");
        btn.appendChild(el("span", "cb-name", c.solved ? "✓ " + c.name : "Chart " + c.number));
        btn.appendChild(el("span", "cb-meta", c.solved ? c.meaning + " - " + plural(c.stars, "star", "stars") : plural(c.stars, "star", "stars") + (season.open ? "" : " - locked")));
        btn.addEventListener("click", function () {
          if (!season.open) { showToast("That page opens when " + season.need_total + " charts in " + season.after + " are found."); return; }
          send({ action: "pick", chart: c.id });
          setPanel("charts-panel", "charts-toggle-button", false);
          if ($("chart-panel").scrollIntoView) $("chart-panel").scrollIntoView({ block: "start" });
          $("board").focus({ preventScroll: true });
        });
        item.appendChild(btn);
        list.appendChild(item);
      });
      block.appendChild(list);
      holder.appendChild(block);
    });
  }

  function renderAtlas() {
    var atlas = view.atlas;
    var sig = JSON.stringify(atlas.items.map(function (i) { return [i.id, i.solved, i.current]; }));
    if (sig === atlasSig) return;
    atlasSig = sig;
    var svg = $("atlas");
    svg.textContent = "";
    svg.setAttribute("viewBox", "0 0 " + atlas.w + " " + atlas.h);
    svgEl("rect", { x: 0, y: 0, width: atlas.w, height: atlas.h, fill: "var(--sky-b)" }, svg);
    for (var h = 0; h <= 24; h += 2) {
      var gx = (24 - h) / 24 * atlas.w;
      svgEl("line", { x1: gx, y1: 0, x2: gx, y2: atlas.h, "class": "a-grid" }, svg);
      if (h < 24) svgEl("text", { x: gx - 4, y: 16, "class": "a-label", "text-anchor": "end" }, svg).textContent = h + "h";
    }
    [60, 30, 0, -30, -60].forEach(function (dec) {
      var gy = (90 - dec) / 180 * atlas.h;
      svgEl("line", { x1: 0, y1: gy, x2: atlas.w, y2: gy, "class": "a-grid" + (dec === 0 ? " eq" : "") }, svg);
      svgEl("text", { x: 6, y: gy - 4, "class": "a-label" }, svg).textContent = (dec > 0 ? "+" : "") + dec + "°";
    });
    var seasonOpen = {};
    view.seasons.forEach(function (s, i) { seasonOpen[i] = s.open; });
    atlas.items.forEach(function (it) {
      var g = svgEl("g", { "class": "a-item" + (it.solved ? " found" : " locked") + (it.current ? " current" : ""), tabindex: "0", role: "button", "data-chart": it.id }, svg);
      var seasonName = view.seasons[it.season].name;
      if (it.solved) {
        g.setAttribute("aria-label", it.name + ", found. Open its card.");
        it.lines.forEach(function (l) {
          var coords = { x1: it.pts[l[0]][0], y1: it.pts[l[0]][1], x2: it.pts[l[1]][0], y2: it.pts[l[1]][1] };
          svgEl("line", Object.assign({ "class": "a-line" }, coords), g);
          svgEl("line", Object.assign({ "class": "a-hit" }, coords), g);
        });
        it.pts.forEach(function (p) { svgEl("circle", { cx: p[0], cy: p[1], r: 3.6, "class": "a-dot" }, g); });
        svgEl("text", { x: it.x, y: it.y + it.r + 18, "class": "a-title" }, g).textContent = it.name;
      } else {
        g.setAttribute("aria-label", seasonName + " chart " + it.number + ", not found yet" + (seasonOpen[it.season] ? ". Go to the chart." : ". That page is not open yet."));
        svgEl("circle", { cx: it.x, cy: it.y, r: 13, "class": "a-ring" }, g);
        svgEl("circle", { cx: it.x, cy: it.y, r: 22, "class": "a-hit" }, g);
        svgEl("text", { x: it.x, y: it.y + 30, "class": "a-tag" }, g).textContent = seasonName.split(" ")[0] + " " + it.number;
      }
      var go = function () {
        if (it.solved) openCard(it.id);
        else if (seasonOpen[it.season]) {
          send({ action: "pick", chart: it.id });
          setPanel("atlas-panel", "atlas-toggle-button", false);
          if ($("chart-panel").scrollIntoView) $("chart-panel").scrollIntoView({ block: "start" });
        } else showToast("That page opens when " + view.seasons[it.season].need_total + " charts in " + view.seasons[it.season].after + " are found.");
      };
      g.addEventListener("click", go);
      g.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
    });
  }

  function renderCards() {
    var sig = JSON.stringify(view.cards.map(function (c) { return c.id; }));
    if (sig === cardsSig) return;
    cardsSig = sig;
    var holder = $("atlas-cards");
    holder.textContent = "";
    $("cards-empty").hidden = view.cards.length > 0;
    view.cards.forEach(function (c) {
      var d = el("details", "card");
      d.id = "card-" + c.id;
      d.appendChild(el("summary", null, c.name + " - " + c.meaning));
      var dl = el("dl");
      [["Page", c.season + ", chart " + c.number], ["Stars", String(c.stars)],
       ["Brightest star", c.brightest.name + " (magnitude " + c.brightest.mag + ")"], ["Best seen", c.best.charAt(0).toUpperCase() + c.best.slice(1)],
       ["Line changes it took", String(c.moves)]].forEach(function (row) {
        dl.appendChild(el("dt", null, row[0]));
        dl.appendChild(el("dd", null, row[1]));
      });
      d.appendChild(dl);
      d.appendChild(el("p", "card-note", c.note));
      c.sources.forEach(function (s) { d.appendChild(el("p", "card-src", s)); });
      holder.appendChild(d);
    });
  }
  function openCard(id) {
    setPanel("atlas-panel", "atlas-toggle-button", true);
    var d = $("card-" + id) || document.getElementById("card-" + id);
    if (d) { d.open = true; if (d.scrollIntoView) d.scrollIntoView({ block: "center" }); var s = d.querySelector("summary"); if (s) s.focus({ preventScroll: true }); }
  }

  // ---- About (with the live Wikipedia read), What's New ---------------------------------------------------------
  function listFill(id, items) {
    var node = $(id);
    node.textContent = "";
    items.forEach(function (text) { node.appendChild(el("li", null, text)); });
  }
  function renderInfo() {
    var info = view.info;
    if (!info) return;
    setText($("info-page-framing"), info.framing);
    setText($("pledge-heading"), info.pledge_heading);
    listFill("pledge-list", info.pledge);
    setText($("how-heading"), info.how_heading);
    listFill("how-list", info.how);
    setText($("facts-heading"), info.facts_heading);
    var list = $("info-page-sources");
    if (list.dataset.drawn) return;
    list.dataset.drawn = "1";
    info.facts.forEach(function (fact) {
      var item = el("li", "info-page-source");
      item.appendChild(el("strong", null, fact.heading));
      item.appendChild(el("p", "info-page-framing", fact.fact));
      item.appendChild(el("p", "info-page-tie-in", fact.tie_in));
      var link = el("a", null, fact.source.title);
      link.href = fact.source.url; link.target = "_blank"; link.rel = "noopener noreferrer";
      var src = el("p", "info-page-source-note");
      src.appendChild(document.createTextNode("Source: "));
      src.appendChild(link);
      src.appendChild(document.createTextNode(", " + fact.source.publisher + ". Read on " + fact.source.date_read + "."));
      item.appendChild(src);
      list.appendChild(item);
    });
  }
  function firstSentences(text, max) {
    var out = "";
    var parts = String(text).split(/(?<=[.!?])\s+/);
    for (var i = 0; i < parts.length; i++) {
      if ((out + " " + parts[i]).length > max && out) break;
      out = out ? out + " " + parts[i] : parts[i];
    }
    return out;
  }
  function today() { var d = new Date(); return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2); }
  function loadLiveInfo() {
    if (infoLiveDone || !view || !view.info) return;
    infoLiveDone = true;
    var box = $("info-live");
    var live = view.info.live;
    setText(box.firstChild || box.appendChild(el("p", "note")), "Reading the article summary...");
    var fallback = function () {
      box.textContent = "";
      box.appendChild(el("p", "note", "Wikipedia could not be reached just now, so the notes above stand. They were read on " + view.info.date_read + "."));
    };
    if (typeof fetch !== "function") { fallback(); return; }
    fetch(live.api, { headers: { Accept: "application/json" } }).then(function (r) {
      if (!r.ok) throw new Error("status " + r.status);
      return r.json();
    }).then(function (data) {
      var extract = data && typeof data.extract === "string" ? data.extract.trim() : "";
      if (!extract) throw new Error("empty");
      box.textContent = "";
      box.appendChild(el("p", "info-live-text", firstSentences(extract, 420)));
      var src = el("p", "info-page-source-note");
      src.appendChild(document.createTextNode("Source: "));
      var link = el("a", null, live.title);
      link.href = live.url; link.target = "_blank"; link.rel = "noopener noreferrer";
      src.appendChild(link);
      src.appendChild(document.createTextNode(", " + live.publisher + ", text under CC BY-SA. Read live on " + today() + "."));
      box.appendChild(src);
    }).catch(fallback);
  }
  function renderChangelog(entries) {
    var holder = $("changelog-entries");
    holder.textContent = "";
    entries.forEach(function (entry) {
      var row = el("article", "changelog-entry");
      row.appendChild(el("div", "changelog-date", entry.date));
      row.appendChild(el("p", "changelog-text", entry.entry));
      holder.appendChild(row);
    });
    var long = document.querySelector("#changelog-toggle-button .btn-long");
    if (long) long.textContent = "What's New (" + entries.length + ")";
  }
  function loadChangelog() {
    return fetch("changelog.json").then(function (r) { return r.text(); }).then(function (text) {
      window.CHANGELOG_JSON = text;       // shared/whats-new-banner.js reads this to show a returning player only what is new
      var data = JSON.parse(text);
      var list = Array.isArray(data) ? data : (data && data.changelog) || [];
      renderChangelog(list.slice().sort(function (a, b) { return a.date < b.date ? 1 : -1; }));
    }).catch(function () { renderChangelog([]); });
  }

  // ---- render ---------------------------------------------------------------------------------------
  function render() {
    var c = view.chart;
    allowed = {};
    c.allowed.forEach(function (pair) { allowed[pairKey(pair[0], pair[1])] = true; });
    if (c.id !== boardId) {
      boardId = c.id;
      cursor = 0;
      held = null;
      stroke = null;
      ghostFrom = null;
      atlasSig = "";                                       // the atlas marks the current chart
    }
    if (view.just && foundShown !== view.just.id + ":" + view.totals.done) foundShown = view.just.id + ":" + view.totals.done;
    renderStats();
    renderChartHead();
    drawBoard();
    renderCursorLine();
    renderSeasons();
    renderAtlas();
    renderCards();
    renderInfo();
  }

  // ---- talking to the engine --------------------------------------------------------------------------
  function persist() {
    try {
      var proxy = engine.getState();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(STORE_KEY, JSON.stringify(obj));
    } catch (e) { /* the save widget keeps the real copy */ }
  }
  function send(request) {
    if (!engine) return null;
    var previous = view;
    var reply;
    try { reply = JSON.parse(engine.handle(JSON.stringify(request))); } catch (err) { showToast("Something went wrong. Reload to try again."); return null; }
    if (reply.error) { showToast(reply.error); return null; }
    view = reply;
    render();
    showToast(view.message || "");
    if (request.action === "pick" || request.action === "next") {
      var c = view.chart;
      announce("Chart " + c.number + " of " + c.of + " in " + c.season + ", " + plural(c.stars.length, "star", "stars") + ". " + (c.status === "solved" ? c.name + ", already in your atlas." : view.problems));
    } else if (view.message && request.action === "finish" && view.just) {
      announce(view.message);
    } else if (view.say) {
      announce(view.say);
    }
    if (view.just && (!previous || !previous.just || previous.just.id !== view.just.id)) {
      if ($("done-card").scrollIntoView) $("done-card").scrollIntoView({ block: "nearest" });
    }
    persist();
    return view;
  }

  function neighbourChart(delta) {
    var list = allCharts().filter(function (c) { return c.open; });
    var idx = list.findIndex(function (c) { return c.current; });
    var target = list[idx + delta];
    if (target) send({ action: "pick", chart: target.id });
  }
  function askThen(id, message, confirmLabel, go) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: false, onConfirm: go });
    else go();
  }

  function wire() {
    $("toast").addEventListener("click", function () { showToast(""); });
    var board = $("board");
    board.addEventListener("pointerdown", onPointerDown);
    board.addEventListener("pointermove", onPointerMove);
    board.addEventListener("pointerup", onPointerUp);
    board.addEventListener("pointercancel", onPointerCancel);
    board.addEventListener("keydown", onBoardKey);
    board.addEventListener("focus", function () { if (view && !stroke && document.activeElement === board && showCursor) drawBoard(); });
    board.addEventListener("blur", function () { showCursor = false; if (view) { drawBoard(); renderCursorLine(); } });
    $("undo-button").addEventListener("click", function () { send({ action: "undo" }); });
    $("redo-button").addEventListener("click", function () { send({ action: "redo" }); });
    $("clear-button").addEventListener("click", function () { held = null; send({ action: "clear" }); });
    $("done-button").addEventListener("click", function () { send({ action: "finish" }); });
    $("prev-chart-button").addEventListener("click", function () { neighbourChart(-1); });
    $("next-chart-button").addEventListener("click", function () { send({ action: "next" }); });
    $("done-next-button").addEventListener("click", function () { send({ action: "next" }); $("board").focus({ preventScroll: true }); });
    $("done-atlas-button").addEventListener("click", function () {
      setPanel("atlas-panel", "atlas-toggle-button", true);
      if ($("atlas-panel").scrollIntoView) $("atlas-panel").scrollIntoView({ block: "start" });
    });
    wirePanelToggle("charts-toggle-button", "charts-panel");
    wirePanelToggle("atlas-toggle-button", "atlas-panel");
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    $("info-page-toggle-button").addEventListener("click", function () { if (!$("info-page-panel").hidden) loadLiveInfo(); });
    $("reset-button").addEventListener("click", function () {
      askThen("constellations-reset", "Start the whole atlas over? Every constellation will be taken out of the atlas and your tally will be cleared.", "Take it all out", function () { held = null; atlasSig = ""; cardsSig = ""; chartsSig = ""; send({ action: "reset" }); });
    });
    // The save widget loads a save straight into the engine; this redraws afterwards.
    window.constellationsRefresh = function () { if (engine) { boardId = null; atlasSig = ""; cardsSig = ""; chartsSig = ""; send({ action: "open" }); } };
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        ["charts", "atlas", "changelog", "settings", "info-page"].forEach(function (name) {
          var panel = $(name + "-panel");
          if (panel && !panel.hidden) setPanel(name + "-panel", name + "-toggle-button", false);
        });
      }
    });
  }

  async function boot() {
    var changelog = loadChangelog();
    var pyodide = await window.loadPyodide();
    for (var i = 0; i < ENGINE_MODULES.length; i++) {
      var source = await (await fetch(ENGINE_MODULES[i], { cache: "no-cache" })).text();
      pyodide.FS.writeFile(ENGINE_MODULES[i], source, { encoding: "utf8" });
    }
    await pyodide.runPythonAsync(await (await fetch("game.py", { cache: "no-cache" })).text());
    window.pyodide = pyodide;   // the shared save widget looks for it
    engine = { handle: pyodide.globals.get("handle"), getState: pyodide.globals.get("get_state"), loadState: pyodide.globals.get("load_state") };
    var saved = lsGet(STORE_KEY);
    if (saved && saved !== "{}") {
      lsSet(BACKUP_KEY, saved);      // kept until the next good save, so a load problem can never cost the player a game
      try { engine.loadState(pyodide.toPy(JSON.parse(saved))); } catch (e) { /* a bad save never blocks play */ }
    }
    $("engine-status").textContent = "";
    send({ action: "open" });
    await changelog;
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The observatory could not open (" + err + "). Reload to try again.";
  });
})();
