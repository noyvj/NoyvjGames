/* Constellations view: glue only. The engine (game.py and its modules) holds every rule; this file draws what handle() returns as an SVG
   sky, turns pointer, touch and keyboard input into `toggle` requests, and shows the charts, the atlas and its cards. It never decides
   whether a number holds or the chart is finished: it asks the engine, and draws the answer.

   The page script is cut into four classic scripts that share ONE object, window.ConstellationsApp (see the File map in
   CLAUDE.md). They load in this order and each is wrapped in its own function, so no new global names exist:
     app-1-core.js     constants, shared state, helpers, panels, the stats, persist(), send(), neighbourChart(), askThen()
     app-2-board.js    the chart head, the SVG board, pointer input, the keyboard ring, zoom
     app-3-panels.js   the suggestion ladder, goals and difficulty, achievements, the charts panel, atlas and cards,
                       About (with the live reads) and What's New
     app.js            the tutorial steps, render(), wire() and boot() (loads last)
   State that more than one part reads or writes lives on the object: A.engine, A.view, A.boardId, A.cursor, A.showCursor,
   A.held, A.stroke, A.ghostFrom, A.allowed, A.atlasSig, A.cardsSig, A.chartsSig, A.foundShown, A.goalsPanel, A.zoomIdx,
   A.knownEarned (null until the first view, so loading a game or a save never fires a toast), A.achText. Functions another
   part calls are exported as A.name at the end of their own part. */
(function () {
  "use strict";

  var A = window.ConstellationsApp = {};
  A.engine = null;
  A.view = null;
  A.boardId = null;
  A.cursor = 0;
  A.showCursor = false;
  A.held = null;
  A.stroke = null;
  A.ghostFrom = null;
  A.allowed = {};
  A.atlasSig = "";
  A.cardsSig = "";
  A.chartsSig = "";
  A.foundShown = "";
  A.goalsPanel = null;
  A.zoomIdx = 0;
  A.knownEarned = null;
  A.achText = "";

  var ENGINE_MODULES = ["sky.py", "charts_s1.py", "charts_s2.py", "charts_s3.py", "charts_s4.py", "charts_s5.py", "charts.py", "hints.py", "goals.py", "achievements.py", "info.py"];
  var STORE_KEY = "constellations:state";
  var BACKUP_KEY = "constellations:state-backup";
  var SVG_NS = "http://www.w3.org/2000/svg";
  var BADGE = 28;              // radius of a numbered star's badge, in chart units (a chart is 1000 units wide)
  var STAR_HIT = 54;           // a press within this many units of a star is a press on that star
  var GRID = 100;

  var $ = function (id) { return document.getElementById(id); };

  var ZOOMS = [1, 1.5, 2, 3];  // board sizes (1 = fit the screen; larger ones scroll sideways)

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
  function pairKey(a, b) { return a < b ? a + "-" + b : b + "-" + a; }

  // ---- panels --------------------------------------------------------------------------------------
  function setPanel(panelId, buttonId, open) {
    $(panelId).hidden = !open;
    $(buttonId).setAttribute("aria-expanded", String(open));
  }
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () { setPanel(panelId, buttonId, $(panelId).hidden); });
  }

  // ---- the stats -------------------------------------------------------------------------------------
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
    var t = A.view.totals;
    bumpStat("stat-done", t.done + "/" + t.charts);
    bumpStat("stat-stars", t.stars);
    bumpStat("stat-pages", t.pages_open + "/" + t.pages);
    bumpStat("stat-seasons", t.seasons_done + "/" + t.pages);
    bumpStat("stat-lines", t.lines);
    bumpStat("stat-hints", t.hints);
  }

  // ---- talking to the engine --------------------------------------------------------------------------
  function persist() {
    try {
      var proxy = A.engine.getState();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(STORE_KEY, JSON.stringify(obj));
    } catch (e) { /* the save widget keeps the real copy */ }
  }
  function send(request) {
    if (!A.engine) return null;
    var previous = A.view;
    var reply;
    A.achText = "";
    try { reply = JSON.parse(A.engine.handle(JSON.stringify(request))); } catch (err) { showToast("Something went wrong. Reload to try again."); return null; }
    if (reply.error) { showToast(reply.error); return null; }
    A.view = reply;
    A.render();
    showToast((A.view.message || "") + (A.achText ? (A.view.message ? " " : "") + A.achText : ""));
    var extra = A.achText ? " " + A.achText : "";
    if (request.action === "pick" || request.action === "next") {
      var c = A.view.chart;
      announce("Chart " + c.number + " of " + c.of + " in " + c.season + ", " + plural(c.stars.length, "star", "stars") + ". " + (c.status === "solved" ? c.name + ", already in your atlas." : A.view.problems) + extra);
    } else if (A.view.message && request.action === "finish" && A.view.just) {
      announce(A.view.message + extra);
    } else if (A.view.say) {
      announce(A.view.say + extra);
    } else if (A.achText) {
      announce(A.achText);
    }
    if (A.view.just && (!previous || !previous.just || previous.just.id !== A.view.just.id)) {
      if ($("done-card").scrollIntoView) $("done-card").scrollIntoView({ block: "nearest" });
    }
    persist();
    return A.view;
  }

  function neighbourChart(delta) {
    var list = A.allCharts().filter(function (c) { return c.open; });
    var idx = list.findIndex(function (c) { return c.current; });
    var target = list[idx + delta];
    if (target) send({ action: "pick", chart: target.id });
  }
  function askThen(id, message, confirmLabel, go) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: false, onConfirm: go });
    else go();
  }

  // what the other parts use
  A.$ = $;
  A.announce = announce;
  A.askThen = askThen;
  A.BACKUP_KEY = BACKUP_KEY;
  A.BADGE = BADGE;
  A.el = el;
  A.ENGINE_MODULES = ENGINE_MODULES;
  A.GRID = GRID;
  A.lsGet = lsGet;
  A.lsSet = lsSet;
  A.neighbourChart = neighbourChart;
  A.pairKey = pairKey;
  A.plural = plural;
  A.renderStats = renderStats;
  A.send = send;
  A.setPanel = setPanel;
  A.setText = setText;
  A.showToast = showToast;
  A.STAR_HIT = STAR_HIT;
  A.STORE_KEY = STORE_KEY;
  A.svgEl = svgEl;
  A.wirePanelToggle = wirePanelToggle;
  A.ZOOMS = ZOOMS;
})();
