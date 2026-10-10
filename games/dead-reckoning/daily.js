/* Dead Reckoning -- the Daily Chart panel: today's chart, a month calendar of past dates (any past date can be played)
   and a tally grid. Glue only: the engine's view (view.daily) holds the dates, the results and the counts. The ONLY
   clock read in the game is `today()` below, which tells the engine which date's chart to make; nothing here counts
   time, nothing expires and nothing is streaked. Loaded before app.js, which calls DeadReckoningDaily.render(). */
(function () {
  "use strict";
  var MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  var STARS = ["", "★", "★★", "★★★"];
  var cal = null;
  var lastSend = null, lastView = null, lastOpened = null;

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  }
  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }
  function iso(y, m, d) { return new Date(Date.UTC(y, m, d)).toISOString().slice(0, 10); }
  function today() { return new Date().toISOString().slice(0, 10); }

  /* HOOK for the future opt-in daily leaderboard (a separate backend job, NOT built in this pass). When a daily
     result is on screen, the entry a board would take is passed here. Assign DeadReckoningDaily.leaderboardHook. */
  var api = { today: today, render: render, leaderboardHook: null };
  window.DeadReckoningDaily = api;

  function open(date) {
    var go = function () {
      if (lastOpened) lastOpened();
      lastSend({ action: "start_daily", date: date });
      $("daily-panel").hidden = true;
      $("daily-toggle-button").setAttribute("aria-expanded", "false");
    };
    var v = lastView;
    if (v && v.phase === "plan" && v.legs.length && v.chart.id !== "daily-" + date && window.ConfirmDialog) {
      window.ConfirmDialog.ask({ id: "dead-reckoning-switch-chart", message: "Leave this chart? The plan you have here will be lost.", confirmLabel: "Open the daily chart", onConfirm: go });
    } else go();
  }

  function renderToday(d) {
    var line = $("daily-today");
    if (!d.open) { setText(line, "The first Daily Chart opens on " + d.epoch + "."); $("daily-today-button").disabled = true; return; }
    $("daily-today-button").disabled = false;
    var text = "Chart " + d.number + " (" + d.today + "): level " + d.level.difficulty + ", " + d.level.name + ". ";
    text += d.record ? "You have played it: " + d.record.stars + " of 3 stars." : "Not played yet.";
    setText(line, text);
  }

  function renderCalendar(d) {
    var grid = $("daily-calendar");
    var sig = JSON.stringify([cal, d.days, d.today]);
    if (grid.dataset.sig === sig) return;
    grid.dataset.sig = sig;
    grid.textContent = "";
    ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].forEach(function (name) {
      var h = el("span", "daily-dow", name);
      h.setAttribute("aria-hidden", "true");
      grid.appendChild(h);
    });
    setText($("daily-cal-title"), MONTHS[cal.m] + " " + cal.y);
    var first = new Date(Date.UTC(cal.y, cal.m, 1)).getUTCDay();
    var count = new Date(Date.UTC(cal.y, cal.m + 1, 0)).getUTCDate();
    for (var pad = 0; pad < first; pad++) { var gap = el("span"); gap.setAttribute("aria-hidden", "true"); grid.appendChild(gap); }
    for (var n = 1; n <= count; n++) {
      (function (day) {
        var date = iso(cal.y, cal.m, day);
        var isOpen = date >= d.epoch && date <= d.today;
        var rec = d.days[date];
        var word = rec ? rec.stars + " of 3 stars" : (isOpen ? "not played" : "not open");
        var btn = el("button", "daily-day" + (date === d.today ? " today" : ""));
        btn.type = "button";
        btn.disabled = !isOpen;
        btn.dataset.date = date;
        btn.setAttribute("data-testid", "dead-reckoning-daily-day");
        btn.setAttribute("aria-label", MONTHS[cal.m] + " " + day + ": " + word + (date === d.today ? " (today)" : ""));
        btn.appendChild(el("span", "num", String(day)));
        var mark = el("span", "mark", rec ? (STARS[rec.stars] || "·") : (isOpen ? "." : ""));
        mark.setAttribute("aria-hidden", "true");
        btn.appendChild(mark);
        btn.addEventListener("click", function () { open(date); });
        grid.appendChild(btn);
      })(n);
    }
    $("daily-cal-prev").disabled = iso(cal.y, cal.m - 1, 28).slice(0, 7) < d.epoch.slice(0, 7);
    $("daily-cal-next").disabled = iso(cal.y, cal.m + 1, 1) > d.today;
  }

  // The bigger picture: one small square per open day, the newest 120; the sentence above it is the real answer.
  function renderGrid(d) {
    var box = $("daily-grid");
    var t = d.tally;
    setText($("daily-tally"), t.open ? "Played " + t.played + " of " + t.open + " open days (" + t.three + " with three stars). Skipped days cost nothing." : "");
    var sig = JSON.stringify([d.days, d.today, d.epoch]);
    if (box.dataset.sig === sig) return;
    box.dataset.sig = sig;
    box.textContent = "";
    box.setAttribute("aria-label", t.open ? "Grid of the open days: " + t.played + " played of " + t.open : "No open days yet");
    if (!t.open) return;
    var days = Math.min(t.open, 120);
    for (var i = days - 1; i >= 0; i--) {
      var date = new Date(Date.parse(d.today + "T00:00:00Z") - i * 86400000).toISOString().slice(0, 10);
      var rec = d.days[date];
      var cell = el("span", "daily-cell" + (rec ? " done" : ""), rec ? String(rec.stars) : "");
      cell.title = date + (rec ? ": " + rec.stars + " of 3 stars" : ": not played");
      box.appendChild(cell);
    }
  }

  function render(view, send, onOpened) {
    lastSend = send;
    lastView = view;
    lastOpened = onOpened;
    var d = view.daily;
    var line = $("daily-line");
    var info = view.chart.daily;
    line.hidden = !info;
    if (info) setText(line, "Daily Chart " + info.number + " (" + info.date + "), level " + info.difficulty + ", " + info.name + ". The same sea for everyone that day; nothing here changes your campaign stars or practice total.");
    if (!d) { $("daily-panel").hidden = true; return; }
    if (!cal) cal = { y: parseInt(d.today.slice(0, 4), 10), m: parseInt(d.today.slice(5, 7), 10) - 1 };
    renderToday(d);
    renderGrid(d);
    if (!$("daily-archive").hidden) renderCalendar(d);
    if (view.phase === "reveal" && d.entry && typeof api.leaderboardHook === "function") {
      try { api.leaderboardHook(d.entry); } catch (e) { /* a hook must never break the page */ }
    }
  }

  function wire() {
    $("daily-today-button").addEventListener("click", function () {
      var d = lastView && lastView.daily;
      if (d && d.open) open(d.today);
    });
    $("daily-archive-button").addEventListener("click", function () {
      var box = $("daily-archive");
      box.hidden = !box.hidden;
      $("daily-archive-button").setAttribute("aria-expanded", String(!box.hidden));
      var d = lastView && lastView.daily;
      if (d) cal = { y: parseInt(d.today.slice(0, 4), 10), m: parseInt(d.today.slice(5, 7), 10) - 1 };
      if (!box.hidden && d) renderCalendar(d);
    });
    function step(n) {
      var moved = new Date(Date.UTC(cal.y, cal.m + n, 1));
      cal = { y: moved.getUTCFullYear(), m: moved.getUTCMonth() };
      if (lastView && lastView.daily) renderCalendar(lastView.daily);
    }
    $("daily-cal-prev").addEventListener("click", function () { step(-1); });
    $("daily-cal-next").addEventListener("click", function () { step(1); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire); else wire();
})();
