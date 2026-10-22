/* Constellations, part 4 of 4 (loads last): the tutorial steps, render(), wire() and boot(). */
(function () {
  "use strict";

  var A = window.ConstellationsApp;
  var $ = A.$, applyZoom = A.applyZoom, askThen = A.askThen, BACKUP_KEY = A.BACKUP_KEY, drawBoard = A.drawBoard,
      ENGINE_MODULES = A.ENGINE_MODULES, loadChangelog = A.loadChangelog, loadLiveInfo = A.loadLiveInfo,
      loadLiveLines = A.loadLiveLines, lsGet = A.lsGet, lsSet = A.lsSet, neighbourChart = A.neighbourChart,
      onBoardKey = A.onBoardKey, onPointerCancel = A.onPointerCancel, onPointerDown = A.onPointerDown,
      onPointerMove = A.onPointerMove, onPointerUp = A.onPointerUp, pairKey = A.pairKey, pressHint = A.pressHint,
      renderAchievements = A.renderAchievements, renderAtlas = A.renderAtlas, renderCards = A.renderCards,
      renderChartHead = A.renderChartHead, renderCursorLine = A.renderCursorLine, renderHints = A.renderHints,
      renderInfo = A.renderInfo, renderSeasons = A.renderSeasons, renderStats = A.renderStats, send = A.send,
      sendDifficulty = A.sendDifficulty, setPanel = A.setPanel, setZoom = A.setZoom, showToast = A.showToast,
      STORE_KEY = A.STORE_KEY, wireDifficulty = A.wireDifficulty, wireGoals = A.wireGoals,
      wirePanelToggle = A.wirePanelToggle, ZOOMS = A.ZOOMS;

  // ---- the tutorial (shared/tutorial.js; offered from the opening screen, restartable from the toolbar) ------------
  var TUTORIAL_STEPS = [
    { title: "Welcome to the observatory", text: "Each chart is a patch of real sky. You join the stars with lines until the shape that appears is a constellation, and it is kept in your Sky Atlas. Nothing is timed, nothing can go wrong, and you can skip this tour at any time." },
    { selector: "#board", title: "Reading the numbers", text: "A number on a star says how many lines must touch it. A star with no number can have any number of lines, or none. Lines may not cross, and all the lines together must make one connected shape. A number that holds gets a double ring and a tick." },
    { selector: "#board", title: "Drawing a line", text: "Drag from one star to another, or tap one star and then the next. Press the same two stars again to take the line away. A thick double line is already drawn for you; a pair with a cross through it can never be joined." },
    { selector: ".tools", title: "Undo and Done", text: "Undo, Redo and Erase my lines are always there. When every number holds and the lines make one piece, Done adds the constellation to your atlas." },
    { selector: "#hint-box", title: "Stuck? Ask", text: "The suggestion button never opens by itself. A nudge says which star has a certain line, a hint shows the line and why it is certain, and the last rung shows the whole shape. Every chart can be finished without guessing." },
    { selector: "#charts-toggle-button", title: "Charts and seasons", text: "Charts come in five seasons of eight. Five finished charts in a season open the next page, and inside a season you can play the charts in any order. A chart shows its name only once you have finished it." },
    { selector: "#atlas-toggle-button", title: "The Sky Atlas", text: "Every constellation you find is drawn here at its real place in the sky, with a card that has its note, its brightest star and its sources." },
    { selector: "#settings-toggle-button", title: "Settings and difficulty", text: "Star letters, text size, reduced motion, effects, high contrast and the light theme are in Settings. Difficulty (Easy, Normal, Hard) changes only how the suggestions open. On a small screen the + button under the chart makes the board larger." },
    { title: "That is all", text: "Press ? at any time for the keyboard help. The Tutorial button in the toolbar brings this tour back." }
  ];

  // ---- render ---------------------------------------------------------------------------------------
  function render() {
    var c = A.view.chart;
    A.allowed = {};
    c.allowed.forEach(function (pair) { A.allowed[pairKey(pair[0], pair[1])] = true; });
    if (c.id !== A.boardId) {
      A.boardId = c.id;
      A.cursor = 0;
      A.held = null;
      A.stroke = null;
      A.ghostFrom = null;
      A.atlasSig = "";                                       // the atlas marks the current chart
    }
    if (A.view.just && A.foundShown !== A.view.just.id + ":" + A.view.totals.done) A.foundShown = A.view.just.id + ":" + A.view.totals.done;
    renderStats();
    renderChartHead();
    drawBoard();
    renderCursorLine();
    renderSeasons();
    renderAtlas();
    renderCards();
    renderInfo();
    renderHints();
    renderAchievements();
    if (A.goalsPanel) A.goalsPanel.refresh();
  }

  function wire() {
    $("toast").addEventListener("click", function () { showToast(""); });
    var board = $("board");
    board.addEventListener("pointerdown", onPointerDown);
    board.addEventListener("pointermove", onPointerMove);
    board.addEventListener("pointerup", onPointerUp);
    board.addEventListener("pointercancel", onPointerCancel);
    board.addEventListener("keydown", onBoardKey);
    board.addEventListener("focus", function () { if (A.view && !A.stroke && document.activeElement === board && A.showCursor) drawBoard(); });
    board.addEventListener("blur", function () { A.showCursor = false; if (A.view) { drawBoard(); renderCursorLine(); } });
    $("undo-button").addEventListener("click", function () { send({ action: "undo" }); });
    $("redo-button").addEventListener("click", function () { send({ action: "redo" }); });
    $("clear-button").addEventListener("click", function () { A.held = null; send({ action: "clear" }); });
    $("done-button").addEventListener("click", function () { send({ action: "finish" }); });
    $("prev-chart-button").addEventListener("click", function () { neighbourChart(-1); });
    $("next-chart-button").addEventListener("click", function () { send({ action: "next" }); });
    $("done-next-button").addEventListener("click", function () { send({ action: "next" }); $("board").focus({ preventScroll: true }); });
    $("done-atlas-button").addEventListener("click", function () {
      setPanel("atlas-panel", "atlas-toggle-button", true);
      if ($("atlas-panel").scrollIntoView) $("atlas-panel").scrollIntoView({ block: "start" });
    });
    wirePanelToggle("charts-toggle-button", "charts-panel");
    wirePanelToggle("atlas-toggle-button", "atlas-panel");
    wirePanelToggle("achievements-toggle-button", "achievements-panel");
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    $("info-page-toggle-button").addEventListener("click", function () { if (!$("info-page-panel").hidden) { loadLiveInfo(); loadLiveLines(); } });
    $("hint-button").addEventListener("click", function () { pressHint(false); });
    $("hint-draw-button").addEventListener("click", function () { send({ action: "hint_draw" }); $("board").focus({ preventScroll: true }); });
    $("hints-checkbox").addEventListener("change", function () { lsSet("constellations:hints-hidden", $("hints-checkbox").checked ? "0" : "1"); if (A.view) renderHints(); });
    $("zoom-in-button").addEventListener("click", function () { setZoom(A.zoomIdx + 1); });
    $("zoom-out-button").addEventListener("click", function () { setZoom(A.zoomIdx - 1); });
    $("zoom-reset-button").addEventListener("click", function () { setZoom(0); });
    var savedZoom = parseInt(lsGet("constellations:zoom"), 10);
    A.zoomIdx = savedZoom >= 0 && savedZoom < ZOOMS.length ? savedZoom : 0;
    applyZoom();
    wireDifficulty();
    wireGoals();
    $("reset-button").addEventListener("click", function () {
      askThen("constellations-reset", "Start the whole atlas over? Every constellation will be taken out of the atlas and your tally will be cleared.", "Take it all out", function () { A.held = null; A.atlasSig = ""; A.cardsSig = ""; A.chartsSig = ""; send({ action: "reset" }); });
    });
    // The save widget loads a save straight into the engine; this redraws afterwards.
    window.constellationsRefresh = function () { if (A.engine) { A.boardId = null; A.atlasSig = ""; A.cardsSig = ""; A.chartsSig = ""; A.knownEarned = null; send({ action: "open" }); } };
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        ["charts", "atlas", "achievements", "changelog", "settings", "info-page"].forEach(function (name) {
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
    A.engine = { handle: pyodide.globals.get("handle"), getState: pyodide.globals.get("get_state"), loadState: pyodide.globals.get("load_state") };
    var saved = lsGet(STORE_KEY);
    if (saved && saved !== "{}") {
      lsSet(BACKUP_KEY, saved);      // kept until the next good save, so a load problem can never cost the player a game
      try { A.engine.loadState(pyodide.toPy(JSON.parse(saved))); } catch (e) { /* a bad save never blocks play */ }
    }
    $("engine-status").textContent = "";
    send({ action: "open" });
    sendDifficulty();
    await changelog;
    if (window.GameTutorial) window.GameTutorial.init(window.constellationsTutorialSteps ? window.constellationsTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS, { gameId: "constellations" });
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The observatory could not open (" + err + "). Reload to try again.";
  });

  // what the other parts use
  A.render = render;
})();
