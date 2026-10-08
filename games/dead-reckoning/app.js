/* Dead Reckoning view: glue only. The engine (game.py and its modules) holds every rule; this file draws what
   handle() returns and forwards what the player does. The only arithmetic here is cosmetic: turning a tap on the chart
   into chart coordinates, and pacing the playback of a track the engine already computed. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["geom.py", "sim.py", "chartkit.py", "charts_open.py", "charts_wind.py", "charts_fixes.py", "pars.py", "charts.py", "render.py", "solver.py", "state.py", "progress.py", "fixes.py"];
  var STORE_KEY = "dead-reckoning:state";

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;   // { handle, getState, loadState }
  var view = null;
  var selected = 0;    // the leg the quick-turn buttons act on

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }

  // ---- accessibility helpers -----------------------------------------------------------------------
  // Live regions only announce when their text really changes, so assign through setText.
  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }
  function announce(text) {
    var live = $("announce");
    live.textContent = "";
    setTimeout(function () { live.textContent = text; }, 40);
  }
  function el(tag, text, className) {
    var node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function reducedMotion() { return document.documentElement.getAttribute("data-reduced-motion") === "true"; }
  function fmt(n) { return String(Math.round(n * 100) / 100); }
  function stars(n) { return "★".repeat(n) + "☆".repeat(3 - n); }

  // ---- the chart ---------------------------------------------------------------------------------
  // ---- chart picker and captain's log ----------------------------------------------------------------
  function renderPicker() {
    var body = $("picker-body");
    var sig = JSON.stringify(view.picker);
    if (body.dataset.signature === sig) return;
    body.dataset.signature = sig;
    body.textContent = "";
    view.picker.forEach(function (chapter, n) {
      var wrap = el("section", undefined, "picker-chapter");
      wrap.appendChild(el("h3", "Chapter " + (n + 1) + ": " + chapter.name + " (" + chapter.cleared + " of " + chapter.total + " cleared)"));
      wrap.appendChild(el("p", chapter.blurb, "note"));
      if (!chapter.unlocked) {
        wrap.appendChild(el("p", chapter.lock_text, "note"));
        body.appendChild(wrap);
        return;
      }
      var list = el("ul", undefined, "picker-list");
      chapter.charts.forEach(function (c, i) {
        var li = el("li");
        var b = el("button");
        b.type = "button";
        b.appendChild(document.createTextNode((i + 1) + ". " + c.name));
        b.appendChild(el("span", stars(c.stars), "mini-stars"));
        b.setAttribute("aria-label", c.name + ", " + c.stars + " of 3 stars" + (c.current ? ", open now" : ""));
        if (c.current) b.setAttribute("aria-current", "true");
        b.addEventListener("click", function () { openChart(c.id); });
        li.appendChild(b);
        list.appendChild(li);
      });
      wrap.appendChild(list);
      body.appendChild(wrap);
    });
  }

  function openChart(id) {
    function go() {
      selected = 0;
      send({ action: "start", chart_id: id });
      $("picker-panel").hidden = true;
      setToggle("picker-toggle-button", "picker-panel");
    }
    if (view.phase === "plan" && view.legs.length && view.chart.id !== id && window.ConfirmDialog) {
      window.ConfirmDialog.ask({ id: "dead-reckoning-switch-chart", message: "Leave this chart? The plan you have here will be lost.", confirmLabel: "Open the other chart", onConfirm: go });
    } else go();
  }

  function renderLog() {
    var holder = $("log-entries");
    holder.textContent = "";
    view.story.log.forEach(function (entry) {
      var wrap = el("article", undefined, "log-entry");
      wrap.appendChild(el("h3", entry.name));
      wrap.appendChild(el("p", entry.text, "log-line"));
      holder.appendChild(wrap);
    });
  }

  function setToggle(buttonId, panelId) { $(buttonId).setAttribute("aria-expanded", String(!$(panelId).hidden)); }
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () {
      $(panelId).hidden = !$(panelId).hidden;
      setToggle(buttonId, panelId);
    });
  }

  function renderChart() {
    var holder = $("chart-holder");
    if (holder.dataset.signature !== view.svg) {
      holder.innerHTML = view.svg;           // the engine's own markup: no player text goes in
      holder.dataset.signature = view.svg;
    }
    var list = $("chart-notes-list");
    list.textContent = "";
    view.notes.forEach(function (line) { list.appendChild(el("li", line)); });
    setText($("chart-title"), view.chart.name);
    setText($("chart-goal"), view.chart.goal);
    setText($("chart-intro"), view.story.intro);
  }

  // A tap on the chart marks the ruler's point. Converting the tap to nautical miles is the one bit of geometry the view does.
  function onChartTap(event) {
    if (!view || view.phase !== "plan") return;
    var svg = $("dr-chart");
    if (!svg || !svg.contains(event.target)) return;
    var ctm = svg.getScreenCTM();
    if (!ctm) return;
    var pt = svg.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;
    var local = pt.matrixTransform(ctm.inverse());
    var f = view.frame;
    var x = (local.x - f.left) / f.s;
    var y = f.size - (local.y - f.top) / f.s;
    if (x < -0.5 || y < -0.5 || x > f.size + 0.5 || y > f.size + 0.5) return;
    $("ruler").open = true;
    send({ action: "point", x: x, y: y });
  }

  // ---- the plan ----------------------------------------------------------------------------------
  function stepperField(i, field, label, value, min, max, step, unit) {
    var wrap = el("div", undefined, "field");
    var id = "leg-" + i + "-" + field;
    var lab = el("label", label + (unit ? " (" + unit + ")" : ""));
    lab.setAttribute("for", id);
    var box = el("span", undefined, "stepper");
    var down = el("button", "−");
    down.type = "button";
    down.setAttribute("aria-label", "Decrease " + label.toLowerCase() + " of leg " + (i + 1));
    var input = el("input");
    input.type = "number";
    input.id = id;
    input.min = min; input.max = max; input.step = step;
    input.inputMode = field === "heading" ? "numeric" : "decimal";
    input.dataset.field = field;
    input.dataset.leg = i;
    input.value = value;
    var up = el("button", "+");
    up.type = "button";
    up.setAttribute("aria-label", "Increase " + label.toLowerCase() + " of leg " + (i + 1));
    down.addEventListener("click", function () { selected = i; send({ action: "nudge", i: i, field: field, delta: -step }); });
    up.addEventListener("click", function () { selected = i; send({ action: "nudge", i: i, field: field, delta: step }); });
    input.addEventListener("change", function () {
      var v = parseFloat(input.value);
      if (isNaN(v)) { input.value = view.legs[i][field]; return; }
      var req = { action: "set_leg", i: i };
      req[field] = v;
      selected = i;
      send(req);
    });
    input.addEventListener("focus", function () { selected = i; markSelected(); });
    box.appendChild(down); box.appendChild(input); box.appendChild(up);
    wrap.appendChild(lab); wrap.appendChild(box);
    return wrap;
  }

  function markSelected() {
    Array.prototype.forEach.call($("legs-list").children, function (li, index) {
      li.classList.toggle("selected", index === selected);
      li.setAttribute("aria-current", index === selected ? "true" : "false");
    });
  }

  function renderLegs() {
    var list = $("legs-list");
    var n = view.legs.length;
    var sailed = view.sailed || 0;
    if (selected >= n) selected = Math.max(0, n - 1);
    if (selected < sailed) selected = Math.min(sailed, Math.max(0, n - 1));
    var sig = n + ":" + sailed;
    if (list.dataset.signature !== sig) {
      list.textContent = "";
      view.legs.forEach(function (leg, i) {
        var li = el("li", undefined, i < sailed ? "leg sailed" : "leg");
        var head = el("div", undefined, "leg-head");
        head.appendChild(el("span", String(i + 1), "leg-number"));
        if (i < sailed) {
          head.appendChild(el("strong", "Watch " + (i + 1) + " (sailed): steer " + String(leg.heading).padStart(3, "0") + " at " + fmt(leg.speed) + " kn for " + fmt(leg.hours) + " h"));
          li.appendChild(head);
          list.appendChild(li);
          return;
        }
        head.appendChild(el("strong", "Leg " + (i + 1)));
        var rm = el("button", "Remove");
        rm.type = "button";
        rm.setAttribute("aria-label", "Remove leg " + (i + 1));
        rm.addEventListener("click", function () { send({ action: "remove_leg", i: i }); });
        head.appendChild(rm);
        li.appendChild(head);
        var fields = el("div", undefined, "leg-fields");
        fields.appendChild(stepperField(i, "heading", "Heading", leg.heading, 0, 359, 1, "degrees"));
        fields.appendChild(stepperField(i, "speed", "Speed", leg.speed, view.limits.speeds[0], view.limits.speeds[1], 0.5, "knots"));
        fields.appendChild(stepperField(i, "hours", "Time", leg.hours, 0.5, view.limits.max_hours, 0.5, "hours"));
        li.appendChild(fields);
        li.addEventListener("click", function () { selected = i; markSelected(); });
        list.appendChild(li);
      });
      if (!n) list.appendChild(el("li", "No legs yet. Add one, or let a helper start you off.", "note"));
      list.dataset.signature = sig;
    }
    view.legs.forEach(function (leg, i) {
      if (i < sailed) return;
      ["heading", "speed", "hours"].forEach(function (field) {
        var input = $("leg-" + i + "-" + field);
        if (input && document.activeElement !== input && input.value !== String(leg[field])) input.value = leg[field];
      });
    });
    markSelected();
    $("turns").hidden = n <= sailed;
  }

  function renderPlanner() {
    var t = view.totals;
    setText($("total-legs"), String(t.legs));
    setText($("total-hours"), fmt(t.hours));
    setText($("deadline-hours"), fmt(t.deadline) + " h");
    $("total-hours").classList.toggle("over", t.over);
    setText($("total-distance"), fmt(t.distance));
    var plot = t.legs
      ? "Your plot ends " + fmt(t.plot_miss) + " nm from the flag, after " + fmt(t.hours) + " hours" + (t.over ? " (over the deadline of " + fmt(t.deadline) + ")." : ".")
      : "Add a leg to start plotting.";
    setText($("plot-line"), plot);
    $("allow-checkbox").checked = view.allow;
    renderLegs();
    var watching = view.chart.mode === "watch";
    var pending = t.legs - (view.sailed || 0);
    setEnabled("add-leg-button", t.legs < view.limits.max_legs && !(watching && pending > 0));
    setEnabled("clear-button", pending > 0);
    setText($("sail-button"), watching ? "Sail this watch" : "Sail");
    setEnabled("sail-button", !watching || pending > 0);
    renderMode();
    renderWatch();
    setEnabled("undo-button", view.can_undo);
    // helpers
    var h = view.helpers;
    setEnabled("current-flag-button", h.current);
    setEnabled("current-point-button", h.current && !!view.point);
    setEnabled("naive-point-button", !!view.point);
    var note = "The naive helper steers straight at the target and ignores every current: a starting guess, not the answer.";
    if (!h.current_unlocked) note += " The helper that allows for the chart unlocks after you clear " + h.current_after + " charts.";
    else if (!h.current) note += " Switch on “Allow for the charted currents” to use the helper that allows for the chart.";
    setText($("helper-note"), note);
    // ruler
    var p = view.point;
    if (p) {
      if (document.activeElement !== $("point-x")) $("point-x").value = p.x;
      if (document.activeElement !== $("point-y")) $("point-y").value = p.y;
      setText($("ruler-readout"), "P is " + fmt(p.distance) + " nm away on a bearing of " + String(p.bearing).padStart(3, "0") + " degrees from where your plot ends.");
    } else {
      setText($("ruler-readout"), "No point marked.");
    }
  }

  function renderMode() {
    var box = $("mode-box");
    var many = view.chart.modes.length > 1 && !(view.sailed > 0);
    box.hidden = !many;
    if (!many) return;
    var watching = view.chart.mode === "watch";
    $("mode-plan-button").setAttribute("aria-pressed", String(!watching));
    $("mode-watch-button").setAttribute("aria-pressed", String(watching));
    setText($("mode-note"), watching
      ? "Sail one leg at a time. After each watch, take a bearing and distance off any landmark in sight and plan the next from your corrected plot."
      : "Commit the whole course up front, then sail it. No fixes: the hardest, cleanest puzzle.");
  }

  function renderWatch() {
    var w = view.watch;
    $("watch-box").hidden = !w;
    if (!w) return;
    $("anchor-button").hidden = !w.can_anchor;
    var status;
    if (!w.sailed) status = "Plan the first watch, then sail it. Between watches you can take a fix if a landmark is in sight.";
    else {
      status = "After watch " + w.sailed + " you believe you are at " + fmt(w.believed[0]) + " east, " + fmt(w.believed[1]) + " north.";
      if (w.fog) status += " Fog: no landmark can be seen.";
      else if (!w.readings.length) status += " No landmark is in sight from here.";
    }
    setText($("watch-status"), status);
    setText($("watch-heading"), w.sailed ? "After watch " + w.sailed : "Before the first watch");
    var list = $("fix-list");
    list.textContent = "";
    w.readings.forEach(function (r) {
      var li = el("li", undefined, w.applied === r.id ? "applied" : "");
      li.appendChild(el("span", r.name + " (" + r.kind + "): bearing " + String(r.bearing).padStart(3, "0") + " degrees, " + fmt(r.range) +
        " nm off. Good to about " + r.bearing_err + " degrees and " + r.range_err_pct + " percent.", "reading"));
      var b = el("button", w.applied === r.id ? "Fix applied" : "Take this fix");
      b.type = "button";
      b.setAttribute("aria-label", (w.applied === r.id ? "Fix applied from " : "Take a fix from ") + r.name);
      b.addEventListener("click", function () { if (w.applied !== r.id) send({ action: "take_fix", landmark: r.id }); });
      li.appendChild(b);
      list.appendChild(li);
    });
    var log = $("watch-log");
    log.textContent = "";
    w.log.forEach(function (line) { log.appendChild(el("li", line)); });
  }

  function setEnabled(id, enabled) {
    var btn = $(id);
    if (enabled) btn.removeAttribute("aria-disabled"); else btn.setAttribute("aria-disabled", "true");
  }
  function isOff(btn) { return btn.disabled || btn.getAttribute("aria-disabled") === "true"; }
  function guard(id, handler) { $(id).addEventListener("click", function () { if (!isOff($(id))) handler(); }); }

  // ---- the passage: playback and the result card ---------------------------------------------------
  var playback = { key: null, raf: 0, index: 0, finished: false };

  function showUpTo(index) {
    var pts = view.reveal.points;
    index = Math.max(0, Math.min(pts.length - 1, index));
    playback.index = index;
    var line = $("dr-true-track");
    if (line) line.setAttribute("points", pts.slice(0, index + 1).map(function (p) { return p[1] + "," + p[2]; }).join(" "));
    var ship = $("dr-ship");
    if (ship) {
      var cur = pts[index], prev = pts[Math.max(0, index - 1)];
      var angle = index > 0 ? Math.atan2(cur[1] - prev[1], -(cur[2] - prev[2])) * 180 / Math.PI : 0;
      var shape = ship.firstElementChild;
      if (shape) shape.setAttribute("transform", "translate(" + cur[1] + "," + cur[2] + ") rotate(" + fmt(angle) + ")");
    }
    var t = pts[index][0];
    document.querySelectorAll(".dr-ribbon").forEach(function (r) { r.style.display = parseFloat(r.getAttribute("data-t")) <= t + 1e-9 ? "" : "none"; });
    var range = $("scrub-range");
    range.value = index;
    var label = "Hour " + fmt(t) + " of " + fmt(view.reveal.hours);
    range.setAttribute("aria-valuetext", label);
    setText($("playback-time"), label);
    renderEvents(t);
    if (index >= pts.length - 1) finishPlayback();
  }

  function renderEvents(t) {
    var list = $("event-list");
    list.textContent = "";
    var shown = view.reveal.events.filter(function (e) { return e.t <= t + 1e-9; });
    shown.forEach(function (e) { list.appendChild(el("li", e.text)); });
    if (!shown.length) list.appendChild(el("li", "Nothing to report yet.", "note"));
  }

  function finishPlayback() {
    if (playback.finished) return;
    playback.finished = true;
    cancelAnimationFrame(playback.raf);
    var r = view.reveal;
    $("playback").hidden = true;
    var card = $("result-card");
    card.hidden = false;
    card.classList.remove("fresh");
    void card.offsetWidth;
    card.classList.add("fresh");
    setText($("result-title"), r.title);
    setText($("result-stars"), stars(r.stars));
    $("result-stars").setAttribute("aria-label", r.stars_text);
    setText($("result-stars-text"), r.stars_text + (r.best_stars > r.stars ? " this time (your best here: " + r.best_stars + ")" : ""));
    var lines = $("result-lines");
    lines.textContent = "";
    r.lines.forEach(function (line) { lines.appendChild(el("li", line)); });
    var crit = $("result-criteria");
    crit.textContent = "";
    r.criteria.forEach(function (c) { crit.appendChild(el("li", c.text, c.ok ? "ok" : "no")); });
    renderEvents(Infinity);
    renderResultExtras();
    announce(r.title + ". " + r.stars_text + ". " + r.lines[0]);
  }

  function renderResultExtras() {
    var r = view.reveal;
    setText($("result-log"), r.log || "");
    $("next-chart-button").hidden = !r.next_chart;
    if (r.next_chart) setText($("next-chart-button"), "Next chart: " + r.next_chart.name);
    $("par-button").hidden = !(r.par && !r.par.shown);
    $("use-par-button").hidden = !(r.par && r.par.shown);
    $("par-box").hidden = !(r.par && r.par.shown);
    var parLines = $("par-lines");
    parLines.textContent = "";
    if (r.par && r.par.shown) r.par.lines.forEach(function (line) { parLines.appendChild(el("li", line)); });
  }

  function startPlayback() {
    var r = view.reveal;
    cancelAnimationFrame(playback.raf);
    playback.finished = false;
    var range = $("scrub-range");
    range.max = r.points.length - 1;
    $("result-card").hidden = true;
    $("playback").hidden = false;
    if (reducedMotion() || r.points.length < 2) { showUpTo(r.points.length - 1); return; }
    showUpTo(0);
    var last = r.points.length - 1;
    var seconds = Math.max(2.5, Math.min(7, r.hours * 0.8));
    var began = null;
    function frame(now) {
      if (began === null) began = now;
      var idx = Math.min(last, Math.floor((now - began) / (seconds * 1000) * last));
      if (idx !== playback.index) showUpTo(idx);
      if (playback.index < last) playback.raf = requestAnimationFrame(frame);
    }
    playback.raf = requestAnimationFrame(frame);
  }

  function renderResult() {
    var reveal = view.phase === "reveal";
    $("planner-panel").hidden = reveal;
    $("result-panel").hidden = !reveal;
    if (!reveal) { cancelAnimationFrame(playback.raf); playback.key = null; $("playback").hidden = true; return; }
    var key = JSON.stringify([view.chart.id, view.legs]);
    if (playback.key !== key) {
      playback.key = key;
      startPlayback();
    } else if (playback.finished) renderResultExtras();
  }

  // ---- render --------------------------------------------------------------------------------------
  function render() {
    renderChart();
    renderPicker();
    renderLog();
    if (view.phase === "plan") renderPlanner();
    renderResult();
  }

  // ---- talking to the engine -----------------------------------------------------------------------
  function persist() {
    try {
      var proxy = engine.getState();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(STORE_KEY, JSON.stringify(obj));
    } catch (e) { /* the save widget is the real save */ }
  }
  function send(request) {
    var result = JSON.parse(engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    $("engine-status").textContent = "";
    view = result;
    render();
    persist();
    return result;
  }

  // ---- controls ------------------------------------------------------------------------------------
  function trySail() {
    if (!view || view.phase !== "plan") return;
    var t = view.totals;
    var message = null;
    if (view.chart.mode === "watch") { if (t.legs <= (view.sailed || 0)) return; if (t.over) message = "Your passage is over the " + fmt(t.deadline) + " hour deadline. Sail this watch anyway?"; }
    else if (!t.legs) message = "Sail with no legs? The ship will stay where she is.";
    else if (t.over && !message) message = "Your plan takes " + fmt(t.hours) + " hours, over the " + fmt(t.deadline) + " hour deadline. Sail anyway?";
    if (message && window.ConfirmDialog) {
      window.ConfirmDialog.ask({ id: t.legs ? "dead-reckoning-sail-late" : "dead-reckoning-sail-empty", message: message, confirmLabel: "Sail",
        onConfirm: function () { send({ action: "sail" }); } });
      return;
    }
    send({ action: "sail" });
  }

  function wire() {
    window.deadReckoningRefresh = function () { if (engine) send({ action: "open" }); };
    $("chart-holder").addEventListener("click", onChartTap);
    guard("add-leg-button", function () { selected = view.legs.length; send({ action: "add_leg" }); });
    guard("clear-button", function () { send({ action: "clear" }); });
    guard("undo-button", function () { send({ action: "undo" }); });
    guard("sail-button", trySail);
    guard("naive-flag-button", function () { selected = view.legs.length; send({ action: "helper", kind: "naive", target: "flag" }); });
    guard("current-flag-button", function () { selected = view.legs.length; send({ action: "helper", kind: "current", target: "flag" }); });
    guard("naive-point-button", function () { selected = view.legs.length; send({ action: "helper", kind: "naive", target: "point" }); });
    guard("current-point-button", function () { selected = view.legs.length; send({ action: "helper", kind: "current", target: "point" }); });
    guard("point-set-button", function () {
      var x = parseFloat($("point-x").value), y = parseFloat($("point-y").value);
      if (!isNaN(x) && !isNaN(y)) send({ action: "point", x: x, y: y });
    });
    guard("point-clear-button", function () { send({ action: "clear_point" }); });
    $("allow-checkbox").addEventListener("change", function () { send({ action: "allow", value: $("allow-checkbox").checked }); });
    $("turns").addEventListener("click", function (e) {
      var b = e.target.closest("button[data-turn]");
      if (b && view.legs.length) send({ action: "nudge", i: selected, field: "heading", delta: parseInt(b.dataset.turn, 10) });
    });
    guard("anchor-button", function () {
      var go = function () { send({ action: "anchor" }); };
      if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: "dead-reckoning-anchor", message: "Drop anchor here and end the passage? It will be scored from where the ship really is.", confirmLabel: "Drop anchor", onConfirm: go });
      else go();
    });
    guard("mode-plan-button", function () { send({ action: "set_mode", mode: "plan" }); });
    guard("mode-watch-button", function () { send({ action: "set_mode", mode: "watch" }); });
    guard("skip-button", function () { showUpTo(view.reveal.points.length - 1); });
    $("scrub-range").addEventListener("input", function () {
      cancelAnimationFrame(playback.raf);
      showUpTo(parseInt($("scrub-range").value, 10));
    });
    guard("next-chart-button", function () { selected = 0; send({ action: "next_chart" }); });
    guard("par-button", function () { send({ action: "show_par" }); });
    guard("use-par-button", function () { selected = 0; send({ action: "use_par" }); });
    wirePanelToggle("picker-toggle-button", "picker-panel");
    wirePanelToggle("log-toggle-button", "log-panel");
    guard("retry-button", function () { send({ action: "retry" }); });
    guard("redo-button", function () { send({ action: "restart" }); });
    document.addEventListener("keydown", onKey);
  }

  // Everything is reachable with Tab; these are speed-ups, and only fire when focus is not in a field or on a button.
  function onKey(e) {
    if (e.altKey || e.ctrlKey || e.metaKey || !view) return;
    var tag = e.target && e.target.tagName;
    if (/^(INPUT|TEXTAREA|SELECT|BUTTON|SUMMARY)$/.test(tag)) return;
    var key = e.key.toLowerCase();
    if (view.phase === "plan") {
      if (key === "s") { e.preventDefault(); trySail(); }
      else if (key === "z") { e.preventDefault(); if (view.can_undo) send({ action: "undo" }); }
      else if (key === "a" || key === "enter") { e.preventDefault(); if (view.legs.length < view.limits.max_legs) { selected = view.legs.length; send({ action: "add_leg" }); } }
    }
  }

  function setBusy(busy) {
    ["add-leg-button", "clear-button", "undo-button", "sail-button", "naive-flag-button", "current-flag-button", "naive-point-button",
      "current-point-button", "point-set-button", "point-clear-button", "retry-button", "redo-button", "skip-button", "next-chart-button",
      "par-button", "use-par-button", "anchor-button", "mode-plan-button", "mode-watch-button"].forEach(function (id) { $(id).disabled = busy; });
  }

  async function boot() {
    setBusy(true);
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
    setBusy(false);
    send({ action: "open" });
    if (window.MobileHud) window.MobileHud.init([{ selector: "#total-hours", label: "Hours" }, { selector: "#total-legs", label: "Legs" }]);
    if (window.MobileDock) window.MobileDock.init("#sail-dock");
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The chart table could not start (" + err + "). Reload to try again.";
  });
})();
