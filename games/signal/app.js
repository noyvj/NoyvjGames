/*
 * Signal -- browser glue. Contains NO game rules.
 *
 * Every rule (generator, solver, scoring, streaks, achievements, share text,
 * save merge) lives in game.py and runs in Pyodide. This file only:
 *   - paints the static shell instantly, from the last engine view cached in
 *     localStorage ("signal:lastview") and the last saved state
 *     ("signal:state"), so a returning player sees their board, readings and
 *     archive calendar before the engine exists;
 *   - loads Pyodide + game.py LAZILY after first paint (or on the first tap
 *     or key press, whichever comes first) and queues taps made meanwhile;
 *   - forwards taps to the engine as JSON and draws whatever view it returns.
 * The only arithmetic here is presentation: the label of a tile, the height
 * of a bar, and the calendar layout.
 */
(function () {
  "use strict";

  var GAME = "signal";
  // Mirrors game.py's EPOCH (tests/test_shell.py asserts they agree).
  var EPOCH = "2026-09-27";
  var PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js";
  var LS_STATE = "signal:state";
  var LS_VIEW = "signal:lastview";
  var MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  var GLYPHS = "▁▂▃▄▅▆▇█";
  var SYMBOL = { none: "·", inprogress: "…", won: "✔", lost: "✖" };
  var SLOW_MODES = { wide: true, bigsky: true };

  var $ = function (id) { return document.getElementById(id); };
  var api = null;
  var engineReady = false;
  var engineStarting = false;
  var booting = false;
  var view = null;
  var cachedValid = false;
  var queue = [];
  var pendingCells = {};
  var tool = "ping";
  var cursor = { r: 0, c: 0 };
  var jump = { col: null, row: "" };
  var currentState = null;
  var cal = { y: 0, m: 0 };
  var catalog = { ach: [], log: [] };
  var toastQueue = [];
  var pendingSettings = {};
  var timings = { paint: null, pyodide: null, game: null, ready: null, firstPing: null, firstPingQueued: false };
  var lastShareText = "";

  function lsGet(key) { try { return window.localStorage.getItem(key); } catch (e) { return null; } }
  function lsSet(key, value) { try { window.localStorage.setItem(key, value); } catch (e) { /* convenience only */ } }
  function lsRemove(key) { try { window.localStorage.removeItem(key); } catch (e) { /* convenience only */ } }
  function jsonParse(text) { try { return JSON.parse(text); } catch (e) { return null; } }
  function utcToday() { return new Date().toISOString().slice(0, 10); }
  function label(r, c) { return String.fromCharCode(65 + c) + (r + 1); }
  // Lets the browser paint a "working" message before a long synchronous engine
  // call. Races a frame against a short timer so a background tab (where
  // requestAnimationFrame never fires) cannot stall the game.
  function nextFrame() {
    return new Promise(function (resolve) {
      var done = false;
      function finish() { if (!done) { done = true; resolve(); } }
      requestAnimationFrame(function () { setTimeout(finish, 0); });
      setTimeout(finish, 60);
    });
  }
  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  // ---- static catalogs (fetched at once: the shared whats-new banner and the
  // engine both read these window globals) ---------------------------------
  var catalogPromise = Promise.all([
    fetch("achievements.json").then(function (r) { return r.text(); }),
    fetch("changelog.json").then(function (r) { return r.text(); }),
  ]).then(function (texts) {
    window.ACHIEVEMENTS_JSON = texts[0];
    window.CHANGELOG_JSON = texts[1];
    var a = jsonParse(texts[0]);
    var l = jsonParse(texts[1]);
    catalog.ach = a && a.achievements ? a.achievements : [];
    var list = Array.isArray(l) ? l : (l && l.changelog) || [];
    catalog.log = list.slice().sort(function (x, y) { return x.date < y.date ? 1 : -1; });
    renderChangelog();
    renderAchievements();
  }).catch(function (err) { console.error("signal: catalog fetch failed", err); });

  // ---- default / cached view -----------------------------------------------
  function defaultView() {
    return {
      session: { type: "daily", date: utcToday(), mode: "easy", label: "Signal · Easy · Daily", number: null, code: null },
      board: { n: 9, k: 2, radius: 4, budget: 8, par: null, top: 5, assist: true, spacing: 3, mode_label: "Easy" },
      pings: [], marks: [], status: "inprogress", pings_left: 8, can_commit: false, possible: null,
      truth: null, guess: null, result: null, stats: null, ach: null, settings: { mode: "easy", assist_shading: true, ascii_share: false, last_preset: "easy" },
      today: utcToday(), epoch: EPOCH, next_utc: null, first_run: true, ascii: false,
    };
  }

  function loadCachedView() {
    var cached = jsonParse(lsGet(LS_VIEW) || "null");
    if (!cached || !cached.board || !cached.session || !Array.isArray(cached.pings)) return null;
    // Fill anything an older cached view lacks so the static paint never throws.
    var base = defaultView();
    cached.settings = cached.settings || base.settings;
    cached.marks = Array.isArray(cached.marks) ? cached.marks : [];
    if (typeof cached.pings_left !== "number") cached.pings_left = cached.board.budget - cached.pings.length;
    if (!cached.status) cached.status = "inprogress";
    return cached;
  }

  // A cached view is only safe to queue taps against if the engine will boot
  // into the very same puzzle: a daily must still be today's; archive and
  // practice sessions are resumed as they were.
  function isCachedValid(v) {
    if (!v) return true; // brand-new visitor: boot opens today's Easy, same as the stub
    if (v.session.type === "daily") return v.session.date === utcToday();
    return true;
  }

  // ---- rendering ---------------------------------------------------------------
  function setMessage(text) { $("message-line").textContent = text || ""; }

  function renderTabs() {
    var s = view.session;
    var tabs = document.querySelectorAll("[data-mode-tab]");
    var practiceVisible = !$("practice-controls").hidden;
    for (var i = 0; i < tabs.length; i++) {
      var t = tabs[i].getAttribute("data-mode-tab");
      var pressed = false;
      if (t === "practice") pressed = s.type === "practice" || practiceVisible;
      else if (t === "archive") pressed = s.type === "archive";
      else pressed = s.type === "daily" && s.mode === t;
      tabs[i].setAttribute("aria-pressed", String(pressed));
    }
  }

  function renderBoard() {
    var b = view.board;
    var n = b.n;
    var boardEl = $("board");
    var hadFocus = boardEl.contains(document.activeElement);
    boardEl.style.setProperty("--n", n);
    boardEl.setAttribute("role", "group");
    boardEl.innerHTML = "";
    if (cursor.r >= n || cursor.c >= n) cursor = { r: Math.floor(n / 2), c: Math.floor(n / 2) };
    var pinged = {};
    view.pings.forEach(function (p) { pinged[p.r + "," + p.c] = p; });
    var marks = {};
    view.marks.forEach(function (m) { marks[m[0] + "," + m[1]] = true; });
    var possible = null;
    if (view.possible) {
      possible = {};
      view.possible.forEach(function (m) { possible[m[0] + "," + m[1]] = true; });
    }
    var truth = null;
    var guess = null;
    if (view.truth) {
      truth = {};
      view.truth.forEach(function (m) { truth[m[0] + "," + m[1]] = true; });
      guess = {};
      (view.guess || []).forEach(function (m) { guess[m[0] + "," + m[1]] = true; });
    }
    boardEl.appendChild(el("span", "axis"));
    for (var c0 = 0; c0 < n; c0++) boardEl.appendChild(el("span", "axis", String.fromCharCode(65 + c0)));
    for (var r = 0; r < n; r++) {
      boardEl.appendChild(el("span", "axis", String(r + 1)));
      for (var c = 0; c < n; c++) {
        var key = r + "," + c;
        var btn = el("button", "cell");
        btn.type = "button";
        btn.setAttribute("data-r", r);
        btn.setAttribute("data-c", c);
        var ring = r === 0 || c === 0 || r === n - 1 || c === n - 1;
        if (ring) btn.classList.add("ring");
        btn.tabIndex = (r === cursor.r && c === cursor.c) ? 0 : -1;
        var desc = label(r, c);
        var p = pinged[key];
        if (p) {
          btn.classList.add("pinged");
          var fill = el("span", "cell-fill");
          fill.style.height = Math.round(p.fill * 100) + "%";
          btn.appendChild(fill);
          btn.appendChild(el("span", "cell-num", String(p.v)));
          btn.appendChild(el("span", "cell-glyph", p.glyph));
          desc += ", pinged, reading " + p.v + " of about " + b.top;
        } else if (pendingCells[key]) {
          btn.classList.add("pending");
          btn.appendChild(el("span", "cell-num", "…"));
          desc += ", ping queued";
        } else {
          desc += ", not pinged";
        }
        if (marks[key]) { btn.classList.add("marked"); desc += ", marked"; }
        if (possible && !p && !possible[key]) { btn.classList.add("ruled-out"); desc += ", ruled out"; }
        if (truth) {
          var isT = !!truth[key];
          var isG = !!guess[key];
          if (isT && isG) { btn.classList.add("truth-hit"); btn.appendChild(el("span", "cell-tag", "✔")); desc += ", transmitter, you found it"; }
          else if (isT) { btn.classList.add("truth-miss"); btn.appendChild(el("span", "cell-tag", "◎")); desc += ", transmitter you missed"; }
          else if (isG) { btn.classList.add("guess-wrong"); btn.appendChild(el("span", "cell-tag", "✖")); desc += ", wrong guess"; }
        }
        btn.setAttribute("aria-label", desc);
        boardEl.appendChild(btn);
      }
    }
    if (hadFocus) focusCursor();
  }

  function focusCursor() {
    var node = $("board").querySelector('.cell[data-r="' + cursor.r + '"][data-c="' + cursor.c + '"]');
    if (node) node.focus();
  }

  function renderStatus() {
    var b = view.board;
    var used = b.budget - view.pings_left;
    var dots = $("pings-display");
    dots.innerHTML = "";
    for (var i = 0; i < b.budget; i++) dots.appendChild(el("span", i < used ? "used" : "", i < used ? "○" : "●"));
    dots.setAttribute("aria-label", view.pings_left + " pings left");
    $("pings-text").textContent = "Pings: " + view.pings_left + "/" + b.budget;
    $("par-text").textContent = "Par: " + (b.par === null || b.par === undefined ? "-" : b.par);
    $("marks-text").textContent = "Markers: " + view.marks.length + "/" + b.k;
    var finished = view.status !== "inprogress";
    $("commit-button").disabled = !view.can_commit || !engineReady;
    $("give-up-button").disabled = finished || !engineReady;
    $("clear-marks-button").disabled = finished || !engineReady;
    $("session-line").textContent = view.session.label + (view.session.type === "daily" || view.session.type === "archive" ? "" : "");
    var toggle = $("tool-toggle-button");
    toggle.textContent = "Tool: " + (tool === "ping" ? "Ping" : "Mark");
    toggle.setAttribute("aria-pressed", String(tool === "mark"));
    $("warm-line").hidden = engineReady;
    if (!engineReady) {
      $("warm-line").textContent = "Receiver warming up..." + (queue.length ? " " + queue.length + " tap" + (queue.length === 1 ? "" : "s") + " queued." : "");
    }
    if (view.ach) $("achievements-toggle-button").textContent = "🏆 Achievements (" + view.ach.earned + "/" + view.ach.total + ")";
    $("assist-checkbox").checked = !!view.settings.assist_shading;
    $("ascii-checkbox").checked = !!view.settings.ascii_share;
    $("assist-checkbox").disabled = !view.board.assist;
    var sel = $("practice-preset");
    if (document.activeElement !== sel && view.settings.last_preset) sel.value = view.settings.last_preset;
  }

  function renderWaterfall() {
    var box = $("waterfall");
    box.innerHTML = "";
    if (!view.pings.length) {
      box.appendChild(el("span", "wf-empty", "No readings yet."));
      return;
    }
    view.pings.forEach(function (p) {
      var item = el("div", "wf-item");
      item.appendChild(el("span", "wf-glyph", p.glyph));
      item.appendChild(el("span", "", String(p.v)));
      item.appendChild(el("span", "", p.label));
      item.setAttribute("title", p.label + " read " + p.v);
      box.appendChild(item);
    });
  }

  function countdownText() {
    if (!view.next_utc) return "";
    var ms = Date.parse(view.next_utc + "T00:00:00Z") - Date.now();
    if (!(ms > 0)) return "A new puzzle is on the air.";
    var mins = Math.floor(ms / 60000);
    return "Next daily puzzle in " + Math.floor(mins / 60) + "h " + (mins % 60) + "m (UTC midnight).";
  }

  function renderResult() {
    var panel = $("result-panel");
    var res = view.result;
    panel.hidden = !res;
    if (!res) { lastShareText = ""; return; }
    $("result-title").textContent = res.won ? "Signal locked." : "Lost the signal.";
    var detail = res.won
      ? res.pings_used + " of " + res.budget + " pings" + (res.under_par ? ", under par (" + res.par + ")" : (res.at_par ? ", at par" : ", par was " + res.par)) + "."
      : "Par was " + res.par + ". The transmitters are shown on the board (◎ missed, ✔ found, ✖ wrong).";
    $("result-detail").textContent = detail;
    $("next-line").textContent = view.session.type === "daily" ? countdownText() : "";
    var preview = $("share-preview");
    preview.hidden = !lastShareText;
    preview.textContent = lastShareText;
  }

  function render() {
    if (!view) return;
    renderTabs();
    renderBoard();
    renderStatus();
    renderWaterfall();
    renderResult();
    var panel = $("archive-panel");
    if (!panel.hidden) renderCalendar();
  }

  // ---- calendar (engine-less: reads saved days only) ----------------------------
  function dayStatus(date, mode) {
    var days = currentState && currentState.days;
    var rec = days && days[date + ":" + mode];
    if (!rec) return "none";
    return rec.result === "won" || rec.result === "lost" ? rec.result : "inprogress";
  }

  var STATUS_WORD = { none: "not played", inprogress: "in progress", won: "won", lost: "lost" };

  function makeChip(date, dayNumber, mode, enabled) {
    var st = dayStatus(date, mode);
    var chip = el("button", "cal-chip", (mode === "easy" ? "E " : "H ") + SYMBOL[st]);
    chip.type = "button";
    chip.disabled = !enabled;
    chip.setAttribute("aria-label", MONTHS[parseInt(date.slice(5, 7), 10) - 1] + " " + dayNumber + ", " + mode + ": " + STATUS_WORD[st]);
    chip.addEventListener("click", function () {
      $("archive-panel").hidden = true;
      act({ action: "open", date: date, mode: mode });
    });
    return chip;
  }

  function renderCalendar() {
    var grid = $("calendar-grid");
    grid.innerHTML = "";
    ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].forEach(function (d) { grid.appendChild(el("span", "cal-dow", d)); });
    $("cal-title").textContent = MONTHS[cal.m] + " " + cal.y;
    var first = new Date(Date.UTC(cal.y, cal.m, 1));
    var days = new Date(Date.UTC(cal.y, cal.m + 1, 0)).getUTCDate();
    for (var pad = 0; pad < first.getUTCDay(); pad++) grid.appendChild(el("span"));
    var today = utcToday();
    for (var d = 1; d <= days; d++) {
      var date = new Date(Date.UTC(cal.y, cal.m, d)).toISOString().slice(0, 10);
      var enabled = date >= EPOCH && date <= today;
      var cell = el("div", "cal-day" + (enabled ? "" : " off") + (date === today ? " today" : ""));
      cell.appendChild(el("span", "num", String(d)));
      ["easy", "hard"].forEach(function (mode) { cell.appendChild(makeChip(date, d, mode, enabled)); });
      grid.appendChild(cell);
    }
    var prev = new Date(Date.UTC(cal.y, cal.m - 1, 28)).toISOString().slice(0, 10);
    $("cal-prev-button").disabled = prev < EPOCH.slice(0, 7);
    var nextMonth = new Date(Date.UTC(cal.y, cal.m + 1, 1)).toISOString().slice(0, 10);
    $("cal-next-button").disabled = nextMonth > today;
  }

  function openArchive() {
    var ref = (view && view.session.date) || utcToday();
    cal = { y: parseInt(ref.slice(0, 4), 10), m: parseInt(ref.slice(5, 7), 10) - 1 };
    renderCalendar();
  }

  // ---- panels built from static data ----------------------------------------------
  function renderChangelog() {
    var panel = $("changelog-panel");
    panel.innerHTML = "";
    panel.appendChild(el("h2", "panel-heading", "What's New"));
    catalog.log.forEach(function (entry) {
      var row = el("div", "changelog-entry");
      row.appendChild(el("div", "date", entry.date));
      row.appendChild(el("div", "", entry.entry));
      panel.appendChild(row);
    });
    $("changelog-toggle-button").textContent = "📋 What's New (" + catalog.log.length + ")";
  }

  function earnedMap() {
    var out = {};
    var earned = currentState && currentState.earned;
    if (earned) Object.keys(earned).forEach(function (k) { out[k] = earned[k]; });
    var list = currentState && currentState.achievements_earned;
    if (Array.isArray(list)) list.forEach(function (k) { if (!out[k]) out[k] = ""; });
    return out;
  }

  function renderAchievements() {
    var panel = $("achievements-panel");
    panel.innerHTML = "";
    var earned = earnedMap();
    var count = catalog.ach.filter(function (a) { return earned[a.id] !== undefined; }).length;
    panel.appendChild(el("h2", "panel-heading", "Achievements (" + count + "/" + catalog.ach.length + ")"));
    catalog.ach.forEach(function (a) {
      var got = earned[a.id] !== undefined;
      var card = el("div", "achievement-card" + (got ? " achievement-card--earned" : ""));
      card.setAttribute("data-achievement-id", a.id);
      card.appendChild(el("div", "achievement-card-label", a.label));
      card.appendChild(el("p", "achievement-card-description", a.description));
      if (got && earned[a.id]) card.appendChild(el("p", "achievement-card-date", "Earned " + earned[a.id]));
      panel.appendChild(card);
    });
    if (!$("achievements-panel").hidden && window.applyAchievementStats) window.applyAchievementStats();
    if (!view || !view.ach) $("achievements-toggle-button").textContent = "🏆 Achievements (" + count + "/" + catalog.ach.length + ")";
  }

  function renderStats(resp) {
    var panel = $("stats-panel");
    panel.innerHTML = "";
    panel.appendChild(el("h2", "panel-heading", "Stats"));
    if (!resp) {
      panel.appendChild(el("p", "panel-note", "Stats appear once the receiver has warmed up..."));
      return;
    }
    panel.appendChild(el("p", "panel-note", "Longest daily streak (any mode): " + resp.best_streak + " day(s). Daily streaks count wins on the daily puzzle only."));
    Object.keys(resp.stats).forEach(function (mode) {
      var s = resp.stats[mode];
      var block = el("div", "stat-block");
      block.appendChild(el("strong", "", s.label + (s.daily_mode ? "" : " (practice only)")));
      if (s.daily) {
        var d = s.daily;
        var grid = el("div", "stat-grid");
        [["Played", d.played], ["Win %", d.played ? Math.round(100 * d.won / d.played) : 0], ["Streak", d.streak], ["Best", d.best_streak]].forEach(function (pair) {
          var cellBox = el("div");
          cellBox.appendChild(el("b", "", String(pair[1])));
          cellBox.appendChild(el("span", "", pair[0]));
          grid.appendChild(cellBox);
        });
        block.appendChild(grid);
        var max = Math.max.apply(null, d.pings_hist.concat([1]));
        d.pings_hist.forEach(function (count, i) {
          var row = el("div", "hist-row");
          row.appendChild(el("span", "", (i + 1) + " ping" + (i ? "s" : "") + ":"));
          var bar = el("div", "hist-bar");
          bar.style.width = Math.round(140 * count / max) + "px";
          row.appendChild(bar);
          row.appendChild(el("span", "", String(count)));
          block.appendChild(row);
        });
        block.appendChild(el("p", "panel-note", "Archive: " + s.archive.won + " won of " + s.archive.played + " played."));
      }
      block.appendChild(el("p", "panel-note", "Practice: " + s.practice.won + " won of " + s.practice.played + " played."));
      panel.appendChild(block);
    });
  }

  // ---- engine plumbing ---------------------------------------------------------------
  function persistState() {
    try {
      var proxy = window.pyodide.globals.get("get_state")();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      proxy.destroy();
      currentState = jsonParse(JSON.stringify(obj, function (k, v) { return v === undefined ? null : v; }));
      lsSet(LS_STATE, JSON.stringify(currentState));
    } catch (err) {
      console.error("signal: persist failed", err);
    }
    renderAchievements();
  }

  function cacheView() {
    if (view) lsSet(LS_VIEW, JSON.stringify(view));
  }

  function showToast(text) {
    toastQueue.push(text);
    if (toastQueue.length === 1) nextToast();
  }
  function nextToast() {
    if (!toastQueue.length) return;
    var node = $("achievement-toast");
    $("achievement-toast-text").textContent = toastQueue[0];
    node.hidden = false;
    setTimeout(function () {
      node.hidden = true;
      toastQueue.shift();
      nextToast();
    }, 3200);
  }

  function send(req) {
    return JSON.parse(api(JSON.stringify(req)));
  }

  function applyResponse(resp, req) {
    if (resp.view) {
      view = resp.view;
      cachedValid = true;
      if (resp.view.settings && resp.view.settings.last_preset) $("practice-preset").value = resp.view.settings.last_preset;
    }
    if (!resp.ok) {
      setMessage(resp.error || "Something went wrong.");
    } else if (resp.message) {
      setMessage(resp.message);
    } else if (view && view.first_run && !view.pings.length && view.status === "inprogress") {
      setMessage("First time? Tap a tile to ping it. The number is the summed signal there. Then mark where you think the transmitters are.");
    }
    if (req && req.action === "share" && resp.text) lastShareText = resp.text;
    if (req && (req.action === "open" || req.action === "practice") && resp.ok) lastShareText = "";
    (resp.new || []).forEach(function (a) { showToast("Achievement: " + a.label + " (" + a.description + ")"); });
    (resp.events || []).forEach(function (ev) {
      if (ev.type === "leaderboard" && window.NoyvjLeaderboard) window.NoyvjLeaderboard.report(ev.game, ev.board, ev.score, ev.detail);
    });
    if (resp.dirty) persistState();
    if (view) { render(); cacheView(); }
  }

  var QUEUEABLE = { ping: true, mark: true, clear_marks: true, commit: true, give_up: true, open: true, practice: true };

  async function act(req, opts) {
    opts = opts || {};
    if (!engineReady) {
      var relative = req.action === "ping" || req.action === "mark" || req.action === "clear_marks" || req.action === "commit" || req.action === "give_up";
      if (!QUEUEABLE[req.action] || (relative && !cachedValid)) {
        setMessage("Receiver warming up... give it a moment, then tap again.");
        startEngine();
        return;
      }
      queue.push(req);
      if (req.action === "ping") { pendingCells[req.r + "," + req.c] = true; }
      setMessage("Receiver warming up... your tap is queued and will be applied in order.");
      startEngine();
      render();
      return;
    }
    if (opts.slow || (req.action === "practice" && SLOW_MODES[req.mode])) {
      setMessage("Tuning the receiver (generating a big board)...");
      await nextFrame();
    }
    var started = performance.now();
    var resp = send(req);
    if (req.action === "ping" && timings.firstPing === null) {
      timings.firstPing = Math.round(performance.now());
      renderDiagnostics();
    }
    applyResponse(resp, req);
    return performance.now() - started;
  }

  function loadScript(src) {
    return new Promise(function (resolve, reject) {
      var s = document.createElement("script");
      s.src = src;
      s.onload = resolve;
      s.onerror = function () { reject(new Error("could not load " + src)); };
      document.head.appendChild(s);
    });
  }

  function renderDiagnostics() {
    if (timings.paint === null) {
      var paints = performance.getEntriesByName("first-contentful-paint");
      if (paints.length) timings.paint = Math.round(paints[0].startTime);
    }
    var parts = [];
    if (timings.paint !== null) parts.push("first paint " + (timings.paint / 1000).toFixed(2) + " s");
    else {
      var nav = performance.getEntriesByType("navigation")[0];
      if (nav && nav.domContentLoadedEventEnd) parts.push("static shell ready " + (nav.domContentLoadedEventEnd / 1000).toFixed(2) + " s");
    }
    if (timings.pyodide !== null) parts.push("Pyodide loaded " + (timings.pyodide / 1000).toFixed(2) + " s");
    if (timings.ready !== null) parts.push("engine ready " + (timings.ready / 1000).toFixed(2) + " s");
    if (timings.firstPing !== null) parts.push("first ping " + (timings.firstPing / 1000).toFixed(2) + " s" + (timings.firstPingQueued ? " (tapped before ready, queued)" : ""));
    $("diagnostics-line").textContent = parts.length ? "This page load: " + parts.join(", ") + " (all measured from navigation start)." : "";
  }

  async function startEngine() {
    if (engineStarting) return;
    engineStarting = true;
    booting = true;
    try {
      await loadScript(PYODIDE_URL);
      var pyodide = await window.loadPyodide();
      window.pyodide = pyodide;
      timings.pyodide = Math.round(performance.now());
      await catalogPromise;
      var code = await (await fetch("game.py")).text();
      pyodide.runPython(code);
      timings.game = Math.round(performance.now());
      api = pyodide.globals.get("handle");
      var saved = jsonParse(lsGet(LS_STATE) || "null");
      if (saved) {
        var proxy = pyodide.toPy(saved);
        pyodide.globals.get("load_state")(proxy);
        if (proxy.destroy) proxy.destroy();
      }
      var boot = send({ action: "boot" });
      engineReady = true;
      booting = false;
      timings.ready = Math.round(performance.now());
      applyResponse(boot, { action: "boot" });
      if (Object.keys(pendingSettings).length) {
        var s = pendingSettings;
        pendingSettings = {};
        s.action = "settings";
        applyResponse(send(s), s);
      }
      var replay = queue;
      queue = [];
      pendingCells = {};
      if (replay.some(function (q) { return q.action === "ping"; })) timings.firstPingQueued = true;
      for (var i = 0; i < replay.length; i++) {
        var resp = send(replay[i]);
        if (replay[i].action === "ping" && timings.firstPing === null) timings.firstPing = Math.round(performance.now());
        applyResponse(resp, replay[i]);
      }
      persistState();
      renderDiagnostics();
      if (!$("stats-panel").hidden) requestStats();
    } catch (err) {
      console.error("signal: engine failed to start", err);
      booting = false;
      engineStarting = false;
      setMessage("The engine could not load (offline for the first time?). The board is still readable; try reloading.");
    }
  }

  // Called by game.py's load_state() after the save widget loads a save.
  window.signalOnStateLoaded = function () {
    if (!engineReady || booting) return;
    var resp = send({ action: "boot" });
    resp.dirty = true;
    applyResponse(resp, { action: "boot" });
    setMessage("Save loaded.");
  };

  async function requestStats() {
    if (!engineReady) { renderStats(null); return; }
    renderStats(send({ action: "stats" }));
  }

  // ---- user actions ---------------------------------------------------------------------
  function doTool(r, c, forceMark) {
    if (view.status !== "inprogress") { setMessage("This puzzle is finished. Open another from the tabs or the archive."); return; }
    cursor = { r: r, c: c };
    if (forceMark || tool === "mark") act({ action: "mark", r: r, c: c });
    else act({ action: "ping", r: r, c: c });
  }

  function confirmThen(id, message, confirmLabel, allowSkip, fn) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: allowSkip, onConfirm: fn });
    else fn();
  }

  function wire() {
    var boardEl = $("board");
    boardEl.addEventListener("click", function (ev) {
      var btn = ev.target.closest(".cell");
      if (!btn) return;
      doTool(parseInt(btn.getAttribute("data-r"), 10), parseInt(btn.getAttribute("data-c"), 10), ev.shiftKey);
    });
    boardEl.addEventListener("contextmenu", function (ev) {
      var btn = ev.target.closest(".cell");
      if (!btn) return;
      ev.preventDefault();
      doTool(parseInt(btn.getAttribute("data-r"), 10), parseInt(btn.getAttribute("data-c"), 10), true);
    });
    boardEl.addEventListener("keydown", function (ev) {
      var btn = ev.target.closest(".cell");
      if (!btn || ev.ctrlKey || ev.metaKey || ev.altKey) return;
      var n = view.board.n;
      var r = parseInt(btn.getAttribute("data-r"), 10);
      var c = parseInt(btn.getAttribute("data-c"), 10);
      var moved = true;
      if (ev.key === "ArrowUp") r = Math.max(0, r - 1);
      else if (ev.key === "ArrowDown") r = Math.min(n - 1, r + 1);
      else if (ev.key === "ArrowLeft") c = Math.max(0, c - 1);
      else if (ev.key === "ArrowRight") c = Math.min(n - 1, c + 1);
      else moved = false;
      if (moved) {
        ev.preventDefault();
        cursor = { r: r, c: c };
        renderBoard();
        focusCursor();
        return;
      }
      if (ev.key === "Enter") { ev.preventDefault(); doTool(r, c, false); return; }
      if (ev.key === " " || ev.key === "Spacebar") { ev.preventDefault(); doTool(r, c, true); return; }
      // Type a column letter then a row number (D4) to jump the cursor.
      if (/^[a-zA-Z]$/.test(ev.key)) {
        var col = ev.key.toUpperCase().charCodeAt(0) - 65;
        if (col < n) { jump = { col: col, row: "" }; cursor = { r: cursor.r, c: col }; renderBoard(); focusCursor(); ev.preventDefault(); }
      } else if (/^[0-9]$/.test(ev.key) && jump.col !== null) {
        var next = jump.row + ev.key;
        var row = parseInt(next, 10);
        if (row < 1 || row > n) { next = ev.key; row = parseInt(next, 10); }
        if (row >= 1 && row <= n) { jump.row = next; cursor = { r: row - 1, c: jump.col }; renderBoard(); focusCursor(); }
        ev.preventDefault();
      }
    });

    $("tool-toggle-button").addEventListener("click", function () {
      tool = tool === "ping" ? "mark" : "ping";
      renderStatus();
    });

    document.querySelectorAll("[data-mode-tab]").forEach(function (tab) {
      tab.addEventListener("click", function () {
        var t = tab.getAttribute("data-mode-tab");
        if (t === "archive") { $("archive-panel").hidden = false; openArchive(); return; }
        if (t === "practice") {
          $("practice-controls").hidden = false;
          var code = currentState && currentState.practice && currentState.practice.code;
          if (view.session.type !== "practice") {
            if (code) act({ action: "practice", code: code });
            else act({ action: "practice", mode: $("practice-preset").value }, { slow: !!SLOW_MODES[$("practice-preset").value] });
          }
          renderTabs();
          return;
        }
        $("practice-controls").hidden = true;
        act({ action: "open", date: utcToday(), mode: t });
      });
    });

    $("practice-new-button").addEventListener("click", function () {
      var mode = $("practice-preset").value;
      var go = function () { act({ action: "practice", mode: mode }, { slow: !!SLOW_MODES[mode] }); };
      if (view.session.type === "practice" && view.status === "inprogress" && view.pings.length) {
        confirmThen("signal-new-practice", "Leave this practice puzzle unfinished and start a new one?", "New puzzle", true, go);
      } else go();
    });
    $("practice-load-button").addEventListener("click", function () {
      var code = $("practice-code").value.trim();
      if (!code) { setMessage("Type a practice code first, for example P-H4K2Q7."); return; }
      act({ action: "practice", code: code }, { slow: true });
    });
    $("practice-code").addEventListener("keydown", function (ev) { if (ev.key === "Enter") $("practice-load-button").click(); });

    $("commit-button").addEventListener("click", function () {
      confirmThen("signal-commit", "Commit these " + view.board.k + " markers? You only get one answer.", "Commit", true, function () { act({ action: "commit" }); });
    });
    $("clear-marks-button").addEventListener("click", function () { act({ action: "clear_marks" }); });
    $("give-up-button").addEventListener("click", function () {
      confirmThen("signal-give-up", "Give up and reveal the transmitters? This counts as a loss.", "Give up", false, function () { act({ action: "give_up" }); });
    });
    $("share-button").addEventListener("click", async function () {
      if (!engineReady) { setMessage("Receiver warming up..."); return; }
      await act({ action: "share" });
      if (lastShareText && navigator.clipboard && navigator.clipboard.writeText) {
        try { await navigator.clipboard.writeText(lastShareText); setMessage("Result copied to the clipboard."); } catch (e) { setMessage("Copy the result from the box below."); }
      } else setMessage("Copy the result from the box below.");
    });

    // panels backed by engine or static data
    $("archive-toggle-button").addEventListener("click", function () {
      var panel = $("archive-panel");
      panel.hidden = !panel.hidden;
      if (!panel.hidden) openArchive();
    });
    $("cal-prev-button").addEventListener("click", function () { cal.m -= 1; if (cal.m < 0) { cal.m = 11; cal.y -= 1; } renderCalendar(); });
    $("cal-next-button").addEventListener("click", function () { cal.m += 1; if (cal.m > 11) { cal.m = 0; cal.y += 1; } renderCalendar(); });
    $("stats-toggle-button").addEventListener("click", function () {
      var panel = $("stats-panel");
      panel.hidden = !panel.hidden;
      if (!panel.hidden) { startEngine(); requestStats(); }
    });
    $("achievements-toggle-button").addEventListener("click", function () {
      var panel = $("achievements-panel");
      panel.hidden = !panel.hidden;
      if (!panel.hidden) { renderAchievements(); if (window.applyAchievementStats) window.applyAchievementStats(); }
    });
    $("changelog-toggle-button").addEventListener("click", function () { $("changelog-panel").hidden = !$("changelog-panel").hidden; });
    $("info-page-toggle-button").addEventListener("click", function () { $("info-page-panel").hidden = !$("info-page-panel").hidden; });

    // settings that live in the save (engine-side)
    function engineSetting(key, value) {
      if (engineReady) act({ action: "settings", [key]: value });
      else { pendingSettings[key] = value; startEngine(); }
    }
    $("assist-checkbox").addEventListener("change", function (ev) { engineSetting("assist_shading", ev.target.checked); });
    $("ascii-checkbox").addEventListener("change", function (ev) { engineSetting("ascii_share", ev.target.checked); });
    $("theme-setting-button").addEventListener("click", function () { if (window.NoyvjTheme) window.NoyvjTheme.toggle(); });
    $("reset-progress-button").addEventListener("click", function () {
      confirmThen("signal-reset", "Erase ALL Signal progress in this browser (streaks, archive results, achievements)? A save code you already made can still restore it.", "Erase everything", false, async function () {
        if (!engineReady) { setMessage("Wait for the receiver to warm up first."); return; }
        lsRemove(LS_STATE);
        lsRemove(LS_VIEW);
        var resp = send({ action: "reset" });
        lastShareText = "";
        applyResponse(resp, { action: "reset" });
        setMessage("Progress erased.");
      });
    });

    // feedback (plain JS, same shape as the other games)
    var answer = null;
    function pick(value) {
      answer = value;
      $("feedback-yes-button").classList.toggle("selected", value === "yes");
      $("feedback-no-button").classList.toggle("selected", value === "no");
      $("feedback-submit-button").disabled = false;
    }
    $("feedback-yes-button").addEventListener("click", function () { pick("yes"); });
    $("feedback-no-button").addEventListener("click", function () { pick("no"); });
    $("feedback-submit-button").addEventListener("click", async function () {
      if (!answer) return;
      var comment = $("feedback-comment").value.trim();
      $("feedback-submit-button").disabled = true;
      try {
        var res = await fetch("https://noyvjgames.fastapicloud.dev/ratings", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ game_slug: GAME, response: comment ? answer + " — " + comment : answer }),
        });
        if (!res.ok) throw new Error("status " + res.status);
        $("feedback-status").textContent = "Thanks for the feedback!";
      } catch (e) {
        $("feedback-status").textContent = "Feedback submission failed, try again.";
        $("feedback-submit-button").disabled = false;
      }
    });

    // day rollover: only checked when the page becomes visible again
    function checkRollover() {
      if (!engineReady || !view || document.hidden) return;
      if (utcToday() !== view.today) {
        var resp = send({ action: "boot" });
        applyResponse(resp, { action: "boot" });
        setMessage("A new UTC day: fresh puzzles are on the air.");
      } else {
        renderResult();
      }
    }
    document.addEventListener("visibilitychange", checkRollover);
    window.addEventListener("focus", checkRollover);

    // kick the engine off on the first sign of interaction, and after first paint
    var kick = function () { startEngine(); };
    document.addEventListener("pointerdown", kick, { once: true });
    document.addEventListener("keydown", kick, { once: true });
  }

  function init() {
    tool = "ping";
    currentState = jsonParse(lsGet(LS_STATE) || "null");
    var cached = loadCachedView();
    cachedValid = isCachedValid(cached);
    view = cached || defaultView();
    if (cached && !cachedValid) {
      setMessage("Tuning in to today's puzzle... (showing your last board)");
    } else if (!cached) {
      setMessage("Tap a tile to ping it. The receiver is warming up in the background.");
    } else {
      setMessage("Welcome back. Your board is shown while the receiver warms up.");
    }
    cursor = { r: Math.floor(view.board.n / 2), c: Math.floor(view.board.n / 2) };
    wire();
    render();
    renderAchievements();
    var d = new Date();
    cal = { y: d.getUTCFullYear(), m: d.getUTCMonth() };
    // Start the engine right after the shell is painted into the DOM. A timer
    // (not requestAnimationFrame) so a tab opened in the background still warms up.
    setTimeout(startEngine, 0);
  }

  window.SignalApp = { timings: timings, act: act, getView: function () { return view; }, startEngine: startEngine };
  window.SignalTimings = timings;

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
