/* Pocket Bazaar -- the Daily Market on the closed-stall card: today's market, a month calendar of past dates (any
   past date can be played) and a tally grid. Glue only: the engine's view (view.market) holds the dates, the
   results and the counts. The ONLY clock read in the game is `today()` below, which tells the engine which
   date's market to build; nothing here counts time, nothing expires and nothing is streaked.
   Loaded before app.js, which calls PocketBazaarMarket.render(view, send) on every redraw. */
(function () {
  "use strict";
  var MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  var STARS = ["", "★", "★★", "★★★"];
  var cal = null;                                 // {y, m} of the month on show
  var lastSend = null;
  var lastM = null;                               // the market part of the latest view

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

  /* HOOK for the future opt-in market leaderboard (a separate backend job, NOT built in this pass). When a result is
     on the closed card, the entry a board would take is passed here. Assign PocketBazaarMarket.leaderboardHook. */
  var api = { today: today, render: render, leaderboardHook: null };
  window.PocketBazaarMarket = api;

  function stars(n) { return STARS[n] || ""; }

  function renderToday(m) {
    var line = $("market-today");
    if (!m.open) { setText(line, "The first Daily Market opens on " + m.epoch + "."); return; }
    var text = "Market " + m.number + " (" + m.today + "): " + m.festival.name + ", " + m.customers + " customers. ";
    text += m.record ? "You have played it: " + stars(m.record.stars) + " (" + m.record.stars + " of 3 stars), " + m.record.served + " of " + m.record.total + " served." : "Not played yet.";
    setText(line, text);
    $("market-today-button").disabled = false;
  }

  function renderResult(m) {
    var box = $("market-result");
    var r = m.result;
    box.hidden = !r;
    if (!r) return;
    var sig = JSON.stringify(r);
    if (box.dataset.sig === sig) return;
    box.dataset.sig = sig;
    box.textContent = "";
    box.appendChild(el("h4", null, "Market " + r.date + " is done: " + stars(r.stars) + " (" + r.stars + " of 3 stars)"));
    box.appendChild(el("p", null, "Served " + r.served + " of " + r.total + ", " + r.left + " left unserved, " + r.coins + " coins taken at the stall, " + r.beats + " beats, longest chain " + r.best_chain + "."));
    box.appendChild(el("p", "note", (r.improved ? "That is your best for this date. " : "Your best for this date stays " + stars(r.best.stars) + ", " + r.best.served + " of " + r.best.total + " served. ") + "Nothing from this market was added to your stall; play it again or any other date whenever you like."));
  }

  function renderCalendar(m) {
    var grid = $("market-calendar");
    var sig = JSON.stringify([cal, m.days, m.today]);
    if (grid.dataset.sig === sig) return;
    grid.dataset.sig = sig;
    grid.textContent = "";
    ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].forEach(function (d) {
      var h = el("span", "market-dow", d);
      h.setAttribute("aria-hidden", "true");
      grid.appendChild(h);
    });
    setText($("market-cal-title"), MONTHS[cal.m] + " " + cal.y);
    var first = new Date(Date.UTC(cal.y, cal.m, 1)).getUTCDay();
    var count = new Date(Date.UTC(cal.y, cal.m + 1, 0)).getUTCDate();
    for (var pad = 0; pad < first; pad++) { var gap = el("span"); gap.setAttribute("aria-hidden", "true"); grid.appendChild(gap); }
    for (var d = 1; d <= count; d++) {
      (function (day) {
        var date = iso(cal.y, cal.m, day);
        var open = date >= m.epoch && date <= m.today;
        var rec = m.days[date];
        var word = rec ? rec.stars + " of 3 stars" : (open ? "not played" : "not open");
        var btn = el("button", "market-day" + (date === m.today ? " today" : ""));
        btn.type = "button";
        btn.disabled = !open;
        btn.dataset.date = date;
        btn.setAttribute("data-testid", "pocket-bazaar-market-day");
        btn.setAttribute("aria-label", MONTHS[cal.m] + " " + day + ": " + word + (date === m.today ? " (today)" : ""));
        btn.appendChild(el("span", "num", String(day)));
        var mark = el("span", "mark", rec ? stars(rec.stars) : (open ? "." : ""));
        mark.setAttribute("aria-hidden", "true");
        btn.appendChild(mark);
        btn.addEventListener("click", function () { if (lastSend) lastSend({ action: "start_market", date: date }); });
        grid.appendChild(btn);
      })(d);
    }
    var prevMonth = iso(cal.y, cal.m - 1, 28).slice(0, 7);
    $("market-cal-prev").disabled = prevMonth < m.epoch.slice(0, 7);
    $("market-cal-next").disabled = iso(cal.y, cal.m + 1, 1) > m.today;
  }

  // The bigger picture: one small square per open day, the newest 120; the sentence above it is the real answer.
  function renderGrid(m) {
    var box = $("market-grid");
    var t = m.tally;
    setText($("market-tally"), t.open ? "Played " + t.played + " of " + t.open + " open days (" + t.perfect + " with three stars). Skipped days cost nothing." : "");
    var sig = JSON.stringify([m.days, m.today, m.epoch]);
    if (box.dataset.sig === sig) return;
    box.dataset.sig = sig;
    box.textContent = "";
    box.setAttribute("aria-label", t.open ? "Grid of the open days: " + t.played + " played of " + t.open : "No open days yet");
    if (!t.open) return;
    var days = Math.min(t.open, 120);
    for (var i = days - 1; i >= 0; i--) {
      var date = new Date(Date.parse(m.today + "T00:00:00Z") - i * 86400000).toISOString().slice(0, 10);
      var rec = m.days[date];
      var cell = el("span", "market-cell" + (rec ? " done" : ""), rec ? String(rec.stars) : "");
      cell.title = date + (rec ? ": " + rec.stars + " of 3 stars" : ": not played");
      box.appendChild(cell);
    }
  }

  function render(view, send) {
    lastSend = send;
    var m = view.market;
    lastM = m;
    var panel = $("market-panel");
    var active = !!(m && m.active);
    var label = $("stat-day").previousElementSibling;
    if (label) setText(label, active ? "Market" : "Day");
    var banner = $("market-open-banner");
    banner.hidden = !active;
    if (active) setText(banner, "Daily Market " + view.day.number + " (" + m.active + "): a plain stall with no upgrades. Nothing from this market is added to your coins, renown or tally.");
    if (view.phase !== "closed" || !m) { panel.hidden = true; return; }
    panel.hidden = false;
    if (!cal) cal = { y: parseInt(m.today.slice(0, 4), 10), m: parseInt(m.today.slice(5, 7), 10) - 1 };
    renderToday(m);
    renderResult(m);
    renderGrid(m);
    if (m.result) {                                  // the market result replaces the campaign day's summary
      $("summary").hidden = true;
      setText($("closed-heading"), "The Daily Market is done");
    }
    if (!$("market-archive").hidden) renderCalendar(m);
    if (m.result && m.entry && typeof api.leaderboardHook === "function") {
      try { api.leaderboardHook(m.entry); } catch (e) { /* a hook must never break the page */ }
    }
  }

  function wire() {
    $("market-today-button").addEventListener("click", function () {
      var m = lastM;
      if (lastSend) lastSend({ action: "start_market", date: m && m.today ? m.today : today() });
    });
    $("market-archive-button").addEventListener("click", function () {
      var box = $("market-archive");
      box.hidden = !box.hidden;
      $("market-archive-button").setAttribute("aria-expanded", String(!box.hidden));
      var m = lastM;
      if (m && m.today) cal = { y: parseInt(m.today.slice(0, 4), 10), m: parseInt(m.today.slice(5, 7), 10) - 1 };
      if (!box.hidden && m) renderCalendar(m);
    });
    function step(n) {
      var moved = new Date(Date.UTC(cal.y, cal.m + n, 1));
      cal = { y: moved.getUTCFullYear(), m: moved.getUTCMonth() };
      var m = lastM;
      if (m) renderCalendar(m);
    }
    $("market-cal-prev").addEventListener("click", function () { step(-1); });
    $("market-cal-next").addEventListener("click", function () { step(1); });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire); else wire();
})();
