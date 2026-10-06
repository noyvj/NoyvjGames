/* Lexis view: glue only. The engine (game.py and its modules) holds every rule; this file draws what
   handle() returns and forwards what the player does. No game logic lives here. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["lang.py", "pulse.py", "parse.py", "world.py", "scenes.py", "deduce.py", "notebook.py", "compound.py", "compound_scenes.py", "deduce_compound.py", "glyphs.py"];
  var STORE_KEY = "lexis:state";
  var TOKEN_LEN = 4;
  var MAX_OUT = 40;

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;   // { handle, getState, loadState, toJs }
  var view = null;
  var planetsInfo = null;
  var currentPlanet = "pulse";
  var outgoing = "";
  var outgoingGlyph = "";

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }

  // ---- drawing helpers -----------------------------------------------------------------------
  function markNode(ch) {
    var span = document.createElement("span");
    span.className = ch === "1" ? "mark-1" : "mark-0";
    span.setAttribute("aria-hidden", "true");
    return span;
  }
  function describeMarks(marks) {
    return marks.split("").map(function (c) { return c === "1" ? "long" : "short"; }).join(", ");
  }
  function tokenNode(marks) {
    var span = document.createElement("span");
    span.className = "token";
    span.setAttribute("role", "img");
    span.setAttribute("aria-label", describeMarks(marks));
    marks.split("").forEach(function (c) { span.appendChild(markNode(c)); });
    return span;
  }
  function signalNode(marks) {
    var wrap = document.createElement("span");
    wrap.className = "signal";
    for (var i = 0; i < marks.length; i += TOKEN_LEN) wrap.appendChild(tokenNode(marks.slice(i, i + TOKEN_LEN)));
    return wrap;
  }
  function lampsText(n) { return n === 0 ? "no lamps lit" : n === 1 ? "1 lamp lit" : n + " lamps lit"; }

  // ---- render --------------------------------------------------------------------------------
  function renderStation() {
    var lamps = $("lamps");
    lamps.textContent = "";
    var n = view.station.lamps;
    for (var i = 0; i < 7; i++) {
      var lamp = document.createElement("span");
      lamp.className = "lamp" + (i < n ? " lit" : "");
      lamps.appendChild(lamp);
    }
    lamps.setAttribute("aria-label", lampsText(n) + " of 7");
    var door = $("door");
    door.textContent = "Door: " + view.station.door.toUpperCase();
    door.className = "door " + view.station.door;
    $("station-text").textContent = view.station_text;
  }

  function renderScenes() {
    var list = $("scene-list");
    list.textContent = "";
    view.scenes.forEach(function (scene, index) {
      var li = document.createElement("li");
      li.className = "scene";
      var head = document.createElement("div");
      var label = document.createElement("strong");
      label.textContent = "Transmission " + (index + 1) + " ";
      head.appendChild(label);
      head.appendChild(signalNode(scene.marks));
      var what = document.createElement("div");
      what.className = "what";
      var changes = [];
      if (scene.before.lamps !== scene.after.lamps) changes.push("lamps: " + scene.before.lamps + " → " + scene.after.lamps);
      if (scene.before.door !== scene.after.door) changes.push("door: " + scene.before.door + " → " + scene.after.door);
      what.innerHTML = "The station: <b></b>";
      what.querySelector("b").textContent = changes.length ? changes.join("; ") : "no change";
      li.appendChild(head);
      li.appendChild(what);
      list.appendChild(li);
    });
    var left = view.scenes_total - view.scenes.length;
    $("next-scene-button").disabled = left === 0;
    var status = view.scenes.length + " of " + view.scenes_total + " received.";
    if (view.settled) status += " You have seen enough to work out every word. Try sending a signal.";
    $("scene-status").textContent = status;
  }

  function seenTokens() {
    var seen = [];
    view.scenes.forEach(function (scene) {
      for (var i = 0; i < scene.marks.length; i += TOKEN_LEN) {
        var token = scene.marks.slice(i, i + TOKEN_LEN);
        if (seen.indexOf(token) === -1) seen.push(token);
      }
    });
    return seen;
  }

  function renderNotebook() {
    var list = $("notebook-list");
    var keepChecked = {};
    list.querySelectorAll("input[type=checkbox]").forEach(function (box) { if (box.checked) keepChecked[box.dataset.token] = true; });
    list.textContent = "";
    seenTokens().forEach(function (token) {
      var li = document.createElement("li");
      var box = document.createElement("input");
      box.type = "checkbox";
      box.dataset.token = token;
      box.checked = Boolean(keepChecked[token]);
      box.setAttribute("aria-label", "Include this group in the check");
      var glyph = tokenNode(token);
      var input = document.createElement("input");
      input.type = "text";
      input.value = view.notebook[token] || "";
      input.placeholder = "what do you think this means?";
      input.setAttribute("aria-label", "Your guess for the group " + describeMarks(token));
      input.addEventListener("change", function () { send({ action: "write", form: token, gloss: input.value }); });
      li.appendChild(box);
      li.appendChild(glyph);
      li.appendChild(input);
      list.appendChild(li);
    });
    if (!list.children.length) {
      var empty = document.createElement("li");
      empty.className = "note";
      empty.textContent = "Receive a transmission and the groups of marks it contains will appear here.";
      list.appendChild(empty);
    }
  }

  function renderTransmit() {
    var out = $("outgoing");
    out.textContent = "";
    for (var i = 0; i < outgoing.length; i += TOKEN_LEN) {
      var chunk = outgoing.slice(i, i + TOKEN_LEN);
      var token = tokenNode(chunk);
      if (chunk.length < TOKEN_LEN) {
        for (var p = chunk.length; p < TOKEN_LEN; p++) { var pend = document.createElement("span"); pend.className = "mark-pending"; token.appendChild(pend); }
      }
      out.appendChild(token);
    }
    if (!outgoing) { out.textContent = "Nothing yet."; }
    $("send-button").disabled = !outgoing;
    var holder = $("token-buttons");
    holder.textContent = "";
    seenTokens().forEach(function (token) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.appendChild(tokenNode(token));
      btn.setAttribute("aria-label", "Add the group " + describeMarks(token));
      btn.addEventListener("click", function () { addMarks(token); });
      holder.appendChild(btn);
    });
  }

  function renderTabs() {
    var planets = view.planets;
    planetsInfo = planets;
    var two = $("tab-compound");
    two.disabled = !planets.compound.unlocked;
    two.textContent = planets.compound.unlocked ? "Planet 2" + (planets.compound.contact ? " (contact made)" : "") : "Planet 2 (not in range yet)";
    $("tab-pulse").textContent = "Planet 1" + (planets.pulse.contact ? " (contact made)" : "");
    $("tab-pulse").setAttribute("aria-pressed", String(currentPlanet === "pulse"));
    two.setAttribute("aria-pressed", String(currentPlanet === "compound"));
    $("planet-pulse").hidden = currentPlanet !== "pulse";
    $("planet-compound").hidden = currentPlanet !== "compound";
    var goal = view.goal || "";
    var done = planets[currentPlanet].contact;
    $("goal-line").textContent = done ? "Contact made. The crew has what it needs from this planet." : "Crew request: " + goal;
  }

  // ---- planet 2: the compound language ---------------------------------------------------------
  var SVG_NS = "http://www.w3.org/2000/svg";
  function partSvg(code) {
    var svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("class", "part");
    svg.setAttribute("aria-hidden", "true");
    var path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", (view.components || {})[code] || "");
    svg.appendChild(path);
    return svg;
  }
  function glyphNode(glyph) {
    var span = document.createElement("span");
    span.className = "glyph";
    span.setAttribute("role", "img");
    span.setAttribute("aria-label", "a sign of " + glyph.length + " parts");
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
    view.tray.forEach(function (label) {
      var item = document.createElement("span");
      item.className = "tray-item";
      item.textContent = label;
      tray.appendChild(item);
    });
    if (!view.tray.length) tray.textContent = "Empty.";
    $("c-tray-text").textContent = view.tray_text;

    var list = $("c-scene-list");
    list.textContent = "";
    view.scenes.forEach(function (scene, index) {
      var li = document.createElement("li");
      li.className = "scene";
      var head = document.createElement("div");
      var label = document.createElement("strong");
      label.textContent = "Transmission " + (index + 1) + " ";
      head.appendChild(label);
      head.appendChild(glyphNode(scene.glyph));
      var what = document.createElement("div");
      what.className = "what";
      what.innerHTML = "The tray: <b></b>";
      what.querySelector("b").textContent = trayLabelsDiff(scene.before, scene.after);
      li.appendChild(head);
      li.appendChild(what);
      list.appendChild(li);
    });
    $("c-next-scene-button").disabled = view.scenes.length >= view.scenes_total;
    var status = view.scenes.length + " of " + view.scenes_total + " received.";
    if (view.settled) status += " You have seen enough to work out every part. Try a sign you were never shown.";
    $("c-scene-status").textContent = status;

    var nb = $("c-notebook-list");
    var keep = {};
    nb.querySelectorAll("input[type=checkbox]").forEach(function (box) { if (box.checked) keep[box.dataset.token] = true; });
    nb.textContent = "";
    view.letters.forEach(function (code) {
      var li = document.createElement("li");
      var box = document.createElement("input");
      box.type = "checkbox";
      box.dataset.token = code;
      box.checked = Boolean(keep[code]);
      box.setAttribute("aria-label", "Include this part in the check");
      var input = document.createElement("input");
      input.type = "text";
      input.value = view.notebook[code] || "";
      input.placeholder = "what does this part mean?";
      input.setAttribute("aria-label", "Your guess for this part");
      input.addEventListener("change", function () { send({ action: "write", form: code, gloss: input.value }); });
      li.appendChild(box);
      li.appendChild(glyphNode(code));
      li.appendChild(input);
      nb.appendChild(li);
    });
    if (!view.letters.length) {
      var empty = document.createElement("li");
      empty.className = "note";
      empty.textContent = "Receive a transmission and the parts of its sign will appear here.";
      nb.appendChild(empty);
    }

    var out = $("c-outgoing");
    out.textContent = "";
    if (outgoingGlyph) out.appendChild(glyphNode(outgoingGlyph)); else out.textContent = "Nothing yet.";
    $("c-send-button").disabled = !outgoingGlyph;
    var holder = $("c-part-buttons");
    holder.textContent = "";
    view.letters.forEach(function (code) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.appendChild(partSvg(code));
      btn.setAttribute("aria-label", "Add this part to your sign");
      btn.addEventListener("click", function () { if (outgoingGlyph.length < 4) { outgoingGlyph += code; renderCompound(); } });
      holder.appendChild(btn);
    });
  }

  function render() {
    renderTabs();
    if (currentPlanet === "compound") { renderCompound(); return; }
    renderStation();
    renderScenes();
    renderNotebook();
    renderTransmit();
  }

  // ---- talking to the engine -----------------------------------------------------------------
  function persist() {
    try {
      var proxy = engine.getState();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(STORE_KEY, JSON.stringify(obj));
    } catch (e) { /* the save is a convenience until the save widget is wired */ }
  }
  function send(request) {
    request.planet = request.planet || currentPlanet;
    var result = JSON.parse(engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    if (result.right !== undefined) return result;   // a confirm: not a view
    view = result;
    render();
    persist();
    return result;
  }

  function addMarks(marks) {
    if (outgoing.length + marks.length > MAX_OUT) return;
    outgoing += marks;
    renderTransmit();
  }

  function wireCompound() {
    $("tab-pulse").addEventListener("click", function () { currentPlanet = "pulse"; send({ action: "open" }); });
    $("tab-compound").addEventListener("click", function () { currentPlanet = "compound"; send({ action: "open" }); });
    $("c-next-scene-button").addEventListener("click", function () { send({ action: "next_scene" }); });
    $("c-back-button").addEventListener("click", function () { outgoingGlyph = outgoingGlyph.slice(0, -1); renderCompound(); });
    $("c-clear-button").addEventListener("click", function () { outgoingGlyph = ""; renderCompound(); });
    $("c-send-button").addEventListener("click", function () {
      if (!outgoingGlyph) return;
      var result = send({ action: "speak", glyph: outgoingGlyph });
      if (result && result.reaction) $("c-reaction").textContent = result.reaction.text;
      outgoingGlyph = "";
      renderCompound();
    });
    $("c-check-button").addEventListener("click", function () {
      var forms = [];
      $("c-notebook-list").querySelectorAll("input[type=checkbox]").forEach(function (box) { if (box.checked) forms.push(box.dataset.token); });
      var out = $("c-check-result");
      if (!forms.length) { out.textContent = "Tick some entries first."; return; }
      var result = send({ action: "confirm", forms: forms });
      out.textContent = result ? result.right + " of the " + result.chosen + " ticked entries are right." : "";
    });
  }

  function wire() {
    wireCompound();
    $("next-scene-button").addEventListener("click", function () { send({ action: "next_scene" }); });
    $("add-0").addEventListener("click", function () { addMarks("0"); });
    $("add-1").addEventListener("click", function () { addMarks("1"); });
    $("back-button").addEventListener("click", function () { outgoing = outgoing.slice(0, -1); renderTransmit(); });
    $("clear-button").addEventListener("click", function () { outgoing = ""; renderTransmit(); });
    $("send-button").addEventListener("click", function () {
      if (!outgoing) return;
      var result = send({ action: "speak", marks: outgoing });
      if (result && result.reaction) $("reaction").textContent = result.reaction.text;
      outgoing = "";
      renderTransmit();
    });
    $("check-button").addEventListener("click", function () {
      var forms = [];
      $("notebook-list").querySelectorAll("input[type=checkbox]").forEach(function (box) { if (box.checked) forms.push(box.dataset.token); });
      var out = $("check-result");
      if (!forms.length) { out.textContent = "Tick some entries first."; return; }
      var result = send({ action: "confirm", forms: forms });
      out.textContent = result ? result.right + " of the " + result.chosen + " ticked entries are right." : "";
    });
  }

  function setBusy(busy) {
    ["next-scene-button", "check-button", "add-0", "add-1", "back-button", "clear-button", "send-button", "c-next-scene-button", "c-check-button", "c-back-button", "c-clear-button", "c-send-button"].forEach(function (id) { $(id).disabled = busy; });
  }

  async function boot() {
    setBusy(true);
    var pyodide = await window.loadPyodide();
    for (var i = 0; i < ENGINE_MODULES.length; i++) {
      var source = await (await fetch(ENGINE_MODULES[i])).text();
      pyodide.FS.writeFile(ENGINE_MODULES[i], source, { encoding: "utf8" });
    }
    await pyodide.runPythonAsync(await (await fetch("game.py")).text());
    window.pyodide = pyodide;   // the shared save widget (milestone 5) looks for it
    engine = { handle: pyodide.globals.get("handle"), getState: pyodide.globals.get("get_state"), loadState: pyodide.globals.get("load_state") };
    var saved = lsGet(STORE_KEY);
    if (saved) {
      try { engine.loadState(pyodide.toPy(JSON.parse(saved))); } catch (e) { /* a bad save never blocks play */ }
    }
    $("engine-status").textContent = "";
    setBusy(false);
    send({ action: "open" });
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The station could not start (" + err + "). Reload to try again.";
  });
})();
