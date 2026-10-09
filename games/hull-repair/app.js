/* Hull Repair view: glue only. The engine (game.py and its modules) holds every rule; this file draws what handle()
   returns, turns a finger or the keyboard into begin / move / end requests, and forwards what the player does. No game
   logic lives here. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["rules.py", "play.py", "boards_dock.py", "boards_crew.py", "boards_engineering.py", "boards_life.py", "boards_core.py", "boards.py", "progress.py", "render.py", "hints.py", "logbook.py", "achievements.py", "info.py"];
  var STORE_KEY = "hull-repair:state";
  var BACKUP_KEY = "hull-repair:state-backup";
  var GLYPHS = { circle: "●", square: "■", triangle: "▲", diamond: "◆", hexagon: "⬢", pentagon: "⬟", cross: "✚", star: "★" };

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;
  var view = null;
  var boardId = null;
  var drag = null;          // {last: [x, y], active: bool} while a pointer is down
  var kbd = { x: 0, y: 0, holding: false, line: "" };

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
  function showToast(text) {
    var t = $("toast");
    t.textContent = text;
    t.classList.toggle("on", Boolean(text));
  }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }

  // ---- panels --------------------------------------------------------------------------------------
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () {
      $(panelId).hidden = !$(panelId).hidden;
      $(buttonId).setAttribute("aria-expanded", String(!$(panelId).hidden));
    });
  }
  function renderAbout() {
    var about = view.about;
    if (!about || $("pledge-list").dataset.done) return;
    $("pledge-list").dataset.done = "1";
    setText($("info-page-framing"), about.framing);
    setText($("pledge-heading"), about.pledge_heading);
    setText($("how-heading"), about.how_heading);
    about.pledge.forEach(function (line) { $("pledge-list").appendChild(el("li", null, line)); });
    about.how.forEach(function (line) { $("how-list").appendChild(el("li", null, line)); });
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
    document.querySelector("#changelog-toggle-button .btn-long").textContent = "What's New (" + entries.length + ")";
  }
  function loadChangelog() {
    return fetch("changelog.json").then(function (r) { return r.text(); }).then(function (text) {
      window.CHANGELOG_JSON = text;
      var data = JSON.parse(text);
      var list = Array.isArray(data) ? data : (data && data.changelog) || [];
      renderChangelog(list.slice().sort(function (a, b) { return a.date < b.date ? 1 : -1; }));
    }).catch(function () { renderChangelog([]); });
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
    bumpStat("stat-patched", view.totals.patched + "/" + view.totals.rooms);
    bumpStat("stat-restored", view.totals.restored + "/" + view.totals.rooms);
    bumpStat("stat-laid", view.tally.laid);
    bumpStat("stat-empty", view.board.empty + "/" + view.board.cells);
    bumpStat("stat-erased", view.tally.erased);
    bumpStat("stat-undos", view.tally.undos);
    bumpStat("stat-hints", view.tally.hints);
  }

  // ---- the board -------------------------------------------------------------------------------------
  function boardSvg() { return $("board-holder").querySelector("svg"); }
  function renderBoard() {
    var b = view.board;
    if (b.svg) {
      $("board-holder").innerHTML = b.svg;
      boardId = b.id;
      kbd = { x: Math.min(kbd.x, b.w - 1), y: Math.min(kbd.y, b.h - 1), holding: false, line: "" };
      placeCursor(false);
      $("result-card").hidden = true;
    }
    var layer = boardSvg() && boardSvg().querySelector("#hr-lines");
    if (layer && layer.dataset.sig !== view.layer) {
      layer.dataset.sig = view.layer;
      layer.innerHTML = view.layer;
    }
    setText($("board-chapter"), b.chapter + " · room " + b.number + " of " + b.of + " · " + b.w + " by " + b.h);
    setText($("board-heading"), b.name);
    var note = $("board-new");
    note.hidden = !b.new;
    setText(note, b.new ? "New on this deck. " + b.new : "");
    var words = $("words-lines");
    if (words.dataset.sig !== b.id) {
      words.dataset.sig = b.id;
      words.textContent = "";
      b.words.forEach(function (l) { words.appendChild(el("li", null, l)); });
    }
    var joined = b.lines.filter(function (l) { return l.state === "connected"; }).length;
    setText($("board-line"), "Lines joined " + joined + "/" + b.lines.length + " · cells still empty " + b.empty);
    renderChips();
    $("undo-button").disabled = !view.can_undo;
    document.documentElement.setAttribute("data-board-status", b.status_name);
  }
  function renderChips() {
    var ul = $("line-chips");
    var sig = view.board.id + view.board.lines.map(function (l) { return l.c + l.state; }).join("");
    if (ul.dataset.sig === sig) return;
    ul.dataset.sig = sig;
    ul.textContent = "";
    view.board.lines.forEach(function (l) {
      var li = el("li");
      var b = el("button", l.state === "connected" ? "joined" : "");
      b.type = "button";
      b.className += " hr-c-" + l.c;
      b.dataset.testid = "hull-repair-line-" + l.c;
      var g = el("span", "glyph", GLYPHS[l.shape]);
      g.setAttribute("aria-hidden", "true");
      b.appendChild(g);
      b.appendChild(el("span", null, l.c + " " + l.name));
      b.appendChild(el("span", "state", l.state === "connected" ? "joined" : (l.state === "drawing" ? "drawing" : "open")));
      b.setAttribute("aria-label", l.name + " line, letter " + l.c + ", " + (l.state === "connected" ? "joined" : l.state === "drawing" ? "not finished" : "not started") + ". Press to clear this line.");
      b.addEventListener("click", function () { send({ action: "clear_line", line: l.c }); });
      li.appendChild(b);
      ul.appendChild(li);
    });
  }
  function renderResult() {
    var r = view.result;
    var card = $("result-card");
    if (!r) { card.hidden = true; return; }
    card.hidden = false;
    card.className = "result-card " + r.status_name;
    if (r.status === 2) {
      setText($("result-title"), "Room restored");
      setText($("result-text"), "Every line is joined and every cell is covered." + (r.first ? " The room is back on." : ""));
    } else {
      setText($("result-title"), "Room patched");
      setText($("result-text"), "Every line is joined. " + plural(r.empty, "cell is", "cells are") + " still empty: cover them all to restore this room." + (r.first ? " The room is back on, dimly." : ""));
    }
    var log = $("result-log");
    log.hidden = !(r.first && r.log);
    setText(log, r.log ? "Log, " + r.room + ": " + r.log : "");
    var next = $("next-button");
    next.hidden = !r.next;
    if (r.next) setText(next, "Next room: " + r.next_name);
  }
  function renderRooms() {
    var holder = $("rooms-body");
    var sig = JSON.stringify(view.rooms.map(function (c) { return [c.open, c.rooms.map(function (r) { return r.status + (r.current ? "c" : ""); })]; }));
    if (holder.dataset.sig === sig) return;
    holder.dataset.sig = sig;
    holder.textContent = "";
    view.rooms.forEach(function (c) {
      if (!c.total) return;
      var sec = el("section", "chapter" + (c.open ? "" : " locked"));
      sec.appendChild(el("h3", null, c.name + " (" + c.patched + "/" + c.total + " patched, " + c.restored + " restored)"));
      sec.appendChild(el("p", "note", c.open ? c.blurb : "Locked: patch " + c.need + " rooms of " + c.prev_name + " to open this deck."));
      var ul = el("ul", "room-grid");
      c.rooms.forEach(function (r) {
        var li = el("li");
        var b = el("button", "room-btn s" + r.status + (r.current ? " current" : ""));
        b.type = "button";
        b.dataset.testid = "hull-repair-room-" + r.id;
        b.appendChild(el("span", "rname", r.number + ". " + r.name));
        b.appendChild(el("span", "rmeta", r.open ? (r.status_name.charAt(0).toUpperCase() + r.status_name.slice(1) + " · " + r.size + " · " + plural(r.lines, "line", "lines")) : "Locked"));
        b.setAttribute("aria-label", r.number + ", " + r.name + ". " + (r.open ? r.status_name + ", " + r.size + ", " + plural(r.lines, "line", "lines") : "Locked") + (r.current ? ". Current room" : ""));
        if (!r.open) b.setAttribute("aria-disabled", "true");
        b.addEventListener("click", function () {
          if (!r.open) { showToast("That deck opens once " + c.need + " rooms of " + c.prev_name + " are patched."); return; }
          send({ action: "pick", board: r.id });
          $("rooms-panel").hidden = true;
          $("rooms-toggle-button").setAttribute("aria-expanded", "false");
          var anchor = $("board-panel");
          if (anchor.scrollIntoView) anchor.scrollIntoView({ block: "start" });
        });
        li.appendChild(b);
        ul.appendChild(li);
      });
      sec.appendChild(ul);
      holder.appendChild(sec);
    });
  }
  function renderMap() {
    var holder = $("map-holder");
    if (holder.dataset.sig === view.map) return;
    holder.dataset.sig = view.map;
    holder.innerHTML = view.map;
  }
  function onMapClick(e) {
    var room = e.target.closest ? e.target.closest(".hr-room[data-id]") : null;
    if (!room) return;
    if (room.getAttribute("data-open") !== "1") { showToast("That deck is not open yet: patch five rooms of the deck before it."); return; }
    send({ action: "pick", board: room.getAttribute("data-id") });
    $("rooms-panel").hidden = true;
    $("rooms-toggle-button").setAttribute("aria-expanded", "false");
    var anchor = $("board-panel");
    if (anchor.scrollIntoView) anchor.scrollIntoView({ block: "start" });
  }
  var knownEarned = null;
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
    $("achievements-toggle-button").textContent = "Achievements (" + earnedNow.length + "/" + view.achievements.length + ")";
    if (knownEarned !== null) {
      earnedNow.filter(function (id) { return knownEarned.indexOf(id) === -1; }).forEach(function (id) {
        var a = view.achievements.filter(function (x) { return x.id === id; })[0];
        showToast("Achievement unlocked: " + a.label + ".");
        announce("Achievement unlocked: " + a.label + ".");
      });
    }
    knownEarned = earnedNow;
  }
  function renderLog() {
    var found = view.log.filter(function (e) { return e.found; }).length;
    setText($("log-summary"), found + " of " + view.log.length + " log lines found. Each room you patch adds its line, in any order, and nothing here can be missed.");
    $("log-toggle-button").textContent = "Repair log (" + found + "/" + view.log.length + ")";
    var list = $("log-list");
    var sig = view.log.map(function (e) { return e.found ? "1" : "0"; }).join("");
    if (list.dataset.sig === sig) return;
    list.dataset.sig = sig;
    list.textContent = "";
    view.log.forEach(function (e) {
      var li = el("li", e.found ? "" : "missing");
      li.appendChild(el("span", "log-room", e.name));
      li.appendChild(document.createTextNode(" (" + e.deck + ")"));
      if (e.found) li.appendChild(el("p", "log-line story-text", e.line));
      else li.appendChild(el("p", "note", "Not found yet: patch this room to read its line."));
      list.appendChild(li);
    });
  }
  function renderGoalStrip() {
    var list = $("goals-list");
    var sig = view.goals.map(function (g) { return g.id + g.have; }).join(",");
    if (list.dataset.sig === sig) return;
    list.dataset.sig = sig;
    list.textContent = "";
    if (!view.goals.length) { list.appendChild(el("li", null, "Every goal you can reach right now is done. New ones appear as new decks open.")); return; }
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
    var h = view.hint;
    var btn = $("hint-button");
    btn.hidden = h.rung >= 3;
    setText(btn, h.rung === 0 ? "Need a nudge?" : (h.rung === 1 ? "Another hint" : "Show the answer"));
    $("hint-nudge").hidden = !h.nudge;
    setText($("hint-nudge"), h.nudge ? "Nudge: " + h.nudge : "");
    $("hint-hint").hidden = !h.hint;
    setText($("hint-hint"), h.hint ? "Hint: " + h.hint : "");
    $("hint-answer").hidden = !h.answer;
  }
  function render() {
    renderAbout();
    renderBoard();
    renderStats();
    renderResult();
    renderRooms();
    renderMap();
    renderLog();
    renderAchievements();
    renderGoalStrip();
    renderHints();
  }

  // ---- talking to the engine --------------------------------------------------------------------------------
  function persist() {
    try {
      var proxy = engine.getState();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(STORE_KEY, JSON.stringify(obj));
    } catch (e) { /* the save widget keeps the real copy */ }
  }
  function send(request, quiet) {
    if (!engine) return null;
    var result = JSON.parse(engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    var previous = view;
    view = result;
    if (!quiet) showToast("");
    if (request.action === "pick" || request.action === "next" || request.action === "reset") $("result-card").hidden = true;
    render();
    if (result.ok === false && result.message) setText($("board-line"), result.message);
    if (request.action === "end" && view.result && (!previous || !previous.result || previous.result.status !== view.result.status)) {
      announce(view.result.status === 2 ? "Room restored." : "Room patched. " + plural(view.result.empty, "cell", "cells") + " still empty.");
    }
    if (request.action === "end" || request.action === "undo" || request.action === "clear" || request.action === "clear_line" || request.action === "pick" || request.action === "next" || request.action === "hint" || request.action === "load_answer") persist();
    return result;
  }

  // ---- pointer drawing ---------------------------------------------------------------------------------------
  function cellAt(e) {
    var svg = boardSvg();
    if (!svg || !view) return null;
    var r = svg.getBoundingClientRect();
    if (!r.width || !r.height) return null;
    var b = view.board;
    var vbW = b.w * b.cell + 2 * b.pad;
    var vbH = b.h * b.cell + 2 * b.pad;
    var vx = (e.clientX - r.left) / r.width * vbW - b.pad;
    var vy = (e.clientY - r.top) / r.height * vbH - b.pad;
    var x = Math.floor(vx / b.cell);
    var y = Math.floor(vy / b.cell);
    if (x < 0 || y < 0 || x >= b.w || y >= b.h) return null;
    return [x, y];
  }
  function stepsBetween(a, b) {
    var out = [];
    var x = a[0];
    var y = a[1];
    while (x !== b[0] || y !== b[1]) {
      var dx = b[0] - x;
      var dy = b[1] - y;
      if (Math.abs(dx) >= Math.abs(dy)) x += dx > 0 ? 1 : -1; else y += dy > 0 ? 1 : -1;
      out.push([x, y]);
    }
    return out;
  }
  function onPointerDown(e) {
    if (e.button !== undefined && e.button !== 0) return;
    var cell = cellAt(e);
    if (!cell) return;
    e.preventDefault();
    var holder = $("board-holder");
    if (holder.setPointerCapture) { try { holder.setPointerCapture(e.pointerId); } catch (err) { /* synthetic events */ } }
    var res = send({ action: "begin", x: cell[0], y: cell[1] }, true);
    drag = { last: cell, active: Boolean(res && res.ok), id: e.pointerId };
    kbd.x = cell[0];
    kbd.y = cell[1];
    placeCursor(false);
  }
  function onPointerMove(e) {
    if (!drag || !drag.active) return;
    var cell = cellAt(e);
    if (!cell || (cell[0] === drag.last[0] && cell[1] === drag.last[1])) return;
    e.preventDefault();
    var steps = stepsBetween(drag.last, cell);
    drag.last = cell;
    var res = send({ action: "move", cells: steps }, true);
    if (res && res.ok === false) setText($("board-line"), res.message);
  }
  function onPointerUp(e) {
    if (!drag) return;
    var was = drag;
    drag = null;
    var holder = $("board-holder");
    if (holder.releasePointerCapture) { try { holder.releasePointerCapture(was.id); } catch (err) { /* ignore */ } }
    if (was.active) send({ action: "end" });
    else if (view && view.message && view.ok === false) showToast(view.message);
  }

  // ---- keyboard drawing ----------------------------------------------------------------------------------------
  function placeCursor(show) {
    var svg = boardSvg();
    if (!svg) return;
    var c = svg.querySelector("#hr-cursor");
    if (!c || !view) return;
    var cell = view.board.cell;
    c.setAttribute("x", kbd.x * cell);
    c.setAttribute("y", kbd.y * cell);
    if (show !== false) c.removeAttribute("hidden"); else c.setAttribute("hidden", "hidden");
  }
  function describeCursor(prefix) {
    var res = send({ action: "cell", x: kbd.x, y: kbd.y }, true);
    if (res && res.cell_text) announce((prefix ? prefix + " " : "") + res.cell_text);
  }
  function currentPath(line) {
    var l = view.board.paths && view.board.paths[line];
    return l || [];
  }
  function onBoardKey(e) {
    if (!view || e.ctrlKey || e.metaKey || e.altKey) return;
    var b = view.board;
    var key = e.key;
    var dirs = { ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0] };
    if (dirs[key]) {
      e.preventDefault();
      var nx = kbd.x + dirs[key][0];
      var ny = kbd.y + dirs[key][1];
      if (nx < 0 || ny < 0 || nx >= b.w || ny >= b.h) return;
      kbd.x = nx;
      kbd.y = ny;
      placeCursor(true);
      if (kbd.holding) {
        var res = send({ action: "move", cells: [[nx, ny]] }, true);
        if (res && res.ok === false) { announce(res.message); kbd.x -= dirs[key][0]; kbd.y -= dirs[key][1]; placeCursor(true); return; }
      }
      describeCursor("");
      return;
    }
    if (key === "Enter" || key === " ") {
      e.preventDefault();
      if (kbd.holding) {
        kbd.holding = false;
        send({ action: "end" });
        announce("Let go.");
      } else {
        var r = send({ action: "begin", x: kbd.x, y: kbd.y }, true);
        if (r && r.ok) { kbd.holding = true; placeCursor(true); announce("Holding a line. Arrow keys draw, Enter lets go."); }
        else if (r) announce(r.message);
      }
      return;
    }
    if (key === "Escape" && kbd.holding) {
      e.preventDefault();
      kbd.holding = false;
      send({ action: "end" });
      announce("Let go.");
      return;
    }
    if (key === "Backspace" || key === "Delete") {
      e.preventDefault();
      if (!kbd.holding) { announce("Press Enter on a line's end to pick it up first."); return; }
      var line = null;
      Object.keys(b.paths || {}).forEach(function (c) {
        var p = b.paths[c];
        var last = p[p.length - 1];
        if (last && last[0] === kbd.x && last[1] === kbd.y) line = c;
      });
      if (!line || b.paths[line].length < 2) { announce("Nothing to take back."); return; }
      var back = b.paths[line][b.paths[line].length - 2];
      kbd.x = back[0];
      kbd.y = back[1];
      send({ action: "move", cells: [back] }, true);
      placeCursor(true);
      describeCursor("");
      return;
    }
    if ((key === "z" || key === "Z") && !kbd.holding) {
      e.preventDefault();
      send({ action: "undo" });
    }
  }
  function onGlobalKey(e) {
    if (!view || e.ctrlKey || e.metaKey || e.altKey) return;
    var tag = e.target && e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || tag === "BUTTON" || tag === "SUMMARY" || tag === "A") return;
    if (e.target === $("board-holder")) return;
    if (document.querySelector("dialog[open], .confirm-dialog, [role='dialog']")) return;
    if (e.key === "z" || e.key === "Z") { e.preventDefault(); send({ action: "undo" }); }
  }

  function askThen(id, message, confirmLabel, go) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: false, onConfirm: go });
    else go();
  }

  function wire() {
    $("toast").addEventListener("click", function () { showToast(""); });
    wirePanelToggle("rooms-toggle-button", "rooms-panel");
    wirePanelToggle("log-toggle-button", "log-panel");
    wirePanelToggle("achievements-toggle-button", "achievements-panel");
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    $("map-holder").addEventListener("click", onMapClick);
    $("hint-button").addEventListener("click", function () { send({ action: "hint" }); });
    $("answer-load-button").addEventListener("click", function () { send({ action: "load_answer" }); });
    var holder = $("board-holder");
    holder.addEventListener("pointerdown", onPointerDown);
    holder.addEventListener("pointermove", onPointerMove);
    holder.addEventListener("pointerup", onPointerUp);
    holder.addEventListener("pointercancel", onPointerUp);
    holder.addEventListener("keydown", onBoardKey);
    holder.addEventListener("focus", function () { placeCursor(true); });
    holder.addEventListener("blur", function () { if (!kbd.holding) placeCursor(false); });
    $("next-button").addEventListener("click", function () { send({ action: "next" }); });
    $("undo-button").addEventListener("click", function () { send({ action: "undo" }); });
    $("clear-button").addEventListener("click", function () { send({ action: "clear" }); });
    $("reset-button").addEventListener("click", function () {
      askThen("hull-repair-reset", "Start the whole station over? Your repairs, lines and tally will be erased.", "Erase it", function () { send({ action: "reset" }); });
    });
    document.addEventListener("keydown", onGlobalKey);
    // The save widget loads a save straight into the engine; this redraws afterwards.
    window.hullRepairRefresh = function () { if (engine) { boardId = null; send({ action: "open" }); } };
  }

  var TUTORIAL_STEPS = [
    { title: "Welcome to the station", text: "Tern is dark and needs its power and pipes laid again, one room at a time. Join each pair of matching ports with a line. Nothing is timed, and a wrong line only costs you a tap to take it back. Skip any time and reopen this from the Tutorial button." },
    { selector: "#board-holder", title: "The board", text: "Solid shapes are sources and ringed shapes are sinks; a source and sink with the same shape and letter belong together. Drag from a port to lay a line, and drop it on its partner. Lines move one cell at a time and never cross or share a cell. Holes are hull that is gone." },
    { selector: "#line-chips", title: "Your lines", text: "Each line shows whether it is joined. Tap one to clear just that line. Dragging back along a line shortens it, dragging across another line cuts it, and tapping the end of a line takes one cell back." },
    { selector: "#board-line", title: "Patched and restored", text: "Joining every line patches the room and lights it dimly. Covering every cell as well restores it fully. The dots mark cells nothing covers yet; every board has exactly one way to cover them all." },
    { selector: "#hint-button", title: "Hints are free", text: "A nudge says where to start, a hint draws the opening of one line as a dotted ghost, and the answer draws the whole layout. Using them never costs anything, and the room still counts." },
    { selector: "#goals", title: "Your goals", text: "Three goals stay in view, in any order. Every line you lay, erase or hint you ask for counts toward something on the screen." },
    { selector: "#rooms-toggle-button", title: "The station", text: "Station opens the map: every patched room lights up there, and the Repair log keeps a line from the people who left. A deck opens once five of the one before are patched. New parts arrive deck by deck: bridges, valves, mixers." },
    { title: "You are ready", text: "Take your time. Your repairs are saved as you go." }
  ];

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
    if (window.GameTutorial) window.GameTutorial.init(window.hullRepairTutorialSteps ? window.hullRepairTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS, { gameId: "hull-repair" });
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The station could not start (" + err + "). Reload to try again.";
  });
})();
