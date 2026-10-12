/* Slingshot view: glue only. The engine (game.py and its modules) holds every rule and flies every plan; this file draws what handle() returns
   as an SVG chart, turns the burn editor and the time slider into requests, and shows the missions, the atlas and its cards. It never works out a
   path, a closest approach or whether a goal is met: it asks the engine, and draws the answer. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["bodies_data.py", "bodies.py", "orbit.py", "plan.py", "missions_base.py", "missions_c1.py", "missions_c2.py", "missions_c3.py", "refplans.py", "missions.py", "atlas.py", "info.py"];
  var STORE_KEY = "slingshot:state";
  var BACKUP_KEY = "slingshot:state-backup";
  var SVG_NS = "http://www.w3.org/2000/svg";
  var C = 500;               // the chart's centre, in its 1000 x 1000 drawing units
  var R_MAX = 440;           // the longest distance from the centre that is drawn

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;
  var view = null;
  var missionShown = null;   // the mission the plan editor is drawn for
  var planSig = "";
  var scrubTime = Infinity;  // the time (in the mission's unit) the slider is at; Infinity = the end of the flight
  var scrubIdx = 0;
  var pendingScrubs = 0;
  var scrubTimer = null;
  var playTimer = null;
  var chaptersSig = "", atlasSig = "", cardsSig = "";
  var foundShown = "";

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
  function grouped(n) { return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  function fmtKm(x) {
    var a = Math.abs(x);
    if (a >= 1e7) return (x / 1e6).toFixed(1) + " million km";
    if (a >= 1e6) return (x / 1e6).toFixed(2) + " million km";
    return grouped(x) + " km";
  }
  function fmtKmps(v) { return v.toFixed(3) + " km/s"; }
  function reducedMotion() { return document.documentElement.getAttribute("data-reduced-motion") === "true"; }

  // ---- panels --------------------------------------------------------------------------------------
  var PANELS = ["missions", "atlas", "changelog", "settings", "info-page"];
  function setPanel(panelId, buttonId, open) {
    $(panelId).hidden = !open;
    $(buttonId).setAttribute("aria-expanded", String(open));
  }
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () { setPanel(panelId, buttonId, $(panelId).hidden); });
  }

  // ---- the stats ---------------------------------------------------------------------------------------
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
    bumpStat("stat-done", t.done + "/" + t.missions);
    bumpStat("stat-saved", t.saved.toFixed(2) + " km/s");
    bumpStat("stat-flights", t.flights);
    bumpStat("stat-chapters", t.chapters_open + "/" + t.chapters);
    bumpStat("stat-edits", t.edits);
  }

  // ---- the mission -------------------------------------------------------------------------------------
  function renderMission() {
    var m = view.mission;
    setText($("mission-kicker"), "Chapter " + m.chapter + ", " + m.chapter_name + " - mission " + m.number + " of " + m.of + " - to " + m.dest);
    setText($("mission-heading-main"), m.name + (m.done ? " (done)" : ""));
    setText($("mission-brief"), m.brief);
    setText($("mission-goal"), m.goal_text);
    setText($("mission-note"), "Desk: " + m.note);
    var used = view.flight.fuel;
    var planned = view.plan.fuel;
    var over = used > m.budget + 1e-9;
    var text = "Fuel: this plan spends " + used.toFixed(3) + " of " + m.budget.toFixed(2) + " km/s" +
      (over ? " (over the budget by " + (used - m.budget).toFixed(3) + ")" : "") + "." + (m.best !== null ? " Best so far on this mission: " + m.best.toFixed(3) + " km/s." : "");
    if (planned > used + 1e-9) text += " " + (planned - used).toFixed(3) + " km/s of the plan is never used because the flight ends first.";
    setText($("fuel-text"), text);
    var fill = $("fuel-fill");
    fill.style.width = Math.min(100, 100 * used / m.budget) + "%";
    fill.classList.toggle("over", over);
    $("mission-panel").classList.toggle("done", m.done);
    $("prev-mission-button").disabled = prevMissionId() === null;
  }

  // ---- the chart ---------------------------------------------------------------------------------------
  function chartScale() {
    var f = view.flight;
    var ext = f.extent;
    var p = f.path;
    var maxr = 0;
    for (var i = 0; i < p.x.length; i++) maxr = Math.max(maxr, Math.hypot(p.x[i], p.y[i]));
    f.bodies.forEach(function (b) { if (b.a <= ext * 1.02) maxr = Math.max(maxr, b.a); });
    return R_MAX / Math.max(ext, maxr * 1.06);
  }
  function px(x, s) { return C + x * s; }
  function py(y, s) { return C - y * s; }
  function sampleIndexFor(time) {
    var t = view.flight.path.t;
    if (!t.length) return 0;
    if (time === Infinity || time >= t[t.length - 1]) return t.length - 1;
    var lo = 0, hi = t.length - 1;
    while (lo < hi) { var mid = (lo + hi) >> 1; if (t[mid] < time) lo = mid + 1; else hi = mid; }
    return lo;
  }
  function bodyGlyph(parent, x, y, r, cls) {
    var pts = [];
    for (var i = 0; i < 6; i++) { var a = Math.PI / 3 * i + Math.PI / 6; pts.push((x + r * Math.cos(a)).toFixed(1) + "," + (y + r * Math.sin(a)).toFixed(1)); }
    svgEl("polygon", { points: pts.join(" "), "class": cls }, parent);
    svgEl("polygon", { points: [x.toFixed(1) + "," + (y - r).toFixed(1), (x + r * 0.87).toFixed(1) + "," + (y - r * 0.5).toFixed(1), x.toFixed(1) + "," + y.toFixed(1)].join(" "), "class": "c-facet" }, parent);
  }

  function drawChart() {
    var f = view.flight;
    var p = f.path;
    var svg = $("chart");
    var s = chartScale();
    svg.textContent = "";
    svg.setAttribute("viewBox", "0 0 1000 1000");
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    svgEl("rect", { x: 0, y: 0, width: 1000, height: 1000, "class": "c-bg" }, svg);
    for (var g = 1; g <= 3; g++) svgEl("circle", { cx: C, cy: C, r: R_MAX * g / 3, "class": "c-grid" }, svg);
    svgEl("line", { x1: 40, y1: C, x2: 960, y2: C, "class": "c-grid" }, svg);
    svgEl("line", { x1: C, y1: 40, x2: C, y2: 960, "class": "c-grid" }, svg);
    var idx = Math.min(scrubIdx, Math.max(0, p.x.length - 1));
    // orbit rings of the bodies that move
    f.bodies.forEach(function (b) {
      if (b.a * s <= 480) svgEl("circle", { cx: C, cy: C, r: (b.a * s).toFixed(1), "class": "c-orbit" }, svg);
    });
    // the goal ring for a "get this close to the centre" goal
    var goal = view.mission.goal;
    if (goal && goal.kind === "reach") {
      var gr = goal.radius * s;
      if (gr > 6 && gr < 700) {
        svgEl("circle", { cx: C, cy: C, r: gr.toFixed(1), "class": "c-goalring" }, svg);
        svgEl("text", { x: C + gr * 0.7071 + 8, y: C - gr * 0.7071 - 6, "class": "c-label c-goaltext" }, svg).textContent = "goal";
      }
    }
    // the central body
    var cen = f.central;
    bodyGlyph(svg, C, C, cen.id === "sun" ? 30 : 22, "c-central");
    svgEl("text", { x: C, y: C + (cen.id === "sun" ? 52 : 44), "class": "c-label c-names c-central-label", "text-anchor": "middle" }, svg).textContent = cen.label;
    // the path: solid up to the slider, dashed after it
    if (p.x.length > 1) {
      var done = [], rest = [];
      for (var i = 0; i < p.x.length; i++) {
        var pt = px(p.x[i], s).toFixed(1) + "," + py(p.y[i], s).toFixed(1);
        if (i <= idx) done.push(pt);
        if (i >= idx) rest.push(pt);
      }
      if (rest.length > 1) svgEl("polyline", { points: rest.join(" "), "class": "c-path-rest" }, svg);
      if (done.length > 1) {
        svgEl("polyline", { points: done.join(" "), "class": "c-path-glow" }, svg);
        svgEl("polyline", { points: done.join(" "), "class": "c-path" }, svg);
      }
    }
    // start marker
    if (p.x.length) {
      var sx = px(p.x[0], s), sy = py(p.y[0], s);
      svgEl("circle", { cx: sx, cy: sy, r: 7, "class": "c-start" }, svg);
      svgEl("text", { x: sx + 11, y: sy + 28, "class": "c-label c-names" }, svg).textContent = "start";
    }
    // burns
    f.burns.forEach(function (b) {
      var bx = px(b.x, s), by = py(b.y, s);
      svgEl("polygon", { points: [bx + "," + (by - 14), (bx + 14) + "," + by, bx + "," + (by + 14), (bx - 14) + "," + by].join(" "), "class": "c-burn" }, svg);
      svgEl("text", { x: bx, y: by + 5, "class": "c-burn-n", "text-anchor": "middle" }, svg).textContent = String(b.i + 1);
    });
    // the bodies at the slider's time
    f.bodies.forEach(function (b) {
      var bx = px(b.x[idx], s), by = py(b.y[idx], s);
      if (b.soi !== null && b.soi * s >= 6) svgEl("circle", { cx: bx, cy: by, r: (b.soi * s).toFixed(1), "class": "c-soi" }, svg);
      if (b.target) svgEl("circle", { cx: bx, cy: by, r: 22, "class": "c-target" }, svg);
      bodyGlyph(svg, bx, by, 11, "c-body" + (b.target ? " target" : ""));
      svgEl("text", { x: bx + 16, y: by - 14, "class": "c-label c-names" }, svg).textContent = b.label + (b.target ? " (goal)" : "");
    });
    // the probe
    if (p.x.length) {
      var wx = px(p.x[idx], s), wy = py(p.y[idx], s);
      svgEl("circle", { cx: wx, cy: wy, r: 15, "class": "c-probe-ring" }, svg);
      svgEl("circle", { cx: wx, cy: wy, r: 6, "class": "c-probe" }, svg);
      svgEl("text", { x: wx + 20, y: wy + 30, "class": "c-label c-probe-label" }, svg).textContent = view.mission.probe;
    }
    svg.setAttribute("aria-label", "Flight chart centred on " + cen.label + ". " + view.flight.verdict);
  }

  function readoutText() {
    var f = view.flight;
    var p = f.path;
    var i = Math.min(scrubIdx, p.x.length - 1);
    if (i < 0) return "";
    var u = f.unit;
    var tv = p.t[i];
    var parts = [capitalise(u.name.replace(/s$/, "")) + " " + (u.digits ? tv.toFixed(u.digits).replace(/\.?0+$/, "") : Math.round(tv))];
    var r = Math.hypot(p.x[i], p.y[i]);
    if (f.central.id === "sun") parts.push((r / 149597870.7).toFixed(2) + " AU from the Sun");
    else parts.push(fmtKm(r) + " from " + f.central.label);
    parts.push(p.speed[i].toFixed(2) + " km/s");
    var tb = f.bodies.filter(function (b) { return b.target; })[0];
    if (tb && p.target_dist[i] !== null) parts.push(fmtKm(p.target_dist[i]) + " from " + tb.label);
    if (p.frame[i]) parts.push("inside the sphere of influence of " + capitalise(p.frame[i]));
    return parts.join("; ") + ".";
  }
  function capitalise(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

  function renderScrub() {
    var p = view.flight.path;
    var slider = $("scrub");
    slider.max = String(Math.max(0, p.x.length - 1));
    scrubIdx = sampleIndexFor(scrubTime);
    slider.value = String(scrubIdx);
    var text = readoutText();
    setText($("scrub-readout"), text);
    slider.setAttribute("aria-valuetext", text);
  }

  function setScrubIdx(i, counted) {
    var p = view.flight.path;
    scrubIdx = Math.max(0, Math.min(p.x.length - 1, i));
    scrubTime = p.t[scrubIdx];
    $("scrub").value = String(scrubIdx);
    drawChart();
    var text = readoutText();
    setText($("scrub-readout"), text);
    $("scrub").setAttribute("aria-valuetext", text);
    if (counted) countScrub();
  }
  function countScrub() {
    pendingScrubs = Math.min(40, pendingScrubs + 1);
    clearTimeout(scrubTimer);
    scrubTimer = setTimeout(function () {
      if (pendingScrubs && engine) { var n = pendingScrubs; pendingScrubs = 0; send({ action: "scrub", n: n }, true); }
    }, 900);
  }
  function stopPlay() { if (playTimer) { clearInterval(playTimer); playTimer = null; } $("scrub-play-button").textContent = "Play the flight"; }
  function playFlight() {
    stopPlay();
    var n = view.flight.path.x.length;
    if (n < 2) return;
    if (reducedMotion()) { setScrubIdx(n - 1, false); return; }
    var i = 0;
    var stepBy = Math.max(1, Math.ceil(n / 140));
    setScrubIdx(0, false);
    $("scrub-play-button").textContent = "Stop";
    playTimer = setInterval(function () {
      i += stepBy;
      if (i >= n - 1) { setScrubIdx(n - 1, false); stopPlay(); return; }
      setScrubIdx(i, false);
    }, 28);
  }

  // ---- the close-up of each pass -------------------------------------------------------------------------
  function renderCloseups() {
    var box = $("closeup-box");
    var arcs = view.flight.arcs;
    var sig = JSON.stringify(arcs.map(function (a) { return [a.body, a.k, a.pts.length, a.pts[0], a.pts[a.pts.length - 1]]; }));
    box.hidden = arcs.length === 0;
    if (box.dataset.sig === sig) return;
    box.dataset.sig = sig;
    var holder = $("closeup");
    holder.textContent = "";
    arcs.forEach(function (a) {
      var wrap = el("div", "closeup-item");
      var near = true;
      var svg = svgEl("svg", { viewBox: "0 0 400 400", "class": "closeup-svg", role: "img", "aria-label": "Close-up of the pass of " + a.label }, wrap);
      var cap = el("p", "note", "");
      var btn = el("button", null, "Show the whole sphere of influence");
      btn.type = "button";
      function draw() {
        svg.textContent = "";
        var maxr = 0, minr = Infinity;
        a.pts.forEach(function (q) { var r = Math.hypot(q[0], q[1]); maxr = Math.max(maxr, r); minr = Math.min(minr, r); });
        var ext = near ? Math.max(minr * 4, a.radius * 3) : Math.max(maxr, a.soi) * 1.05;
        var k = 170 / ext;
        svgEl("rect", { x: 0, y: 0, width: 400, height: 400, "class": "c-bg" }, svg);
        svgEl("circle", { cx: 200, cy: 200, r: Math.max(4, a.radius * k), "class": "c-central" }, svg);
        if (a.soi * k < 190) svgEl("circle", { cx: 200, cy: 200, r: a.soi * k, "class": "c-soi" }, svg);
        var pts = a.pts.map(function (q) { return (200 + q[0] * k).toFixed(1) + "," + (200 - q[1] * k).toFixed(1); }).join(" ");
        svgEl("polyline", { points: pts, "class": "c-path" }, svg);
        var best = a.pts[0], bestR = Infinity;
        a.pts.forEach(function (q) { var r = Math.hypot(q[0], q[1]); if (r < bestR) { bestR = r; best = q; } });
        svgEl("circle", { cx: 200 + best[0] * k, cy: 200 - best[1] * k, r: 8, "class": "c-start" }, svg);
        svgEl("text", { x: 12, y: 24, "class": "c-label c-names" }, svg).textContent = a.label + (near ? ": close view, " + fmtKm(ext) + " across" : ": whole sphere of influence");
        setText(cap, "Closest approach marked with a ring. Body drawn to size; the path runs in from the edge and out again" + (a.captured ? " into an orbit round it" : "") + (a.impact ? " and hits the surface" : "") + ".");
        btn.textContent = near ? "Show the whole sphere of influence" : "Zoom to the closest approach";
      }
      btn.addEventListener("click", function () { near = !near; draw(); });
      draw();
      wrap.appendChild(cap);
      wrap.appendChild(btn);
      holder.appendChild(wrap);
    });
  }

  // ---- the plan editor ---------------------------------------------------------------------------------------
  var AT_OPTIONS = [["time", "at the time below"], ["peri", "at the nearest point of the path, after the time below"], ["apo", "at the farthest point of the path, after the time below"]];
  function activeField() {
    var a = document.activeElement;
    if (a && a.dataset && a.dataset.field && a.closest && a.closest(".burn-card")) return { i: a.closest(".burn-card").getAttribute("data-i"), field: a.dataset.field };
    if (a && a.id && a.id.indexOf("pass-input-") === 0) return { pass: a.id };
    return null;
  }
  function restoreField(f) {
    if (!f) return;
    var node = null;
    if (f.pass) node = document.getElementById(f.pass);
    else {
      var card = document.querySelector('.burn-card[data-i="' + f.i + '"]');
      if (card) node = card.querySelector('[data-field="' + f.field + '"]');
    }
    if (node) node.focus({ preventScroll: true });
  }
  function numberOr(node, fallback) { var v = parseFloat(node.value); return isNaN(v) ? fallback : v; }

  function burnCard(b) {
    var m = view.mission;
    var card = el("div", "burn-card");
    card.setAttribute("data-i", b.i);
    var head = el("div", "burn-head");
    head.appendChild(el("strong", null, "Burn " + (b.i + 1)));
    var del = el("button", null, "Remove");
    del.type = "button";
    del.setAttribute("aria-label", "Remove burn " + (b.i + 1));
    del.addEventListener("click", function () { send({ action: "burn_del", i: b.i }); });
    head.appendChild(del);
    card.appendChild(head);
    var fields = el("div", "burn-fields");
    // when
    var lab1 = el("label", null, "Happens ");
    var sel = el("select");
    sel.setAttribute("data-field", "at");
    AT_OPTIONS.forEach(function (o) { var op = el("option", null, o[1]); op.value = o[0]; if (o[0] === b.at) op.selected = true; sel.appendChild(op); });
    sel.addEventListener("change", function () { send({ action: "burn_set", i: b.i, at: sel.value }); });
    lab1.appendChild(sel);
    fields.appendChild(lab1);
    var lab2 = el("label", null, "Time (" + m.unit + ") ");
    var t = el("input");
    t.type = "number"; t.step = String(m.step_value); t.min = "0"; t.max = String(m.steps * m.step_value);
    t.value = m.digits ? Number(b.t_value).toFixed(m.digits) : String(Math.round(b.t_value));
    t.setAttribute("data-field", "t");
    t.addEventListener("change", function () { send({ action: "burn_set", i: b.i, t: Math.round(numberOr(t, 0) / m.step_value) }); });
    lab2.appendChild(t);
    fields.appendChild(lab2);
    var lab3 = el("label", null, "Direction (degrees) ");
    var h = el("input");
    h.type = "number"; h.step = "0.1"; h.min = "-180"; h.max = "180"; h.value = Number(b.head).toFixed(1);
    h.setAttribute("data-field", "head");
    h.addEventListener("change", function () { send({ action: "burn_set", i: b.i, head: numberOr(h, 0) }); });
    lab3.appendChild(h);
    fields.appendChild(lab3);
    var quick = el("div", "quick-dir");
    quick.setAttribute("role", "group");
    quick.setAttribute("aria-label", "Set the direction of burn " + (b.i + 1));
    [["Ahead", 0], ["Back", 180], ["Left", 90], ["Right", -90]].forEach(function (q) {
      var qb = el("button", null, q[0]);
      qb.type = "button";
      qb.addEventListener("click", function () { send({ action: "burn_set", i: b.i, head: q[1] }); });
      quick.appendChild(qb);
    });
    fields.appendChild(quick);
    var lab4 = el("label", null, "Strength (km/s) ");
    var dv = el("input");
    dv.type = "number"; dv.step = "0.001"; dv.min = "0"; dv.max = "20"; dv.value = Number(b.dv).toFixed(3);
    dv.setAttribute("data-field", "dv");
    dv.addEventListener("change", function () { send({ action: "burn_set", i: b.i, dv: Math.max(0, numberOr(dv, 0)) }); });
    lab4.appendChild(dv);
    fields.appendChild(lab4);
    card.appendChild(fields);
    card.appendChild(el("p", "note burn-words", "Direction: " + b.words + "."));
    return card;
  }

  function passRow(slot) {
    var row = el("div", "pass-row");
    var lab = el("label", null, "Closest-approach burn at " + slot.label + " (km/s, negative slows down) ");
    var inp = el("input");
    inp.type = "number"; inp.step = "0.001"; inp.min = "-20"; inp.max = "20"; inp.value = Number(slot.dv).toFixed(3);
    inp.id = "pass-input-" + slot.body;
    inp.addEventListener("change", function () { send({ action: "pass_set", body: slot.body, dv: numberOr(inp, 0) }); });
    lab.appendChild(inp);
    row.appendChild(lab);
    return row;
  }

  function renderPlan() {
    var plan = view.plan;
    var m = view.mission;
    var sig = m.id + "|" + JSON.stringify(plan.burns) + "|" + JSON.stringify(plan.pass);
    var undo = $("undo-button"), redo = $("redo-button"), clear = $("clear-button");
    undo.disabled = !view.can_undo;
    redo.disabled = !view.can_redo;
    clear.disabled = !view.can_clear;
    $("add-burn-button").disabled = plan.burns.length >= plan.max_burns;
    $("add-burn-here-button").disabled = plan.burns.length >= plan.max_burns;
    $("fly-button").disabled = false;
    if (sig === planSig) return;
    planSig = sig;
    var focus = activeField();
    var list = $("burn-list");
    list.textContent = "";
    if (!plan.burns.length) list.appendChild(el("p", "note empty-plan", "No burns yet. Add one, or press Burn here on the chart."));
    plan.burns.forEach(function (b) { list.appendChild(burnCard(b)); });
    var main = $("pass-list"), more = $("pass-list-more");
    main.textContent = ""; more.textContent = "";
    var extra = 0;
    plan.pass.forEach(function (slot) {
      if (slot.primary) main.appendChild(passRow(slot));
      else { more.appendChild(passRow(slot)); extra++; }
    });
    $("more-pass-box").hidden = extra === 0;
    restoreField(focus);
  }

  // ---- results -----------------------------------------------------------------------------------------------
  var TITLES = { success: "Goal met", over_budget: "Goal met, but over the fuel budget", crash: "Wren hits something", miss: "Not there yet" };
  function renderResults() {
    var f = view.flight;
    var empty = view.plan.burns.length === 0 && !view.plan.pass.some(function (s) { return s.dv; });
    setText($("result-title"), empty ? "No plan yet" : TITLES[f.outcome]);
    $("result-card").setAttribute("data-outcome", empty ? "none" : f.outcome);
    setText($("result-verdict"), empty ? "With no burns Wren just keeps going round. Add a burn to see where it goes." : f.verdict);
    var det = $("result-details");
    det.textContent = "";
    if (!empty) f.details.forEach(function (line) { det.appendChild(el("li", null, line)); });
    var burns = $("result-burns");
    burns.textContent = "";
    if (!empty) f.burn_text.forEach(function (line) { burns.appendChild(el("li", null, line)); });
    var words = $("chart-text-body");
    words.textContent = "";
    f.words.forEach(function (line) { words.appendChild(el("p", null, line)); });
    var card = $("done-card");
    var just = view.just;
    card.hidden = !just;
    if (just) {
      setText($("done-title"), (just.first ? "Mission done: " : "Reached again: ") + view.mission.name);
      setText($("done-text"), "Fuel used " + fmtKmps(just.fuel) + " of " + view.mission.budget.toFixed(2) + " km/s" + (just.saved > 0 ? ", " + fmtKmps(just.saved) + " (" + just.saved_pct + " percent) saved." : "."));
    }
  }

  // ---- missions panel, atlas and cards -----------------------------------------------------------------------
  function prevMissionId() {
    var list = [];
    view.chapters.forEach(function (ch) { if (ch.open) ch.missions.forEach(function (m) { list.push(m); }); });
    var idx = list.findIndex(function (m) { return m.current; });
    return idx > 0 ? list[idx - 1].id : null;
  }
  function renderChapters() {
    var sig = JSON.stringify(view.chapters);
    if (sig === chaptersSig) return;
    chaptersSig = sig;
    var holder = $("chapter-list");
    holder.textContent = "";
    view.chapters.forEach(function (ch) {
      var block = el("section", "chapter-block" + (ch.open ? "" : " locked"));
      block.setAttribute("aria-label", ch.name);
      block.appendChild(el("h3", null, "Chapter " + ch.id + ": " + ch.name + " - " + ch.done + " of " + ch.total + " done"));
      block.appendChild(el("p", "note blurb", ch.open ? ch.blurb : "Opens when " + ch.need_total + " missions in " + ch.after + " are done (" + ch.need + " more)."));
      var list = el("ul", "mission-list");
      ch.missions.forEach(function (m) {
        var item = el("li");
        var btn = el("button", "mission-btn" + (m.done ? " done" : "") + (m.current ? " current" : ""));
        btn.type = "button";
        btn.setAttribute("data-mission", m.id);
        if (!ch.open) btn.setAttribute("aria-disabled", "true");
        if (m.current) btn.setAttribute("aria-current", "true");
        btn.appendChild(el("span", "mb-name", (m.done ? "✓ " : "") + ch.id + "." + m.number + " " + m.name));
        btn.appendChild(el("span", "mb-meta", (m.done ? "Done, fuel " + m.fuel.toFixed(2) + " of " + m.budget.toFixed(2) + " km/s" : "To " + m.dest + ", budget " + m.budget.toFixed(2) + " km/s") + (ch.open ? "" : " - locked")));
        btn.addEventListener("click", function () {
          if (!ch.open) { showToast("That chapter opens when " + ch.need_total + " missions in " + ch.after + " are done."); return; }
          gotoMission(m.id);
          setPanel("missions-panel", "missions-toggle-button", false);
        });
        item.appendChild(btn);
        list.appendChild(item);
      });
      block.appendChild(list);
      holder.appendChild(block);
    });
  }
  function gotoMission(id) {
    stopPlay();
    scrubTime = Infinity;
    send({ action: "pick", mission: id });
    if ($("mission-panel").scrollIntoView) $("mission-panel").scrollIntoView({ block: "start" });
  }

  function renderAtlas() {
    var cols = view.atlas.columns;
    var sig = JSON.stringify(cols);
    if (sig === atlasSig) return;
    atlasSig = sig;
    var svg = $("atlas");
    svg.textContent = "";
    var W = 70 + cols.length * 130, H = 90 + Math.max.apply(null, cols.map(function (c) { return c.marks.length; })) * 54 + 30;
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.style.minWidth = Math.min(W, 900) + "px";
    svgEl("rect", { x: 0, y: 0, width: W, height: H, "class": "c-bg" }, svg);
    svgEl("line", { x1: 30, y1: 46, x2: W - 20, y2: 46, "class": "a-axis" }, svg);
    svgEl("text", { x: 30, y: 24, "class": "a-note" }, svg).textContent = "Near the Sun  →  far from the Sun (not to scale)";
    cols.forEach(function (col, ci) {
      var x = 70 + ci * 130;
      var r = col.radius ? 6 + 3.2 * Math.log10(Math.max(1, col.radius)) : 10;
      bodyGlyph(svg, x, 46, Math.min(18, r), col.kind === "space" ? "c-central" : "c-body");
      svgEl("text", { x: x, y: 82, "class": "a-title", "text-anchor": "middle" }, svg).textContent = col.label;
      svgEl("text", { x: x, y: 98, "class": "a-tag", "text-anchor": "middle" }, svg).textContent = col.done + " of " + col.total + " done";
      col.marks.forEach(function (mk, mi) {
        var y = 130 + mi * 54;
        var g = svgEl("g", { "class": "a-mark" + (mk.done ? " done" : "") + (mk.open ? "" : " locked") + (mk.current ? " current" : ""), tabindex: "0", role: "button", "data-mission": mk.id }, svg);
        g.setAttribute("aria-label", "Chapter " + mk.chapter + " mission " + mk.number + ", " + mk.name + (mk.done ? ", done, fuel " + mk.fuel.toFixed(2) + " km/s, " + mk.saved_pct + " percent under budget" : mk.open ? ", not done yet" : ", locked"));
        svgEl("circle", { cx: x, cy: y, r: 17, "class": "a-ring" }, g);
        if (mk.done) svgEl("circle", { cx: x, cy: y, r: 12, "class": "a-ring2" }, g);
        svgEl("text", { x: x, y: y + 5, "class": "a-num", "text-anchor": "middle" }, g).textContent = mk.done ? "✓" : mk.chapter + "." + mk.number;
        svgEl("text", { x: x, y: y + 31, "class": "a-sub", "text-anchor": "middle" }, g).textContent = mk.done ? mk.fuel.toFixed(2) + " km/s" : mk.open ? "to do" : "locked";
        var go = function () {
          if (!mk.open) { showToast("That chapter is not open yet."); return; }
          gotoMission(mk.id);
          setPanel("atlas-panel", "atlas-toggle-button", false);
        };
        g.addEventListener("click", go);
        g.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); } });
      });
    });
    var text = $("atlas-text");
    text.textContent = "";
    cols.forEach(function (col) {
      var p = el("p", null, col.label + ": " + col.done + " of " + col.total + " done. ");
      p.appendChild(document.createTextNode(col.marks.map(function (mk) {
        return mk.chapter + "." + mk.number + " " + mk.name + (mk.done ? " (done, " + mk.fuel.toFixed(2) + " km/s, " + mk.saved_pct + " percent under budget)" : mk.open ? " (to do)" : " (locked)");
      }).join("; ") + "."));
      text.appendChild(p);
    });
  }

  function renderCards() {
    var sig = JSON.stringify(view.cards);
    if (sig === cardsSig) return;
    cardsSig = sig;
    var holder = $("atlas-cards");
    holder.textContent = "";
    $("cards-empty").hidden = view.cards.length > 0;
    view.cards.forEach(function (c) {
      var d = el("details", "card");
      d.id = "card-" + c.id;
      d.appendChild(el("summary", null, c.label + " - best fuel " + c.best.toFixed(2) + " km/s (" + plural(c.missions, "mission", "missions") + " done)"));
      var dl = el("dl");
      c.lines.forEach(function (row) {
        dl.appendChild(el("dt", null, row.title));
        dl.appendChild(el("dd", null, row.text));
      });
      d.appendChild(dl);
      d.appendChild(el("p", "card-src", "Source: " + c.source));
      holder.appendChild(d);
    });
  }

  // ---- About, What's New -------------------------------------------------------------------------------------
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
    setText($("model-heading"), info.model_heading);
    listFill("model-list", info.model);
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

  // ---- render --------------------------------------------------------------------------------------------------
  function render() {
    var m = view.mission;
    if (m.id !== missionShown) {
      missionShown = m.id;
      planSig = "";
      scrubTime = Infinity;
      chaptersSig = "";
      atlasSig = "";
    }
    renderStats();
    renderMission();
    renderScrub();
    drawChart();
    renderCloseups();
    renderPlan();
    renderResults();
    renderChapters();
    renderAtlas();
    renderCards();
    renderInfo();
  }

  // ---- talking to the engine -----------------------------------------------------------------------------------
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
    var reply;
    try { reply = JSON.parse(engine.handle(JSON.stringify(request))); } catch (err) { showToast("Something went wrong. Reload to try again."); return null; }
    if (reply.error) { showToast(reply.error); return null; }
    view = reply;
    render();
    if (quiet) { persist(); return view; }
    showToast(view.message || "");
    if (request.action === "pick" || request.action === "next") {
      announce("Mission " + view.mission.chapter + "." + view.mission.number + ", " + view.mission.name + ". " + view.mission.goal_text);
    } else if (view.say) {
      announce(view.say);
    }
    if (view.just && $("done-card").scrollIntoView) $("done-card").scrollIntoView({ block: "nearest" });
    persist();
    return view;
  }

  function neighbourMission(delta) {
    var list = [];
    view.chapters.forEach(function (ch) { if (ch.open) ch.missions.forEach(function (m) { list.push(m); }); });
    var idx = list.findIndex(function (m) { return m.current; });
    var target = list[idx + delta];
    if (target) gotoMission(target.id);
  }
  function askThen(id, message, confirmLabel, go) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: false, onConfirm: go });
    else go();
  }
  function addBurn(atSlider) {
    var m = view.mission;
    var k = 0;
    if (atSlider) {
      var path = view.flight.path;
      k = path.k[Math.min(scrubIdx, path.k.length - 1)] || 0;
    }
    stopPlay();
    send({ action: "burn_add", t: k, head: 0, dv: m.budget > 3 ? 0.5 : 0.1, at: "time" });
    if (view.added !== null && view.added !== undefined) {
      var card = document.querySelector('.burn-card[data-i="' + view.added + '"]');
      var field = card && card.querySelector('[data-field="dv"]');
      if (field) field.focus({ preventScroll: false });
    }
  }
  function flyPlan() {
    stopPlay();
    var before = view.tally.flights;
    var reply = send({ action: "fly" });
    if (reply && reply.tally.flights > before) {
      scrubTime = Infinity;
      playFlight();
      $("result-card").scrollIntoView && $("result-card").scrollIntoView({ block: "nearest" });
    }
  }

  function onChartKey(e) {
    if (!view) return;
    var mod = e.ctrlKey || e.metaKey;
    var n = view.flight.path.x.length;
    if (mod && (e.key === "z" || e.key === "Z")) { e.preventDefault(); send({ action: e.shiftKey ? "redo" : "undo" }); return; }
    if (mod && (e.key === "y" || e.key === "Y")) { e.preventDefault(); send({ action: "redo" }); return; }
    if (mod || e.altKey) return;
    var handled = true;
    switch (e.key) {
      case "ArrowLeft": case "ArrowDown": stopPlay(); setScrubIdx(scrubIdx - 1, true); break;
      case "ArrowRight": case "ArrowUp": stopPlay(); setScrubIdx(scrubIdx + 1, true); break;
      case "PageUp": stopPlay(); setScrubIdx(scrubIdx + 10, true); break;
      case "PageDown": stopPlay(); setScrubIdx(scrubIdx - 10, true); break;
      case "Home": stopPlay(); setScrubIdx(0, true); break;
      case "End": stopPlay(); setScrubIdx(n - 1, true); break;
      case "b": case "B": addBurn(true); break;
      case "f": case "F": flyPlan(); break;
      default: handled = false;
    }
    if (handled) e.preventDefault();
  }

  function wire() {
    $("toast").addEventListener("click", function () { showToast(""); });
    $("chart").addEventListener("keydown", onChartKey);
    var slider = $("scrub");
    slider.addEventListener("input", function () { stopPlay(); setScrubIdx(Number(slider.value), false); });
    slider.addEventListener("change", function () { countScrub(); });
    $("scrub-start-button").addEventListener("click", function () { stopPlay(); setScrubIdx(0, true); });
    $("scrub-back-button").addEventListener("click", function () { stopPlay(); setScrubIdx(scrubIdx - 1, true); });
    $("scrub-forward-button").addEventListener("click", function () { stopPlay(); setScrubIdx(scrubIdx + 1, true); });
    $("scrub-end-button").addEventListener("click", function () { stopPlay(); setScrubIdx(view.flight.path.x.length - 1, true); });
    $("scrub-play-button").addEventListener("click", function () { if (playTimer) stopPlay(); else playFlight(); });
    $("add-burn-button").addEventListener("click", function () { addBurn(false); });
    $("add-burn-here-button").addEventListener("click", function () { addBurn(true); });
    $("undo-button").addEventListener("click", function () { send({ action: "undo" }); });
    $("redo-button").addEventListener("click", function () { send({ action: "redo" }); });
    $("clear-button").addEventListener("click", function () { send({ action: "plan_clear" }); });
    $("fly-button").addEventListener("click", flyPlan);
    $("prev-mission-button").addEventListener("click", function () { neighbourMission(-1); });
    $("next-mission-button").addEventListener("click", function () { stopPlay(); scrubTime = Infinity; send({ action: "next" }); });
    $("done-next-button").addEventListener("click", function () { stopPlay(); scrubTime = Infinity; send({ action: "next" }); if ($("mission-panel").scrollIntoView) $("mission-panel").scrollIntoView({ block: "start" }); });
    $("done-atlas-button").addEventListener("click", function () {
      setPanel("atlas-panel", "atlas-toggle-button", true);
      if ($("atlas-panel").scrollIntoView) $("atlas-panel").scrollIntoView({ block: "start" });
    });
    wirePanelToggle("missions-toggle-button", "missions-panel");
    wirePanelToggle("atlas-toggle-button", "atlas-panel");
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    var labels = $("labels-checkbox");
    labels.checked = lsGet("slingshot:labels") !== "0";
    document.documentElement.setAttribute("data-labels", labels.checked ? "on" : "off");
    labels.addEventListener("change", function () {
      lsSet("slingshot:labels", labels.checked ? "1" : "0");
      document.documentElement.setAttribute("data-labels", labels.checked ? "on" : "off");
    });
    $("reset-button").addEventListener("click", function () {
      askThen("slingshot-reset", "Start over? Every mission will be cleared, with every plan and count.", "Clear it all", function () { chaptersSig = ""; atlasSig = ""; cardsSig = ""; scrubTime = Infinity; send({ action: "reset" }); });
    });
    // The save widget loads a save straight into the engine; this redraws afterwards.
    window.slingshotRefresh = function () { if (engine) { missionShown = null; chaptersSig = ""; atlasSig = ""; cardsSig = ""; scrubTime = Infinity; send({ action: "open" }); } };
    document.addEventListener("keydown", function (e) {
      // undo and redo work anywhere except while typing in a field (a field keeps its own undo)
      var tag = e.target && e.target.tagName;
      if ((e.ctrlKey || e.metaKey) && !e.altKey && tag !== "INPUT" && tag !== "SELECT" && tag !== "TEXTAREA" && e.target !== $("chart") && view) {
        if (e.key === "z" || e.key === "Z") { e.preventDefault(); send({ action: e.shiftKey ? "redo" : "undo" }); return; }
        if (e.key === "y" || e.key === "Y") { e.preventDefault(); send({ action: "redo" }); return; }
      }
      if (e.key === "Escape") {
        PANELS.forEach(function (name) {
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
    $("engine-status").textContent = "Kestrel Desk could not open (" + err + "). Reload to try again.";
  });
})();
