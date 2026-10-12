/* Reaction Bench view: glue only. The engine (game.py and its modules) holds every rule; this file draws what handle() returns as
   flasks, dials, an atom ledger, a shelf and a periodic table, and turns pointer, touch and keyboard input into requests. It never
   decides whether an equation balances or whether a product list is right: it asks the engine and draws the answer. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["elements.py", "chem.py", "reactions_c1.py", "reactions_c2.py", "reactions_c3.py", "reactions_c4.py", "reactions_c5.py", "reactions.py", "info.py", "hints.py", "goals.py"];
  var STORE_KEY = "reaction-bench:state";
  var BACKUP_KEY = "reaction-bench:state-backup";
  var FENNEL_KEY = "reaction-bench:fennel-hidden";
  var HINTS_KEY = "reaction-bench:hints-hidden";
  var PUBCHEM_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/periodictable/JSON";
  var DIFF_GAME = "reaction-bench";
  var SVG_NS = "http://www.w3.org/2000/svg";

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;
  var view = null;
  var eqSig = "";              // what the equation row is currently built for
  var listSig = { orders: "", shelf: "", table: "", choice: "" };
  var cardSymbol = null;       // the element card that is open
  var glowShown = "";
  var infoLiveDone = false;
  var flaskCount = 0;
  var wasBalanced = false;
  var goalsPanel = null;
  var live = { state: "idle", rows: null, date: "" };      // the PubChem periodic table, read live the first time a card is wanted

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }
  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }
  function announce(text) {
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

  // ---- panels --------------------------------------------------------------------------------------
  function setPanel(panelId, buttonId, open) {
    $(panelId).hidden = !open;
    $(buttonId).setAttribute("aria-expanded", String(open));
  }
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () { setPanel(panelId, buttonId, $(panelId).hidden); });
  }

  // ---- formulas: elements with subscripts, bracket groups drawn as a bracket ----------------------------
  function appendTree(parent, tree) {
    tree.forEach(function (part) {
      if (part.t === "el") {
        parent.appendChild(document.createTextNode(part.sym));
        if (part.n > 1) parent.appendChild(el("sub", null, String(part.n)));
      } else {
        var group = el("span", "grp");
        group.appendChild(el("span", "br", "("));
        appendTree(group, part.parts);
        group.appendChild(el("span", "br", ")"));
        parent.appendChild(group);
        if (part.n > 1) parent.appendChild(el("sub", null, String(part.n)));
      }
    });
  }
  function formulaNode(sp) {
    var node = el("span", "formula");
    node.setAttribute("aria-label", sp.name + ", " + sp.formula);
    appendTree(node, sp.tree);
    return node;
  }

  // ---- flasks (drawn by code): conical for what goes in, round for what comes out -------------------
  var CONE = "M30 6H50V34L74 80Q76 84 72 84H8Q4 84 6 80L30 34Z";
  var ROUND = "M32 6H48V31.2A28 28 0 1 1 32 31.2Z";
  function flaskSvg(role, coef, full) {
    var svg = svgEl("svg", { viewBox: "0 0 80 90", "class": "flask", "aria-hidden": "true", focusable: "false" });
    var id = "flask-clip-" + (flaskCount++);
    var path = role === "product" ? ROUND : CONE;
    var defs = svgEl("defs", null, svg);
    var clip = svgEl("clipPath", { id: id }, defs);
    svgEl("path", { d: path }, clip);
    var level = full ? 0.85 : coef === undefined ? 0 : 0.12 + 0.8 * (coef - 1) / 11;
    var top = role === "product" ? 86 - level * 56 : 84 - level * 50;
    if (level > 0) {
      var g = svgEl("g", { "clip-path": "url(#" + id + ")" }, svg);
      svgEl("rect", { x: 0, y: top, width: 80, height: 90 - top, "class": role === "product" ? "flask-liquid-out" : "flask-liquid-in" }, g);
      if (role !== "product") for (var x = -40; x < 90; x += 9) svgEl("line", { x1: x, y1: 90, x2: x + 50, y2: top - 2, "class": "flask-hatch" }, g);
      svgEl("line", { x1: 0, y1: top, x2: 80, y2: top, "class": "flask-tick" }, g);
    }
    svgEl("path", { d: path, "class": "flask-glass" }, svg);
    svgEl("path", { d: role === "product" ? "M22 52Q24 42 32 38" : "M28 62L20 78", "class": "flask-glint", "stroke": "#fff", "stroke-width": 3, "fill": "none", "stroke-linecap": "round", opacity: 0.3 }, svg);
    return svg;
  }

  // ---- atom chips: a faceted shape and the symbol, never colour alone ------------------------------
  function shapePoints(kind, cx, cy, r) {
    var pts = [];
    var n = [0, 4, 3, 4, 5, 6][kind];
    var rot = [0, Math.PI / 4, -Math.PI / 2, 0, -Math.PI / 2, 0][kind];
    for (var i = 0; i < n; i++) {
      var a = rot + i * 2 * Math.PI / n;
      pts.push((cx + r * Math.cos(a)).toFixed(1) + "," + (cy + r * Math.sin(a)).toFixed(1));
    }
    return pts.join(" ");
  }
  var CHIP = 22, PER_ROW = 6, CHIP_CAP = 30;
  function trayNode(symbol, number, count) {
    var shown = Math.min(count, CHIP_CAP);
    var rows = Math.max(1, Math.ceil(shown / PER_ROW));
    var width = Math.min(Math.max(shown, 1), PER_ROW) * CHIP + (count > CHIP_CAP ? 34 : 0);
    var svg = svgEl("svg", { viewBox: "0 0 " + Math.max(width, CHIP) + " " + (rows * CHIP), width: Math.max(width, CHIP), height: rows * CHIP, "aria-hidden": "true", focusable: "false" });
    var kind = number % 6;
    for (var i = 0; i < shown; i++) {
      var cx = (i % PER_ROW) * CHIP + CHIP / 2, cy = Math.floor(i / PER_ROW) * CHIP + CHIP / 2;
      if (kind === 0) svgEl("circle", { cx: cx, cy: cy, r: 9.2, "class": "chip-body" }, svg);
      else svgEl("polygon", { points: shapePoints(kind, cx, cy, 10), "class": "chip-body" }, svg);
      svgEl("polygon", { points: shapePoints(kind, cx - 1, cy - 2, 5), "class": "chip-facet" }, svg);
      var t = svgEl("text", { x: cx, y: cy + 0.5, "class": "chip-letter" }, svg);
      t.textContent = symbol;
      if (symbol.length > 1) t.setAttribute("style", "font-size:9px");
    }
    if (count > CHIP_CAP) {
      var more = svgEl("text", { x: Math.min(shown, PER_ROW) * CHIP + 2, y: (rows - 0.5) * CHIP, "class": "chip-more" }, svg);
      more.textContent = "+" + (count - CHIP_CAP);
    }
    return svg;
  }

  // ---- stats -----------------------------------------------------------------------------------------
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
    bumpStat("stat-shelved", view.totals.shelved + "/" + view.totals.orders);
    bumpStat("stat-elements", view.totals.elements + "/" + view.totals.bench);
    bumpStat("stat-turns", view.totals.turns);
    bumpStat("stat-runs", view.totals.runs);
    bumpStat("stat-hints", view.totals.hints);
  }

  // ---- the equation row ------------------------------------------------------------------------------
  function dialLabel(sp) { return "Coefficient for " + sp.name + ", " + sp.formula; }
  function buildDial(sp, enabled) {
    var wrap = el("div", "dial" + (enabled ? "" : " off"));
    wrap.setAttribute("role", "group");
    wrap.setAttribute("aria-label", dialLabel(sp));
    var minus = el("button", null, "−");
    minus.type = "button"; minus.tabIndex = -1;
    minus.setAttribute("aria-label", "One fewer " + sp.formula);
    var val = el("span", "dial-val");
    val.setAttribute("role", "spinbutton");
    val.tabIndex = enabled ? 0 : -1;
    val.setAttribute("aria-label", dialLabel(sp));
    val.setAttribute("aria-valuemin", String(view.reaction.min));
    val.setAttribute("aria-valuemax", String(view.reaction.max));
    var plus = el("button", null, "+");
    plus.type = "button"; plus.tabIndex = -1;
    plus.setAttribute("aria-label", "One more " + sp.formula);
    minus.addEventListener("click", function () { turn(sp.index, -1); });
    plus.addEventListener("click", function () { turn(sp.index, 1); });
    val.addEventListener("keydown", function (e) { dialKey(e, sp.index); });
    wrap.appendChild(minus); wrap.appendChild(val); wrap.appendChild(plus);
    return wrap;
  }
  function turn(index, delta) { send({ action: "dial", index: index, delta: delta }); }
  function dialKey(e, index) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    var k = e.key, cur = view.reaction.species[index].coef;
    if (k === "ArrowUp" || k === "ArrowRight") send({ action: "dial", index: index, delta: 1 });
    else if (k === "ArrowDown" || k === "ArrowLeft") send({ action: "dial", index: index, delta: -1 });
    else if (k === "PageUp") send({ action: "dial", index: index, delta: 3 });
    else if (k === "PageDown") send({ action: "dial", index: index, delta: -3 });
    else if (k === "Home") send({ action: "dial", index: index, value: view.reaction.min });
    else if (k === "End") send({ action: "dial", index: index, value: view.reaction.max });
    else if (/^[1-9]$/.test(k)) send({ action: "dial", index: index, value: Number(k) });
    else return;
    e.preventDefault();
    e.stopPropagation();
    void cur;
  }
  function buildEquation() {
    var rx = view.reaction;
    var eq = $("equation");
    eq.textContent = "";
    var known = rx.picked;
    rx.species.forEach(function (sp, i) {
      // each sign travels with the formula after it, so a wrapped row can start with "+" or an arrow but never end with one
      var term = el("div", "term");
      if (sp.role === "product" && sp.index === rx.n_reactants) term.appendChild(el("span", "op", "→")).setAttribute("aria-hidden", "true");
      else if (i > 0) term.appendChild(el("span", "op", "+")).setAttribute("aria-hidden", "true");
      var box = el("div", "species");
      box.dataset.index = String(sp.index);
      box.appendChild(el("span", "role", sp.role === "reactant" ? (sp.carried ? "Goes in (carried over)" : "Goes in") : (sp.carried ? "Comes out (carried on)" : "Comes out")));
      var holder = el("div", "flask-holder");
      holder.appendChild(flaskSvg(sp.role, sp.coef));
      box.appendChild(holder);
      box.appendChild(buildDial(sp, known));
      box.appendChild(formulaNode(sp));
      box.appendChild(el("span", "sname", sp.name));
      term.appendChild(box);
      eq.appendChild(term);
    });
    if (!known) {
      var tail = el("div", "term");
      tail.appendChild(el("span", "op", "→")).setAttribute("aria-hidden", "true");
      var unk = el("div", "unknown-box");
      unk.appendChild(el("strong", null, "?"));
      unk.appendChild(el("span", "note", "Choose what comes out, just above."));
      tail.appendChild(unk);
      eq.appendChild(tail);
    }
  }
  function updateEquation() {
    var rx = view.reaction;
    var boxes = $("equation").querySelectorAll(".species");
    rx.species.forEach(function (sp, i) {
      var box = boxes[i];
      var val = box.querySelector(".dial-val");
      setText(val, String(sp.coef));
      val.setAttribute("aria-valuenow", String(sp.coef));
      val.setAttribute("aria-valuetext", sp.coef + " " + sp.name);
      val.classList.toggle("hinted", Boolean(view.hint && view.hint.dial === sp.index));
      var holder = box.querySelector(".flask-holder");
      if (holder.dataset.coef !== String(sp.coef)) {
        holder.dataset.coef = String(sp.coef);
        holder.textContent = "";
        holder.appendChild(flaskSvg(sp.role, sp.coef));
      }
    });
  }
  function renderEquation() {
    var rx = view.reaction;
    var sig = rx.id + "|" + rx.picked + "|" + rx.species.length;
    if (sig !== eqSig) { eqSig = sig; buildEquation(); }
    updateEquation();
    var line = rx.equation ? "In words: " + rx.equation + "." : "In words: " + rx.left_text + " gives ... (choose what comes out first).";
    setText($("equation-line"), line);
  }

  // ---- the ledger ------------------------------------------------------------------------------------
  function renderLedger() {
    var rx = view.reaction;
    var body = $("ledger-body");
    body.textContent = "";
    rx.ledger.forEach(function (row) {
      var tr = el("tr", row.ok ? "ok" : "off");
      var th = el("th", "el", row.name.charAt(0).toUpperCase() + row.name.slice(1) + " (" + row.symbol + ")");
      th.scope = "row";
      tr.appendChild(th);
      [["left", row.left], ["right", row.right]].forEach(function (pair) {
        var td = el("td");
        td.appendChild(el("span", "num", String(pair[1])));
        var tray = el("span", "tray");
        tray.appendChild(trayNode(row.symbol, row.number, pair[1]));
        td.appendChild(tray);
        tr.appendChild(td);
      });
      var td = el("td", "diff");
      var sign = row.diff > 0 ? "+" + row.diff : row.diff < 0 ? "−" + (-row.diff) : "0";
      td.appendChild(el("span", "sign", sign));
      td.appendChild(el("span", "glyph", row.ok ? "✓" : "✗"));
      td.appendChild(el("span", "word", row.ok ? "Equal" : row.diff > 0 ? plural(row.diff, "too many on the right", "too many on the right") : plural(-row.diff, "too few on the right", "too few on the right")));
      tr.appendChild(td);
      tr.setAttribute("aria-label", row.text);
      body.appendChild(tr);
    });
    var status;
    if (!rx.picked) status = "Choose what comes out to see the ledger.";
    else if (rx.balanced) status = rx.lowest ? "Every element reads equal. Press Run." : "Every element reads equal. These settings could also be divided down to a smaller set, and Run works either way.";
    else {
      var off = rx.ledger.filter(function (r) { return !r.ok; }).length;
      status = plural(off, "element is", "elements are") + " still off.";
    }
    setText($("ledger-status"), status);
    $("ledger").hidden = !rx.picked;
    $("ledger-heading").hidden = $("ledger-note").hidden = !rx.picked;
    var run = $("run-button");
    run.setAttribute("aria-disabled", String(!rx.can_run));
    setText(run, rx.status === "shelved" ? "Run again" : "Run");
    $("reset-dials-button").disabled = !rx.picked;
  }

  // ---- the order and the product choice ----------------------------------------------------------------
  function renderOrder() {
    var rx = view.reaction;
    setText($("bench-kicker"), rx.chapter + " - order " + rx.number + " of " + rx.of);
    setText($("bench-heading"), rx.title);
    var routeLine = $("route-line");
    routeLine.hidden = !rx.route;
    if (rx.route) setText(routeLine, rx.route.note);
    var hide = lsGet(FENNEL_KEY) === "1";
    setText($("fennel-line"), hide ? "" : "Fennel: " + rx.fennel);
    var list = openOrders();
    var idx = list.findIndex(function (o) { return o.current; });
    $("prev-order-button").disabled = idx <= 0;
    $("next-order-button").disabled = false;
    var card = $("shelved-card");
    card.hidden = rx.status !== "shelved";
    if (rx.status === "shelved") {
      setText($("shelved-title"), rx.title + " is on the shelf (run " + plural(rx.runs, "time", "times") + ").");
      setText($("shelved-text"), rx.blurb);
    }
    renderChoices();
  }
  function renderChoices() {
    var rx = view.reaction;
    var box = $("choice-box");
    box.hidden = !rx.choices;
    if (!rx.choices) { listSig.choice = ""; return; }
    var sig = rx.id + "|" + rx.choices.map(function (c) { return c.tried ? "t" : "u"; }).join("");
    if (sig === listSig.choice) return;
    var hadFocus = box.contains(document.activeElement) ? document.activeElement.dataset.index : null;
    listSig.choice = sig;
    var ul = $("choice-list");
    ul.textContent = "";
    rx.choices.forEach(function (c) {
      var li = el("li");
      var b = el("button", "choice-btn" + (c.tried ? " tried" : ""));
      b.type = "button";
      b.dataset.index = String(c.index);
      b.setAttribute("data-testid", "reaction-bench-choice-" + c.index);
      b.appendChild(el("span", "letter", String.fromCharCode(65 + c.index) + " (" + (c.index + 1) + ")"));
      var parts = el("span", "parts");
      c.species.forEach(function (sp, i) {
        if (i) parts.appendChild(document.createTextNode(" + "));
        parts.appendChild(formulaNode(sp));
        parts.appendChild(document.createTextNode(" "));
        parts.appendChild(el("small", null, "(" + sp.name + ")"));
      });
      b.appendChild(parts);
      if (c.tried) {
        b.appendChild(el("span", "note", "Tried: not this one."));
        b.appendChild(el("p", "choice-reason", c.reason));
        b.setAttribute("aria-label", "Option " + (c.index + 1) + ", tried, not this one. " + c.reason);
      }
      b.addEventListener("click", function () { send({ action: "choose", option: c.index }); });
      li.appendChild(b);
      ul.appendChild(li);
    });
    if (hadFocus !== null) { var again = ul.querySelector('[data-index="' + hadFocus + '"]'); if (again) again.focus({ preventScroll: true }); }
  }

  // ---- orders panel and shelf --------------------------------------------------------------------------
  function goTo(id) {
    send({ action: "pick", reaction: id });
    setPanel("orders-panel", "orders-toggle-button", false);
    setPanel("shelf-panel", "shelf-toggle-button", false);
    $("bench-panel").focus({ preventScroll: false });
  }
  function renderOrders() {
    var sig = JSON.stringify(view.orders.map(function (c) { return [c.open, c.need, c.orders.map(function (o) { return (o.shelved ? "s" : o.locked ? "l" : "u") + (o.current ? "*" : ""); }).join("")]; }));
    if (sig === listSig.orders) return;
    listSig.orders = sig;
    var holder = $("orders");
    holder.textContent = "";
    view.orders.forEach(function (c, ci) {
      var block = el("section", "chapter-block" + (c.open ? "" : " locked"));
      block.setAttribute("aria-label", c.name);
      block.appendChild(el("h3", null, "Chapter " + (ci + 1) + ": " + c.name + (c.open ? " (" + c.shelved + " of " + c.total + " shelved)" : " (locked)")));
      block.appendChild(el("p", "note blurb", c.open ? c.blurb : "Opens when " + plural(c.need, "more order", "more orders") + " in " + c.after + " " + (c.need === 1 ? "is" : "are") + " on the shelf."));
      if (c.open) {
        var ul = el("ul", "order-list");
        c.orders.forEach(function (o) {
          var li = el("li");
          var b = el("button", "order-btn" + (o.shelved ? " shelved" : "") + (o.current ? " current" : "") + (o.locked ? " route-locked" : ""));
          b.type = "button";
          b.appendChild(el("span", "mark", o.shelved ? "Shelved" : o.locked ? "Needs step 1" : "Not yet"));
          var label = el("span", null, o.number + ". " + o.title);
          if (o.route) label.appendChild(el("small", "route-tag", " " + o.route + ", step " + o.step + " of 2" + (o.locked ? ". Shelve " + o.needs + " first." : "")));
          b.appendChild(label);
          if (o.current) b.setAttribute("aria-current", "true");
          if (o.locked) b.setAttribute("aria-disabled", "true");
          b.addEventListener("click", function () { goTo(o.id); });
          li.appendChild(b);
          ul.appendChild(li);
        });
        block.appendChild(ul);
      }
      holder.appendChild(block);
    });
  }
  function renderShelf() {
    setText($("shelf-count"), view.totals.shelved + " of " + view.totals.orders + " compounds on the shelf.");
    var sig = JSON.stringify(view.orders.map(function (c) { return [c.open, c.need, c.orders.map(function (o) { return (o.shelved ? "s" + o.runs : o.locked ? "l" : "u"); }).join("")]; }));
    if (sig === listSig.shelf) return;
    listSig.shelf = sig;
    var holder = $("shelf");
    holder.textContent = "";
    view.orders.forEach(function (c, ci) {
      var block = el("section", "chapter-block" + (c.open ? "" : " locked"));
      block.setAttribute("aria-label", c.name);
      block.appendChild(el("h3", null, c.name + " (" + c.shelved + " of " + c.total + ")"));
      if (!c.open) block.appendChild(el("p", "note blurb", "Locked: " + plural(c.need, "more order", "more orders") + " in " + c.after + " opens it."));
      else {
        var ul = el("ul", "flask-grid");
        c.orders.forEach(function (o) {
          var li = el("li");
          var b = el("button", "flask-btn" + (o.shelved ? "" : " empty"));
          b.type = "button";
          b.appendChild(flaskSvg("product", undefined, o.shelved));
          b.appendChild(el("span", "fb-name", o.title));
          b.appendChild(el("span", "fb-meta", o.shelved ? "On the shelf: " + o.makes + ", run " + plural(o.runs, "time", "times") : o.locked ? "Empty flask. Needs " + o.needs + " first." : "Empty flask"));
          if (o.locked) b.setAttribute("aria-disabled", "true");
          b.addEventListener("click", function () { goTo(o.id); });
          li.appendChild(b);
          ul.appendChild(li);
        });
        block.appendChild(ul);
      }
      holder.appendChild(block);
    });
  }

  // ---- the periodic table ------------------------------------------------------------------------------
  function renderTable() {
    var t = view.table;
    setText($("table-count"), t.found + " of " + t.bench + " bench elements found (the table has all " + t.all + " places).");
    var sig = t.cells.map(function (c) { return c.state === "found" ? "f" : c.state === "bench" ? "b" : "o"; }).join("") + "|" + cardSymbol;
    if (sig !== listSig.table) {
      listSig.table = sig;
      var grid = $("table");
      grid.textContent = "";
      t.markers.forEach(function (m) {
        var d = el("div", "marker", m.text);
        d.style.gridRow = String(m.row); d.style.gridColumn = String(m.col);
        d.setAttribute("title", m.label);
        grid.appendChild(d);
      });
      t.cells.forEach(function (c) {
        var tile;
        if (c.state === "found") {
          tile = el("button", "tile found" + (cardSymbol === c.symbol ? " open" : ""));
          tile.type = "button";
          tile.setAttribute("aria-label", c.name + ", element " + c.z + ". Open its card.");
          tile.appendChild(el("span", "z", String(c.z)));
          tile.appendChild(el("span", "s", c.symbol));
          tile.addEventListener("click", function () { openCard(c.symbol); });
        } else if (c.state === "bench") {
          tile = el("div", "tile dark");
          tile.appendChild(el("span", "z", String(c.z)));
          tile.appendChild(el("span", "s", "?"));
          var sr = el("span", "sr-only", "Element " + c.z + ", not found yet");
          tile.appendChild(sr);
        } else {
          tile = el("div", "tile off");
          tile.appendChild(el("span", "z", String(c.z)));
          tile.appendChild(el("span", "s", c.symbol));
          tile.appendChild(el("span", "sr-only", c.name + ", not on this bench"));
        }
        tile.style.gridRow = String(c.row); tile.style.gridColumn = String(c.col);
        grid.appendChild(tile);
      });
      // the text version of the same table
      var text = $("table-text");
      text.textContent = "";
      var found = t.cells.filter(function (c) { return c.state === "found"; });
      var dark = t.cells.filter(function (c) { return c.state === "bench"; }).length;
      text.appendChild(el("p", null, found.length ? "Found: " + found.map(function (c) { return c.name + " (" + c.symbol + ", " + c.z + ")"; }).join(", ") + "." : "Nothing is lit yet."));
      text.appendChild(el("p", null, plural(dark, "tile is", "tiles are") + " still dark. The other " + (t.all - t.found - dark) + " places are not on this bench."));
    }
    renderCard();
  }
  // Live facts: the PubChem Periodic Table service is read once per visit, the first time a card is wanted. If it cannot be reached
  // the bundled snapshot stands, and the card says so in one quiet line.
  function loadLiveElements() {
    if (live.state !== "idle") return;
    if (typeof fetch !== "function") { live.state = "failed"; return; }
    live.state = "loading";
    fetch(PUBCHEM_URL, { headers: { Accept: "application/json" } }).then(function (r) {
      if (!r.ok) throw new Error("status " + r.status);
      return r.json();
    }).then(function (data) {
      var cols = data.Table.Columns.Column, rows = {};
      data.Table.Row.forEach(function (row) {
        var o = {};
        cols.forEach(function (name, i) { o[name] = row.Cell[i]; });
        rows[o.Symbol] = o;
      });
      if (!rows.H) throw new Error("unreadable");
      live.rows = rows; live.date = today(); live.state = "done";
      renderCard();
    }).catch(function () { live.state = "failed"; renderCard(); });
  }
  function openCard(sym) {
    cardSymbol = sym;
    listSig.table = "";
    loadLiveElements();
    renderTable();
    $("element-card").focus({ preventScroll: false });
  }
  function renderCard() {
    var card = $("element-card");
    var data = cardSymbol && view.table.cards[cardSymbol];
    card.hidden = !data;
    if (!data) { cardSymbol = null; return; }
    var row = live.state === "done" && live.rows ? live.rows[data.symbol] : null;
    var mass = row && row.AtomicMass ? row.AtomicMass : data.mass;
    var kind = row && row.GroupBlock ? row.GroupBlock : data.kind;
    var state = row && row.StandardState ? row.StandardState.toLowerCase() : data.state;
    setText($("card-title"), data.name + " (" + data.symbol + ")");
    setText($("card-line"), "Element " + data.number + ", " + (data.group ? "group " + data.group + ", " : "") + "period " + data.period + ". " + kind + ", a " + state + " at room temperature. Atomic mass " + mass + ".");
    setText($("card-use"), data.use);
    var used = data.reactions.length ? "Used in your shelved orders: " + data.reactions.join(", ") + "." : "";
    var more = data.more ? " " + plural(data.more, "more open order uses", "more open orders use") + " it." : "";
    setText($("card-reactions"), (used + more).trim());
    var source;
    if (row) {
      var year = row.YearDiscovered;
      source = "Mass, kind and state: read live from the PubChem Periodic Table (pubchem.ncbi.nlm.nih.gov) on " + live.date + "." +
        (year ? (/^\d+$/.test(year) ? " Discovered " + year + "." : " Known since " + String(year).toLowerCase() + " times.") : "");
    } else {
      source = "Mass and kind: bundled snapshot of the " + data.source + ", read " + data.snapshot + "." +
        (live.state === "failed" ? " The live read could not be reached just now, so this copy stands." : live.state === "loading" ? " Reading it live now..." : "");
    }
    setText($("card-source"), source);
  }

  // ---- the suggestion ladder (the engine owns every rule; this only shows the rungs the player has pressed for) --------------
  var RUNG_LABELS = { 1: "Nudge", 2: "Hint", 3: "Answer" };
  function renderHints() {
    var ui = view.hint_ui;
    var shown = lsGet(HINTS_KEY) !== "1";
    $("hint-box").hidden = !shown || !ui.available;
    $("hints-checkbox").checked = shown;
    var button = $("hint-button");
    button.hidden = ui.next === 0;
    setText(button, ui.label || "Would you like a suggestion?");
    var note = "";
    if (ui.balanced) note = "Every element reads equal, so there is nothing to suggest. Press Run.";
    else if (ui.next === 1) note = ui.opens_two ? "On Easy this opens the nudge and the hint together. Nothing is shown until you press." : "Nothing is shown until you press.";
    else if (ui.next === 3) note = (ui.stage === "choose" ? "This chooses the right list for you." : "This sets every dial to the answer.") + (ui.confirm ? " It asks first." : "") + " Run is still yours to press.";
    else if (ui.limit) note = "Hard has no answer step: the nudge and the hint are all the help there is.";
    setText($("hint-note"), note);
    var list = $("hint-list");
    var h = view.hint;
    var sig = h ? [h.rung, h.nudge, h.hint, h.answer].join("|") : "";
    if (list.dataset.sig === sig) return;
    list.dataset.sig = sig;
    list.textContent = "";
    list.hidden = !h;
    if (!h) return;
    [[1, h.nudge], [2, h.hint], [3, h.answer]].forEach(function (pair) {
      if (pair[0] > h.rung || !pair[1]) return;
      var li = el("li", "hint-item hint-rung-" + pair[0]);
      li.appendChild(el("span", "hint-label", RUNG_LABELS[pair[0]]));
      li.appendChild(el("span", "hint-text", pair[1]));
      list.appendChild(li);
    });
  }
  function pressHint(confirmed) {
    if (!view || view.hint_ui.next === 0) return;
    if (view.hint_ui.next === 3 && view.hint_ui.confirm && !confirmed) {
      var choose = view.hint_ui.stage === "choose";
      askThen("reaction-bench-hint-answer", choose ? "Choose the right list for you? The dials open, and you still balance it." : "Set every dial to the answer for you? You still press Run.", choose ? "Choose it" : "Set the dials", function () { pressHint(true); });
      return;
    }
    var result = send({ action: "hint", confirm: confirmed === true });
    if (!result) return;
    var items = $("hint-list").querySelectorAll(".hint-item");
    if (result.hint && items.length) { var last = items[items.length - 1]; last.setAttribute("tabindex", "-1"); last.focus({ preventScroll: true }); }
    else if (result.ok && result.reaction.picked) { var dial = document.querySelector("#equation .dial-val"); if (dial) dial.focus({ preventScroll: true }); }
  }

  // ---- goals and difficulty ---------------------------------------------------------------------------------------------
  var DIFF_TEXT = {
    easy: "The suggestion button opens the nudge and the hint together on its first press, and the answer needs no extra question.",
    normal: "The game as designed: a nudge, then a hint, then (after a question) the answer, each only when you press.",
    hard: "No answer step: the nudge and the hint are all the suggestions there are. Orders, proofs and records are the same."
  };
  function sendDifficulty() {
    if (!engine) return null;
    if (!window.NoyvjDifficulty) return send({ action: "open" });
    return send({ action: "difficulty", level: window.NoyvjDifficulty.get(DIFF_GAME) });
  }
  function wireDifficulty() {
    if (!window.NoyvjDifficulty) return;
    window.NoyvjDifficulty.mount("#difficulty-slot", { game: DIFF_GAME, collapsible: true, descriptions: DIFF_TEXT });
    window.NoyvjDifficulty.onChange(function (d) { if (d.game === DIFF_GAME) sendDifficulty(); });
  }
  function wireGoals() {
    if (!window.NoyvjGoals) return;
    goalsPanel = window.NoyvjGoals.mount("#goals", { game: "reaction-bench", title: "Goals", getGoals: function () { return view ? view.goals : []; } });
    if (goalsPanel && window.NoyvjGoals.bindCheckbox) window.NoyvjGoals.bindCheckbox(goalsPanel, "#goals-checkbox");
  }

  // ---- the tutorial (shared/tutorial.js; offered from the opening screen, restartable from the toolbar) ----------------
  var TUTORIAL_STEPS = [
    { title: "Welcome to the night shift", text: "Each order is a chemical equation. You turn a dial in front of every formula until the atoms on both sides are equal, then run it and the compound goes on the shelf. Nothing is timed and nothing can go wrong. Skip any time and reopen this from the Tutorial button." },
    { selector: "#bench", title: "Dials in front of each formula", text: "A conical flask is something that goes in and a round flask is something that comes out. The number on a dial says how many of that substance take part. Use the plus and minus buttons, or the arrow keys and the digits." },
    { selector: "#ledger-status", title: "The atom ledger", text: "Below the bench a table counts every element on the left and on the right. Each row shows a tick and the word Equal, or a cross and how many too many or too few. When every row reads equal, Run works." },
    { selector: "#run-button", title: "Run", text: "Run puts the compound on the shelf and lights a tile on the periodic table for every new element you used. You can run an order again any time, and Reset dials is free." },
    { selector: "#hint-box", title: "Stuck? Ask", text: "The suggestion button never opens by itself. A nudge says where to look, a hint says what to turn, and the last rung gives the answer after a question. Every order can be finished without guessing." },
    { selector: "#orders-toggle-button", title: "The order board", text: "Five shelved orders in a chapter open the next one. From chapter 2 you choose what comes out from four lists first, and in the last chapter each route has two steps: what step one makes is carried into step two." },
    { selector: "#table-toggle-button", title: "The periodic table", text: "Each element you use lights its tile. Open a lit tile for its card: facts read live from PubChem, with the date, and a bundled copy if you are offline." },
    { selector: "#settings-toggle-button", title: "Settings and difficulty", text: "Text size, reduced motion, high contrast and the light theme are in Settings. Difficulty (Easy, Normal, Hard) changes only how the suggestions open; nothing is locked." },
    { title: "That is all", text: "Press ? at any time for the keyboard help. The Tutorial button in the toolbar brings this tour back." }
  ];

  // ---- About and What's New (the same shape as the sibling games) -------------------------------------------
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
    renderStats();
    renderOrder();
    renderEquation();
    renderLedger();
    renderOrders();
    renderShelf();
    renderTable();
    renderInfo();
    renderHints();
    if (goalsPanel) goalsPanel.refresh();
    if (view.just && view.just.first !== undefined && glowShown !== view.just.id + ":" + view.totals.runs) {
      glowShown = view.just.id + ":" + view.totals.runs;
      var bench = $("bench");
      bench.classList.remove("shelf-glow");
      void bench.offsetWidth;
      bench.classList.add("shelf-glow");
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
    var rx = view.reaction, parts = [];
    if (request.action === "dial") {
      var sp = rx.species[request.index];
      if (!view.ok) parts.push(view.message);
      else {
        parts.push(sp.name + " " + sp.coef + ".");
        var off = rx.ledger.filter(function (r) { return !r.ok; });
        if (rx.balanced) parts.push("Every element reads equal. Press Run.");
        else parts.push(plural(off.length, "element is", "elements are") + " still off: " + off.map(function (r) { return r.name + " " + (r.diff > 0 ? "+" : "") + r.diff; }).join(", ") + ".");
      }
    } else if (request.action === "run" || request.action === "choose" || request.action === "hint") {
      parts.push(view.message);
    } else if (request.action === "pick" || request.action === "next") {
      parts.push(rx.chapter + " order " + rx.number + ": " + rx.title + ".");
    }
    void previous;
    if (parts.length) announce(parts.join(" "));
  }
  function send(request, quiet) {
    if (!engine) return null;
    var result = JSON.parse(engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    var previous = view;
    view = result;
    if (!quiet) showToast("");
    if (view.message && (!view.ok || (view.just && request.action === "run") || request.action === "reset" || request.action === "choose")) showToast(view.message);
    render();
    announceChanges(request, previous);
    if (request.action === "choose" && view.reaction.picked) { var first = document.querySelector("#equation .dial-val"); if (first) first.focus({ preventScroll: true }); }
    if (["dial", "reset_dials", "choose", "run", "pick", "next", "reset", "hint"].indexOf(request.action) >= 0) persist();
    return result;
  }
  function askThen(id, message, confirmLabel, go) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: false, onConfirm: go });
    else go();
  }
  function openOrders() {
    var list = [];
    view.orders.forEach(function (c) { if (c.open) c.orders.forEach(function (o) { if (!o.locked) list.push(o); }); });
    return list;
  }
  function stepOrder(delta) {
    var list = openOrders();
    var idx = list.findIndex(function (o) { return o.current; });
    var target = list[idx + delta];
    if (target) send({ action: "pick", reaction: target.id });
  }

  // ---- keyboard shortcuts for the bench --------------------------------------------------------------------
  function typing(t) { return t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable); }
  function overlayOpen() {
    var c = document.getElementById("confirm-dialog-overlay");
    var h = document.getElementById("kb-shortcuts-panel");
    return Boolean((c && !c.hidden && c.offsetParent !== null) || (h && !h.hidden));
  }
  function onKey(e) {
    if (!view || e.ctrlKey || e.metaKey || e.altKey || typing(e.target) || overlayOpen()) return;
    var k = e.key;
    if (k === "r" || k === "R") { send({ action: "run" }); e.preventDefault(); }
    else if (k === "n" || k === "N") { send({ action: "next" }); e.preventDefault(); }
    else if (k === "h" || k === "H") { pressHint(false); e.preventDefault(); }
    else if (k === "[") { stepOrder(-1); e.preventDefault(); }
    else if (k === "]") { stepOrder(1); e.preventDefault(); }
    else if (/^[1-4]$/.test(k) && view.reaction.choices && e.target.getAttribute("role") !== "spinbutton") {
      var n = Number(k) - 1;
      if (n < view.reaction.choices.length) { send({ action: "choose", option: n }); e.preventDefault(); }
    }
  }

  function wire() {
    $("toast").addEventListener("click", function () { showToast(""); });
    wirePanelToggle("orders-toggle-button", "orders-panel");
    wirePanelToggle("shelf-toggle-button", "shelf-panel");
    wirePanelToggle("table-toggle-button", "table-panel");
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    $("info-page-toggle-button").addEventListener("click", function () { if (!$("info-page-panel").hidden) loadLiveInfo(); });
    $("table-toggle-button").addEventListener("click", function () { if (!$("table-panel").hidden) loadLiveElements(); });
    $("hint-button").addEventListener("click", function () { pressHint(false); });
    $("hints-checkbox").addEventListener("change", function () { lsSet(HINTS_KEY, $("hints-checkbox").checked ? "0" : "1"); if (view) renderHints(); });
    wireDifficulty();
    wireGoals();
    $("prev-order-button").addEventListener("click", function () { stepOrder(-1); });
    $("next-order-button").addEventListener("click", function () { send({ action: "next" }); });
    $("run-button").addEventListener("click", function () { send({ action: "run" }); });
    $("reset-dials-button").addEventListener("click", function () { send({ action: "reset_dials" }); });
    $("shelved-next-button").addEventListener("click", function () { send({ action: "next" }); $("bench-panel").focus({ preventScroll: false }); });
    $("shelved-shelf-button").addEventListener("click", function () { setPanel("shelf-panel", "shelf-toggle-button", true); $("shelf-panel").scrollIntoView({ block: "start" }); });
    $("shelved-table-button").addEventListener("click", function () { setPanel("table-panel", "table-toggle-button", true); $("table-panel").scrollIntoView({ block: "start" }); });
    $("card-close-button").addEventListener("click", function () { cardSymbol = null; listSig.table = ""; renderTable(); });
    var fennel = $("fennel-checkbox");
    fennel.checked = lsGet(FENNEL_KEY) !== "1";
    fennel.addEventListener("change", function () { lsSet(FENNEL_KEY, fennel.checked ? "0" : "1"); if (view) renderOrder(); });
    $("reset-button").addEventListener("click", function () {
      askThen("reaction-bench-reset", "Start the whole bench over? Every compound on the shelf and every lit tile will be cleared.", "Clear the bench", function () { cardSymbol = null; eqSig = ""; listSig = { orders: "", shelf: "", table: "", choice: "" }; send({ action: "reset" }); });
    });
    // The save widget loads a save straight into the engine; this redraws afterwards.
    window.reactionBenchRefresh = function () { if (engine) { eqSig = ""; listSig = { orders: "", shelf: "", table: "", choice: "" }; cardSymbol = null; send({ action: "open" }); } };
    document.addEventListener("keydown", onKey);
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
    sendDifficulty();
    await changelog;
    if (window.GameTutorial) window.GameTutorial.init(TUTORIAL_STEPS, { gameId: "reaction-bench" });
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The bench could not open (" + err + "). Reload to try again.";
  });
})();
