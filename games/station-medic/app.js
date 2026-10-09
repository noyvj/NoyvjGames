/* Station Medic view: glue only. The engine (game.py and its modules) holds every rule; this file draws what handle() returns
   and forwards what the player does. No game logic lives here. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["lexicon.py", "cast.py", "shift.py", "solver.py", "casekit.py", "cases_1.py", "cases_2.py", "cases_3.py", "cases_4.py", "cases_5.py", "cases.py", "progress.py", "codex.py", "achievements.py", "render.py", "hints.py", "info.py"];
  var STORE_KEY = "station-medic:state";
  var BACKUP_KEY = "station-medic:state-backup";

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;
  var view = null;
  var shiftId = null;
  var sel = 0;

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
    setText($("info-page-notice"), about.notice);
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
    var t = view.totals;
    bumpStat("stat-shifts", t.done + "/" + t.shifts);
    bumpStat("stat-clean", t.clean);
    bumpStat("stat-patients", t.patients);
    bumpStat("stat-records", view.record.found + "/" + view.record.total);
    bumpStat("stat-scans", view.tally.scans);
    bumpStat("stat-treats", view.tally.treats);
    bumpStat("stat-restores", view.tally.restores);
    bumpStat("stat-borrows", view.tally.borrows);
    bumpStat("stat-hints", view.tally.hints);
    bumpStat("stat-comforts", view.tally.comforts);
    bumpStat("stat-steady", t.steady);
    bumpStat("stat-rough", t.rough);
  }
  function sealNode(name) {
    return el("span", "seal seal-" + name.toLowerCase(), name);
  }

  // ---- the ward ----------------------------------------------------------------------------------------
  function statusOf(p) {
    if (p.closed) return "Settled";
    var bits = [];
    if (p.iso) bits.push("Cold room");
    if (p.steady === 1) bits.push("Steadied");
    if (p.steady === 2) bits.push("Tally helping");
    if (p.shaking && !p.steady) bits.push("Shaking");
    if (p.risky && !p.iso) bits.push("Flecks");
    return bits.length ? bits.join(", ") : "Waiting";
  }
  function renderShiftHead() {
    var s = view.shift;
    setText($("shift-chapter"), s.chapter + " · shift " + s.number + " of " + s.of + (s.best ? " · best seal: " + s.best_name : ""));
    setText($("shift-heading"), s.title);
    setText($("shift-intro"), s.intro);
    if ($("scene-holder").dataset.sig !== s.id) {
      $("scene-holder").dataset.sig = s.id;
      $("scene-holder").innerHTML = s.scene;
    }
    var open = view.patients.filter(function (p) { return !p.closed; }).length;
    setText($("ward-count"), "(" + open + " waiting, " + (view.patients.length - open) + " settled)");
    var cost = s.cost;
    setText($("cost-line"), "Cost so far: " + cost + (cost === 0 ? " (clean so far)" : " (" + s.grade_now_name.toLowerCase() + ")"));
  }
  function renderPatients() {
    var holder = $("patients");
    if (sel >= view.patients.length) sel = 0;
    var sig = view.patients.map(function (p) { return [p.i, p.closed, p.iso, p.steady, sel === p.i].join(":"); }).join("|") + shiftId;
    if (holder.dataset.sig === sig) return;
    holder.dataset.sig = sig;
    holder.textContent = "";
    view.patients.forEach(function (p) {
      var b = el("button", "patient" + (p.closed ? " settled" : ""));
      b.type = "button";
      b.dataset.testid = "station-medic-patient-" + p.i;
      b.setAttribute("aria-pressed", String(p.i === sel));
      var portrait = el("span");
      portrait.innerHTML = p.portrait;
      b.appendChild(portrait);
      b.appendChild(el("span", "pname", p.first));
      b.appendChild(el("span", "pstatus", statusOf(p)));
      b.setAttribute("aria-label", p.name + ", " + p.role + ". " + statusOf(p) + (p.i === sel ? ". Looking at them now." : ""));
      b.addEventListener("click", function () { sel = p.i; renderBedside(); renderPatients(); renderSheet(); });
      holder.appendChild(b);
    });
  }
  function actButton(letter, label, extra, ok, why, handler, testid) {
    var b = el("button", ok ? "" : "unavailable");
    b.type = "button";
    b.dataset.testid = testid;
    if (letter) b.appendChild(el("span", "letter", letter));
    b.appendChild(document.createTextNode(label));
    if (extra) b.appendChild(el("span", "left", extra));
    if (!ok) { b.setAttribute("aria-disabled", "true"); b.title = why; }
    b.setAttribute("aria-label", label + (extra ? " " + extra : "") + (ok ? "" : ". Not available: " + why));
    b.addEventListener("click", handler);
    return b;
  }
  function renderBedside() {
    var p = view.patients[sel];
    if (!p) return;
    $("bedside-portrait").innerHTML = p.portrait;
    setText($("bedside-name"), p.name + " · " + statusOf(p));
    setText($("bedside-role"), p.role);
    setText($("bedside-say"), "“" + p.say + "”");
    var signs = $("bedside-signs");
    signs.textContent = "";
    p.signs.forEach(function (s) { signs.appendChild(el("li", null, s.name)); });
    var notes = $("bedside-notes");
    notes.textContent = "";
    p.notes.forEach(function (n) { notes.appendChild(el("li", null, n)); });
    var readings = $("bedside-readings");
    readings.textContent = "";
    if (!p.readings.length) readings.appendChild(el("li", "unknown", "No scans on this shift."));
    p.readings.forEach(function (r) {
      var text = r.test + ": " + (r.state === "unknown" ? "not run" : r.state === "positive" ? r.positive : "nothing");
      readings.appendChild(el("li", r.state, text));
    });
    setText($("bedside-certain"), p.matches.length === 1 ? "(only one fits)" : "(" + p.matches.length + " fit)");
    var matches = $("bedside-matches");
    matches.textContent = "";
    p.matches.forEach(function (m) { matches.appendChild(el("li", null, m)); });
    var state = p.closed ? p.name + ": " + p.outcome : (p.shaking && !p.steady ? p.first + " is shaking too hard for a scan or a treatment until steadied." : (p.risky && !p.iso ? p.first + " might be catching: the cold room first." : ""));
    setText($("bedside-state"), state);
    var cab = view.cabinet;
    var scanRow = $("scan-row"), treatRow = $("treat-row"), careRow = $("care-row");
    scanRow.textContent = ""; treatRow.textContent = ""; careRow.textContent = "";
    $("bedside-actions").hidden = p.closed;
    if (p.closed) return;
    if (!cab.tests.length) scanRow.appendChild(el("span", "note", "No scans on this shift."));
    cab.tests.forEach(function (t) {
      var a = p.actions.scan[t.t];
      var left = shelfCount(t.item);
      scanRow.appendChild(actButton(t.glyph, t.name, "(" + left + " left)", a.ok, a.why, function () { act({ action: "scan", p: p.i, t: t.t }); }, "station-medic-scan-" + t.t));
    });
    cab.tx.forEach(function (x) {
      var a = p.actions.treat[x.x];
      var left = shelfCount(x.item);
      var tags = x.tags.length ? " [" + x.tags.join(", ") + "]" : "";
      treatRow.appendChild(actButton(x.glyph, x.name + tags, "(" + left + " left)", a.ok, a.why, function () { act({ action: "treat", p: p.i, x: x.x }); }, "station-medic-treat-" + x.x));
    });
    var care = p.care;
    if (care.band !== undefined && care.band) careRow.appendChild(actButton("", "Steadying band", "", care.band.ok, care.band.why, function () { act({ action: "band", p: p.i }); }, "station-medic-band"));
    if (care.robot) careRow.appendChild(actButton("", "Ask Tally to steady", "", care.robot.ok, care.robot.why, function () { act({ action: "robot", p: p.i }); }, "station-medic-robot"));
    if (care.isolate) careRow.appendChild(actButton("", "Move to the cold room", "", care.isolate.ok, care.isolate.why, function () { act({ action: "isolate", p: p.i }); }, "station-medic-isolate"));
    if (care.release) careRow.appendChild(actButton("", "Back to the ward", "", care.release.ok, care.release.why, function () { act({ action: "release", p: p.i }); }, "station-medic-release"));
    careRow.appendChild(actButton("", "Comfort care", "(cost 1)", true, "", function () { act({ action: "comfort", p: p.i }); }, "station-medic-comfort"));
  }
  function shelfCount(itemName) {
    var found = view.cabinet.items.filter(function (i) { return i.name === itemName; })[0];
    return found ? found.count : 0;
  }
  function renderCabinet() {
    var cab = view.cabinet;
    var list = $("cabinet-list");
    list.textContent = "";
    cab.items.forEach(function (i) {
      var li = el("li", "shelf" + (i.count === 0 ? " empty" : ""));
      li.appendChild(el("span", "letter", i.glyph));
      var body = el("span", "sname", i.name);
      body.appendChild(el("span", "uses", i.uses.join(", ")));
      li.appendChild(body);
      li.appendChild(el("span", "count", String(i.count)));
      li.setAttribute("aria-label", i.name + ": " + plural(i.count, "left", "left") + " of " + i.start + ". Used for " + i.uses.join(", "));
      list.appendChild(li);
    });
    var extra = [];
    if (cab.beds) extra.push("Cold room: " + cab.beds_used + " of " + plural(cab.beds, "bed", "beds") + " in use.");
    if (cab.robots) extra.push("Tally: " + (cab.robots_used ? "steadying one patient" : "free to steady one patient") + ".");
    setText($("cabinet-extra"), extra.join(" "));
    var row = $("borrow-row");
    row.textContent = "";
    cab.items.forEach(function (i) {
      row.appendChild(actButton(i.glyph, "Borrow " + i.name.toLowerCase(), "(cost 1)", true, "", function () { act({ action: "borrow", item: i.i }); }, "station-medic-borrow-" + i.id));
    });
  }
  function renderSheet() {
    var list = $("sheet-list");
    var fits = (view.patients[sel] || { fits: [] }).fits;
    list.textContent = "";
    view.sheet.forEach(function (c) {
      var li = el("li", fits.indexOf(c.id) === -1 ? "ruled-out" : "");
      var head = el("span", "cname", c.name);
      if (c.spreads) head.appendChild(el("span", "tag", "spreads"));
      li.appendChild(head);
      li.appendChild(el("span", "cline", "Signs: " + c.signs.join(", ")));
      li.appendChild(el("span", "cline", "Scans: " + (c.scans.length ? c.scans.join("; ") : "none read positive")));
      li.appendChild(el("span", "cline", "Cured by: " + c.cures.join(" or ") + ". Only eased by: " + c.ease + "."));
      list.appendChild(li);
    });
  }
  function renderLog() {
    var list = $("log-list");
    list.textContent = "";
    view.log.forEach(function (l) {
      var cls = l.kind === "refused" ? "refused" : (/Cost \d/.test(l.msg) ? "cost" : (l.kind === "cure" ? "cure" : ""));
      list.appendChild(el("li", cls, l.msg));
    });
    list.scrollTop = list.scrollHeight;
  }
  function renderGoalStrip() {
    var list = $("goals-list");
    var sig = view.goals.map(function (g) { return g.id + g.have; }).join(",");
    if (list.dataset.sig === sig) return;
    list.dataset.sig = sig;
    list.textContent = "";
    if (!view.goals.length) { list.appendChild(el("li", null, "Every goal you can reach right now is done. New ones appear as new chapters open.")); return; }
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
  function renderRecord() {
    var r = view.record;
    var sig = r.found + ":" + r.crew_told;
    if ($("record-body").dataset.sig === sig) return;
    $("record-body").dataset.sig = sig;
    setText($("record-notice"), r.notice);
    setText($("record-summary"), r.found + " of " + r.total + " pages filed. Pages are filed by playing: nothing is missable and nothing runs out.");
    var body = $("record-body");
    body.textContent = "";
    r.sections.forEach(function (sec) {
      var d = el("details", "record-section");
      if (sec.id === "crew" || sec.found < sec.total) d.open = false;
      var sum = el("summary", null, sec.name + " (" + sec.found + "/" + sec.total + ")");
      d.appendChild(sum);
      var ul = el("ul", "record-list");
      sec.entries.forEach(function (e) {
        var li = el("li", e.unlocked ? "filed" : "unfiled");
        li.appendChild(el("strong", null, e.title));
        li.appendChild(el("span", "rtext", e.text));
        e.lines.forEach(function (l) { li.appendChild(el("span", "rline", l)); });
        ul.appendChild(li);
      });
      d.appendChild(ul);
      body.appendChild(d);
    });
  }
  function renderResult() {
    var r = view.result;
    var card = $("result-card");
    card.hidden = !r;
    if (!r) return;
    setText($("result-title"), "Shift done");
    var g = $("result-grade");
    g.textContent = "";
    g.appendChild(sealNode(r.grade_name));
    g.appendChild(document.createTextNode(" Cost " + r.cost + (r.new_best ? ". A new best seal for this shift." : ". Your best here is " + r.best_name + ".")));
    setText($("result-text"), r.line);
    var beats = $("result-beats");
    beats.textContent = "";
    r.beats.forEach(function (b) {
      var li = el("li", "story-text");
      li.appendChild(el("strong", null, b.who + ": "));
      li.appendChild(document.createTextNode(b.text));
      beats.appendChild(li);
    });
    $("next-button").hidden = !r.next;
    setText($("next-button"), r.next ? "Next shift: " + r.next_name : "Next shift");
  }
  function renderHints() {
    var h = view.hint;
    var btn = $("hint-button");
    var done = view.shift.done;
    btn.hidden = done || h.rung >= 3;
    setText(btn, h.rung === 0 ? "Need a nudge?" : (h.rung === 1 ? "Another hint" : "Show the answer"));
    $("hint-nudge").hidden = !h.nudge;
    setText($("hint-nudge"), h.nudge ? "Nudge: " + h.nudge : "");
    $("hint-hint").hidden = !h.hint;
    setText($("hint-hint"), h.hint ? "Hint: " + h.hint : "");
    $("hint-answer").hidden = !h.answer;
    if (h.answer) {
      setText($("hint-answer-text"), "Answer: " + h.answer);
      setText($("hint-do-button"), h.kind === "restore" ? "Restore the shift" : "Do it for me");
    }
  }
  function renderShifts() {
    var holder = $("shifts-body");
    holder.textContent = "";
    view.rooms.forEach(function (c) {
      var sec = el("section", "chapter" + (c.open ? "" : " locked"));
      var h = el("h3", null, c.name + " (" + c.done + "/" + c.total + ")");
      sec.appendChild(h);
      sec.appendChild(el("p", "note", c.open ? c.blurb : "Locked: done " + c.need + " shifts of " + c.prev_name + " to open this."));
      var ul = el("ul", "shift-grid");
      c.shifts.forEach(function (r) {
        var li = el("li");
        var b = el("button", "shift-btn" + (r.current ? " current" : ""));
        b.type = "button";
        b.dataset.testid = "station-medic-shift-" + r.id;
        b.appendChild(el("span", "rname", r.number + ". " + r.name));
        var meta = el("span", "rmeta");
        if (r.grade) { meta.appendChild(sealNode(r.grade_name)); meta.appendChild(document.createTextNode(" " + plural(r.patients, "patient", "patients"))); }
        else meta.textContent = r.open ? (r.started ? "Started, " : "Not done, ") + plural(r.patients, "patient", "patients") : "Locked";
        b.appendChild(meta);
        b.setAttribute("aria-label", r.number + ", " + r.name + ". " + (r.grade ? r.grade_name + " seal" : (r.open ? "Not done" : "Locked")) + (r.current ? ". Current shift" : ""));
        if (!r.open) b.setAttribute("aria-disabled", "true");
        b.addEventListener("click", function () {
          if (!r.open) { showToast("That chapter opens once " + c.need + " shifts of " + c.prev_name + " are done."); return; }
          sel = 0;
          send({ action: "pick", shift: r.id });
          $("shifts-panel").hidden = true;
          $("shifts-toggle-button").setAttribute("aria-expanded", "false");
          var anchor = $("shift-panel");
          if (anchor.scrollIntoView) anchor.scrollIntoView({ block: "start" });
        });
        li.appendChild(b);
        ul.appendChild(li);
      });
      sec.appendChild(ul);
      holder.appendChild(sec);
    });
  }

  // ---- render everything ----------------------------------------------------------------------------------
  function render() {
    renderAbout();
    if (view.shift.id !== shiftId) {
      shiftId = view.shift.id;
      $("patients").dataset.sig = "";
      var first = view.patients.filter(function (p) { return !p.closed; })[0];
      sel = first ? first.i : 0;
    }
    renderStats();
    renderShiftHead();
    renderPatients();
    renderBedside();
    renderCabinet();
    renderSheet();
    renderLog();
    renderResult();
    renderHints();
    renderShifts();
    renderGoalStrip();
    renderRecord();
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
  function send(request) {
    if (!engine) return null;
    var result = JSON.parse(engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    view = result;
    showToast("");
    render();
    setText($("action-line"), result.message || "");
    if (result.message) announce(result.message);
    persist();
    return result;
  }
  // an action on the shift: after it, move to the next patient still waiting if this one is settled
  function act(request) {
    var before = view.patients[sel];
    var result = send(request);
    if (result && result.ok && before && view.patients[sel] && view.patients[sel].closed) {
      var next = view.patients.filter(function (p) { return !p.closed; })[0];
      if (next) { sel = next.i; render(); }
    }
  }

  // ---- keyboard ------------------------------------------------------------------------------------------
  function onKey(e) {
    if (!view || e.ctrlKey || e.metaKey || e.altKey) return;
    var tag = e.target && e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (document.querySelector("dialog[open], .confirm-dialog, [role='dialog']")) return;
    var n = parseInt(e.key, 10);
    if (n >= 1 && n <= view.patients.length && e.key.length === 1) {
      sel = n - 1;
      render();
    }
  }

  function askThen(id, message, confirmLabel, go) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: false, onConfirm: go });
    else go();
  }

  function wire() {
    $("toast").addEventListener("click", function () { showToast(""); });
    wirePanelToggle("shifts-toggle-button", "shifts-panel");
    wirePanelToggle("record-toggle-button", "record-panel");
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    $("hint-button").addEventListener("click", function () { send({ action: "hint" }); });
    $("hint-do-button").addEventListener("click", function () { act({ action: "hint_do" }); });
    $("next-button").addEventListener("click", function () { sel = 0; send({ action: "next" }); });
    $("restore-button").addEventListener("click", function () {
      var started = view && (view.log.length > 1 || view.shift.cost > 0 || view.result);
      if (!started) { send({ action: "restore" }); return; }
      askThen("station-medic-restore", "Restore this shift to its start? Your seals are kept; only this shift's actions are cleared.", "Restore it", function () { send({ action: "restore" }); });
    });
    $("reset-button").addEventListener("click", function () {
      askThen("station-medic-reset", "Start the whole station over? Your seals, records and tally will be erased.", "Erase it", function () { shiftId = null; send({ action: "reset" }); });
    });
    document.addEventListener("keydown", onKey);
    document.addEventListener("station-medic-narrow-change", function () { if (view) renderSheet(); });
    // The save widget loads a save straight into the engine; this redraws afterwards.
    window.stationMedicRefresh = function () { if (engine) { shiftId = null; send({ action: "open" }); } };
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
    $("engine-status").textContent = "The infirmary could not start (" + err + "). Reload to try again.";
  });
})();
