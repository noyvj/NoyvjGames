/* Signal, part 2 of 4: resume state, tabs, board, status, waterfall, result, render(), the calendar, changelog, achievements and stats panels. */
(function () {
  "use strict";

  var A = window.SignalPage;
  var $ = A.$, EPOCH = A.EPOCH, LS_CURSOR = A.LS_CURSOR, LS_TOOL = A.LS_TOOL, MONTHS = A.MONTHS,
      SYMBOL = A.SYMBOL, catalog = A.catalog, el = A.el, label = A.label, lsGet = A.lsGet, lsSet = A.lsSet,
      utcToday = A.utcToday;

  // ---- rendering ---------------------------------------------------------------
  function setMessage(text) { $("message-line").textContent = text || ""; }

  function saveResumeState() {
    if (!A.view || A.view.status !== "inprogress") return;
    lsSet(LS_TOOL, A.tool);
    lsSet(LS_CURSOR, JSON.stringify(A.cursor));
  }

  function restoreResumeState() {
    if (!A.view || A.view.status !== "inprogress") return;
    var savedTool = lsGet(LS_TOOL);
    var savedCursor = lsGet(LS_CURSOR);
    var n = A.view.board.n;
    if (savedTool === "ping" || savedTool === "mark") A.tool = savedTool;
    if (savedCursor) {
      try {
        var c = JSON.parse(savedCursor);
        if (typeof c.r === "number" && typeof c.c === "number" && c.r >= 0 && c.r < n && c.c >= 0 && c.c < n) A.cursor = c;
      } catch (e) {}
    }
    showResumeBanner();
  }

  var resumeBannerEl = null;
  function showResumeBanner() {
    if (resumeBannerEl) return;
    resumeBannerEl = document.createElement("div");
    resumeBannerEl.className = "resume-banner";
    resumeBannerEl.innerHTML = '<span>Resuming your last board</span><button type="button">Dismiss</button>';
    resumeBannerEl.querySelector("button").addEventListener("click", function () {
      resumeBannerEl.classList.remove("visible");
      setTimeout(function () { if (resumeBannerEl) resumeBannerEl.remove(); resumeBannerEl = null; }, 350);
    });
    document.body.appendChild(resumeBannerEl);
    requestAnimationFrame(function () { resumeBannerEl.classList.add("visible"); });
    setTimeout(function () {
      if (resumeBannerEl && resumeBannerEl.parentNode) {
        resumeBannerEl.classList.remove("visible");
        setTimeout(function () { if (resumeBannerEl) resumeBannerEl.remove(); resumeBannerEl = null; }, 350);
      }
    }, 4000);
  }

  function renderTabs() {
    var s = A.view.session;
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
    var b = A.view.board;
    var n = b.n;
    var boardEl = $("board");
    var hadFocus = boardEl.contains(document.activeElement);
    boardEl.style.setProperty("--n", n);
    boardEl.setAttribute("role", "group");
    boardEl.innerHTML = "";
    if (A.cursor.r >= n || A.cursor.c >= n) A.cursor = { r: Math.floor(n / 2), c: Math.floor(n / 2) };
    var pinged = {};
    A.view.pings.forEach(function (p) { pinged[p.r + "," + p.c] = p; });
    var marks = {};
    A.view.marks.forEach(function (m) { marks[m[0] + "," + m[1]] = true; });
    var possible = null;
    if (A.view.possible) {
      possible = {};
      A.view.possible.forEach(function (m) { possible[m[0] + "," + m[1]] = true; });
    }
    var truth = null;
    var guess = null;
    if (A.view.truth) {
      truth = {};
      A.view.truth.forEach(function (m) { truth[m[0] + "," + m[1]] = true; });
      guess = {};
      (A.view.guess || []).forEach(function (m) { guess[m[0] + "," + m[1]] = true; });
    }
    boardEl.appendChild(el("span", "axis"));
    for (var c0 = 0; c0 < n; c0++) boardEl.appendChild(el("span", "axis", String.fromCharCode(65 + c0)));
    for (var r = 0; r < n; r++) {
      boardEl.appendChild(el("span", "axis", String(r + 1)));
      for (var c = 0; c < n; c++) {
        var key = r + "," + c;
        var btn = el("button", "cell");
        // A 9x9 board cannot have 44px cells on a 360px screen; shared/touch-targets.css skips these.
        btn.setAttribute("data-touch-exempt", "");
        btn.type = "button";
        btn.setAttribute("data-r", r);
        btn.setAttribute("data-c", c);
        var ring = r === 0 || c === 0 || r === n - 1 || c === n - 1;
        if (ring) btn.classList.add("ring");
        btn.tabIndex = (r === A.cursor.r && c === A.cursor.c) ? 0 : -1;
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
        } else if (A.pendingCells[key]) {
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
    var node = $("board").querySelector('.cell[data-r="' + A.cursor.r + '"][data-c="' + A.cursor.c + '"]');
    if (node) node.focus();
  }

  function renderStatus() {
    var b = A.view.board;
    var used = b.budget - A.view.pings_left;
    var dots = $("pings-display");
    dots.innerHTML = "";
    for (var i = 0; i < b.budget; i++) dots.appendChild(el("span", i < used ? "used" : "", i < used ? "○" : "●"));
    dots.setAttribute("aria-label", A.view.pings_left + " pings left");
    $("pings-text").textContent = "Pings: " + A.view.pings_left + "/" + b.budget;
    $("par-text").textContent = "Par: " + (b.par === null || b.par === undefined ? "-" : b.par);
    $("marks-text").textContent = "Markers: " + A.view.marks.length + "/" + b.k;
    var finished = A.view.status !== "inprogress";
    $("commit-button").disabled = !A.view.can_commit || !A.engineReady;
    $("give-up-button").disabled = finished || !A.engineReady;
    $("clear-marks-button").disabled = finished || !A.engineReady;
    $("session-line").textContent = A.view.session.label + (A.view.session.type === "daily" || A.view.session.type === "archive" ? "" : "");
    var toggle = $("tool-toggle-button");
    toggle.textContent = "Tool: " + (A.tool === "ping" ? "Ping" : "Mark");
    toggle.setAttribute("aria-pressed", String(A.tool === "mark"));
    var pingBtn = $("mobile-ping-button");
    var markBtn = $("mobile-mark-button");
    if (pingBtn) {
      pingBtn.setAttribute("aria-pressed", String(A.tool === "ping"));
      markBtn.setAttribute("aria-pressed", String(A.tool === "mark"));
    }
    $("warm-line").hidden = A.engineReady;
    if (!A.engineReady) {
      $("warm-line").textContent = "Receiver warming up..." + (A.queue.length ? " " + A.queue.length + " tap" + (A.queue.length === 1 ? "" : "s") + " queued." : "");
    }
    if (A.view.ach) $("achievements-toggle-button").textContent = "🏆 Achievements (" + A.view.ach.earned + "/" + A.view.ach.total + ")";
    $("assist-checkbox").checked = !!A.view.settings.assist_shading;
    $("ascii-checkbox").checked = !!A.view.settings.ascii_share;
    $("streak-checkbox").checked = !!A.view.settings.show_streaks;
    $("assist-checkbox").disabled = !A.view.board.assist;
    var sel = $("practice-preset");
    if (document.activeElement !== sel && A.view.settings.last_preset) sel.value = A.view.settings.last_preset;
  }

  function renderWaterfall() {
    var box = $("waterfall");
    box.innerHTML = "";
    if (!A.view.pings.length) {
      box.appendChild(el("span", "wf-empty", "No readings yet."));
      return;
    }
    A.view.pings.forEach(function (p) {
      var item = el("div", "wf-item");
      item.appendChild(el("span", "wf-glyph", p.glyph));
      item.appendChild(el("span", "", String(p.v)));
      item.appendChild(el("span", "", p.label));
      item.setAttribute("title", p.label + " read " + p.v);
      box.appendChild(item);
    });
  }

  function countdownText() {
    if (!A.view.next_utc) return "";
    var ms = Date.parse(A.view.next_utc + "T00:00:00Z") - Date.now();
    if (!(ms > 0)) return "A new puzzle is on the air.";
    var mins = Math.floor(ms / 60000);
    return "Next daily puzzle in " + Math.floor(mins / 60) + "h " + (mins % 60) + "m (UTC midnight).";
  }

  function renderResult() {
    var panel = $("result-panel");
    var res = A.view.result;
    panel.hidden = !res;
    if (!res) { A.lastShareText = ""; return; }
    $("result-title").textContent = res.won ? "Signal locked." : "Lost the signal.";
    var detail = res.won
      ? res.pings_used + " of " + res.budget + " pings" + (res.under_par ? ", under par (" + res.par + ")" : (res.at_par ? ", at par" : ", par was " + res.par)) + "."
      : "Par was " + res.par + ". The transmitters are shown on the board (◎ missed, ✔ found, ✖ wrong).";
    $("result-detail").textContent = detail;
    $("next-line").textContent = A.view.session.type === "daily" ? countdownText() : "";
    var preview = $("share-preview");
    preview.hidden = !A.lastShareText;
    preview.textContent = A.lastShareText;
  }

  function render() {
    if (!A.view) return;
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
    var days = A.currentState && A.currentState.days;
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
      A.act({ action: "open", date: date, mode: mode });
    });
    return chip;
  }

  function renderCalendar() {
    var grid = $("calendar-grid");
    grid.innerHTML = "";
    ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].forEach(function (d) { grid.appendChild(el("span", "cal-dow", d)); });
    $("cal-title").textContent = MONTHS[A.cal.m] + " " + A.cal.y;
    var first = new Date(Date.UTC(A.cal.y, A.cal.m, 1));
    var days = new Date(Date.UTC(A.cal.y, A.cal.m + 1, 0)).getUTCDate();
    for (var pad = 0; pad < first.getUTCDay(); pad++) grid.appendChild(el("span"));
    var today = utcToday();
    for (var d = 1; d <= days; d++) {
      var date = new Date(Date.UTC(A.cal.y, A.cal.m, d)).toISOString().slice(0, 10);
      var enabled = date >= EPOCH && date <= today;
      var cell = el("div", "cal-day" + (enabled ? "" : " off") + (date === today ? " today" : ""));
      cell.setAttribute("data-date", date);
      var currentMode = (A.view && A.view.session && A.view.session.mode) || "easy";
      cell.setAttribute("data-mode", currentMode);
      var res = dayStatus(date, currentMode);
      if (res !== "none") cell.setAttribute("data-result", res === "inprogress" ? "in-progress" : res);
      cell.appendChild(el("span", "num", String(d)));
      ["easy", "hard"].forEach(function (mode) { cell.appendChild(makeChip(date, d, mode, enabled)); });
      grid.appendChild(cell);
    }
    var prev = new Date(Date.UTC(A.cal.y, A.cal.m - 1, 28)).toISOString().slice(0, 10);
    $("cal-prev-button").disabled = prev < EPOCH.slice(0, 7);
    var nextMonth = new Date(Date.UTC(A.cal.y, A.cal.m + 1, 1)).toISOString().slice(0, 10);
    $("cal-next-button").disabled = nextMonth > today;
  }

  function openArchive() {
    var ref = (A.view && A.view.session.date) || utcToday();
    A.cal = { y: parseInt(ref.slice(0, 4), 10), m: parseInt(ref.slice(5, 7), 10) - 1 };
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
    var earned = A.currentState && A.currentState.earned;
    if (earned) Object.keys(earned).forEach(function (k) { out[k] = earned[k]; });
    var list = A.currentState && A.currentState.achievements_earned;
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
    if (!A.view || !A.view.ach) $("achievements-toggle-button").textContent = "🏆 Achievements (" + count + "/" + catalog.ach.length + ")";
  }

  function renderStats(resp) {
    var panel = $("stats-panel");
    panel.innerHTML = "";
    panel.appendChild(el("h2", "panel-heading", "Stats"));
    if (!resp) {
      panel.appendChild(el("p", "panel-note", "Stats appear once the receiver has warmed up..."));
      return;
    }
    var showStreaks = resp.best_streak !== null && resp.best_streak !== undefined;

    // Quiet streak: total solved (big, never goes down) with streak beside it
    if (resp.total_solved !== undefined) {
      var qs = el("div", "quiet-streak");
      qs.style.fontSize = "2rem";
      qs.style.fontWeight = "bold";
      qs.style.marginBottom = "0.5rem";
      qs.textContent = resp.total_solved + " solved";
      if (showStreaks && resp.best_streak !== null) {
        var streakSpan = el("span", "", " · streak: " + resp.best_streak);
        streakSpan.style.fontSize = "1rem";
        streakSpan.style.fontWeight = "normal";
        qs.appendChild(streakSpan);
      }
      panel.appendChild(qs);
    }

    panel.appendChild(el("p", "panel-note", showStreaks
      ? "Longest daily streak (any mode): " + resp.best_streak + " day(s). Daily streaks count wins on the daily puzzle only."
      : "Daily streaks are off, so missing a day costs nothing. You can switch them on in Settings."));
    Object.keys(resp.stats).forEach(function (mode) {
      var s = resp.stats[mode];
      var block = el("div", "stat-block");
      block.appendChild(el("strong", "", s.label + (s.daily_mode ? "" : " (practice only)")));
      if (s.daily) {
        var d = s.daily;
        var grid = el("div", "stat-grid");
        [["Played", d.played], ["Win %", d.played ? Math.round(100 * d.won / d.played) : 0]].concat(showStreaks ? [["Streak", d.streak], ["Best", d.best_streak]] : []).forEach(function (pair) {
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

  // what the other parts use (see the File map in CLAUDE.md)
  A.focusCursor = focusCursor; A.openArchive = openArchive; A.render = render;
  A.renderAchievements = renderAchievements; A.renderBoard = renderBoard; A.renderCalendar = renderCalendar;
  A.renderChangelog = renderChangelog; A.renderResult = renderResult; A.renderStats = renderStats;
  A.renderStatus = renderStatus; A.renderTabs = renderTabs; A.restoreResumeState = restoreResumeState;
  A.saveResumeState = saveResumeState; A.setMessage = setMessage;
})();
