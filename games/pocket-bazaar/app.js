/* Pocket Bazaar view: glue only. The engine (game.py and its modules) holds every rule; this file draws what
   handle() returns and forwards what the player does. No game logic lives here (the one exception is "which
   cells could this good merge with", which the engine sends as `partners`). */
(function () {
  "use strict";
  var ENGINE_MODULES = ["goods.py", "rng.py", "board.py"];
  var STORE_KEY = "pocket-bazaar:state";
  var DRAG_THRESHOLD = 8;

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;
  var view = null;
  var selected = null;       // the cell number of the picked-up good
  var cursor = 0;            // the cell the arrow keys are on (roving tab stop)
  var broomArmed = false;
  var activeCrate = 0;
  var cellEls = [];
  var shelfEl = null;
  var drag = null;
  var suppressClick = false;

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

  // ---- drawing a good ------------------------------------------------------------------------
  function goodNode(cell) {
    var wrap = el("span", "good shape-" + cell.shape + " fam-" + cell.family + " t" + cell.tier);
    wrap.appendChild(el("span", "good-shape"));
    wrap.appendChild(el("span", "good-text", cell.letter + (cell.family === "wild" ? "" : cell.tier)));
    var pips = el("span", "pips");
    pips.setAttribute("aria-hidden", "true");
    if (cell.tier >= 5) pips.appendChild(el("span", "pip star", "★"));
    else for (var i = 0; i < cell.tier; i++) pips.appendChild(el("span", "pip"));
    wrap.appendChild(pips);
    return wrap;
  }

  // ---- the grid ------------------------------------------------------------------------------
  function makeCell(i, label) {
    var b = el("button", "cell");
    b.type = "button";
    b.dataset.cell = i;
    b.dataset.drop = "cell:" + i;
    b.dataset.testid = "pocket-bazaar-cell-" + i;
    b.dataset.label = label;
    b.tabIndex = -1;
    b.addEventListener("click", function () { if (suppressClick) return; onCell(i); });
    return b;
  }

  function ensureGrid(b) {
    var grid = $("board");
    var sig = b.w + "x" + b.h + (b.shelf ? "s" : "");
    if (grid.dataset.signature === sig) return;
    grid.textContent = "";
    cellEls = [];
    grid.style.setProperty("--cols", b.w);
    for (var i = 0; i < b.w * b.h; i++) {
      var row = Math.floor(i / b.w) + 1, col = (i % b.w) + 1;
      var c = makeCell(i, "Row " + row + ", column " + col);
      cellEls.push(c);
      grid.appendChild(c);
    }
    var slot = $("shelf-slot");
    slot.textContent = "";
    shelfEl = null;
    if (b.shelf) {
      slot.hidden = false;
      slot.appendChild(el("div", null, "Shelf"));
      shelfEl = makeCell(b.w * b.h, "Shelf");
      shelfEl.tabIndex = 0;
      slot.appendChild(shelfEl);
    } else {
      slot.hidden = true;
    }
    grid.dataset.signature = sig;
    cursor = Math.min(cursor, b.w * b.h - 1);
  }

  function cellButton(i) { return i < cellEls.length ? cellEls[i] : shelfEl; }
  function cellAt(i) { return view && view.board.cells[i] ? view.board.cells[i] : null; }

  function renderBoard() {
    var b = view.board;
    ensureGrid(b);
    var partners = selected !== null && view.partners[String(selected)] ? view.partners[String(selected)] : [];
    if (selected !== null && !cellAt(selected)) selected = null;
    b.cells.forEach(function (cell, i) {
      var btn = cellButton(i);
      if (!btn) return;
      var sig = cell ? cell.code : "";
      if (btn.dataset.sig !== sig) {
        btn.textContent = "";
        if (cell) btn.appendChild(goodNode(cell));
        btn.dataset.sig = sig;
      }
      btn.classList.toggle("has-good", Boolean(cell));
      btn.classList.toggle("selected", selected === i);
      btn.classList.toggle("partner", partners.indexOf(i) !== -1);
      btn.classList.toggle("broom-armed", broomArmed);
      var label = btn.dataset.label + ": " + (cell ? cell.label : "empty");
      if (selected === i) label += ", picked up";
      if (partners.indexOf(i) !== -1) label += ", would merge";
      btn.setAttribute("aria-label", label);
      btn.setAttribute("aria-pressed", selected === i ? "true" : "false");
      if (i < cellEls.length) btn.tabIndex = i === cursor ? 0 : -1;
    });
  }

  function renderCrates() {
    var holder = $("crates");
    var sig = view.crates.map(function (c) { return c.family; }).join(",");
    if (holder.dataset.signature !== sig) {
      holder.textContent = "";
      view.crates.forEach(function (crate, n) {
        var btn = el("button", "crate-btn");
        btn.type = "button";
        btn.dataset.family = crate.family;
        btn.dataset.testid = "pocket-bazaar-crate-" + crate.family;
        var icon = el("span", "crate-icon good shape-" + crate.shape + " fam-" + crate.family);
        icon.setAttribute("aria-hidden", "true");
        icon.appendChild(el("span", "good-shape"));
        icon.appendChild(el("span", "good-text", crate.letter));
        btn.appendChild(icon);
        btn.appendChild(el("span", null, crate.name));
        btn.setAttribute("aria-label", crate.name + " crate, key " + (n + 1));
        btn.addEventListener("click", function () { activeCrate = n; send({ action: "crate", family: crate.family }); });
        holder.appendChild(btn);
      });
      holder.dataset.signature = sig;
    }
    Array.prototype.forEach.call(holder.children, function (btn, n) { btn.classList.toggle("active", n === activeCrate); });
  }

  function renderInfo() {
    var info = $("selection-info");
    var cell = selected !== null ? cellAt(selected) : null;
    var text;
    if (broomArmed) {
      text = "Broom ready: tap a good to sweep it away for free. Esc puts the broom down.";
    } else if (cell) {
      text = cell.label + " picked up.";
      if (cell.family !== "wild" && cell.tier < 5) {
        var has = (view.partners[String(selected)] || []).length > 0;
        text += has ? " Tap a marked match (+) to merge it into " + cell.next + "." : " No match yet: it needs another " + cell.name + " to become " + cell.next + ".";
      } else if (cell.family === "wild") {
        text += " A wildcard merges with any good below a showpiece.";
      } else {
        text += " A showpiece: it does not merge any further.";
      }
      text += " Sells for " + cell.sell + (cell.sell === 1 ? " coin." : " coins.");
    } else {
      text = view.full ? "The counter is full. Merge, sell or sweep something to make room." : "Open a crate to put a good on the counter. Two identical goods merge into a better one.";
    }
    setText(info, text);
    var sell = $("sell-button");
    setText(sell, cell ? "Sell (" + cell.sell + ")" : "Sell");
    $("broom-button").setAttribute("aria-pressed", broomArmed ? "true" : "false");
  }

  function bumpStat(id, value) {
    var node = $(id);
    var next = String(value);
    if (node.textContent === next) return;
    var had = node.textContent !== "" && node.dataset.seen === "1";
    node.textContent = next;
    node.dataset.seen = "1";
    if (had) {
      node.classList.remove("bump");
      void node.offsetWidth;
      node.classList.add("bump");
    }
  }
  function renderStats() {
    bumpStat("stat-coins", view.coins);
    bumpStat("stat-crates", view.tally.crates);
    bumpStat("stat-merges", view.tally.merges);
    bumpStat("stat-chain", view.best_chain);
    bumpStat("stat-sold", view.tally.sold);
    bumpStat("stat-swept", view.tally.swept);
  }

  function showMessage(text, ok) {
    var m = $("message");
    setText(m, text || "");
    m.classList.toggle("refused", ok === false && Boolean(text));
  }

  function render(event) {
    renderBoard();
    renderCrates();
    renderInfo();
    renderStats();
    if (event && (event.kind === "merge" || event.kind === "crate")) {
      var target = cellButton(event.kind === "merge" ? event.dst : event.at);
      if (target) {
        target.classList.remove("pop");
        void target.offsetWidth;
        target.classList.add("pop");
        setTimeout(function () { target.classList.remove("pop"); }, 600);
      }
    }
  }

  // ---- talking to the engine -----------------------------------------------------------------
  function persist() {
    try {
      var proxy = engine.getState();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(STORE_KEY, JSON.stringify(obj));
    } catch (e) { /* the save is a convenience until the save widget is wired */ }
  }
  function send(request) {
    if (!engine) return null;
    var result = JSON.parse(engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    view = result;
    if (request.action === "drop" || request.action === "sell" || request.action === "broom") selected = null;
    render(result.event);
    showMessage(result.message, result.ok);
    if (result.message) announce(result.message);
    persist();
    return result;
  }

  // ---- what taps do --------------------------------------------------------------------------
  function select(i) {
    selected = i;
    broomArmed = false;
    if (i !== null && i < cellEls.length) cursor = i;
    render();
    if (i !== null) announce((cellAt(i) ? cellAt(i).label : "") + " picked up");
  }
  function onCell(i) {
    var g = cellAt(i);
    cursor = i < cellEls.length ? i : cursor;
    if (broomArmed) {
      if (g) send({ action: "broom", at: i }); else showMessage("There is nothing there to sweep.", false);
      return;
    }
    if (selected === null) { if (g) select(i); return; }
    if (selected === i) { select(null); return; }
    var partners = view.partners[String(selected)] || [];
    if (!g || partners.indexOf(i) !== -1) { send({ action: "drop", from: selected, to: i }); return; }
    select(i);                                   // a different good: change the pick instead of swapping by accident
  }
  function doSell() {
    if (selected === null) { showMessage("Pick up a good first (tap it), then press Sell.", false); return; }
    send({ action: "sell", at: selected });
  }
  function doBroom() {
    if (selected !== null) { send({ action: "broom", at: selected }); return; }
    broomArmed = !broomArmed;
    render();
    announce(broomArmed ? "Broom ready. Tap a good to sweep it away." : "Broom put down.");
  }
  function letGo() {
    broomArmed = false;
    select(null);
  }

  // ---- dragging (pointer events: the same code serves a mouse, a finger and a pen) -----------------
  function dropTargetAt(x, y) {
    var node = document.elementFromPoint(x, y);
    return node ? node.closest("[data-drop]") : null;
  }
  function clearOver() {
    Array.prototype.forEach.call(document.querySelectorAll(".drop-over"), function (n) { n.classList.remove("drop-over"); });
  }
  function onPointerDown(e) {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    var btn = e.target.closest("[data-cell]");
    if (!btn || broomArmed) return;
    var i = Number(btn.dataset.cell);
    if (!cellAt(i)) return;
    drag = { from: i, x: e.clientX, y: e.clientY, active: false, id: e.pointerId, ghost: null };
  }
  function onPointerMove(e) {
    if (!drag || e.pointerId !== drag.id) return;
    if (!drag.active) {
      if (Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y) < DRAG_THRESHOLD) return;
      drag.active = true;
      select(drag.from);
      var cell = cellAt(drag.from);
      drag.ghost = goodNode(cell);
      drag.ghost.classList.add("dragging-ghost");
      document.body.appendChild(drag.ghost);
    }
    e.preventDefault();
    drag.ghost.style.left = e.clientX + "px";
    drag.ghost.style.top = e.clientY + "px";
    clearOver();
    var target = dropTargetAt(e.clientX, e.clientY);
    if (target) target.classList.add("drop-over");
  }
  function endDrag(e, cancelled) {
    if (!drag || (e && e.pointerId !== drag.id)) return;
    var d = drag;
    drag = null;
    if (!d.active) return;
    if (d.ghost && d.ghost.parentNode) d.ghost.parentNode.removeChild(d.ghost);
    clearOver();
    suppressClick = true;
    setTimeout(function () { suppressClick = false; }, 0);
    if (cancelled) return;
    var target = dropTargetAt(e.clientX, e.clientY);
    if (!target) { select(null); return; }
    var spec = target.dataset.drop;
    if (spec === "sell") send({ action: "sell", at: d.from });
    else if (spec === "broom") send({ action: "broom", at: d.from });
    else if (spec.indexOf("cell:") === 0) {
      var to = Number(spec.slice(5));
      if (to === d.from) select(d.from); else send({ action: "drop", from: d.from, to: to });
    } else select(null);
  }

  // ---- the keyboard --------------------------------------------------------------------------
  function moveCursor(dx, dy) {
    var b = view.board;
    var row = Math.floor(cursor / b.w), col = cursor % b.w;
    row = Math.max(0, Math.min(b.h - 1, row + dy));
    col = Math.max(0, Math.min(b.w - 1, col + dx));
    cursor = row * b.w + col;
    renderBoard();
    cellEls[cursor].focus();
  }
  function onKey(e) {
    if (!view || e.ctrlKey || e.metaKey || e.altKey) return;
    var tag = e.target && e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    var onGrid = e.target && e.target.closest && e.target.closest("#board");
    var key = e.key;
    if (onGrid && key.indexOf("Arrow") === 0) {
      e.preventDefault();
      moveCursor(key === "ArrowRight" ? 1 : key === "ArrowLeft" ? -1 : 0, key === "ArrowDown" ? 1 : key === "ArrowUp" ? -1 : 0);
      return;
    }
    if (key === "Escape") { letGo(); return; }
    if (key === "b" || key === "B") { e.preventDefault(); if (onGrid && selected === null && cellAt(cursor)) send({ action: "broom", at: cursor }); else doBroom(); return; }
    if (key === "s" || key === "S") { e.preventDefault(); if (selected === null && onGrid && cellAt(cursor)) select(cursor); doSell(); return; }
    if (key === "c" || key === "C") {
      e.preventDefault();
      activeCrate = (activeCrate + 1) % view.crates.length;
      renderCrates();
      $("crates").children[activeCrate].focus();
      return;
    }
    if (/^[1-9]$/.test(key) && Number(key) <= view.crates.length) {
      e.preventDefault();
      activeCrate = Number(key) - 1;
      send({ action: "crate", family: view.crates[activeCrate].family });
    }
  }

  function wire() {
    $("sell-button").addEventListener("click", doSell);
    $("broom-button").addEventListener("click", doBroom);
    var grid = $("counter");
    grid.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove, { passive: false });
    window.addEventListener("pointerup", function (e) { endDrag(e, false); });
    window.addEventListener("pointercancel", function (e) { endDrag(e, true); });
    document.addEventListener("keydown", onKey);
    // The save widget (a later milestone) loads a save straight into the engine; this redraws afterwards.
    window.pocketBazaarRefresh = function () { if (engine) { selected = null; send({ action: "open" }); } };
  }

  function setBusy(busy) {
    Array.prototype.forEach.call(document.querySelectorAll(".crate-btn, #sell-button, #broom-button"), function (b) { b.disabled = busy; });
  }

  async function boot() {
    var pyodide = await window.loadPyodide();
    for (var i = 0; i < ENGINE_MODULES.length; i++) {
      var source = await (await fetch(ENGINE_MODULES[i])).text();
      pyodide.FS.writeFile(ENGINE_MODULES[i], source, { encoding: "utf8" });
    }
    await pyodide.runPythonAsync(await (await fetch("game.py")).text());
    window.pyodide = pyodide;   // the shared save widget looks for it
    engine = { handle: pyodide.globals.get("handle"), getState: pyodide.globals.get("get_state"), loadState: pyodide.globals.get("load_state") };
    var saved = lsGet(STORE_KEY);
    if (saved) {
      try { engine.loadState(pyodide.toPy(JSON.parse(saved))); } catch (e) { /* a bad save never blocks play */ }
    }
    $("engine-status").textContent = "";
    send({ action: "open" });
    setBusy(false);
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The stall could not open (" + err + "). Reload to try again.";
  });
})();
