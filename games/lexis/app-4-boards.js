/* Lexis, part 4 of 5: number bench, star map, glyph museum, globe, evidence board, sign keyboard, transmission cards and render(). */
(function () {
  "use strict";

  var A = window.LexisApp;
  var $ = A.$, addToMessage = A.addToMessage, describeMarks = A.describeMarks, fillOnce = A.fillOnce,
      guard = A.guard, ordinalIn = A.ordinalIn, partSvg = A.partSvg, renderAchievements = A.renderAchievements,
      renderBridge = A.renderBridge, renderCompound = A.renderCompound, renderInfo = A.renderInfo,
      renderNotebook = A.renderNotebook, renderReport = A.renderReport, renderScenes = A.renderScenes,
      renderStation = A.renderStation, renderStory = A.renderStory, renderTabs = A.renderTabs,
      renderTransmit = A.renderTransmit, saveResumeFrame = A.saveResumeFrame, seenTokens = A.seenTokens,
      setEnabled = A.setEnabled, setText = A.setText, signalNode = A.signalNode, tokenNode = A.tokenNode,
      tokenOfMessage = A.tokenOfMessage;

  // ---- number bench --------------------------------------------------------------------------

  function generateBenchTarget() {
    return "0" + Math.floor(Math.random() * 8).toString(2).padStart(3, "0");
  }

  function renderBench() {
    var targetEl = $("bench-target");
    targetEl.textContent = "";
    if (A.benchTarget) {
      var tNode = tokenNode(A.benchTarget);
      tNode.setAttribute("aria-label", "Target: " + A.benchTarget);
      targetEl.appendChild(tNode);
    } else {
      targetEl.textContent = "Press 'New puzzle' to start.";
    }

    var aEl = $("bench-a");
    var bEl = $("bench-b");
    [aEl, bEl].forEach(function (el) { el.textContent = ""; });
    for (var i = 0; i < 4; i++) {
      var bit = 3 - i; // 8, 4, 2, 1
      var swA = document.createElement("button");
      swA.type = "button";
      swA.className = "switch" + (A.currentBenchA & (1 << bit) ? " on" : "");
      swA.textContent = (A.currentBenchA & (1 << bit)) ? "1" : "0";
      swA.setAttribute("aria-label", "Bit " + (bit + 1) + " for first number");
      swA.addEventListener("click", function () { A.currentBenchA ^= (1 << bit); renderBench(); });
      aEl.appendChild(swA);

      var swB = document.createElement("button");
      swB.type = "button";
      swB.className = "switch" + (A.currentBenchB & (1 << bit) ? " on" : "");
      swB.textContent = (A.currentBenchB & (1 << bit)) ? "1" : "0";
      swB.setAttribute("aria-label", "Bit " + (bit + 1) + " for second number");
      swB.addEventListener("click", function () { A.currentBenchB ^= (1 << bit); renderBench(); });
      bEl.appendChild(swB);
    }

    var resultEl = $("bench-result");
    if (!A.benchTarget) {
      resultEl.textContent = "";
    } else {
      var sum = A.currentBenchA + A.currentBenchB;
      if (sum > 7) {
        resultEl.textContent = "Overflow! The bench only holds up to 7.";
      } else if (sum === parseInt(A.benchTarget.substring(1), 2)) {
        resultEl.textContent = "Correct! Generating new puzzle...";
        A.benchTarget = generateBenchTarget();
        A.currentBenchA = 0;
        A.currentBenchB = 0;
        renderBench();
      } else {
        resultEl.textContent = "Not quite. Adjust the switches.";
      }
    }
  }

  function renderStarMap() {
    var container = $("star-map-container");
    if (!container) return;
    container.textContent = "";
    var map = A.view.star_map || [];
    var discovered = new Set(A.view.discovered_stars || []);
    map.forEach(function(star) {
      var dot = document.createElement("div");
      dot.className = "star-dot" + (discovered.has(star.id) ? " discovered" : "");
      dot.style.left = (star.x * 10) + "%";
      dot.style.top = (star.y * 10) + "%";
      dot.setAttribute("role", "button");
      dot.setAttribute("tabindex", "0");
      dot.setAttribute("aria-label", discovered.has(star.id) ? star.label + ", tuned" : "Untuned signal at " + star.x + "," + star.y);
      dot.addEventListener("click", function() { A.send({ action: "tune_star", id: star.id }); });
      container.appendChild(dot);
    });
    var info = $("star-map-info");
    if (info) {
      if (A.view.tuned_star) {
        info.textContent = "Tuned: " + A.view.tuned_star.label + " at (" + A.view.tuned_star.x + ", " + A.view.tuned_star.y + "), strength " + A.view.tuned_star.strength;
        delete A.view.tuned_star;
      } else {
        info.textContent = "";
      }
    }
  }

  function renderMuseum() {
    var list = $("museum-wall");
    list.textContent = "";
    (A.view.museum || []).forEach(function (item) {
      var card = document.createElement("div");
      card.className = "museum-card" + (item.confirmed ? " confirmed" : "");
      card.setAttribute("aria-label", item.planet + ": " + item.form + (item.confirmed ? ", meaning: " + item.meaning : ", not yet confirmed"));
      
      var planetLabel = document.createElement("span");
      planetLabel.className = "museum-planet";
      planetLabel.textContent = "Planet " + ({pulse: 1, compound: 2, bridge: 3}[item.planet]);
      
      var formSpan = document.createElement("div");
      formSpan.className = "museum-form";
      formSpan.textContent = item.form;
      
      var meaningDiv = document.createElement("div");
      meaningDiv.className = "museum-meaning";
      meaningDiv.textContent = item.confirmed ? item.meaning : "?";
      
      card.appendChild(planetLabel);
      card.appendChild(formSpan);
      card.appendChild(meaningDiv);
      list.appendChild(card);
    });
  }

  function renderGlobe() {
    var container = $("globe-container");
    if (!container) return;
    var lamps = (A.view && A.view.station && A.view.station.lamps) ? A.view.station.lamps : 0;
    try {
      container.innerHTML = A.engine.globe_svg(lamps);
    } catch (e) { /* fallback to empty */ }
  }

  // ---- evidence board (R4-PX-19) -----------------------------------------------------------------
  // The fragments are the Pulse transmissions received so far; the player names what might be sending each one.
  // The names live in the engine (`name_pin`) and so in the save.
  function renderEvidenceBoard() {
    var pins = $("evidence-pins");
    var board = A.view.evidence || { fragments: [], pins: {} };
    fillOnce(pins, board.fragments.join(","), function () {
      board.fragments.forEach(function (marks, i) {
        var pin = document.createElement("div");
        pin.className = "evidence-pin";
        var fragment = document.createElement("div");
        fragment.className = "evidence-fragment";
        var label = document.createElement("strong");
        label.textContent = "Fragment " + (i + 1) + " ";
        fragment.appendChild(label);
        fragment.appendChild(signalNode(marks));
        var input = document.createElement("input");
        input.type = "text";
        input.className = "evidence-input";
        input.maxLength = 60;
        input.dataset.pin = String(i);
        input.placeholder = "What is sending this?";
        input.setAttribute("aria-label", "Your guess for what is sending fragment " + (i + 1));
        input.addEventListener("change", function () { A.send({ action: "name_pin", pin: i, text: input.value }); });
        pin.appendChild(fragment);
        pin.appendChild(input);
        pins.appendChild(pin);
      });
      if (!board.fragments.length) {
        var empty = document.createElement("p");
        empty.className = "note";
        empty.textContent = "Receive a transmission on planet 1 and it is pinned here.";
        pins.appendChild(empty);
      }
    });
    pins.querySelectorAll("input[type=text]").forEach(function (input) {
      var stored = board.pins[input.dataset.pin] || "";
      if (document.activeElement !== input && input.value !== stored) input.value = stored;
    });
  }

  // ---- sign keyboard (R4-LEMO-4, phones only: the CSS hides it on wider screens) -----------------------
  // The signs you know, as a grid at the bottom. Names are ordinals, never the internal letters.
  function signKeyboardItems() {
    if (!A.view) return [];
    if (A.currentPlanet === "pulse") return seenTokens();
    if (A.currentPlanet === "compound") return A.view.letters || [];
    return Array.from(new Set((A.view.nouns || []).concat(A.view.markers || [], A.view.numbers || [])));
  }
  function signKeyboardButton(item) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "sign-btn";
    if (A.currentPlanet === "pulse") {
      btn.appendChild(tokenNode(item));
      btn.setAttribute("aria-label", "Add group " + ordinalIn(seenTokens(), item) + " (" + describeMarks(item) + ")");
      btn.addEventListener("click", function () { A.addMarks(item); });
    } else if (A.currentPlanet === "compound") {
      btn.appendChild(partSvg(item));
      btn.setAttribute("aria-label", "Add part " + ordinalIn(A.view.letters, item));
      btn.addEventListener("click", function () { A.addPart(item); });
    } else {
      btn.appendChild(tokenOfMessage(item));
      var n = ordinalIn(A.view.nouns, item), m = ordinalIn(A.view.markers, item);
      btn.setAttribute("aria-label", n ? "Add thing " + n : m ? "Add small sign " + m : "Add number: " + describeMarks(item));
      btn.addEventListener("click", function () { addToMessage(item); });
    }
    return btn;
  }
  function renderSignKeyboard() {
    var kb = $("sign-keyboard"), grid = $("sign-grid");
    var items = signKeyboardItems();
    kb.hidden = !items.length;
    $("game").classList.toggle("has-sign-keyboard", items.length > 0);
    fillOnce(grid, A.currentPlanet + ":" + items.join(","), function () {
      items.forEach(function (item) { grid.appendChild(signKeyboardButton(item)); });
    });
  }

  // ---- transmission cards (R4-LEMO-1, phones only) ------------------------------------------------------
  // Received Pulse transmissions, one full-screen card at a time. Swipe up (or Next) for the following one; when
  // the last one is showing and more exist, Next also receives the next transmission. Nothing is timed, so there
  // is no autoplay to pause.
  var cardIndex = 0;
  function sceneChanges(scene) {
    var changes = [];
    if (scene.before.lamps !== scene.after.lamps) changes.push("lamps: " + scene.before.lamps + " → " + scene.after.lamps);
    if (scene.before.door !== scene.after.door) changes.push("door: " + scene.before.door + " → " + scene.after.door);
    return changes.length ? changes.join("; ") : "no change";
  }
  function sceneCardViewer() { return $("scene-card-viewer"); }
  function renderSceneCardToggle() {
    var btn = $("scene-card-toggle-button");
    btn.hidden = !(A.currentPlanet === "pulse" && (A.view.scenes || []).length > 0);
    if (btn.hidden && !sceneCardViewer().hidden) closeSceneCards();
    else if (!sceneCardViewer().hidden) renderSceneCard();
  }
  function renderSceneCard() {
    var scenes = A.view.scenes, total = scenes.length;
    cardIndex = Math.max(0, Math.min(cardIndex, total - 1));
    var scene = scenes[cardIndex], card = $("scene-card");
    card.textContent = "";
    if (!scene) return;
    var head = document.createElement("strong");
    head.textContent = "Transmission " + (cardIndex + 1);
    var what = document.createElement("div");
    what.className = "what";
    what.textContent = "The station: " + sceneChanges(scene);
    card.appendChild(head);
    card.appendChild(signalNode(scene.marks));
    card.appendChild(what);
    setText($("scene-card-count"), "Transmission " + (cardIndex + 1) + " of " + A.view.scenes_total);
    setEnabled("scene-card-prev", cardIndex > 0);
    setEnabled("scene-card-next", cardIndex < total - 1 || total < A.view.scenes_total);
  }
  function stepSceneCard(delta) {
    if (delta > 0 && cardIndex >= A.view.scenes.length - 1) {
      if (A.view.scenes.length < A.view.scenes_total) { cardIndex = A.view.scenes.length; A.send({ action: "next_scene" }); }
      return;
    }
    cardIndex = Math.max(0, cardIndex + delta);
    renderSceneCard();
  }
  function openSceneCards() {
    cardIndex = Math.max(0, A.view.scenes.length - 1);
    sceneCardViewer().hidden = false;
    $("scene-card-toggle-button").setAttribute("aria-expanded", "true");
    renderSceneCard();
    $("scene-card").focus();
  }
  function closeSceneCards() {
    sceneCardViewer().hidden = true;
    $("scene-card-toggle-button").setAttribute("aria-expanded", "false");
    if (!$("scene-card-toggle-button").hidden) $("scene-card-toggle-button").focus();
  }
  function wireSceneCards() {
    $("scene-card-toggle-button").addEventListener("click", openSceneCards);
    $("scene-card-close").addEventListener("click", closeSceneCards);
    guard("scene-card-prev", function () { stepSceneCard(-1); });
    guard("scene-card-next", function () { stepSceneCard(1); });
    var viewer = sceneCardViewer(), startY = null;
    viewer.addEventListener("touchstart", function (e) { startY = e.touches[0].clientY; }, { passive: true });
    viewer.addEventListener("touchend", function (e) {
      if (startY === null) return;
      var dy = e.changedTouches[0].clientY - startY;
      startY = null;
      if (dy < -50) stepSceneCard(1);
      else if (dy > 50) stepSceneCard(-1);
    }, { passive: true });
    viewer.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { e.stopPropagation(); closeSceneCards(); }
      else if (e.key === "ArrowDown" || e.key === "PageDown") { e.preventDefault(); stepSceneCard(1); }
      else if (e.key === "ArrowUp" || e.key === "PageUp") { e.preventDefault(); stepSceneCard(-1); }
    });
  }

  function render() {
    renderGlobe();
    renderAchievements();
    renderStory();
    renderReport();
    renderInfo();
    renderTabs();
    renderStarMap();
    renderMuseum();
    renderEvidenceBoard();
    renderSceneCardToggle();
    renderSignKeyboard();
    if (A.currentPlanet === "bridge") { renderBridge(); return; }
    if (A.currentPlanet === "compound") { renderCompound(); return; }
    if (A.currentPlanet === "pulse") renderBench();
    renderStation();
    renderScenes();
    renderNotebook();
    renderTransmit();
    saveResumeFrame();
  }

  // what the other parts use (see the File map in CLAUDE.md)
  A.generateBenchTarget = generateBenchTarget; A.render = render; A.renderBench = renderBench;
  A.sceneChanges = sceneChanges; A.wireSceneCards = wireSceneCards;
})();
