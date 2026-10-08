/* Pocket Bazaar view: glue only. The engine (game.py and its modules) holds every rule; this file draws what
   handle() returns and forwards what the player does. No game logic lives here (the one exception is "which
   cells could this good merge with", which the engine sends as `partners`). */
(function () {
  "use strict";
  var ENGINE_MODULES = ["goods.py", "rng.py", "board.py", "orders.py", "days.py", "festival.py", "renown.py", "shop.py", "day.py"];
  var STORE_KEY = "pocket-bazaar:state";
  var BACKUP_KEY = "pocket-bazaar:state-backup";
  var DRAG_THRESHOLD = 8;

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;
  var view = null;
  var selected = null;       // the cell number of the picked-up good
  var cursor = 0;            // the cell the arrow keys are on (roving tab stop)
  var broomArmed = false;
  var activeCrate = 0;
  var cellEls = [];
  var cardEls = [];
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

  function itemNode(item) {
    var wrap = el("span", "item" + (item.done ? " done" : ""));
    var good = el("span", "good shape-" + item.shape + " fam-" + item.family + " t" + item.tier);
    good.appendChild(el("span", "good-shape"));
    good.appendChild(el("span", "good-text", item.letter + (item.tier_text || item.tier)));
    wrap.appendChild(good);
    return wrap;
  }

  // ---- the queue -----------------------------------------------------------------------------
  function customerLabel(c) {
    var order = c.items.map(function (i) { return i.label + (i.done ? " (handed over)" : ""); }).join("; ");
    return c.name + ", " + c.kind + ". Wants " + order + ". " + c.patience + " of " + c.max + " beats of patience left. Pays " + c.pay + " coins.";
  }
  function renderQueue() {
    var holder = $("queue");
    var wants = selected !== null ? (view.deliverable[String(selected)] || []) : [];
    var sig = view.customers.map(function (c) { return c.name + c.items.map(function (i) { return i.done ? 1 : 0; }).join(""); }).join("|") + view.customers.length;
    if (holder.dataset.signature !== sig) {
      holder.textContent = "";
      holder.dataset.signature = sig;
      cardEls = [];
      for (var n = 0; n < view.day.window; n++) {
        var btn = el("button", "customer");
        btn.type = "button";
        btn.dataset.drop = "customer:" + n;
        btn.dataset.testid = "pocket-bazaar-customer-" + n;
        btn.addEventListener("click", (function (k) { return function () { if (!suppressClick) onCustomer(k); }; })(n));
        cardEls.push(btn);
        holder.appendChild(btn);
      }
    }
    cardEls.forEach(function (btn, n) {
      var c = view.customers[n];
      if (!c) {
        btn.className = "customer empty";
        btn.textContent = "";
        btn.dataset.sig = "";
        btn.disabled = false;
        btn.setAttribute("aria-label", "Empty spot at the stall");
        btn.appendChild(el("span", "note", view.day.waiting ? "" : "-"));
        return;
      }
      var low = c.patience * 4 <= c.max;
      var sigc = c.name + "|" + c.patience + "|" + c.items.map(function (i) { return i.done ? 1 : 0; }).join("");
      btn.className = "customer " + c.archetype + (low ? " low" : "") + (wants.indexOf(n) !== -1 ? " wants" : "");
      if (btn.dataset.sig !== sigc) {
        btn.dataset.sig = sigc;
        btn.textContent = "";
        var head = el("span", "cust-head");
        head.appendChild(el("span", "cust-face", c.name.charAt(0)));
        var names = el("span", null);
        names.style.minWidth = "0";
        names.appendChild(el("span", "cust-name", c.name));
        head.appendChild(names);
        btn.appendChild(head);
        btn.appendChild(el("span", "cust-kind", c.kind));
        var order = el("span", "cust-order");
        c.items.forEach(function (i) { order.appendChild(itemNode(i)); });
        btn.appendChild(order);
        btn.appendChild(el("span", "cust-want", "Wants it!"));
        var pat = el("span", "cust-patience");
        var bar = el("span", "bar");
        var fill = el("span", "bar-fill");
        fill.style.width = Math.max(0, Math.min(100, Math.round(100 * c.patience / c.max))) + "%";
        bar.appendChild(fill);
        pat.appendChild(bar);
        pat.appendChild(el("span", "beats", String(c.patience)));
        btn.appendChild(pat);
      }
      btn.setAttribute("aria-label", customerLabel(c) + (wants.indexOf(n) !== -1 ? " Would take the good you picked up." : ""));
    });
    var d = view.day;
    var line = $("queue-line");
    var f = view.festival;
    var sigq = f.id + "|" + d.waiting + "|" + d.left + "|" + (view.upcoming ? view.upcoming.name : "");
    if (line.dataset.sig !== sigq) {
      line.dataset.sig = sigq;
      line.textContent = "";
      var chip = el("span", "chip " + f.tone, f.name);
      chip.title = f.blurb;
      line.appendChild(chip);
      line.appendChild(document.createTextNode(" " + (d.waiting ? d.waiting + " more in line" : "last of the line") + (d.left ? " \u00B7 " + d.left + " left" : "")));
      if (view.upcoming) {
        var up = view.upcoming;
        line.appendChild(document.createTextNode(". Next up: " + up.name + " wants " + up.items.map(function (i) { return i.label; }).join(", ")));
      }
    }
    holder.setAttribute("aria-label", "Customers at the stall" + (d.waiting ? ", " + d.waiting + " more waiting in line" : ""));
  }

  function onCustomer(n) {
    if (!view || view.phase !== "open") return;
    if (selected === null) {
      var c = view.customers[n];
      if (c) showMessage(customerLabel(c), true);
      return;
    }
    send({ action: "deliver", from: selected, to: n });
  }

  // ---- the closed stall ----------------------------------------------------------------------
  function renderClosed() {
    var sum = view.summary;
    $("summary").hidden = !sum;
    var heading = $("closed-heading");
    if (sum) {
      setText(heading, "Day " + sum.number + " is done");
      setText($("summary-stars"), "\u2605".repeat(sum.stars) + "\u2606".repeat(3 - sum.stars));
      $("summary-stars").setAttribute("aria-label", sum.stars + " of 3 stars");
      var list = $("summary-list");
      list.textContent = "";
      [["Served", sum.served + " of " + sum.total], ["Left unserved", String(sum.left)],
       ["Coins today", String(sum.coins)], ["Beats played", String(sum.beats)], ["Longest chain", String(sum.best_chain)], ["Renown", String(view.renown)]].forEach(function (row) {
        list.appendChild(el("dt", null, row[0]));
        list.appendChild(el("dd", null, row[1]));
      });
      setText($("closed-text"), "Your coins are saved. Open the next day whenever you like: there is no rush and nothing to miss.");
      setText($("summary-festival"), view.summary_festival ? "Festival: " + view.summary_festival.name : "");
      var bests = [];
      if (sum.new_bests.indexOf("combo") !== -1) bests.push("longest combo: " + sum.streak + " orders in a row");
      if (sum.new_bests.indexOf("day_coins") !== -1) bests.push("most coins in a day: " + sum.coins);
      var bestLine = $("summary-bests");
      bestLine.classList.toggle("just-improved", bests.length > 0);
      setText(bestLine, bests.length ? "New personal best: " + bests.join("; ") + "." : "Personal bests: longest combo " + view.best.combo + ", most coins in a day " + view.best.day_coins + ".");
      var unlockLine = $("summary-unlocks");
      unlockLine.hidden = !sum.unlocks.length;
      setText(unlockLine, sum.unlocks.length ? "New: " + sum.unlocks.map(function (u) { return view.unlock_names[u]; }).join(", ") + "!" : "");
    } else {
      setText(heading, view.days_played ? "The stall is closed" : "Welcome to your stall");
      setText($("closed-text"), view.days_played ? "Open the next day whenever you like." : "Customers will ask for goods. Open crates, merge them into better ones and hand them over. Nothing here runs on a clock.");
    }
    setText($("start-day-button"), "Open day " + view.next_day);
    var nu = view.next_unlock;
    setText($("renown-line"), "Renown " + view.renown + (nu ? ": " + (nu.need - view.renown) + " more opens " + nu.name + "." : ": everything is open."));
    var c = view.campaign;
    setText($("campaign-line"), c.mode === "campaign" ? "Market Days: day " + c.day + " of " + c.of : "Free Stall: day " + c.day + " (the campaign is done; days keep coming, slowly harder)");
    var f = view.festival;
    setText($("festival-label"), sum ? "Tomorrow's festival" : "Today's festival");
    setText($("festival-name"), f.name);
    var tone = $("festival-tone");
    setText(tone, f.tone === "tricky" ? "harder day" : "easier day");
    tone.className = "chip " + f.tone;
    setText($("festival-blurb"), f.blurb);
    renderShop();
  }

  function renderShop() {
    var list = $("shop-list");
    var sig = view.upgrades.map(function (u) { return u.id + (u.owned ? "o" : u.affordable ? "a" : "n"); }).join(",") + "|" + view.coins;
    var toggle = $("shop-toggle-button");
    setText(toggle, "Upgrades (" + view.upgrades.filter(function (u) { return u.owned; }).length + "/" + view.upgrades.length + ")");
    if (list.dataset.sig === sig) return;
    list.dataset.sig = sig;
    list.textContent = "";
    view.upgrades.forEach(function (u) {
      var li = el("li", "shop-item" + (u.owned ? " owned" : ""));
      li.appendChild(el("span", "shop-name", u.name));
      li.appendChild(el("span", "shop-blurb", u.blurb));
      if (u.owned) {
        li.appendChild(el("span", "shop-owned", "Owned \u2713"));
      } else {
        var btn = el("button", "shop-buy", "Buy " + u.cost);
        btn.type = "button";
        btn.dataset.testid = "pocket-bazaar-buy-" + u.id;
        btn.setAttribute("aria-label", "Buy " + u.name + " for " + u.cost + " coins" + (u.affordable ? "" : ", you need " + (u.cost - view.coins) + " more"));
        if (!u.affordable) btn.setAttribute("aria-disabled", "true");
        btn.addEventListener("click", function () { send({ action: "buy", id: u.id }); });
        li.appendChild(btn);
      }
      list.appendChild(li);
    });
  }

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
  function cellAt(i) { return view && view.board && view.board.cells[i] ? view.board.cells[i] : null; }

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
        btn.appendChild(el("span", "crate-name", crate.name));
        btn.setAttribute("aria-label", crate.name + " crate, key " + (n + 1));
        btn.addEventListener("click", function () { activeCrate = n; send({ action: "crate", family: crate.family }); });
        holder.appendChild(btn);
      });
      holder.dataset.signature = sig;
    }
    holder.dataset.many = view.crates.length > 3 ? "1" : "0";
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
      if ((view.deliverable[String(selected)] || []).length) text += " A customer wants it: tap them to hand it over.";
      text += " Sells for " + cell.sell + (cell.sell === 1 ? " coin." : " coins.");
    } else {
      text = view.full ? "The counter is full. Merge, sell or sweep something to make room." : "Open a crate to put a basic good on the counter. Two identical goods merge into a better one.";
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
    bumpStat("stat-day", view.day ? view.day.number : view.next_day);
    bumpStat("stat-served", view.day ? view.day.served + "/" + view.day.total : (view.summary ? view.summary.served + "/" + view.summary.total : "0"));
    bumpStat("stat-combo", "x" + (view.day ? view.day.mult : 1));
    var pips = $("stat-combo-pips");
    var pipText = "";
    if (view.day && view.day.mult < 3) {
      var need = 2, have = need - view.day.to_next;
      pipText = "\u25CF".repeat(have) + "\u25CB".repeat(need - have);
    } else if (view.day) { pipText = "max"; }
    setText(pips, pipText);
    $("stat-combo").parentNode.title = view.day ? "Order combo x" + view.day.mult + (view.day.to_next ? ": " + view.day.to_next + " more in a row for the next step" : ": the highest") : "";
    bumpStat("stat-orders", view.tally.orders);
    bumpStat("stat-crates", view.tally.crates);
    bumpStat("stat-merges", view.tally.merges);
    bumpStat("stat-chain", view.best_chain);
    bumpStat("stat-sold", view.tally.sold);
    bumpStat("stat-swept", view.tally.swept);
  }

  function showMessage(text, ok, flavor) {
    var m = $("message");
    var extra = (flavor || []).join(" ");
    var sig = (text || "") + "|" + extra;
    if (m.dataset.sig !== sig) {
      m.dataset.sig = sig;
      m.textContent = text || "";
      if (extra) m.appendChild(el("span", "msg-flavor", extra));
    }
    m.classList.toggle("refused", ok === false && Boolean(text));
  }

  function render(event) {
    var open = view.phase === "open";
    $("closed-card").hidden = open;
    $("open-area").hidden = !open;
    renderStats();
    if (!open) { renderClosed(); return; }
    renderQueue();
    renderBoard();
    renderCrates();
    renderInfo();
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
    if (request.action === "drop" || request.action === "sell" || request.action === "broom" || request.action === "deliver" || request.action === "start_day") selected = null;
    if (request.action === "start_day") { cursor = 0; broomArmed = false; }
    render(result.event);
    showMessage(result.message, result.ok, result.flavor);
    if (result.message) announce(result.message + " " + (result.flavor || []).join(" "));
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
    else if (spec.indexOf("customer:") === 0) send({ action: "deliver", from: d.from, to: Number(spec.slice(9)) });
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
    if (!view || view.phase !== "open" || e.ctrlKey || e.metaKey || e.altKey) return;
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
    if (key === "d" || key === "D") {
      e.preventDefault();
      if (selected === null && onGrid && cellAt(cursor)) select(cursor);
      if (selected === null) { showMessage("Pick up a good first, then press D to hand it over.", false); return; }
      var takers = view.deliverable[String(selected)] || [];
      send({ action: "deliver", from: selected, to: takers.length ? takers[0] : 0 });
      return;
    }
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
    $("start-day-button").addEventListener("click", function () { send({ action: "start_day" }); });
    $("shop-toggle-button").addEventListener("click", function () {
      var panel = $("shop-panel");
      panel.hidden = !panel.hidden;
      $("shop-toggle-button").setAttribute("aria-expanded", String(!panel.hidden));
    });
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
    setBusy(false);
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The stall could not open (" + err + "). Reload to try again.";
  });
})();
