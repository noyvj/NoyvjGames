/* Mirror Lab view: glue only. The engine (game.py and its modules) holds every rule and draws the bench as an SVG string; this file
   puts that SVG on the page, turns taps, drags and keys into place / flip / pickup / move requests, and keeps the keyboard cursor
   ring. No game logic lives here: where a beam goes and whether a sensor is lit is always the engine's answer. */
(function () {
  "use strict";
  var DIFF_GAME = "mirror-lab";
  var DIFF_TEXT = {
    easy: "The first hint press opens the nudge and the hint together, and Place them needs no question first.",
    normal: "The game as designed: a nudge, then a hint, then the whole answer, and Place them asks first.",
    hard: "No answer step: the nudge and the hint are all the help there is. Benches, tags and records are the same on all three; nothing is locked."
  };
  var ENGINE_MODULES = ["optics.py", "bench.py", "benches_ch1.py", "benches_ch2.py", "benches_ch3.py", "benches_ch4.py", "benches_ch5.py", "benches.py", "progress.py", "render.py", "logbook.py", "trace_text.py", "hints.py", "goals.py", "achievements.py", "info.py"];
  var STORE_KEY = "mirror-lab:state";
  var BACKUP_KEY = "mirror-lab:state-backup";
  var DIR_NAMES = ["north", "east", "south", "west"];
  var SVG_NS = "http://www.w3.org/2000/svg";
  var DRAG_PIXELS = 8;

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;
  var view = null;
  var benchId = null;            // the bench the page is currently drawn for
  var held = null;               // a tray piece name, "pickup", or null
  var cursor = { r: 0, c: 0 };
  var drag = null;               // a drag in progress: {from, piece, r, c, x, y, started, ghost}
  var suppressClick = false;
  var knownEarned = null;        // the achievement ids earned in the last view (null until the first view, so loading never toasts)

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }
  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }
  function announce(text) {
    if (!text) return;
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
  function showToast(text) {
    var t = $("toast");
    t.textContent = text;
    t.classList.toggle("on", Boolean(text));
  }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }
  function cellName(r, c) { return "row " + (r + 1) + ", column " + (c + 1); }

  // ---- panels --------------------------------------------------------------------------------------
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () {
      $(panelId).hidden = !$(panelId).hidden;
      $(buttonId).setAttribute("aria-expanded", String(!$(panelId).hidden));
    });
  }

  // ---- stats ---------------------------------------------------------------------------------------
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
    bumpStat("stat-cleared", t.cleared + "/" + t.benches);
    bumpStat("stat-sensors", t.sensors);
    bumpStat("stat-placed", view.tally.placed);
    bumpStat("stat-fewest", t.fewest);
    bumpStat("stat-picked", view.tally.picked);
    bumpStat("stat-flips", view.tally.flips);
    bumpStat("stat-hints", view.tally.hints);
  }

  // ---- the bench -----------------------------------------------------------------------------------
  function placedAt(r, c) {
    var list = view.bench.placed;
    for (var i = 0; i < list.length; i++) if (list[i].r === r && list[i].c === c) return list[i];
    return null;
  }
  function isSlot(r, c) { return view.bench.rows[r].charAt(c) === "o"; }
  function trayItem(piece) {
    var list = view.bench.tray;
    for (var i = 0; i < list.length; i++) if (list[i].piece === piece) return list[i];
    return null;
  }
  function describeCell(r, c) {
    var b = view.bench;
    var ch = b.rows[r].charAt(c);
    var where = cellName(r, c) + ": ";
    var p = placedAt(r, c);
    if (p) return where + p.words + (p.flips ? ", tap or press Enter to flip, P to pick up" : ", Enter or P to pick up") + ".";
    if (ch === "o") return where + "empty slot.";
    if (ch === "#") return where + "wall.";
    var facing = "^>v<".indexOf(ch);
    if (facing >= 0) return where + "emitter facing " + DIR_NAMES[facing] + ".";
    if (ch === "/") return where + "fixed mirror, slash.";
    if (ch === "\\") return where + "fixed mirror, backslash.";
    for (var i = 0; i < b.sensors.length; i++) {
      if (b.sensors[i].r === r && b.sensors[i].c === c) return where + b.sensors[i].words + ".";
    }
    return where + "floor, nothing can go here.";
  }

  function firstSlot() {
    var rows = view.bench.rows;
    for (var r = 0; r < rows.length; r++) for (var c = 0; c < rows[r].length; c++) if (rows[r].charAt(c) === "o") return { r: r, c: c };
    return { r: 0, c: 0 };
  }
  function drawCursor() {
    var svg = $("bench-holder").querySelector("svg");
    if (!svg) return;
    var old = svg.querySelector(".ml-cursor");
    if (old) old.remove();
    var b = view.bench;
    var ring = document.createElementNS(SVG_NS, "rect");
    ring.setAttribute("class", "ml-cursor");
    ring.setAttribute("x", b.pad + cursor.c * b.cell + 2);
    ring.setAttribute("y", b.pad + cursor.r * b.cell + 2);
    ring.setAttribute("width", b.cell - 4);
    ring.setAttribute("height", b.cell - 4);
    ring.setAttribute("rx", 8);
    svg.appendChild(ring);
  }
  function renderBench() {
    var b = view.bench;
    var holder = $("bench-holder");
    if (benchId !== b.id) {
      benchId = b.id;
      cursor = firstSlot();
      held = b.tray.length === 1 && b.tray[0].left > 0 ? b.tray[0].piece : null;
      holder.setAttribute("aria-label", "Optics bench " + b.name + ", " + b.w + " columns by " + b.h + " rows");
      announce("Bench " + b.name + ". " + b.brief);
    }
    if (holder.dataset.svg !== b.svg) {
      holder.innerHTML = b.svg;
      holder.dataset.svg = b.svg;
    }
    drawCursor();
    setText($("bench-chapter"), "Chapter " + b.chapter + ", " + b.chapter_name + " - bench " + b.number + " of " + b.of);
    setText($("bench-heading"), b.name);
    setText($("bench-brief"), b.brief);
    setText($("lit-line"), b.lit + " of " + plural(b.need, "sensor", "sensors") + " lit" + (b.decoys_hit ? ", a decoy is lit" : "") + " - " + plural(b.pieces, "piece", "pieces") + " placed");
    setText($("emitter-line"), b.emitters.join(" "));
    var list = $("sensor-list");
    list.textContent = "";
    b.sensors.forEach(function (s) {
      var li = el("li", (s.lit ? "lit" : "") + (s.hit ? " hit" : ""), s.text);
      list.appendChild(li);
    });
    $("next-button").disabled = !(b.status === "cleared" && b.next);
    $("next-button").textContent = b.next ? "Next bench" : "No more open benches";
    $("clear-button").disabled = b.pieces === 0;
  }
  function renderTray() {
    var b = view.bench;
    var holder = $("tray");
    var current = held;
    if (current && current !== "pickup") {
      var it = trayItem(current);
      if (!it || it.left <= 0) current = null;
    }
    held = current;
    holder.textContent = "";
    b.tray.forEach(function (t, i) {
      var btn = el("button", "tray-btn");
      btn.type = "button";
      btn.setAttribute("data-piece", t.piece);
      btn.setAttribute("data-testid", "mirror-lab-tray-" + t.piece);
      btn.setAttribute("aria-pressed", String(held === t.piece));
      btn.disabled = t.left <= 0 && held !== t.piece;
      btn.innerHTML = t.icon + '<span class="tray-text"><span>' + (i + 1) + ". " + t.label + '</span><span class="tray-count">' + t.left + " of " + t.total + " left</span></span>";
      btn.setAttribute("aria-label", t.label + ", " + t.left + " of " + t.total + " left" + (held === t.piece ? ", chosen" : ""));
      btn.addEventListener("click", function () {
        if (suppressClick) return;
        setHeld(held === t.piece ? null : t.piece);
      });
      btn.addEventListener("pointerdown", function (e) { startDrag(e, "tray", t.piece, null, null, btn); });
      holder.appendChild(btn);
    });
    $("pickup-tool-button").setAttribute("aria-pressed", String(held === "pickup"));
    renderToolLine();
  }
  function renderToolLine() {
    var text;
    if (held === "pickup") text = "Pick up tool: tap a placed piece to take it back to the tray.";
    else if (held) {
      var it = trayItem(held);
      text = "Holding: " + it.label + " (" + it.left + " left). Tap a dashed slot to place it" + (it.flips ? "; tap a placed one to flip it." : ".");
    } else text = "Choose a piece from the tray, then tap a dashed slot. Tap a placed mirror or prism to flip it.";
    setText($("tool-line"), text);
  }
  function setHeld(next) {
    held = next;
    renderTray();
    if (next === "pickup") announce("Pick up tool chosen. Tap a placed piece to take it back.");
    else if (next) announce(trayItem(next).label + " chosen.");
    else announce("Nothing chosen.");
  }

  function renderVerdict() {
    var v = view.verdict;
    var card = $("verdict-card");
    if (!v) { card.hidden = true; return; }
    card.hidden = false;
    card.className = "verdict-card " + (v.kind === "again" ? "again" : "cleared");
    var best = v.kind === "again" ? v.best : v.pieces;
    var title = v.kind === "cleared" ? "Bench cleared" : v.kind === "improved" ? "Cleared with fewer pieces" : "Still lit";
    setText($("verdict-title"), title + " - " + plural(v.pieces, "piece", "pieces") + " used");
    var tail = v.fewest ? "That is the fewest pieces this bench takes, and the bench is tagged." : "The fewest this bench takes is " + v.par + ". Try again with fewer if you like; nothing is lost.";
    if (v.kind === "again") tail = "Your best so far is " + plural(best, "piece", "pieces") + ". " + tail;
    setText($("verdict-text"), tail);
    setText($("verdict-line"), v.line || "");
  }

  // ---- the benches panel, the map and the Bench Log ------------------------------------------------
  function renderBenches() {
    $("map-holder").innerHTML = view.map;
    var body = $("benches-body");
    body.textContent = "";
    view.chapters.forEach(function (ch) {
      var section = el("section", "chapter");
      section.appendChild(el("h3", null, "Chapter " + ch.number + ": " + ch.name + " (" + ch.cleared + "/" + ch.benches.length + ")"));
      section.appendChild(el("p", "note", ch.blurb + (ch.open ? "" : " Locked: clear " + ch.need + " benches of the chapter before to open it.")));
      var ul = el("ul", "bench-grid");
      ch.benches.forEach(function (b) {
        var li = document.createElement("li");
        var btn = el("button", "bench-btn" + (b.cleared ? " cleared" : "") + (b.current ? " current" : ""));
        btn.type = "button";
        btn.setAttribute("data-id", b.id);
        btn.setAttribute("data-testid", "mirror-lab-bench-" + b.id);
        btn.disabled = !ch.open;
        btn.appendChild(el("span", "bname", b.number + ". " + b.name));
        btn.appendChild(el("span", "bmeta", !ch.open ? "Locked" : b.cleared ? "Cleared with " + plural(b.best, "piece", "pieces") + (b.fewest ? " (fewest)" : "") : "Not cleared"));
        li.appendChild(btn);
        ul.appendChild(li);
      });
      section.appendChild(ul);
      body.appendChild(section);
    });
  }
  function renderLog() {
    var log = view.log;
    setText($("log-summary"), log.summary.pages + " of " + log.summary.pages_total + " shelf pages filled, " + log.summary.cards + " of " + log.summary.cards_total + " circuit cards filled.");
    var shelf = $("shelf-list");
    shelf.textContent = "";
    log.shelf.forEach(function (p) {
      var li = el("li", p.filled ? "filled" : "empty");
      li.innerHTML = p.icon;
      var box = el("div");
      box.appendChild(el("strong", null, p.title + (p.filled ? "" : " (empty page)")));
      box.appendChild(el("span", "note", p.text));
      li.appendChild(box);
      shelf.appendChild(li);
    });
    var cards = $("cards-list");
    cards.textContent = "";
    log.cards.forEach(function (c) {
      var li = el("li", c.filled ? "filled" : "empty");
      var head = el("strong", null, "Chapter " + c.chapter + ", bench " + c.number + ": " + (c.filled || !c.locked ? c.name : "Locked"));
      li.appendChild(head);
      if (c.filled) {
        if (c.fewest) head.appendChild(el("span", "tag", "Fewest pieces"));
        li.appendChild(el("p", "note", "Cleared with " + plural(c.pieces, "piece", "pieces") + ": " + c.used + "."));
        li.appendChild(el("p", "card-line story-text", c.line));
      } else {
        li.appendChild(el("p", "note", c.locked ? "Clear 5 benches of the chapter before to open this one." : "Not cleared yet."));
      }
      cards.appendChild(li);
    });
  }
  // ---- goals, hints and the About page -------------------------------------------------------------
  function renderGoals() {
    var list = $("goals-list");
    var sig = view.goals.map(function (g) { return g.id + g.have; }).join(",");
    if (list.dataset.sig === sig) return;
    list.dataset.sig = sig;
    list.textContent = "";
    if (!view.goals.length) { list.appendChild(el("li", null, "Every goal is done. Every bench is cleared and tagged.")); return; }
    view.goals.forEach(function (g) {
      var li = el("li");
      li.appendChild(el("strong", null, g.label + ": "));
      li.appendChild(document.createTextNode(g.description + " "));
      var bar = el("span", "bar");
      bar.setAttribute("aria-hidden", "true");
      var fill = el("span", "bar-fill");
      fill.style.width = Math.round(100 * g.have / g.need) + "%";
      bar.appendChild(fill);
      li.appendChild(bar);
      li.appendChild(el("span", "goal-count", " " + g.have + "/" + g.need));
      list.appendChild(li);
    });
  }
  function renderHints() {
    var h = view.bench.hint;
    var btn = $("hint-button");
    btn.hidden = !h.can_ask;
    setText(btn, h.rung === 0 ? "Would you like a suggestion?" : (h.rung === 1 ? "Another hint" : "Another hint: the answer"));
    $("hint-limit").hidden = !(h.max < 3 && h.rung >= h.max);
    $("hint-nudge").hidden = !h.nudge;
    setText($("hint-nudge"), h.nudge ? "Nudge: " + h.nudge : "");
    $("hint-hint").hidden = !h.hint;
    setText($("hint-hint"), h.hint ? "Hint: " + h.hint : "");
    $("hint-answer").hidden = !h.answer;
    $("place-answer-button").hidden = !h.answer;
    var list = $("hint-answer-list");
    var sig = h.answer_lines.join("|");
    if (list.dataset.sig !== sig) {
      list.dataset.sig = sig;
      list.textContent = "";
      h.answer_lines.forEach(function (t) { list.appendChild(el("li", null, t)); });
    }
  }
  function renderAchievements() {
    var list = $("achievements-list");
    var earnedNow = [];
    var sig = view.achievements.map(function (a) { return a.id + a.have; }).join(",");
    if (list.dataset.sig !== sig) {
      list.dataset.sig = sig;
      list.textContent = "";
      view.achievements.forEach(function (a) {
        var li = el("li", a.earned ? "earned" : "");
        li.setAttribute("data-achievement-id", a.id);
        li.appendChild(el("span", "tick", a.earned ? "Earned" : a.have + "/" + a.need));
        var name = el("strong", null, " " + a.label + " ");
        name.setAttribute("data-achievement-label", "");
        li.appendChild(name);
        li.appendChild(el("span", null, a.description));
        list.appendChild(li);
      });
    }
    view.achievements.forEach(function (a) { if (a.earned) earnedNow.push(a.id); });
    setText($("achievements-count"), view.achievements_summary.text);
    setText($("achievements-toggle-button"), "Achievements (" + earnedNow.length + "/" + view.achievements.length + ")");
    if (knownEarned !== null) {
      earnedNow.filter(function (id) { return knownEarned.indexOf(id) === -1; }).forEach(function (id) {
        var a = view.achievements.filter(function (x) { return x.id === id; })[0];
        showToast("Achievement unlocked: " + a.label + ".");
        announce("Achievement unlocked: " + a.label + ".");
      });
    }
    knownEarned = earnedNow;
  }
  function renderInfo() {
    var info = view.info;
    if (!info) return;
    setText($("info-page-framing"), info.framing);
    setText($("how-heading"), info.how_heading);
    setText($("pledge-heading"), info.pledge_heading);
    if ($("info-page-sources").dataset.built === "1") return;
    $("info-page-sources").dataset.built = "1";
    fillList($("how-list"), info.how);
    fillList($("pledge-list"), info.pledge);
    var list = $("info-page-sources");
    list.textContent = "";
    info.facts.forEach(function (fact) {
      var item = el("li", "info-page-source");
      item.appendChild(el("strong", null, fact.heading));
      item.appendChild(el("p", "info-page-framing", fact.fact));
      item.appendChild(el("p", "info-page-tie-in", fact.tie_in));
      var link = el("a", null, fact.source.title);
      link.href = fact.source.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      var src = el("p", "info-page-source-note");
      src.appendChild(document.createTextNode("Source: "));
      src.appendChild(link);
      src.appendChild(document.createTextNode(", " + fact.source.publisher + ". Read on " + fact.source.date_read + "."));
      item.appendChild(src);
      list.appendChild(item);
    });
  }
  function fillList(list, lines) {
    list.textContent = "";
    lines.forEach(function (t) { list.appendChild(el("li", null, t)); });
  }

  // ---- what's new: the page sets window.CHANGELOG_JSON (the raw text of changelog.json) for shared/whats-new-banner.js ----
  function renderChangelog(entries) {
    var holder = $("changelog-entries");
    holder.textContent = "";
    entries.forEach(function (entry) {
      var row = el("article", "changelog-entry");
      row.appendChild(el("div", "changelog-date", entry.date));
      row.appendChild(el("p", "changelog-text", entry.entry));
      holder.appendChild(row);
    });
    $("changelog-toggle-button").textContent = "What's New (" + entries.length + ")";
  }
  function loadChangelog() {
    return fetch("changelog.json").then(function (r) { return r.text(); }).then(function (text) {
      window.CHANGELOG_JSON = text;
      var data = JSON.parse(text);
      var list = Array.isArray(data) ? data : (data && data.changelog) || [];
      renderChangelog(list.slice().sort(function (a, b) { return a.date < b.date ? 1 : -1; }));
    }).catch(function () { renderChangelog([]); });
  }

  function render() {
    renderBench();
    renderTray();
    renderStats();
    renderVerdict();
    renderBenches();
    renderLog();
    renderGoals();
    renderHints();
    renderAchievements();
    renderInfo();
  }

  // ---- talking to the engine -----------------------------------------------------------------------
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
    var result = JSON.parse(engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    view = result;
    showToast("");
    render();
    if (!result.ok) showToast(result.message);
    if (request.action !== "open" && request.action !== "pick" && request.action !== "next" && result.message) announce(result.message);
    if (result.verdict && result.verdict.kind === "cleared") announce("Bench cleared. " + (result.verdict.line || ""));
    if (request.action !== "open") persist();
    return result;
  }

  // ---- taps, keys and drags ------------------------------------------------------------------------
  function act(r, c) {
    cursor = { r: r, c: c };
    drawCursor();
    var p = placedAt(r, c);
    if (!isSlot(r, c)) { showToast(""); announce(describeCell(r, c)); return; }
    if (held === "pickup") {
      if (p) send({ action: "pickup", r: r, c: c });
      else showToast("Nothing to pick up there.");
      return;
    }
    if (held) {
      if (p && p.piece === held) {
        if (p.flips) send({ action: "flip", r: r, c: c });
        else showToast("A " + trayItem(held).label.toLowerCase() + " is already there. Use the pick up tool to move it.");
      } else send({ action: "place", r: r, c: c, piece: held });
      return;
    }
    if (p) {
      if (p.flips) { send({ action: "flip", r: r, c: c }); return; }
      var piece = p.piece;
      if (send({ action: "pickup", r: r, c: c })) { held = piece; renderTray(); }
      return;
    }
    showToast("Choose a piece from the tray first.");
  }
  function cellFromEvent(target) {
    var hit = target && target.closest ? target.closest(".ml-hit") : null;
    if (!hit) return null;
    return { r: parseInt(hit.getAttribute("data-r"), 10), c: parseInt(hit.getAttribute("data-c"), 10) };
  }
  function onBenchClick(e) {
    if (suppressClick) return;
    var cell = cellFromEvent(e.target);
    if (cell) act(cell.r, cell.c);
  }

  function startDrag(e, from, piece, r, c, source) {
    if (e.pointerType !== "mouse" || e.button !== 0) return;        // touch and pen use tap to choose and tap to place
    drag = { from: from, piece: piece, r: r, c: c, x: e.clientX, y: e.clientY, started: false, ghost: null, source: source };
    document.addEventListener("pointermove", onDragMove);
    document.addEventListener("pointerup", onDragEnd);
    document.addEventListener("pointercancel", onDragCancel);
  }
  function onDragMove(e) {
    if (!drag) return;
    if (!drag.started) {
      if (Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y) < DRAG_PIXELS) return;
      drag.started = true;
      var ghost = el("div", "drag-ghost");
      var t = trayItem(drag.piece);
      ghost.innerHTML = t ? t.icon : "";
      document.body.appendChild(ghost);
      drag.ghost = ghost;
    }
    drag.ghost.style.left = e.clientX + "px";
    drag.ghost.style.top = e.clientY + "px";
  }
  function endDrag() {
    document.removeEventListener("pointermove", onDragMove);
    document.removeEventListener("pointerup", onDragEnd);
    document.removeEventListener("pointercancel", onDragCancel);
    if (drag && drag.ghost) drag.ghost.remove();
    drag = null;
  }
  function onDragCancel() { endDrag(); }
  function onDragEnd(e) {
    var d = drag;
    endDrag();
    if (!d || !d.started) return;
    suppressClick = true;
    setTimeout(function () { suppressClick = false; }, 0);
    var target = document.elementFromPoint(e.clientX, e.clientY);
    var cell = cellFromEvent(target);
    if (d.from === "tray") {
      if (cell && isSlot(cell.r, cell.c)) {
        cursor = { r: cell.r, c: cell.c };
        var p = placedAt(cell.r, cell.c);
        if (!(p && p.piece === d.piece)) send({ action: "place", r: cell.r, c: cell.c, piece: d.piece });
      }
    } else if (cell && isSlot(cell.r, cell.c)) {
      if (cell.r !== d.r || cell.c !== d.c) send({ action: "move", r: d.r, c: d.c, to_r: cell.r, to_c: cell.c });
    } else if (!cell && !(target && target.closest && target.closest("#bench-holder"))) {
      send({ action: "pickup", r: d.r, c: d.c });
    }
  }
  function onBenchPointerDown(e) {
    var cell = cellFromEvent(e.target);
    if (!cell) return;
    var p = placedAt(cell.r, cell.c);
    if (p) startDrag(e, "bench", p.piece, cell.r, cell.c, null);
  }

  function onBenchKey(e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    var b = view.bench;
    var key = e.key;
    var move = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] }[key];
    if (move) {
      e.preventDefault();
      cursor = { r: Math.max(0, Math.min(b.h - 1, cursor.r + move[0])), c: Math.max(0, Math.min(b.w - 1, cursor.c + move[1])) };
      $("bench-holder").classList.add("kb");
      drawCursor();
      announce(describeCell(cursor.r, cursor.c));
    } else if (key === "Enter" || key === " ") {
      e.preventDefault();
      act(cursor.r, cursor.c);
    } else if (key === "p" || key === "P" || key === "Delete" || key === "Backspace") {
      e.preventDefault();
      if (placedAt(cursor.r, cursor.c)) send({ action: "pickup", r: cursor.r, c: cursor.c });
      else announce("Nothing to pick up at " + cellName(cursor.r, cursor.c) + ".");
    } else if (key === "f" || key === "F") {
      e.preventDefault();
      var p = placedAt(cursor.r, cursor.c);
      if (p && p.flips) send({ action: "flip", r: cursor.r, c: cursor.c });
      else announce("Nothing here flips.");
    } else if (key === "Escape") {
      if (held) { e.preventDefault(); setHeld(null); }
    } else if (key === "0" || key === "u" || key === "U") {
      e.preventDefault();
      setHeld(held === "pickup" ? null : "pickup");
    } else if (/^[1-9]$/.test(key) && b.tray[parseInt(key, 10) - 1]) {
      e.preventDefault();
      var t = b.tray[parseInt(key, 10) - 1];
      if (t.left > 0) setHeld(held === t.piece ? null : t.piece);
      else announce("No " + t.label.toLowerCase() + " left in the tray.");
    }
  }
  function onBenchFocus() { drawCursor(); }

  function onPick(e) {
    var node = e.target.closest ? e.target.closest("[data-id]") : null;
    if (!node || node.getAttribute("aria-disabled") === "true" || node.disabled) return;
    if (e.type === "keydown" && e.key !== "Enter" && e.key !== " ") return;
    if (e.type === "keydown") e.preventDefault();
    send({ action: "pick", bench: node.getAttribute("data-id") });
    if (window.NOYVJ_LAYOUT !== "pc" && $("bench-panel").scrollIntoView) $("bench-panel").scrollIntoView({ block: "start" });      // the Desktop layout never scrolls the page
  }

  function askThen(id, message, confirmLabel, go) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: false, onConfirm: go });
    else go();
  }

  // ---- difficulty (AN-17, shared/difficulty.js): the page keeps the choice, the engine applies it and is never told to save it ----
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

  var TUTORIAL_STEPS = [
    { title: "Welcome to Arden Relay", text: "The light guides here were smashed. On each bench a beam leaves the emitter and you place pieces so it reaches every sensor. Nothing is timed and nothing is lost: any piece can be picked up again. Skip any time and reopen this from the Tutorial button." },
    { selector: "#tray", title: "The tray", text: "These are the pieces you have for this bench. Tap one to choose it, or drag it with a mouse. The count says how many are left." },
    { selector: "#bench-holder", title: "The bench", text: "Dashed squares are slots. Tap a slot to place the chosen piece and the beam redraws at once. Tap a placed mirror or prism to flip it. A white beam is a thin solid line, an S beam is short dashes marked S and an L beam is long dashes marked L." },
    { selector: "#sensor-list", title: "Sensors, in words", text: "Every sensor is listed here in words as well as on the picture. A lit sensor is filled with a tick. A sensor with a cross is a decoy and must stay dark. A sensor never stops a beam." },
    { selector: "#hint-button", title: "Hints are free", text: "A nudge says which piece matters and roughly where, a hint draws one piece as a dotted ghost, and the answer draws them all. They only come when you press, and the bench still counts." },
    { selector: "#goals", title: "Your goals", text: "Three goals stay in view, in any order. Pieces you place, benches you clear and hints you ask for all count toward something on the screen." },
    { selector: "#benches-toggle-button", title: "Benches", text: "Clear 5 benches of a chapter to open the next chapter. Inside a chapter, play the benches in any order. A ring on the map means you cleared a bench with the fewest pieces." },
    { selector: "#difficulty-panel", title: "Easy, Normal or Hard", text: "Normal is the game as designed. Easy and Hard only change how much help the hint ladder gives. Nothing is locked by any choice." },
    { title: "You are ready", text: "Take your time. Your benches are saved as you go." }
  ];

  function wire() {
    $("toast").addEventListener("click", function () { showToast(""); });
    wirePanelToggle("benches-toggle-button", "benches-panel");
    wirePanelToggle("log-toggle-button", "log-panel");
    wirePanelToggle("achievements-toggle-button", "achievements-panel");
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    wireDifficulty();
    $("hint-button").addEventListener("click", function () {
      var btn = $("hint-button");
      send({ action: "hint" });
      if (btn.hidden && document.activeElement === document.body) {
        var next = $("place-answer-button").hidden ? $("hint-box") : $("place-answer-button");
        next.focus();
      }
    });
    $("place-answer-button").addEventListener("click", function () {
      var go = function () { send({ action: "place_answer" }); };
      if (view.difficulty !== "easy" && window.ConfirmDialog) {
        window.ConfirmDialog.ask({ id: "mirror-lab-place-answer", message: "Place the stored answer on the bench? It replaces the pieces on this bench (they go back to the tray) and this bench still counts.", confirmLabel: "Place them", allowSkip: false, onConfirm: go });
      } else go();
    });
    var holder = $("bench-holder");
    holder.addEventListener("click", onBenchClick);
    holder.addEventListener("keydown", onBenchKey);
    holder.addEventListener("focus", onBenchFocus);
    holder.addEventListener("blur", function () { holder.classList.remove("kb"); });
    holder.addEventListener("pointerdown", onBenchPointerDown);
    $("pickup-tool-button").addEventListener("click", function () { setHeld(held === "pickup" ? null : "pickup"); });
    $("clear-button").addEventListener("click", function () { send({ action: "clear_bench" }); });
    $("next-button").addEventListener("click", function () { send({ action: "next" }); });
    $("map-holder").addEventListener("click", onPick);
    $("map-holder").addEventListener("keydown", onPick);
    $("benches-body").addEventListener("click", onPick);
    $("reset-button").addEventListener("click", function () {
      askThen("mirror-lab-reset", "Start the whole lab over? Your cleared benches, Bench Log and tally will be erased.", "Erase it", function () { knownEarned = null; send({ action: "reset" }); held = null; });
    });
    // The save widget loads a save straight into the engine; this redraws afterwards.
    window.mirrorLabRefresh = function () { if (engine) { benchId = null; knownEarned = null; send({ action: "open" }); } };
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
    sendDifficulty();
    await changelog;
    if (window.GameTutorial) window.GameTutorial.init(window.mirrorLabTutorialSteps ? window.mirrorLabTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS, { gameId: "mirror-lab" });
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The bench could not start (" + err + "). Reload to try again.";
  });
})();
