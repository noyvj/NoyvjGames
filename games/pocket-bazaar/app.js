/* Pocket Bazaar, part 5 of 5 (loads last): the peek panel, wire(), the tutorial steps, boot() and the phone dock. */
(function () {
  "use strict";

  var A = window.PocketBazaarApp;
  var $ = A.$, askThen = A.askThen, BACKUP_KEY = A.BACKUP_KEY, cellAt = A.cellAt, doBroom = A.doBroom,
      doSell = A.doSell, el = A.el, endDrag = A.endDrag, ENGINE_MODULES = A.ENGINE_MODULES,
      loadChangelog = A.loadChangelog, lsGet = A.lsGet, lsSet = A.lsSet, mountSeeds = A.mountSeeds, onKey = A.onKey,
      onPointerDown = A.onPointerDown, onPointerMove = A.onPointerMove, select = A.select, sellAt = A.sellAt,
      send = A.send, setText = A.setText, showMessage = A.showMessage, showToast = A.showToast,
      STORE_KEY = A.STORE_KEY, wirePanelToggle = A.wirePanelToggle;

  // R4-PBMO-5 (phones): pull down on the top row or the day banner to peek at the festival and the regulars. The panel
  // shows while the finger is down and goes when it lifts, so a glance never leaves the board. Everything it says is also
  // on screen elsewhere (the day banner, the Regulars button), so there is no gesture-only information.
  function wirePeek() {
    var panel = el("div", "peek-panel");
    panel.id = "peek-panel";
    panel.setAttribute("aria-hidden", "true");
    var title = el("div", "peek-title", "Today's stall");
    var fest = el("div", "peek-festival");
    var reg = el("div", "peek-regulars");
    panel.appendChild(title);
    panel.appendChild(fest);
    panel.appendChild(reg);
    document.body.appendChild(panel);
    function fill() {
      if (!A.view) return;
      var f = A.view.festival;
      setText(fest, f ? f.name + " (" + (f.tone === "tricky" ? "harder day" : "easier day") + "): " + f.blurb : "");
      var here = (A.view.customers || []).filter(function (c) { return c.archetype === "regular"; }).map(function (c) { return c.name; });
      setText(reg, "Regulars met: " + A.view.regulars_met + " of " + A.view.regulars.length + (here.length ? ". At the stall now: " + here.join(", ") + "." : "."));
    }
    function begin(e) {
      if (!window.matchMedia("(max-width: 600px)").matches || !A.view) return;
      var startY = e.clientY;
      function move(ev) {
        if (ev.pointerId !== e.pointerId || ev.clientY - startY < 40) return;
        fill();
        panel.classList.add("open");
      }
      function end(ev) {
        if (ev.pointerId !== e.pointerId) return;
        panel.classList.remove("open");
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", end);
        window.removeEventListener("pointercancel", end);
      }
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", end);
      window.addEventListener("pointercancel", end);
    }
    Array.prototype.forEach.call(document.querySelectorAll(".top-row, #message"), function (node) { node.addEventListener("pointerdown", begin); });
  }

  function wire() {
    $("toast").addEventListener("click", function () { showToast(""); });
    $("start-day-button").addEventListener("click", function () { send({ action: "start_day" }); });
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("achievements-toggle-button", "achievements-panel");
    wirePanelToggle("regulars-toggle-button", "regulars-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    mountSeeds();
    $("reset-button").addEventListener("click", function () {
      askThen("pocket-bazaar-reset", "Start the whole stall over? Your coins, upgrades, renown and personal bests will be erased.", "Erase it", function () {
        A.selected = null;
        send({ action: "reset" });
      });
    });
    $("shop-toggle-button").addEventListener("click", function () {
      var panel = $("shop-panel");
      panel.hidden = !panel.hidden;
      $("shop-toggle-button").setAttribute("aria-expanded", String(!panel.hidden));
    });
    $("sell-button").addEventListener("click", doSell);
    $("broom-button").addEventListener("click", doBroom);
    var grid = $("counter");
    grid.addEventListener("pointerdown", onPointerDown);
    window.addEventListener("pointermove", onPointerMove, { passive: false });
    window.addEventListener("pointerup", function (e) { endDrag(e, false); });
    window.addEventListener("pointercancel", function (e) { endDrag(e, true); });
    document.addEventListener("keydown", onKey);
    $("board").addEventListener("pb-action", function (e) {
      var action = e.detail.action;
      var cellIdx = Number(e.detail.cell);
      if (!A.view || A.view.phase !== "open" || !cellAt(cellIdx)) return;
      if (action === "pick-up") {
        select(cellIdx);
      } else if (action === "sell") {
        sellAt(cellIdx);
      } else if (action === "hand-over") {
        var takers = A.view.deliverable[String(cellIdx)] || [];
        if (takers.length > 0) send({ action: "deliver", from: cellIdx, to: takers[0] });
        else showMessage("No customer wants this.", false);
      }
    });

    // The save widget (a later milestone) loads a save straight into the engine; this redraws afterwards.
    wirePeek();
    window.pocketBazaarApi = { view: function () { return A.view; } };
    window.pocketBazaarRefresh = function () { if (A.engine) { A.selected = null; send({ action: "open" }); } };
  }

  function setBusy(busy) {
    Array.prototype.forEach.call(document.querySelectorAll(".crate-btn, #sell-button, #broom-button"), function (b) { b.disabled = busy; });
  }

  var TUTORIAL_STEPS = [
    { title: "Welcome to the stall", text: "Customers ask for goods; you make them by merging and hand them over. Nothing here runs on a clock: customers wait in beats, which are your own actions, so you can stop and think as long as you like. Skip any time and reopen this from the Tutorial button." },
    { selector: "#stats", title: "Your numbers", text: "Coins, the day, how many customers you have served, and your combo. Every action you take moves one of these, or the tally under the counter." },
    { selector: "#stall-panel", title: "The stall", text: "When a day is open, up to three customers stand at the top with their orders and a patience bar counted in beats. The counter is below, and your crates, Sell and Broom under that." },
    { selector: "#crates", title: "Crates", text: "Tap a crate to put a basic good on the counter. Crates are free and never run out. Each good has a shape, a letter and a number, so you never need colour to tell them apart." },
    { selector: "#board", title: "Merge", text: "Pick up a good and tap an identical one (marked with a +) to merge them into the next tier. Three together jump two tiers, and a merge that lines up with a neighbour keeps going as a chain." },
    { selector: "#queue", title: "Hand over", text: "Pick up a good, then tap a customer who wants it, or drag it over. The right family at the tier asked for, or better, is accepted; a Critic wants exactly that tier." },
    { selector: "#tools", title: "Sell and Broom", text: "Sell turns any good into coins and Broom sweeps it away, so the counter can never jam. Moving, swapping and selling are free; only crates, merges, sweeps and hand-overs are beats." },
    { selector: "#start-day-button", title: "Open the stall", text: "Each market day has a festival that changes one rule, and it says plainly whether it makes the day easier or harder. Between days you can spend coins on permanent upgrades." },
    { title: "You are ready", text: "Take your time. Your stall is saved after every action, and nothing is lost by leaving." }
  ];

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
    setBusy(false);
    // R4-PBMO-6: the engine already keeps the whole day (board, queue, patience) in the save after every action and
    // loads it on boot; this line only says so, so a short break reads as safe.
    if (A.view.phase === "open") showMessage("Back at the stall: your day is just as you left it, every good on the counter and every customer's patience.", true);
    await changelog;
    if (window.GameTutorial) window.GameTutorial.init(window.pocketBazaarTutorialSteps ? window.pocketBazaarTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS, { gameId: "pocket-bazaar" });
  }

  // R4-PBMO-3: the dock along the bottom edge (phones only, CSS) does exactly what Sell, Broom and D do.
  function doHandOver() {
    if (A.selected === null) { showMessage("Pick up a good first (tap it), then press Hand over.", false); return; }
    var takers = A.view.deliverable[String(A.selected)] || [];
    send({ action: "deliver", from: A.selected, to: takers.length ? takers[0] : 0 });
  }
  var dock = document.getElementById("mobile-dock");
  if (dock) {
    dock.addEventListener("click", function (e) {
      var btn = e.target.closest("button[data-action]");
      if (!btn || !A.view || A.view.phase !== "open") return;
      var action = btn.getAttribute("data-action");
      if (action === "sell") doSell();
      else if (action === "broom") doBroom();
      else if (action === "handover") doHandOver();
    });
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The stall could not open (" + err + "). Reload to try again.";
  });
})();
