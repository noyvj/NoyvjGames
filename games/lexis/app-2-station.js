/* Lexis, part 2 of 5: the station, scenes, notebook, transmit panel, planet tabs and planet 2 (the compound language). */
(function () {
  "use strict";

  var A = window.LexisApp;
  var $ = A.$, TOKEN_LEN = A.TOKEN_LEN, attachLongPress = A.attachLongPress, describeMarks = A.describeMarks,
      fillOnce = A.fillOnce, lampsText = A.lampsText, noteScenes = A.noteScenes, ordinalIn = A.ordinalIn,
      setEnabled = A.setEnabled, setText = A.setText, signalNode = A.signalNode,
      syncNotebookValues = A.syncNotebookValues, tokenNode = A.tokenNode;
  var planetsInfo = null;

  // ---- render --------------------------------------------------------------------------------
  function renderStation() {
    var lamps = $("lamps");
    lamps.textContent = "";
    var n = A.view.station.lamps;
    for (var i = 0; i < 7; i++) {
      var lamp = document.createElement("span");
      lamp.className = "lamp" + (i < n ? " lit" : "");
      lamps.appendChild(lamp);
    }
    lamps.setAttribute("aria-label", lampsText(n) + " of 7");
    setText($("lamp-count"), n + " of 7 lit");
    var door = $("door");
    setText(door, "Door: " + A.view.station.door.toUpperCase());
    door.className = "door " + A.view.station.door;
    setText($("station-text"), A.view.station_text);
  }

  function renderScenes() {
    var list = $("scene-list");
    list.textContent = "";
    A.view.scenes.forEach(function (scene, index) {
      var li = document.createElement("li");
      li.className = "scene";
      var head = document.createElement("div");
      var label = document.createElement("strong");
      label.textContent = "Transmission " + (index + 1) + " ";
      head.appendChild(label);
      var sig = signalNode(scene.marks);
      head.appendChild(sig);
      attachLongPress(sig, scene.marks);
      var what = document.createElement("div");
      what.className = "what";
      what.innerHTML = "The station: <b></b>";
      what.querySelector("b").textContent = A.sceneChanges(scene);
      li.appendChild(head);
      li.appendChild(what);
      list.appendChild(li);
    });
    noteScenes("pulse", list);
    var left = A.view.scenes_total - A.view.scenes.length;
    setEnabled("next-scene-button", left !== 0);
    var status = A.view.scenes.length + " of " + A.view.scenes_total + " received.";
    if (A.view.settled) status += " You have seen enough to work out every word. Try sending a signal.";
    setText($("scene-status"), status);
  }

  function seenTokens() {
    var seen = [];
    A.view.scenes.forEach(function (scene) {
      for (var i = 0; i < scene.marks.length; i += TOKEN_LEN) {
        var token = scene.marks.slice(i, i + TOKEN_LEN);
        if (seen.indexOf(token) === -1) seen.push(token);
      }
    });
    return seen;
  }

  function renderNotebook() {
    var list = $("notebook-list");
    var tokens = seenTokens();
    fillOnce(list, tokens.join(","), function () {
      tokens.forEach(function (token, index) {
        var li = document.createElement("li");
        var box = document.createElement("input");
        box.type = "checkbox";
        box.dataset.token = token;
        box.setAttribute("aria-label", "Include group " + (index + 1) + " (" + describeMarks(token) + ") in the check");
        var glyph = tokenNode(token);
        var input = document.createElement("input");
        input.type = "text";
        input.dataset.token = token;
        input.placeholder = "what do you think this means?";
        input.setAttribute("aria-label", "Your guess for group " + (index + 1) + ", " + describeMarks(token));
        input.addEventListener("change", function () { A.send({ action: "write", form: token, gloss: input.value }); });
        li.appendChild(box);
        li.appendChild(glyph);
        li.appendChild(input);
        list.appendChild(li);
      });
      if (!tokens.length) {
        var empty = document.createElement("li");
        empty.className = "note";
        empty.textContent = "Receive a transmission and the groups of marks it contains will appear here.";
        list.appendChild(empty);
      }
    });
    syncNotebookValues(list);
  }

  function renderTransmit() {
    var out = $("outgoing");
    out.textContent = "";
    for (var i = 0; i < A.outgoing.length; i += TOKEN_LEN) {
      var chunk = A.outgoing.slice(i, i + TOKEN_LEN);
      var token = tokenNode(chunk);
      if (chunk.length < TOKEN_LEN) {
        for (var p = chunk.length; p < TOKEN_LEN; p++) { var pend = document.createElement("span"); pend.className = "mark-pending"; token.appendChild(pend); }
      }
      out.appendChild(token);
    }
    if (!A.outgoing) { out.textContent = "Nothing yet."; }
    setEnabled("send-button", Boolean(A.outgoing));
    setEnabled("back-button", Boolean(A.outgoing));
    setEnabled("clear-button", Boolean(A.outgoing));
    var tokens = seenTokens();
    fillOnce($("token-buttons"), tokens.join(","), function (holder) {
      tokens.forEach(function (token, index) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.appendChild(tokenNode(token));
        btn.setAttribute("aria-label", "Add group " + (index + 1) + " (" + describeMarks(token) + ")");
        btn.addEventListener("click", function () { A.addMarks(token); });
        holder.appendChild(btn);
      });
    });
  }

  var knownUnlocked = { pulse: null, compound: null, bridge: null };
  function tabLabel(n, info) {
    return "Planet " + n + (info.unlocked ? (info.contact ? " (contact made)" : "") : " (not in range yet)");
  }

  function renderTabs() {
    var planets = A.view.planets;
    planetsInfo = planets;
    var tabs = { pulse: $("tab-pulse"), compound: $("tab-compound"), bridge: $("tab-bridge") };
    ["pulse", "compound", "bridge"].forEach(function (id, index) {
      if (knownUnlocked[id] === false && planets[id].unlocked) A.showToast("Planet " + (index + 1) + " is now in range.");
      knownUnlocked[id] = planets[id].unlocked;
      tabs[id].disabled = !planets[id].unlocked;
      tabs[id].textContent = tabLabel(index + 1, planets[id]);
      tabs[id].setAttribute("aria-pressed", String(A.currentPlanet === id));
      $("planet-" + id).hidden = A.currentPlanet !== id;
    });
    var goal = A.view.goal || "";
    var done = planets[A.currentPlanet].contact;
    var line = done ? "Contact made. The crew has what it needs from this planet." : "Crew request: " + goal;
    if (done && A.currentPlanet === "bridge") line += " There are no further planets in range yet.";
    setText($("goal-line"), line);
    var made = ["pulse", "compound", "bridge"].filter(function (id) { return planets[id].contact; }).length;
    setText($("contact-line"), "Contact made: " + made + " of 3 planets");
  }

  // ---- planet 2: the compound language ---------------------------------------------------------
  var SVG_NS = "http://www.w3.org/2000/svg";
  function partSvg(code) {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("class", "part");
    svg.dataset.sign = code;
    svg.setAttribute("aria-hidden", "true");
    var path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", (A.view.components || {})[code] || "");
    svg.appendChild(path);
    return svg;
  }
  function glyphNode(glyph) {
    var span = document.createElement("span");
    span.className = "glyph";
    span.dataset.sign = glyph;
    span.setAttribute("role", "img");
    var thing = ordinalIn(A.view.nouns, glyph);       // planet 3: a noun is named by its place in the list of things
    var names = glyph.split("").map(function (code) { var n = ordinalIn(A.view.letters, code); return n ? "part " + n : "a part"; });
    span.setAttribute("aria-label", thing ? "thing " + thing : "a sign of " + glyph.length + " parts: " + names.join(", "));
    glyph.split("").forEach(function (code) { span.appendChild(partSvg(code)); });
    return span;
  }
  function trayLabelsDiff(before, after) {
    var added = after.items.slice(before.items.length);
    return added.length ? "arrives: " + added.join(", ") : "no change";
  }

  function renderCompound() {
    var tray = $("c-tray");
    tray.textContent = "";
    A.view.tray.forEach(function (label) {
      var item = document.createElement("span");
      item.className = "tray-item";
      item.textContent = label;
      tray.appendChild(item);
    });
    if (!A.view.tray.length) tray.textContent = "Empty.";
    setText($("c-tray-text"), A.view.tray_text);

    var list = $("c-scene-list");
    list.textContent = "";
    A.view.scenes.forEach(function (scene, index) {
      var li = document.createElement("li");
      li.className = "scene";
      var head = document.createElement("div");
      var label = document.createElement("strong");
      label.textContent = "Transmission " + (index + 1) + " ";
      head.appendChild(label);
      var gl = glyphNode(scene.glyph);
      head.appendChild(gl);
      attachLongPress(gl, scene.glyph);
      var what = document.createElement("div");
      what.className = "what";
      what.innerHTML = "The tray: <b></b>";
      what.querySelector("b").textContent = trayLabelsDiff(scene.before, scene.after);
      li.appendChild(head);
      li.appendChild(what);
      list.appendChild(li);
    });
    noteScenes("compound", list);
    setEnabled("c-next-scene-button", A.view.scenes.length < A.view.scenes_total);
    var status = A.view.scenes.length + " of " + A.view.scenes_total + " received.";
    if (A.view.settled) status += " You have seen enough to work out every part. Try a sign you were never shown.";
    setText($("c-scene-status"), status);

    var nb = $("c-notebook-list");
    fillOnce(nb, A.view.letters.join(","), function () {
      A.view.letters.forEach(function (code, index) {
        var li = document.createElement("li");
        var box = document.createElement("input");
        box.type = "checkbox";
        box.dataset.token = code;
        box.setAttribute("aria-label", "Include part " + (index + 1) + " in the check");
        var input = document.createElement("input");
        input.type = "text";
        input.dataset.token = code;
        input.placeholder = "what does this part mean?";
        input.setAttribute("aria-label", "Your guess for part " + (index + 1));
        input.addEventListener("change", function () { A.send({ action: "write", form: code, gloss: input.value }); });
        li.appendChild(box);
        li.appendChild(glyphNode(code));
        li.appendChild(input);
        nb.appendChild(li);
      });
      if (!A.view.letters.length) {
        var empty = document.createElement("li");
        empty.className = "note";
        empty.textContent = "Receive a transmission and the parts of its sign will appear here.";
        nb.appendChild(empty);
      }
    });
    syncNotebookValues(nb);

    var out = $("c-outgoing");
    out.textContent = "";
    if (A.outgoingGlyph) out.appendChild(glyphNode(A.outgoingGlyph)); else out.textContent = "Nothing yet.";
    setEnabled("c-send-button", Boolean(A.outgoingGlyph));
    setEnabled("c-back-button", Boolean(A.outgoingGlyph));
    setEnabled("c-clear-button", Boolean(A.outgoingGlyph));
    fillOnce($("c-part-buttons"), A.view.letters.join(","), function (holder) {
      A.view.letters.forEach(function (code, index) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.appendChild(partSvg(code));
        btn.setAttribute("aria-label", "Add part " + (index + 1) + " to your sign");
        btn.addEventListener("click", function () { A.addPart(code); });
        holder.appendChild(btn);
      });
    });
  }

  // what the other parts use (see the File map in CLAUDE.md)
  A.glyphNode = glyphNode; A.partSvg = partSvg; A.renderCompound = renderCompound;
  A.renderNotebook = renderNotebook; A.renderScenes = renderScenes; A.renderStation = renderStation;
  A.renderTabs = renderTabs; A.renderTransmit = renderTransmit; A.seenTokens = seenTokens;
})();
