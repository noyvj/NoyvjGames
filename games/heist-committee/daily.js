/* Heist Committee -- the Daily Job on the contract board: today's job, a month calendar of past dates (any past
   date can be played) and a tally grid. Glue only: the engine's board view (view.daily_board) holds the dates,
   the results and the counts. There is no streak counter anywhere. Needs app.js (window.HC). */
(function () {
  "use strict";
  var HC = window.HC, $ = HC.$, el = HC.el;
  var MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  var SYMBOL = ["o", "v", "*", "**"];            // busted, escaped, clean, par
  var cal = null;                                  // {y, m} of the month on show

  /* HOOK for the future daily leaderboard (a separate backend job, NOT built in this pass). When a daily result
     is on screen, the entry a board would take is passed here. Define HC.dailyLeaderboardHook to receive it. */
  HC.dailyLeaderboardHook = HC.dailyLeaderboardHook || null;

  function iso(y, m, d) { return new Date(Date.UTC(y, m, d)).toISOString().slice(0, 10); }

  function renderToday(b) {
    var box = $("daily-today");
    var sig = JSON.stringify([b.today, b.open, b.number, b.record, b.target && b.target.id]);
    HC.fillOnce(box, sig, function (root) {
      if (!b.open) {
        root.appendChild(el("p", { text: "The first Daily Job opens on " + b.epoch + "." }));
        return;
      }
      root.appendChild(el("p", { "class": "daily-line" }, [el("strong", { text: "Day " + b.number + ": " + b.target.name }),
        " (" + b.target.beats + " beats). " + (b.record ? "You have played it: " + b.tiers[b.record.tier].label + ", best payout " + b.record.net + "." : "Not played yet.")]));
    });
    $("daily-today-button").disabled = !b.open;
  }

  function renderCalendar(b) {
    var grid = $("daily-calendar");
    var sig = JSON.stringify([cal, b.days, b.today]);
    HC.fillOnce(grid, sig, function (root) {
      ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].forEach(function (d) { root.appendChild(el("span", { "class": "daily-dow", "aria-hidden": "true", text: d })); });
      $("daily-cal-title").textContent = MONTHS[cal.m] + " " + cal.y;
      var first = new Date(Date.UTC(cal.y, cal.m, 1)).getUTCDay();
      var count = new Date(Date.UTC(cal.y, cal.m + 1, 0)).getUTCDate();
      for (var pad = 0; pad < first; pad++) root.appendChild(el("span", { "aria-hidden": "true" }));
      for (var d = 1; d <= count; d++) {
        (function (day) {
          var date = iso(cal.y, cal.m, day);
          var open = date >= b.epoch && date <= b.today;
          var rec = b.days[date];
          var word = rec ? b.tiers[rec.tier].label : (open ? "not played" : "not open");
          var btn = el("button", { type: "button", "class": "daily-day" + (date === b.today ? " today" : ""), disabled: open ? null : true,
            "data-date": date, "data-testid": "heist-daily-day",
            "aria-label": MONTHS[cal.m] + " " + day + ": " + word + (date === b.today ? " (today)" : ""),
            onclick: function () { HC.send({ action: "daily_open", date: date }); } },
          [el("span", { "class": "num", text: String(day) }), el("span", { "class": "mark", "aria-hidden": "true", text: rec ? SYMBOL[rec.tier] : (open ? "." : "") })]);
          root.appendChild(btn);
        })(d);
      }
    });
    var prevMonth = iso(cal.y, cal.m - 1, 28).slice(0, 7);
    $("daily-cal-prev").disabled = prevMonth < b.epoch.slice(0, 7);
    $("daily-cal-next").disabled = iso(cal.y, cal.m + 1, 1) > b.today;
  }

  // The bigger picture: one small square per open day, oldest first, newest 120 days; the text line is the real answer.
  function renderGrid(b) {
    var box = $("daily-grid");
    var t = b.tally;
    $("daily-tally").textContent = t.open ? "Played " + t.played + " of " + t.open + " open days (" + t.clean + " with a clean getaway). Skipped days cost nothing." : "";
    HC.fillOnce(box, JSON.stringify([b.days, b.today, b.epoch]), function (root) {
      box.setAttribute("aria-label", t.open ? "Grid of the open days: " + t.played + " played of " + t.open : "No open days yet");
      if (!t.open) return;
      var days = Math.min(t.open, 120);
      for (var i = days - 1; i >= 0; i--) {
        var date = new Date(Date.parse(b.today + "T00:00:00Z") - i * 86400000).toISOString().slice(0, 10);
        var rec = b.days[date];
        root.appendChild(el("span", { "class": "daily-cell" + (rec ? " done tier-" + rec.tier : ""), title: date + (rec ? ": " + b.tiers[rec.tier].label : ": not played"),
          text: rec ? SYMBOL[rec.tier].charAt(0) : "" }));
      }
    });
  }

  function render(view) {
    var b = view.daily_board;
    var panel = $("daily-panel");
    panel.hidden = !b || view.phase !== "board";
    if (!b) return;
    if (!cal) cal = { y: parseInt(b.today.slice(0, 4), 10), m: parseInt(b.today.slice(5, 7), 10) - 1 };
    renderToday(b);
    renderGrid(b);
    if (!$("daily-archive").hidden) renderCalendar(b);
  }

  function wire() {
    $("daily-today-button").addEventListener("click", function () {
      var b = HC.view && HC.view.daily_board;
      if (b && b.open) HC.send({ action: "daily_open", date: b.today });
    });
    $("daily-archive-button").addEventListener("click", function () {
      var box = $("daily-archive");
      box.hidden = !box.hidden;
      $("daily-archive-button").setAttribute("aria-expanded", String(!box.hidden));
      if (HC.view && HC.view.daily_board) {
        var b = HC.view.daily_board;
        cal = { y: parseInt(b.today.slice(0, 4), 10), m: parseInt(b.today.slice(5, 7), 10) - 1 };
        if (!box.hidden) renderCalendar(b);
      }
    });
    function step(n) {
      var moved = new Date(Date.UTC(cal.y, cal.m + n, 1));
      cal = { y: moved.getUTCFullYear(), m: moved.getUTCMonth() };
      if (HC.view && HC.view.daily_board) renderCalendar(HC.view.daily_board);
    }
    $("daily-cal-prev").addEventListener("click", function () { step(-1); });
    $("daily-cal-next").addEventListener("click", function () { step(1); });
  }

  HC.onRender.push(function (view) {
    render(view);
    // In a daily the abandon button says what it really does (nothing is lost).
    var ab = $("abandon-button");
    if (ab) ab.textContent = view.daily ? "Set the daily job aside" : "Abandon job";
    if (view.phase === "payout" && view.daily && view.daily.leaderboard && typeof HC.dailyLeaderboardHook === "function") {
      try { HC.dailyLeaderboardHook(view.daily.leaderboard); } catch (e) { /* a hook must never break the page */ }
    }
  });
  wire();
})();
