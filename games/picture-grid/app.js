/* Picture Grid view: glue only. The engine (game.py and its modules) holds every rule; this file draws what handle() returns as an
   SVG frame, turns pointer, touch and keyboard input into `paint` requests, and shows the gallery wall. It never decides whether
   a line is finished or a mark is wrong: it asks the engine, and draws the answer. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["nonogram.py", "pictures_g1.py", "pictures_g2.py", "pictures_g3.py", "pictures.py"];
  var STORE_KEY = "picture-grid:state";
  var BACKUP_KEY = "picture-grid:state-backup";
  var SVG_NS = "http://www.w3.org/2000/svg";
  var CS = 40;                 // one cell, in drawing units
  var NUM_W = 17;              // width of one row-clue number
  var NUM_H = 19;              // height of one column-clue number
  var TICK = 22;               // room for the "done" tick beside a clue
  var UNKNOWN = ".", FILLED = "#", DOT = "x";

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;
  var view = null;
  var boardId = null;          // the frame the board is currently drawn for
  var geom = null;             // sizes of the drawn board
  var cursor = { r: 0, c: 0 };
  var mode = "fill";           // the tool a tap or a key uses: "fill" or "dot"
  var stroke = null;           // the drag in progress
  var largeId = null;          // the hung picture open in the large view
  var glowShown = "";          // the hung picture whose glow has already played
  var wallSig = "";

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }
  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }
  function announce(text) {
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
  function clueWords(clue) { return clue.length ? clue.join(" ") : "0"; }

  // ---- panels --------------------------------------------------------------------------------------
  function setPanel(panelId, buttonId, open) {
    $(panelId).hidden = !open;
    $(buttonId).setAttribute("aria-expanded", String(open));
  }
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () { setPanel(panelId, buttonId, $(panelId).hidden); });
  }

  // ---- small pixel pictures (gallery thumbnails and the large view) ---------------------------------
  function pixelSvg(rows, tint, label, withBackground) {
    var h = rows.length, w = rows[0].length;
    var paths = ["", "", ""];
    for (var r = 0; r < h; r++) {
      var tone = Math.min(2, Math.floor(r * 3 / h));
      var c = 0;
      while (c < w) {
        if (rows[r].charAt(c) !== "#") { c++; continue; }
        var start = c;
        while (c < w && rows[r].charAt(c) === "#") c++;
        paths[tone] += "M" + start + " " + r + "h" + (c - start) + "v1h-" + (c - start) + "z";
      }
    }
    var svg = svgEl("svg", { viewBox: "0 0 " + w + " " + h, "class": "pixel tint-" + tint, "shape-rendering": "crispEdges", focusable: "false" });
    if (label) { svg.setAttribute("role", "img"); svg.setAttribute("aria-label", label); } else svg.setAttribute("aria-hidden", "true");
    if (withBackground) svgEl("rect", { x: 0, y: 0, width: w, height: h, "class": "px-bg" }, svg);
    for (var t = 0; t < 3; t++) if (paths[t]) svgEl("path", { d: paths[t], "class": "tone" + (t + 1) }, svg);
    return svg;
  }
  function pictureWords(rows) {
    var h = rows.length, w = rows[0].length;
    var lines = ["A " + w + " by " + h + " pixel picture."];
    rows.forEach(function (row, r) {
      var runs = [];
      var c = 0;
      while (c < w) {
        if (row.charAt(c) !== "#") { c++; continue; }
        var start = c;
        while (c < w && row.charAt(c) === "#") c++;
        runs.push(c - start === 1 ? "column " + (start + 1) : "columns " + (start + 1) + " to " + c);
      }
      lines.push("Row " + (r + 1) + ": " + (runs.length ? "filled in " + runs.join(", ") : "empty") + ".");
    });
    return lines.join(" ");
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
    bumpStat("stat-hung", view.totals.hung + "/" + view.totals.pictures);
    bumpStat("stat-cells", view.totals.cells);
    bumpStat("stat-galleries", view.totals.galleries_done + "/" + view.totals.galleries);
    bumpStat("stat-strokes", view.picture.moves);
  }

  // ---- the board -------------------------------------------------------------------------------------
  function cellState(r, c) { return view.grid[r].charAt(c); }
  function isBig() { return document.documentElement.getAttribute("data-big-cells") === "true"; }
  function toneOf(r) { return Math.min(2, Math.floor(r * 3 / view.picture.height)) + 1; }

  function layout() {
    var p = view.picture;
    var rowNums = 1, colNums = 1;
    p.row_clues.forEach(function (c) { rowNums = Math.max(rowNums, c.length); });
    p.col_clues.forEach(function (c) { colNums = Math.max(colNums, c.length); });
    var clueW = rowNums * NUM_W + TICK + 6;
    var clueH = colNums * NUM_H + TICK + 4;
    var W = clueW + p.width * CS;
    var H = clueH + p.height * CS;
    var wrap = $("board-wrap");
    var avail = Math.max(160, wrap.clientWidth - 24);
    var unit = isBig() ? 44 / CS : Math.min(44 / CS, avail / W);
    unit = Math.max(unit, 24 / CS);
    return { clueW: clueW, clueH: clueH, W: W, H: H, unit: unit, scroll: W * unit > avail + 1 };
  }

  function drawMark(parent, r, c, state, pending) {
    var x = geom.clueW + c * CS, y = geom.clueH + r * CS;
    var g = svgEl("g", pending ? { "class": "b-pending" } : null, parent);
    if (state === FILLED) {
      var solved = view.picture.status === "solved";
      svgEl("rect", { x: x + 2, y: y + 2, width: CS - 4, height: CS - 4, rx: 3, "class": "b-fill" + (solved ? " tone" + toneOf(r) : "") }, g);
      svgEl("polygon", { points: (x + 2) + "," + (y + 2) + " " + (x + CS - 2) + "," + (y + 2) + " " + (x + 2) + "," + (y + CS - 2), "class": "b-facet" }, g);
      svgEl("path", { d: "M" + (x + 8) + " " + (y + CS - 3) + "L" + (x + CS - 3) + " " + (y + 8) + "M" + (x + 18) + " " + (y + CS - 3) + "L" + (x + CS - 3) + " " + (y + 18), "class": "b-hatch" }, g);
    } else if (state === DOT) {
      svgEl("circle", { cx: x + CS / 2, cy: y + CS / 2, r: 4.5, "class": "b-dot" }, g);
    }
  }

  function drawBoard() {
    var p = view.picture;
    var svg = $("board");
    geom = layout();
    svg.textContent = "";
    svg.setAttribute("viewBox", "0 0 " + geom.W + " " + geom.H);
    svg.setAttribute("width", Math.round(geom.W * geom.unit));
    svg.setAttribute("height", Math.round(geom.H * geom.unit));
    svg.setAttribute("data-scroll", geom.scroll ? "1" : "0");
    svg.setAttribute("class", "board tint-" + p.tint + (p.status === "solved" ? " solved" : ""));
    var title = svgEl("title", { id: "board-title" }, svg);
    title.textContent = "Frame " + p.number + " of " + p.of + ", " + p.width + " by " + p.height + ". Use the arrow keys to move the ring and Space to mark a cell.";
    var x0 = geom.clueW, y0 = geom.clueH;
    svgEl("rect", { x: x0, y: y0, width: p.width * CS, height: p.height * CS, "class": "b-bg" }, svg);
    if (view.assist.focus) {
      svgEl("rect", { x: x0, y: y0 + cursor.r * CS, width: p.width * CS, height: CS, "class": "b-focus" }, svg);
      svgEl("rect", { x: x0 + cursor.c * CS, y: y0, width: CS, height: p.height * CS, "class": "b-focus" }, svg);
    }
    // clues
    p.row_clues.forEach(function (clue, r) {
      var done = view.satisfied.rows[r];
      var list = clue.length ? clue : [0];
      list.forEach(function (n, i) {
        var t = svgEl("text", { x: geom.clueW - TICK - 6 - (list.length - 1 - i) * NUM_W - NUM_W / 2 + 4, y: y0 + r * CS + CS / 2, "class": "b-clue" + (done ? " done" : "") }, svg);
        t.textContent = n;
      });
      if (done) { var k = svgEl("text", { x: geom.clueW - TICK / 2 - 2, y: y0 + r * CS + CS / 2, "class": "b-check" }, svg); k.textContent = "✓"; }
    });
    p.col_clues.forEach(function (clue, c) {
      var done = view.satisfied.cols[c];
      var list = clue.length ? clue : [0];
      list.forEach(function (n, i) {
        var t = svgEl("text", { x: x0 + c * CS + CS / 2, y: geom.clueH - TICK - 4 - (list.length - 1 - i) * NUM_H - NUM_H / 2 + 4, "class": "b-clue" + (done ? " done" : "") }, svg);
        t.textContent = n;
      });
      if (done) { var k = svgEl("text", { x: x0 + c * CS + CS / 2, y: geom.clueH - TICK / 2 - 1, "class": "b-check" }, svg); k.textContent = "✓"; }
    });
    // marks
    var wrong = {};
    view.wrong.forEach(function (pair) { wrong[pair[0] + "," + pair[1]] = true; });
    for (var r = 0; r < p.height; r++) {
      for (var c = 0; c < p.width; c++) {
        drawMark(svg, r, c, cellState(r, c), false);
        if (wrong[r + "," + c]) {
          var wx = x0 + c * CS, wy = y0 + r * CS;
          svgEl("rect", { x: wx + 3, y: wy + 3, width: CS - 6, height: CS - 6, rx: 3, "class": "b-wrong" }, svg);
          svgEl("path", { d: "M" + (wx + 8) + " " + (wy + 8) + "L" + (wx + CS - 8) + " " + (wy + CS - 8), "class": "b-wrong-slash" }, svg);
        }
      }
    }
    // grid lines, heavier every fifth
    for (var i = 0; i <= p.width; i++) svgEl("line", { x1: x0 + i * CS, y1: y0, x2: x0 + i * CS, y2: y0 + p.height * CS, "class": "b-line" + (i % 5 === 0 && i > 0 && i < p.width ? " major" : "") }, svg);
    for (var j = 0; j <= p.height; j++) svgEl("line", { x1: x0, y1: y0 + j * CS, x2: x0 + p.width * CS, y2: y0 + j * CS, "class": "b-line" + (j % 5 === 0 && j > 0 && j < p.height ? " major" : "") }, svg);
    svgEl("rect", { x: x0, y: y0, width: p.width * CS, height: p.height * CS, "class": "b-edge" }, svg);
    svgEl("g", { id: "preview" }, svg);
    drawCursor();
  }

  function drawCursor() {
    var svg = $("board");
    var old = svg.querySelectorAll(".b-cursor, .b-cursor-under");
    for (var i = 0; i < old.length; i++) svg.removeChild(old[i]);
    if (!geom || !view) return;
    var x = geom.clueW + cursor.c * CS, y = geom.clueH + cursor.r * CS;
    svgEl("rect", { x: x + 1, y: y + 1, width: CS - 2, height: CS - 2, rx: 2, "class": "b-cursor-under" }, svg);
    svgEl("rect", { x: x + 1, y: y + 1, width: CS - 2, height: CS - 2, rx: 2, "class": "b-cursor" }, svg);
  }

  function drawPreview() {
    var g = $("board").querySelector("#preview");
    if (!g) return;
    g.textContent = "";
    if (!stroke) return;
    stroke.cells.forEach(function (cell) {
      if (stroke.val === 0) {
        var x = geom.clueW + cell[1] * CS, y = geom.clueH + cell[0] * CS;
        svgEl("rect", { x: x + 4, y: y + 4, width: CS - 8, height: CS - 8, rx: 3, "class": "b-wrong b-pending", "stroke-dasharray": "2 3" }, g);
      } else drawMark(g, cell[0], cell[1], stroke.val === 1 ? FILLED : DOT, true);
    });
  }

  function cursorWords() {
    var p = view.picture;
    var state = cellState(cursor.r, cursor.c);
    var word = state === FILLED ? "filled" : state === DOT ? "dotted" : "unknown";
    var rowDone = view.satisfied.rows[cursor.r] ? ", done" : "";
    var colDone = view.satisfied.cols[cursor.c] ? ", done" : "";
    return "Row " + (cursor.r + 1) + " of " + p.height + ", column " + (cursor.c + 1) + " of " + p.width + ": " + word + ". Row clue " + clueWords(p.row_clues[cursor.r]) + rowDone + ". Column clue " + clueWords(p.col_clues[cursor.c]) + colDone + ".";
  }
  function renderCursorLine() { setText($("cursor-line"), cursorWords()); }

  function renderClueText() {
    var p = view.picture;
    var holder = $("clue-text-body");
    var sig = p.id + "|" + view.satisfied.rows.join("") + view.satisfied.cols.join("");
    if (holder.dataset.sig === sig) return;
    holder.dataset.sig = sig;
    holder.textContent = "";
    p.row_clues.forEach(function (clue, r) { holder.appendChild(el("p", null, "Row " + (r + 1) + ": " + clueWords(clue) + (view.satisfied.rows[r] ? " (done)" : ""))); });
    p.col_clues.forEach(function (clue, c) { holder.appendChild(el("p", null, "Column " + (c + 1) + ": " + clueWords(clue) + (view.satisfied.cols[c] ? " (done)" : ""))); });
  }

  // ---- input: pointer ---------------------------------------------------------------------------------
  function cellFromEvent(e) {
    var svg = $("board");
    var m = svg.getScreenCTM();
    if (!m) return null;
    var pt = svg.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    var local = pt.matrixTransform(m.inverse());
    var c = Math.floor((local.x - geom.clueW) / CS), r = Math.floor((local.y - geom.clueH) / CS);
    if (r < 0 || c < 0 || r >= view.picture.height || c >= view.picture.width) return null;
    return [r, c];
  }
  function strokeAccepts(cell) {
    var s = cellState(cell[0], cell[1]);
    return stroke.val === 0 ? s === stroke.s0 : s === UNKNOWN;
  }
  function strokeAdd(cell) {
    for (var i = 0; i < stroke.cells.length; i++) if (stroke.cells[i][0] === cell[0] && stroke.cells[i][1] === cell[1]) return;
    if (strokeAccepts(cell)) stroke.cells.push(cell);
  }
  function onPointerDown(e) {
    if (!view || !view.editable || (e.button !== 0 && e.button !== 2)) return;
    var cell = cellFromEvent(e);
    if (!cell) return;
    if (geom.scroll && e.pointerType === "touch") {
      // a scrolling board keeps the touch for panning: a quick tap marks the cell instead (see onPointerUp)
      stroke = { tap: true, start: cell, cells: [], val: 0, s0: UNKNOWN };
      return;
    }
    e.preventDefault();
    cursor = { r: cell[0], c: cell[1] };
    var useDot = e.button === 2 || e.shiftKey || e.altKey || mode === "dot";
    var markChar = useDot ? DOT : FILLED;
    var s0 = cellState(cell[0], cell[1]);
    stroke = { val: s0 === markChar ? 0 : (useDot ? 2 : 1), s0: s0, start: cell, last: cell, cells: [cell], axis: null };
    try { $("board").setPointerCapture(e.pointerId); } catch (err) { /* not essential */ }
    $("board").focus({ preventScroll: true });
    drawPreview();
    drawCursor();
  }
  function onPointerMove(e) {
    if (!stroke || stroke.tap) return;
    var cell = cellFromEvent(e);
    if (!cell) return;
    if (!stroke.axis && (cell[0] !== stroke.start[0] || cell[1] !== stroke.start[1])) {
      stroke.axis = Math.abs(cell[0] - stroke.start[0]) >= Math.abs(cell[1] - stroke.start[1]) ? "col" : "row";
    }
    if (stroke.axis === "row") cell = [stroke.start[0], cell[1]];
    else if (stroke.axis === "col") cell = [cell[0], stroke.start[1]];
    if (cell[0] === stroke.last[0] && cell[1] === stroke.last[1]) return;
    // fill in any cells a fast drag skipped, along the locked line
    var r = stroke.last[0], c = stroke.last[1];
    while (r !== cell[0] || c !== cell[1]) {
      r += Math.sign(cell[0] - r);
      c += Math.sign(cell[1] - c);
      strokeAdd([r, c]);
    }
    stroke.last = cell;
    cursor = { r: cell[0], c: cell[1] };
    drawPreview();
    drawCursor();
  }
  function onPointerUp(e) {
    if (!stroke) return;
    var done = stroke;
    stroke = null;
    if (done.tap) {
      var cell = cellFromEvent(e);
      if (cell && cell[0] === done.start[0] && cell[1] === done.start[1]) markCell(cell, mode === "dot" ? DOT : FILLED);
      return;
    }
    drawPreview();
    sendPaint(done.cells, done.val);
  }
  function onPointerCancel() { stroke = null; drawPreview(); }

  // ---- input: keyboard and buttons ---------------------------------------------------------------------
  function sendPaint(cells, value) {
    if (!cells.length) return;
    send({ action: "paint", cells: cells, value: value });
  }
  function markCell(cell, markChar) {
    if (!view.editable) { showToast("This picture is hung. Press Solve it again to try a fresh frame."); return; }
    cursor = { r: cell[0], c: cell[1] };
    var same = cellState(cell[0], cell[1]) === markChar;
    sendPaint([cell], same ? 0 : (markChar === FILLED ? 1 : 2));
  }
  function setMode(next) {
    mode = next;
    $("mode-fill-button").setAttribute("aria-pressed", String(mode === "fill"));
    $("mode-dot-button").setAttribute("aria-pressed", String(mode === "dot"));
  }
  function moveCursor(dr, dc, paint) {
    var p = view.picture;
    var r = Math.max(0, Math.min(p.height - 1, cursor.r + dr));
    var c = Math.max(0, Math.min(p.width - 1, cursor.c + dc));
    if (r === cursor.r && c === cursor.c) { announce("Edge of the frame."); return; }
    cursor = { r: r, c: c };
    if (paint && view.editable && cellState(r, c) === UNKNOWN) {
      sendPaint([[r, c]], mode === "dot" ? 2 : 1);
      return;
    }
    drawBoard();
    renderCursorLine();
    announce(cursorWords());
  }
  function onBoardKey(e) {
    if (!view) return;
    var key = e.key;
    var cmd = e.ctrlKey || e.metaKey;
    if (cmd && (key === "z" || key === "Z")) { e.preventDefault(); send({ action: e.shiftKey ? "redo" : "undo" }); return; }
    if (cmd && (key === "y" || key === "Y")) { e.preventDefault(); send({ action: "redo" }); return; }
    if (cmd || e.altKey) return;
    var handled = true;
    if (key === "ArrowUp") moveCursor(-1, 0, e.shiftKey);
    else if (key === "ArrowDown") moveCursor(1, 0, e.shiftKey);
    else if (key === "ArrowLeft") moveCursor(0, -1, e.shiftKey);
    else if (key === "ArrowRight") moveCursor(0, 1, e.shiftKey);
    else if (key === "Home") { cursor.c = 0; drawBoard(); renderCursorLine(); announce(cursorWords()); }
    else if (key === "End") { cursor.c = view.picture.width - 1; drawBoard(); renderCursorLine(); announce(cursorWords()); }
    else if (key === " " || key === "Enter") markCell([cursor.r, cursor.c], mode === "dot" ? DOT : FILLED);
    else if (key === "f" || key === "F") { setMode("fill"); announce("Fill tool."); }
    else if (key === "x" || key === "X") { setMode("dot"); announce("Dot tool."); }
    else if (key === "Backspace" || key === "Delete") { if (view.editable && cellState(cursor.r, cursor.c) !== UNKNOWN) sendPaint([[cursor.r, cursor.c]], 0); }
    else handled = false;
    if (handled) e.preventDefault();
  }
  function lineCells(kind) {
    var p = view.picture, out = [], i;
    if (kind === "row") for (i = 0; i < p.width; i++) out.push([cursor.r, i]);
    else if (kind === "col") for (i = 0; i < p.height; i++) out.push([i, cursor.c]);
    else for (var r = 0; r < p.height; r++) for (var c = 0; c < p.width; c++) out.push([r, c]);
    return out;
  }

  // ---- the frame header and the hung card ---------------------------------------------------------------
  function frameList() {
    var out = [];
    view.galleries.forEach(function (g) { if (g.open) g.frames.forEach(function (f) { out.push(f); }); });
    return out;
  }
  function renderFrame() {
    var p = view.picture;
    setText($("frame-kicker"), p.gallery + " · frame " + p.number + " of " + p.of + " · " + p.width + " by " + p.height);
    setText($("frame-heading"), p.status === "open" ? "Frame " + p.number : (p.title || "Frame " + p.number));
    var caption = p.status === "solved" ? p.caption : p.status === "redo" ? "Hung already. You are solving it again from a blank frame." : "Fill the grid from its clues to see what hangs here.";
    setText($("frame-caption"), caption);
    var list = frameList();
    var idx = list.findIndex(function (f) { return f.current; });
    $("prev-frame-button").disabled = idx <= 0;
    $("next-frame-button").disabled = idx < 0 || idx >= list.length - 1;
    $("undo-button").disabled = !view.can_undo;
    $("redo-button").disabled = !view.can_redo;
    ["clear-row-button", "clear-col-button", "clear-all-button"].forEach(function (id) { $(id).disabled = !view.editable; });
    var card = $("hung-card");
    var hung = p.status === "solved";
    card.hidden = !hung;
    if (hung) {
      setText($("hung-title"), p.title + " is hung on the wall");
      setText($("hung-text"), p.caption + " Solved in " + plural(p.moves, "stroke", "strokes") + ". " + (view.totals.hung < view.totals.pictures ? "" : "Every picture is hung."));
    }
    $("assist-check-checkbox").checked = view.assist.check;
    $("assist-autodot-checkbox").checked = view.assist.autodot;
    $("assist-focus-checkbox").checked = view.assist.focus;
  }

  // ---- the gallery wall and the large view ---------------------------------------------------------------
  function hungList() {
    var out = [];
    view.galleries.forEach(function (g) { g.frames.forEach(function (f) { if (f.hung) out.push(f); }); });
    return out;
  }
  function renderWall() {
    var sig = JSON.stringify(view.galleries.map(function (g) { return [g.open, g.need, g.frames.map(function (f) { return (f.hung ? "h" : "u") + (f.current ? "*" : ""); }).join("")]; }));
    if (sig === wallSig) return;
    wallSig = sig;
    var wall = $("wall");
    wall.textContent = "";
    view.galleries.forEach(function (g, gi) {
      var block = el("section", "gallery-block" + (g.open ? "" : " locked"));
      block.setAttribute("aria-label", g.name);
      block.appendChild(el("h3", null, g.name + " (" + g.hung + " of " + g.total + " hung)"));
      block.appendChild(el("p", "note blurb", g.blurb));
      if (!g.open) block.appendChild(el("p", "note", "Opens when " + plural(g.need, "more picture", "more pictures") + " in " + g.after + " " + (g.need === 1 ? "is" : "are") + " hung."));
      var list = el("ul", "frames");
      g.frames.forEach(function (f) {
        var li = el("li");
        var b = el("button", "frame-btn " + (f.hung ? "hung" : "dark") + (f.current ? " current" : ""));
        b.type = "button";
        b.dataset.testid = "picture-grid-frame-" + f.id;
        b.dataset.id = f.id;
        if (f.hung) {
          b.appendChild(pixelSvgThumb(f));
          b.appendChild(el("span", "fb-name", f.title));
          b.appendChild(el("span", "fb-meta", f.size + " · " + plural(f.moves, "stroke", "strokes")));
          b.setAttribute("aria-label", g.name + " " + (f.number) + ", " + f.title + ", hung, solved in " + plural(f.moves, "stroke", "strokes") + ". Opens it large.");
        } else {
          b.appendChild(el("span", "thumb-dark", String(f.number)));
          b.appendChild(el("span", "fb-name", g.open ? "Not hung yet" : "Locked"));
          b.appendChild(el("span", "fb-meta", f.size));
          b.setAttribute("aria-label", g.name + " " + f.number + ", " + (g.open ? "not hung yet, " + f.size + ". Go to this frame." : "locked, " + f.size));
          if (!g.open) b.setAttribute("aria-disabled", "true");
        }
        b.addEventListener("click", function () { onFrameClick(f, g); });
        li.appendChild(b);
        list.appendChild(li);
      });
      block.appendChild(list);
      wall.appendChild(block);
    });
    $("gallery-toggle-button").textContent = "Gallery (" + view.totals.hung + "/" + view.totals.pictures + ")";
  }
  function pixelSvgThumb(f) {
    var svg = pixelSvg(f.rows, f.tint, null, true);
    svg.setAttribute("class", svg.getAttribute("class") + " thumb");
    return svg;
  }
  function onFrameClick(f, g) {
    if (!g.open) { send({ action: "pick", picture: f.id }); return; }
    if (f.hung) { openLarge(f.id); return; }
    send({ action: "pick", picture: f.id });
    closeGalleryToFrame();
  }
  function closeGalleryToFrame() {
    setPanel("gallery-panel", "gallery-toggle-button", false);
    var anchor = $("frame-panel");
    if (anchor.scrollIntoView) anchor.scrollIntoView({ block: "start" });
    $("board").focus({ preventScroll: true });
  }
  function openLarge(id) {
    largeId = id;
    renderLarge();
    var node = $("large-view");
    node.hidden = false;
    if (node.scrollIntoView) node.scrollIntoView({ block: "nearest" });
    node.focus({ preventScroll: true });
  }
  function renderLarge() {
    var node = $("large-view");
    if (!largeId) { node.hidden = true; return; }
    var list = hungList();
    var f = list.filter(function (x) { return x.id === largeId; })[0];
    if (!f) { largeId = null; node.hidden = true; return; }
    var idx = list.indexOf(f);
    setText($("large-title"), f.title);
    var holder = $("large-picture");
    holder.textContent = "";
    holder.appendChild(pixelSvg(f.rows, f.tint, f.title + ", a " + f.size + " pixel picture", true));
    setText($("large-caption"), f.caption);
    setText($("large-meta"), f.size + " · solved in " + plural(f.moves, "stroke", "strokes") + " · picture " + (idx + 1) + " of " + list.length + " hung");
    setText($("large-words"), pictureWords(f.rows));
    $("large-prev-button").disabled = list.length < 2;
    $("large-next-button").disabled = list.length < 2;
  }
  function stepLarge(delta) {
    var list = hungList();
    var idx = list.findIndex(function (x) { return x.id === largeId; });
    if (idx < 0 || !list.length) return;
    largeId = list[(idx + delta + list.length) % list.length].id;
    renderLarge();
  }

  // ---- render ---------------------------------------------------------------------------------------
  function render() {
    var p = view.picture;
    if (p.id !== boardId) {
      boardId = p.id;
      cursor = { r: 0, c: 0 };
      stroke = null;
    }
    renderStats();
    renderFrame();
    drawBoard();
    renderCursorLine();
    renderClueText();
    renderWall();
    renderLarge();
    if (view.just && glowShown !== view.just.id + ":" + view.totals.hung) {
      glowShown = view.just.id + ":" + view.totals.hung;
      var board = $("board");
      board.classList.add("hung-glow");
    }
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
  function announceChanges(request, previous) {
    var parts = [];
    if (request.action === "paint" || request.action === "undo" || request.action === "redo") {
      if (previous && previous.picture.id === view.picture.id) {
        view.satisfied.rows.forEach(function (ok, r) { if (ok && !previous.satisfied.rows[r]) parts.push("Row " + (r + 1) + " done."); });
        view.satisfied.cols.forEach(function (ok, c) { if (ok && !previous.satisfied.cols[c]) parts.push("Column " + (c + 1) + " done."); });
      }
      if (view.assist.check && view.wrong.length) parts.push(plural(view.wrong.length, "cell is", "cells are") + " marked as a mistake.");
      if (!parts.length) parts.push(cursorWords());
      if (view.just) parts = [view.message];
    } else if (request.action === "pick" || request.action === "next") {
      parts.push(view.picture.gallery + " frame " + view.picture.number + ", " + view.picture.size + ".");
    }
    if (parts.length) announce(parts.join(" "));
  }
  function send(request, quiet) {
    if (!engine) return null;
    var result = JSON.parse(engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    var previous = view;
    view = result;
    if (!quiet) showToast("");
    if (view.message && (!view.ok || (view.just && request.action === "paint") || request.action === "reset" || request.action === "retry")) showToast(view.message);
    render();
    announceChanges(request, previous);
    if (["paint", "undo", "redo", "pick", "next", "assist", "retry", "reset"].indexOf(request.action) >= 0) persist();
    return result;
  }
  function askThen(id, message, confirmLabel, go) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: false, onConfirm: go });
    else go();
  }
  function stepFrame(delta) {
    var list = frameList();
    var idx = list.findIndex(function (f) { return f.current; });
    var target = list[idx + delta];
    if (target) send({ action: "pick", picture: target.id });
  }

  function wire() {
    $("toast").addEventListener("click", function () { showToast(""); });
    wirePanelToggle("gallery-toggle-button", "gallery-panel");
    var board = $("board");
    board.addEventListener("pointerdown", onPointerDown);
    board.addEventListener("pointermove", onPointerMove);
    board.addEventListener("pointerup", onPointerUp);
    board.addEventListener("pointercancel", onPointerCancel);
    board.addEventListener("lostpointercapture", function () { if (stroke && !stroke.tap) { onPointerCancel(); } });
    board.addEventListener("contextmenu", function (e) { e.preventDefault(); });
    board.addEventListener("keydown", onBoardKey);
    board.addEventListener("animationend", function () { board.classList.remove("hung-glow"); });
    board.addEventListener("focus", function () { if (view) { renderCursorLine(); } });
    $("mode-fill-button").addEventListener("click", function () { setMode("fill"); });
    $("mode-dot-button").addEventListener("click", function () { setMode("dot"); });
    $("undo-button").addEventListener("click", function () { send({ action: "undo" }); });
    $("redo-button").addEventListener("click", function () { send({ action: "redo" }); });
    $("clear-row-button").addEventListener("click", function () { sendPaint(lineCells("row"), 0); });
    $("clear-col-button").addEventListener("click", function () { sendPaint(lineCells("col"), 0); });
    $("clear-all-button").addEventListener("click", function () { sendPaint(lineCells("all"), 0); });
    $("prev-frame-button").addEventListener("click", function () { stepFrame(-1); });
    $("next-frame-button").addEventListener("click", function () { stepFrame(1); });
    $("hung-next-button").addEventListener("click", function () { send({ action: "next" }); $("board").focus({ preventScroll: true }); });
    $("hung-retry-button").addEventListener("click", function () { send({ action: "retry" }); $("board").focus({ preventScroll: true }); });
    $("hung-gallery-button").addEventListener("click", function () {
      setPanel("gallery-panel", "gallery-toggle-button", true);
      if ($("gallery-panel").scrollIntoView) $("gallery-panel").scrollIntoView({ block: "start" });
    });
    $("large-prev-button").addEventListener("click", function () { stepLarge(-1); });
    $("large-next-button").addEventListener("click", function () { stepLarge(1); });
    $("large-close-button").addEventListener("click", function () { largeId = null; renderLarge(); $("gallery-toggle-button").focus(); });
    $("large-play-button").addEventListener("click", function () {
      var id = largeId;
      if (!id) return;
      send({ action: "pick", picture: id });
      send({ action: "retry" });
      largeId = null;
      closeGalleryToFrame();
    });
    [["assist-check-checkbox", "check"], ["assist-autodot-checkbox", "autodot"], ["assist-focus-checkbox", "focus"]].forEach(function (pair) {
      $(pair[0]).addEventListener("change", function () { send({ action: "assist", name: pair[1], on: $(pair[0]).checked }); });
    });
    $("reset-button").addEventListener("click", function () {
      askThen("picture-grid-reset", "Start the whole gallery over? Every hung picture and your tally will be taken down.", "Take it all down", function () { largeId = null; wallSig = ""; send({ action: "reset" }); });
    });
    // The save widget loads a save straight into the engine; this redraws afterwards.
    window.pictureGridRefresh = function () { if (engine) { boardId = null; wallSig = ""; send({ action: "open" }); } };
    var resizeTimer = null;
    var relayout = function () { clearTimeout(resizeTimer); resizeTimer = setTimeout(function () { if (view) drawBoard(); }, 80); };
    window.addEventListener("resize", relayout);
    document.addEventListener("picture-grid-layout", relayout);
  }

  async function boot() {
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
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The gallery could not open (" + err + "). Reload to try again.";
  });
})();
