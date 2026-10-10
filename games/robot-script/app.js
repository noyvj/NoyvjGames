/* Robot Script view: glue only. The engine (game.py and its modules) holds every rule; this file draws what handle()
   returns, plays a run back, and forwards what the player does. No game logic lives here. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["dsl.py", "room.py", "run.py", "editor.py", "render.py", "progress.py", "info.py", "hints.py", "rooms_moving.py", "rooms_turning.py", "rooms_loops.py", "rooms_routines.py", "rooms_branches.py", "rooms_capstone.py", "rooms.py", "companion.py", "achievements.py", "sandbox.py"];
  var STORE_KEY = "robot-script:state";
  var BACKUP_KEY = "robot-script:state-backup";
  var TILE = 48;
  var SPEED_MS = { slow: 600, normal: 280, fast: 90, instant: 0 };
  var GLYPHS = { F: "↑", L: "↶", R: "↷", G: "⤓", P: "⤒", S: "⚡", rep: "↻", until: "↻?", "if": "?", callA: "A", callB: "B" };

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;
  var view = null;
  var roomId = null;
  var headDeg = 0;
  var play = { frames: null, i: 0, timer: null, trace: null, running: false };
  var refocus = false;
  var sandboxTile = "#";

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
    bumpStat("stat-rooms", view.totals.cleared + "/" + view.totals.rooms);
    bumpStat("stat-gold", view.totals.gold);
    bumpStat("stat-parts", view.scrap.found + "/" + view.scrap.total);
    bumpStat("stat-runs", view.tally.runs);
    bumpStat("stat-written", view.tally.written);
    bumpStat("stat-hints", view.tally.hints);
    bumpStat("stat-sbx-runs", view.tally.sbx_runs);
    bumpStat("stat-sbx-tiles", view.tally.sbx_tiles);
    bumpStat("stat-silver", view.totals.silver);
    bumpStat("stat-bronze", view.totals.bronze);
    bumpStat("stat-halts", view.tally.halts);
  }

  // ---- the room --------------------------------------------------------------------------------------
  function medalNode(name) {
    return el("span", "medal medal-" + name, name.charAt(0).toUpperCase() + name.slice(1));
  }
  function renderGoals(listId, goals) {
    var ul = $(listId);
    ul.textContent = "";
    goals.forEach(function (g) {
      var li = el("li", g.met ? "met" : "", g.label + (g.met ? " (done)" : ""));
      ul.appendChild(li);
    });
  }
  function renderRoomHead() {
    var r = view.room;
    setText($("room-chapter"), r.chapter + " · room " + r.number + " of " + r.of);
    setText($("room-heading"), r.name);
    setText($("room-intro"), r.intro);
    var words = $("words-lines");
    var sig = r.id;
    if (words.dataset.sig !== sig) {
      words.dataset.sig = sig;
      words.textContent = "";
      r.words.lines.forEach(function (l) { words.appendChild(el("li", null, l)); });
      $("words-rows").textContent = "";
      r.words.rows.forEach(function (l) { $("words-rows").appendChild(el("li", null, l)); });
    }
  }
  function svgEl() { return $("room-holder").querySelector("svg"); }
  function applyFrame(f, jump) {
    var svg = svgEl();
    if (!svg) return;
    var robot = svg.querySelector("#rs-robot");
    var mod = ((headDeg % 360) + 360) % 360;
    var delta = (((f[2] * 90 - mod) + 540) % 360) - 180;
    headDeg += delta;
    if (jump) robot.classList.add("jump");
    robot.style.transform = "translate(" + (f[0] * TILE + TILE / 2) + "px," + (f[1] * TILE + TILE / 2) + "px) rotate(" + headDeg + "deg)";
    if (jump) { void robot.getBoundingClientRect(); robot.classList.remove("jump"); }
    svg.querySelector("#rs-carry").classList.toggle("on", f[3] >= 0);
    Array.prototype.forEach.call(svg.querySelectorAll(".rs-part"), function (p) {
      var i = Number(p.id.replace("rs-part-", ""));
      p.classList.toggle("gone", !((f[4] >> i) & 1));
    });
    Array.prototype.forEach.call(svg.querySelectorAll(".rs-fill"), function (p) {
      var i = Number(p.id.replace("rs-fill-", ""));
      p.classList.toggle("on", Boolean((f[5] >> i) & 1));
    });
    Array.prototype.forEach.call(svg.querySelectorAll(".rs-switch"), function (p) {
      var i = Number(p.id.replace("rs-lamp-", ""));
      p.classList.toggle("lit", Boolean((f[6] >> i) & 1));
    });
    Array.prototype.forEach.call(svg.querySelectorAll(".rs-door"), function (p) {
      p.classList.toggle("open", Boolean((f[6] >> Number(p.dataset.sw)) & 1));
    });
  }
  function initialFrame() {
    var s = view.room.start;
    var n = svgEl().querySelectorAll(".rs-part").length;
    return [s[0], s[1], s[2], -1, (1 << n) - 1, 0, 0, ""];
  }
  function markNode(addr, stopped) {
    Array.prototype.forEach.call(document.querySelectorAll(".node.running, .node.stopped"), function (n) { n.classList.remove("running", "stopped"); });
    if (!addr) return;
    var node = document.querySelector('[data-a="' + addr + '"]');
    if (!node) return;
    node.classList.add(stopped ? "stopped" : "running");
    if (node.scrollIntoView) node.scrollIntoView({ block: "nearest" });
  }

  // ---- playback --------------------------------------------------------------------------------------
  function speedMs() {
    var reduced = document.documentElement.getAttribute("data-reduced-motion") === "true";
    var name = document.documentElement.getAttribute("data-run-speed") || "normal";
    if (reduced) return 0;
    return SPEED_MS[name] === undefined ? SPEED_MS.normal : SPEED_MS[name];
  }
  function stopTimer() {
    if (play.timer) { clearInterval(play.timer); play.timer = null; }
    play.running = false;
  }
  function hideResult() {
    $("result-card").hidden = true;
    setText($("run-line"), "");
  }
  function invalidateRun() {
    stopTimer();
    play.trace = null;
    play.frames = null;
    play.i = 0;
    markNode("", false);
    hideResult();
    if (view && svgEl()) {
      applyFrame(initialFrame(), true);
      renderGoals("room-goals", view.room.goals);
    }
    syncPlayButtons();
  }
  function syncPlayButtons() {
    var run = $("run-button");
    var live = play.trace && play.i < play.frames.length - 1;
    setText(run, play.running ? "Pause" : (live ? "Resume" : (play.trace ? "Run again" : "Run")));
    $("step-button").disabled = false;
    $("skip-button").disabled = !live;
    $("rewind-button").disabled = !play.trace || play.i === 0;
  }
  function showFrameAt(i, jump) {
    play.i = i;
    var f = play.frames[i];
    applyFrame(f, jump);
    var last = i === play.frames.length - 1;
    markNode(i === 0 ? "" : f[7], last && play.trace.status !== "cleared" && play.trace.status !== "short" && Boolean(play.trace.at));
    var done = Math.min(i, play.trace.actions);
    setText($("run-line"), done ? "Step " + done + " of " + play.trace.actions : "");
  }
  function advance() {
    if (!play.frames) return;
    if (play.i >= play.frames.length - 1) { finishRun(); return; }
    showFrameAt(play.i + 1, false);
    if (play.i >= play.frames.length - 1) finishRun();
  }
  function finishRun() {
    stopTimer();
    var t = play.trace;
    if (!t) return;
    var halted = t.status === "halt" || t.status === "loop";
    if (halted && t.at) markNode(t.at, true);
    if (t.sandbox) {
      var sc = $("result-card");
      sc.hidden = false;
      sc.className = "result-card " + (halted ? "stopped" : "cleared");
      setText($("result-title"), halted ? "The robot stopped" : "The run is over");
      $("result-medal").textContent = "";
      setText($("result-text"), t.message);
      $("result-goals").textContent = "";
      $("next-button").hidden = true;
      $("scrap-line").hidden = true;
      $("part-line").hidden = true;
      announce(t.message);
      syncPlayButtons();
      return;
    }
    renderGoals("room-goals", t.goals);
    var card = $("result-card");
    card.hidden = false;
    card.className = "result-card " + (t.cleared ? "cleared" : "stopped");
    var medal = $("result-medal");
    medal.textContent = "";
    if (t.cleared) {
      setText($("result-title"), "Room cleared");
      medal.appendChild(medalNode(t.medal_name));
      medal.appendChild(document.createTextNode(" " + plural(t.size, "step", "steps") + " (par " + t.par + ")"));
      var more = t.medal === 3 ? "That is gold." : t.medal === 2 ? "Gold needs " + t.par + " or fewer steps." : "Silver needs " + t.silver + " or fewer steps, gold needs " + t.par + ".";
      setText($("result-text"), (t.new_best ? "A new best for this room. " : "Your best here is " + t.best + ". ") + more);
    } else if (halted) {
      setText($("result-title"), "The robot stopped");
      setText($("result-text"), t.message + " Nothing is lost: change the list and run it again.");
    } else {
      setText($("result-title"), "Not finished yet");
      setText($("result-text"), t.message);
    }
    renderGoals("result-goals", t.goals);
    var sl = $("scrap-line");
    sl.hidden = !(t.cleared && t.scrap_line);
    setText(sl, t.scrap_line ? "Scrap: " + t.scrap_line : "");
    var pl = $("part-line");
    pl.hidden = !(t.part);
    setText(pl, t.part ? (t.part.first ? "Part found for Scrap: " : "Scrap's part: ") + t.part.name + " (" + t.part.finish + ")." : "");
    var next = $("next-button");
    next.hidden = !(t.cleared && t.next);
    if (t.next) setText(next, "Next room: " + t.next_name);
    announce(t.cleared ? "Room cleared, " + t.medal_name + " medal." : t.message);
    syncPlayButtons();
  }
  function startPlay(trace, autoplay) {
    stopTimer();
    play.trace = trace;
    play.frames = trace.frames;
    play.i = 0;
    hideResult();
    applyFrame(play.frames[0], true);
    syncPlayButtons();
    var ms = speedMs();
    if (!autoplay) return;
    if (ms === 0) { showFrameAt(play.frames.length - 1, true); finishRun(); return; }
    play.running = true;
    play.timer = setInterval(advance, ms);
    syncPlayButtons();
  }
  function onRun() {
    if (play.running) { stopTimer(); syncPlayButtons(); return; }
    if (play.trace && play.i < play.frames.length - 1) {
      var ms = speedMs();
      if (ms === 0) { showFrameAt(play.frames.length - 1, true); finishRun(); return; }
      play.running = true;
      play.timer = setInterval(advance, ms);
      syncPlayButtons();
      return;
    }
    var result = send({ action: "run" });
    if (result && result.run) startPlay(result.run, true);
  }
  function onStep() {
    if (play.running) { stopTimer(); }
    if (!play.trace || play.i >= play.frames.length - 1) {
      var result = send({ action: "run" });
      if (!result || !result.run) return;
      startPlay(result.run, false);
    }
    advance();
    syncPlayButtons();
  }
  function onSkip() {
    if (!play.trace) return;
    stopTimer();
    showFrameAt(play.frames.length - 1, true);
    finishRun();
  }
  function onRewind() {
    if (!play.trace) return;
    stopTimer();
    hideResult();
    renderGoals("room-goals", view.room.goals);
    showFrameAt(0, true);
    syncPlayButtons();
  }

  // ---- the list editor ----------------------------------------------------------------------------------
  var PALETTE_SIG = "";
  function condSelect(addr, value) {
    var sel = el("select");
    sel.setAttribute("aria-label", "Condition");
    view.program.conds.forEach(function (c) {
      var o = el("option", null, c.label);
      o.value = c.value;
      sel.appendChild(o);
    });
    sel.value = value;
    sel.addEventListener("change", function () { send({ action: "cond", at: addr, cond: sel.value }, true); });
    return sel;
  }
  function smallButton(text, label, cls, handler) {
    var b = el("button", cls, text);
    b.type = "button";
    b.setAttribute("aria-label", label);
    b.addEventListener("click", handler);
    return b;
  }
  function tools(node, idx, len, name) {
    var frag = document.createDocumentFragment();
    frag.appendChild(el("span", "spacer"));
    frag.appendChild(smallButton("↑", "Move " + name + " up", "node-mv", function () { send({ action: "move", at: node.a, delta: -1 }, true); }));
    frag.appendChild(smallButton("↓", "Move " + name + " down", "node-mv", function () { send({ action: "move", at: node.a, delta: 1 }, true); }));
    frag.appendChild(smallButton("×", "Remove " + name, "node-x", function () { send({ action: "remove", at: node.a }, true); }));
    Array.prototype.forEach.call(frag.querySelectorAll(".node-mv"), function (b, k) {
      if ((k === 0 && idx === 0) || (k === 1 && idx === len - 1)) { b.disabled = true; }
    });
    return frag;
  }
  function buildList(body) {
    var ol = el("ol", "plist");
    ol.dataset.list = body.list;
    var cur = view.program.cursor;
    function gap(i) {
      var li = el("li");
      var b = el("button", "gap" + (cur.list === body.list && cur.index === i ? " current" : ""));
      b.type = "button";
      b.setAttribute("data-touch-exempt", "");
      b.setAttribute("aria-label", (cur.list === body.list && cur.index === i ? "Next step goes here, position " : "Put the next step here, position ") + (i + 1));
      b.dataset.gap = body.list + ":" + i;
      b.addEventListener("click", function () { send({ action: "cursor", list: body.list, index: i }, true); });
      li.appendChild(b);
      return li;
    }
    ol.appendChild(gap(0));
    body.items.forEach(function (node, i) {
      var li = el("li");
      li.appendChild(buildNode(node, i, body.items.length));
      ol.appendChild(li);
      ol.appendChild(gap(i + 1));
    });
    return ol;
  }
  function buildNode(node, idx, len) {
    var name = "step " + (idx + 1);
    if (node.k.length === 1 || node.k === "call") {
      var div = el("div", "node");
      div.dataset.a = node.a;
      var label = node.k === "call" ? "Call " + node.name : node.label;
      div.appendChild(el("span", "node-glyph", node.k === "call" ? node.name : GLYPHS[node.k]));
      div.appendChild(el("span", "node-label", label));
      div.appendChild(tools(node, idx, len, label));
      return div;
    }
    var block = el("div", "block");
    block.dataset.a = node.a;
    var head = el("div", "block-head node");
    head.dataset.a = node.a;
    if (node.k === "rep") {
      head.appendChild(el("span", null, "Repeat"));
      var count = el("span", "count");
      var minus = smallButton("−", "Fewer repeats", "", function () { send({ action: "count", at: node.a, n: node.n - 1 }, true); });
      var plus = smallButton("+", "More repeats", "", function () { send({ action: "count", at: node.a, n: node.n + 1 }, true); });
      var out = el("output", null, String(node.n));
      out.setAttribute("aria-label", node.n + " times");
      count.appendChild(minus); count.appendChild(out); count.appendChild(plus);
      head.appendChild(count);
      head.appendChild(el("span", null, "times"));
      block.appendChild(head);
      head.appendChild(tools(node, idx, len, "the repeat"));
      block.appendChild(buildList(node.body));
    } else if (node.k === "until") {
      head.appendChild(el("span", null, "Repeat until"));
      head.appendChild(condSelect(node.a, node.c));
      head.appendChild(tools(node, idx, len, "the until block"));
      block.appendChild(head);
      block.appendChild(buildList(node.body));
    } else {
      head.appendChild(el("span", null, "If"));
      head.appendChild(condSelect(node.a, node.c));
      head.appendChild(tools(node, idx, len, "the if block"));
      block.appendChild(head);
      block.appendChild(el("p", "block-sub", "then"));
      block.appendChild(buildList(node["then"]));
      block.appendChild(el("p", "block-sub", "otherwise"));
      block.appendChild(buildList(node["else"]));
    }
    void name;
    return block;
  }
  function renderPalette() {
    var p = view.program;
    var sig = p.palette.map(function (x) { return x.k + (x.ok ? 1 : 0); }).join(",");
    if (PALETTE_SIG === sig + roomId) return;
    PALETTE_SIG = sig + roomId;
    var holder = $("palette");
    holder.textContent = "";
    p.palette.forEach(function (item) {
      var b = el("button", null);
      b.type = "button";
      b.dataset.testid = "robot-script-add-" + item.k;
      b.appendChild(el("span", "glyph", GLYPHS[item.k] || "?"));
      b.appendChild(document.createTextNode(item.label));
      b.title = item.detail;
      b.setAttribute("aria-label", item.label + ". " + item.detail + (item.ok ? "" : ". Not possible here: " + item.why));
      if (!item.ok) b.setAttribute("aria-disabled", "true");
      b.addEventListener("click", function () { send({ action: "insert", kind: item.k }, true); });
      holder.appendChild(b);
    });
  }
  function renderProgram() {
    var p = view.program;
    var r = view.room;
    var line = r.sandbox ? plural(p.size, "step", "steps") + " in your list (up to " + p.max + ")." : plural(p.size, "step", "steps") + " in your list. Gold at " + r.par + " or fewer, silver at " + r.silver + "." + (r.best !== null ? " Your best: " + r.best + "." : "");
    setText($("size-line"), line);
    var tabs = $("routine-tabs");
    tabs.textContent = "";
    tabs.hidden = p.routines.length < 2;
    p.routines.forEach(function (rt) {
      var b = el("button", null, rt.label + " (" + rt.size + ")");
      b.type = "button";
      b.setAttribute("aria-pressed", String(rt.name === p.active));
      b.addEventListener("click", function () { send({ action: "routine", name: rt.name }, true); });
      tabs.appendChild(b);
    });
    var holder = $("program");
    var active = p.routines.filter(function (x) { return x.name === p.active; })[0] || p.routines[0];
    var scroll = holder.scrollTop;
    holder.textContent = "";
    holder.setAttribute("role", "group");
    holder.setAttribute("aria-label", active.label + ", " + plural(active.size, "step", "steps"));
    holder.appendChild(buildList(active));
    holder.scrollTop = scroll;
    renderPalette();
    $("undo-button").disabled = !p.can_undo;
    $("clear-button").disabled = p.size === 0;
    $("best-button").hidden = !r.has_best;
    if (refocus) {
      refocus = false;
      var g = holder.querySelector(".gap.current");
      if (g && document.activeElement && document.activeElement.closest && document.activeElement.closest("#program")) g.focus();
    }
  }

  // ---- the room picker -------------------------------------------------------------------------------
  function renderSandboxEntry() {
    var s = view.sandbox;
    var holder = $("sandbox-entry");
    var sig = String(s.open) + String(s.current);
    if (holder.dataset.sig === sig) return;
    holder.dataset.sig = sig;
    holder.textContent = "";
    holder.appendChild(el("h3", null, "Sandbox"));
    holder.appendChild(el("p", "note", s.open ? "Paint any room, write any list, run it as often as you like. Nothing is scored." : "Opens when every room of " + s.need + " is cleared."));
    var b = el("button", s.current ? "room-btn current" : "room-btn", s.open ? (s.current ? "In the sandbox" : "Open the sandbox") : "Locked");
    b.type = "button";
    b.dataset.testid = "robot-script-sandbox-open";
    if (!s.open) b.setAttribute("aria-disabled", "true");
    b.addEventListener("click", function () {
      if (!s.open) { showToast("The sandbox opens once every room of " + s.need + " is cleared."); return; }
      send({ action: "sandbox" });
      $("rooms-panel").hidden = true;
      $("rooms-toggle-button").setAttribute("aria-expanded", "false");
    });
    holder.appendChild(b);
  }
  function renderSandboxTools() {
    var s = view.sandbox;
    var tools = $("sandbox-tools");
    if (tools.dataset.built) return;
    tools.dataset.built = "1";
    s.tiles.forEach(function (t, i) {
      var b = el("button", "tile-tool", t.label);
      b.type = "button";
      b.dataset.tile = t.tile;
      b.dataset.testid = "robot-script-tile-" + i;
      b.setAttribute("aria-pressed", String(i === 1));
      b.addEventListener("click", function () { sandboxTile = t.tile; syncTileTools(); });
      tools.appendChild(b);
    });
    s.presets.forEach(function (p) {
      var o = el("option", null, p.label);
      o.value = p.id;
      $("sbx-preset").appendChild(o);
    });
    $("sbx-col").max = s.size; $("sbx-row").max = s.size;
    syncTileTools();
  }
  function syncTileTools() {
    Array.prototype.forEach.call($("sandbox-tools").querySelectorAll("button"), function (b) { b.setAttribute("aria-pressed", String(b.dataset.tile === sandboxTile)); });
  }
  function onRoomClick(e) {
    if (!view || !view.room.sandbox) return;
    var svg = svgEl();
    if (!svg || !svg.getScreenCTM) return;
    var pt = svg.createSVGPoint();
    pt.x = e.clientX; pt.y = e.clientY;
    var p = pt.matrixTransform(svg.getScreenCTM().inverse());
    var x = Math.floor(p.x / TILE), y = Math.floor(p.y / TILE);
    if (x < 0 || y < 0 || x >= view.room.w || y >= view.room.h) return;
    send({ action: "sbx_paint", x: x, y: y, tile: sandboxTile }, true);
  }
  function renderRooms() {
    renderSandboxEntry();
    renderSandboxTools();
    var holder = $("rooms-body");
    var sig = JSON.stringify(view.rooms.map(function (c) { return c.rooms.map(function (r) { return r.medal + (r.current ? "c" : ""); }); }));
    if (holder.dataset.sig === sig) return;
    holder.dataset.sig = sig;
    holder.textContent = "";
    view.rooms.forEach(function (c) {
      var sec = el("section", "chapter");
      sec.appendChild(el("h3", null, c.name + " (" + c.cleared + "/" + c.total + ")"));
      sec.appendChild(el("p", "note", c.blurb));
      var ul = el("ul", "room-grid");
      c.rooms.forEach(function (r) {
        var li = el("li");
        var b = el("button", "room-btn" + (r.current ? " current" : ""));
        b.type = "button";
        b.dataset.testid = "robot-script-room-" + r.id;
        b.appendChild(el("span", "rname", r.number + ". " + r.name));
        var meta = el("span", "rmeta");
        if (r.medal) {
          meta.appendChild(medalNode(["", "bronze", "silver", "gold"][r.medal]));
          meta.appendChild(document.createTextNode(" " + r.best + " steps, par " + r.par));
        } else {
          meta.textContent = "Not cleared, par " + r.par;
        }
        b.appendChild(meta);
        b.setAttribute("aria-label", r.number + ", " + r.name + ". " + (r.medal ? ["", "Bronze", "Silver", "Gold"][r.medal] + " medal, " + r.best + " steps, par " + r.par : ("Not cleared, par " + r.par)) + (r.current ? ". Current room" : ""));
        b.addEventListener("click", function () {
          send({ action: "pick", room: r.id });
          $("rooms-panel").hidden = true;
          $("rooms-toggle-button").setAttribute("aria-expanded", "false");
          var anchor = $("room-panel");
          if (anchor.scrollIntoView) anchor.scrollIntoView({ block: "start" });
        });
        li.appendChild(b);
        ul.appendChild(li);
      });
      sec.appendChild(ul);
      holder.appendChild(sec);
    });
  }

  // ---- goals, the workshop and the hint ladder ----------------------------------------------------------
  function renderGoalStrip() {
    var list = $("goals-list");
    var sig = view.goals.map(function (g) { return g.id + g.have; }).join(",");
    $("goals").hidden = false;
    if (list.dataset.sig === sig) return;
    list.dataset.sig = sig;
    list.textContent = "";
    if (!view.goals.length) { list.appendChild(el("li", null, "Every goal you can reach right now is done. The sandbox goal appears once the sandbox is open.")); return; }
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
  function renderWorkshop() {
    var s = view.scrap;
    var sig = s.svg + s.found;
    setText($("workshop-summary"), "Scrap has " + s.found + " of " + s.total + " parts back on, " + s.polished + " of them polished.");
    if ($("scrap-holder").dataset.sig !== sig) {
      $("scrap-holder").dataset.sig = sig;
      $("scrap-holder").innerHTML = s.svg;
      var zl = $("zone-list");
      zl.textContent = "";
      s.zones.forEach(function (z) {
        zl.appendChild(el("li", null, z.name + ": " + z.have + "/" + z.need + (z.finish ? " (" + z.finish + ")" : "")));
      });
      var pl = $("parts-list");
      pl.textContent = "";
      s.parts.forEach(function (p) {
        pl.appendChild(el("li", p.found ? "found" : "missing", p.found ? p.name + " (" + p.finish + "), from " + p.room_name : "Not found yet: from " + p.room_name));
      });
    }
  }
  function renderHints() {
    var h = view.hint;
    var btn = $("hint-button");
    btn.hidden = h.rung >= 3;
    setText(btn, h.rung === 0 ? "Would you like a suggestion?" : (h.rung === 1 ? "Another hint" : "Another hint: the answer"));
    $("hint-nudge").hidden = !h.nudge;
    setText($("hint-nudge"), h.nudge ? "Nudge: " + h.nudge : "");
    $("hint-hint").hidden = !h.hint;
    setText($("hint-hint"), h.hint ? "Hint: " + h.hint : "");
    $("hint-answer").hidden = !h.answer;
    if (h.answer) setText($("hint-answer-lines"), h.answer.lines.join("\n"));
  }

  // ---- render everything ----------------------------------------------------------------------------------
  function render() {
    renderAbout();
    var changed = view.room.id !== roomId;
    if (view.room.svg) {
      $("room-holder").innerHTML = view.room.svg;
      roomId = view.room.id;
      PALETTE_SIG = "";
      headDeg = view.room.start[2] * 90;
      invalidateRun();
    } else if (changed) {
      roomId = view.room.id;
    }
    renderStats();
    renderRoomHead();
    if (!play.trace) renderGoals("room-goals", view.room.goals);
    renderProgram();
    renderRooms();
    renderGoalStrip();
    renderAchievements();
    renderWorkshop();
    renderHints();
    syncPlayButtons();
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
  function send(request, isEdit) {
    if (!engine) return null;
    var result = JSON.parse(engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    if (isEdit && result.ok) invalidateRun();
    view = result;
    showToast("");
    if (request.action === "pick" || request.action === "next" || request.action === "reset") invalidateRun();
    render();
    var edit = $("edit-line");
    var isFail = result.ok === false && request.action !== "run";
    setText(edit, isFail ? result.message : "");
    if (isFail) announce(result.message);
    else if (isEdit && request.action === "insert") announce("Added. " + plural(view.program.size, "step", "steps") + " in the list.");
    persist();
    return result;
  }

  // ---- keyboard ------------------------------------------------------------------------------------------
  function onKey(e) {
    if (!view || e.ctrlKey || e.metaKey || e.altKey) return;
    var tag = e.target && e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (document.querySelector("dialog[open], .confirm-dialog, [role='dialog']")) return;
    var key = e.key;
    var map = { f: "F", l: "L", r: "R", g: "G", p: "P", s: "S" };
    if (map[key.toLowerCase()] && key.length === 1) {
      var item = view.program.palette.filter(function (x) { return x.k === map[key.toLowerCase()]; })[0];
      if (!item) return;
      e.preventDefault();
      refocus = true;
      send({ action: "insert", kind: item.k }, true);
      return;
    }
    if (key === "Backspace" || key === "Delete") {
      var cur = view.program.cursor;
      if (cur.index > 0) {
        e.preventDefault();
        refocus = true;
        send({ action: "remove", at: cur.list + "/" + (cur.index - 1) }, true);
      }
      return;
    }
    if (key === "z" || key === "Z") { e.preventDefault(); refocus = true; send({ action: "undo" }, true); return; }
    if (key === "Enter" && !(tag === "BUTTON" || tag === "A" || tag === "SUMMARY")) { e.preventDefault(); onRun(); }
  }

  function askThen(id, message, confirmLabel, go) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: false, onConfirm: go });
    else go();
  }

  function wire() {
    $("toast").addEventListener("click", function () { showToast(""); });
    wirePanelToggle("rooms-toggle-button", "rooms-panel");
    wirePanelToggle("workshop-toggle-button", "workshop-panel");
    wirePanelToggle("achievements-toggle-button", "achievements-panel");
    $("hint-button").addEventListener("click", function () { send({ action: "hint" }); });
    $("answer-load-button").addEventListener("click", function () { send({ action: "load_answer" }, true); });
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    $("room-holder").addEventListener("click", onRoomClick);
    $("sbx-paint-button").addEventListener("click", function () {
      send({ action: "sbx_paint", x: Number($("sbx-col").value) - 1, y: Number($("sbx-row").value) - 1, tile: sandboxTile }, true);
    });
    $("sbx-preset-button").addEventListener("click", function () {
      askThen("robot-script-preset", "Replace the sandbox room with this preset? The room you painted will be erased.", "Replace it", function () {
        send({ action: "sbx_preset", name: $("sbx-preset").value }, true);
      });
    });
    $("run-button").addEventListener("click", onRun);
    $("step-button").addEventListener("click", onStep);
    $("skip-button").addEventListener("click", onSkip);
    $("rewind-button").addEventListener("click", onRewind);
    $("next-button").addEventListener("click", function () { send({ action: "next" }); });
    $("undo-button").addEventListener("click", function () { send({ action: "undo" }, true); });
    $("clear-button").addEventListener("click", function () { send({ action: "clear" }, true); });
    $("best-button").addEventListener("click", function () { send({ action: "load_best" }, true); });
    $("reset-button").addEventListener("click", function () {
      askThen("robot-script-reset", "Start the whole deck over? Your medals, lists and tally will be erased.", "Erase it", function () { send({ action: "reset" }); });
    });
    document.addEventListener("keydown", onKey);
    // The save widget loads a save straight into the engine; this redraws afterwards.
    window.robotScriptRefresh = function () { if (engine) { roomId = null; send({ action: "open" }); } };
  }

  var TUTORIAL_STEPS = [
    { title: "Welcome to the deck", text: "A maintenance robot does exactly what your list says. Write the list, press Run, and watch. Nothing is timed, and a run that goes wrong costs nothing. Skip any time and reopen this from the Tutorial button." },
    { selector: "#room-panel", title: "The room", text: "The robot starts on its tile facing the way its nose points. The checklist above the room says what the room needs: here, reach the glowing exit pad. Parts are diamonds, sockets are dashed frames, switches are numbered plates and doors are barred and lettered." },
    { selector: "#palette", title: "Instructions", text: "Tap an instruction to add it to your list. The robot only has what this room allows; later chapters add more. Forward moves one tile, and every instruction you add is one step." },
    { selector: "#program", title: "Your list", text: "The marked gap shows where the next step goes. Tap another gap to add somewhere else, the arrows move a step, and the x removes it. Undo takes back your last change." },
    { selector: "#run-button", title: "Run, Step and Skip", text: "Run plays your list. Step does one action at a time and Skip jumps to the end. If the robot cannot do a step (a wall, a shut door, nothing to pick up), it stops there and says why. Your list stays, so just fix it and run again." },
    { selector: "#size-line", title: "Steps and medals", text: "Fewer steps earn better medals: gold at the reference length, silver a little over, bronze for any clear. Hints are free and never touch a medal." },
    { selector: "#goals", title: "Your goals", text: "Three goals stay in view, and you can do them in any order. Every run, every step you write and every hint you ask for counts toward something on the screen." },
    { selector: "#rooms-toggle-button", title: "Rooms and Scrap", text: "Rooms lists every chapter, and every room is open from the start. Each room you clear gives Scrap, the salvage drone in the Workshop, a part, and a better list gives the same part a better finish. Once you have cleared every room of Loops, the third chapter, a free sandbox opens." },
    { title: "You are ready", text: "Take your time. Your lists and medals are saved as you go." }
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
    if (window.GameTutorial) window.GameTutorial.init(window.robotScriptTutorialSteps ? window.robotScriptTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS, { gameId: "robot-script" });
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The deck could not start (" + err + "). Reload to try again.";
  });
})();
