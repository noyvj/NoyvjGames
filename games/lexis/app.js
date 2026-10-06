/* Lexis view: glue only. The engine (game.py and its modules) holds every rule; this file draws what
   handle() returns and forwards what the player does. No game logic lives here. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["lang.py", "pulse.py", "parse.py", "world.py", "scenes.py", "deduce.py", "notebook.py", "compound.py", "compound_scenes.py", "deduce_compound.py", "glyphs.py", "achievements.py", "bridge.py", "bridge_scenes.py", "deduce_bridge.py"];
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
  var outgoingMessage = [];   // planet 3: the tokens of the message being built
  var MAX_MESSAGE = 6;

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

  function tabLabel(n, info) {
    return "Planet " + n + (info.unlocked ? (info.contact ? " (contact made)" : "") : " (not in range yet)");
  }

  function renderTabs() {
    var planets = view.planets;
    planetsInfo = planets;
    var tabs = { pulse: $("tab-pulse"), compound: $("tab-compound"), bridge: $("tab-bridge") };
    ["pulse", "compound", "bridge"].forEach(function (id, index) {
      tabs[id].disabled = !planets[id].unlocked;
      tabs[id].textContent = tabLabel(index + 1, planets[id]);
      tabs[id].setAttribute("aria-pressed", String(currentPlanet === id));
      $("planet-" + id).hidden = currentPlanet !== id;
    });
    var goal = view.goal || "";
    var done = planets[currentPlanet].contact;
    var line = done ? "Contact made. The crew has what it needs from this planet." : "Crew request: " + goal;
    if (done && currentPlanet === "bridge") line += " There are no further planets in range yet.";
    $("goal-line").textContent = line;
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

  // ---- planet 3: the bridge language ------------------------------------------------------------
  var NUMBER_TOKEN = /^0[01]{3}$/;
  function markerNode(letter) {
    var span = document.createElement("span");
    span.className = "glyph marker";
    span.setAttribute("role", "img");
    span.setAttribute("aria-label", "a small sign");
    span.appendChild(partSvg(letter));
    return span;
  }
  // One token of a message: a noun (two-part sign), a small sign (marker), or a number (pulses).
  function tokenOfMessage(token) {
    if (NUMBER_TOKEN.test(token)) return tokenNode(token);
    if (token.length === 1 && (view.components || {})[token] && "pnq".indexOf(token) !== -1) return markerNode(token);
    if ((view.components || {})[token[0]] !== undefined) return glyphNode(token);
    var other = document.createElement("span");
    other.textContent = token;
    return other;
  }
  function messageNode(tokens) {
    var wrap = document.createElement("span");
    wrap.className = "message";
    tokens.forEach(function (token) { wrap.appendChild(tokenOfMessage(token)); });
    return wrap;
  }
  function stockDiff(before, after) {
    var was = {}, now = {}, changes = [];
    before.items.forEach(function (i) { was[i.label] = i.count; });
    after.items.forEach(function (i) { now[i.label] = i.count; });
    Object.keys(now).concat(Object.keys(was).filter(function (l) { return !(l in now); })).forEach(function (label) {
      var from = was[label] || 0, to = now[label] || 0;
      if (from !== to) changes.push(label + ": " + from + " → " + to);
    });
    return changes.length ? changes.join("; ") : "no change";
  }
  function addToMessage(token) {
    if (outgoingMessage.length >= MAX_MESSAGE) return;
    outgoingMessage.push(token);
    renderBridge();
  }
  function bridgeButton(holder, node, label, token) {
    var btn = document.createElement("button");
    btn.type = "button";
    btn.appendChild(node);
    btn.setAttribute("aria-label", label);
    btn.addEventListener("click", function () { addToMessage(token); });
    holder.appendChild(btn);
  }

  function renderBridge() {
    var stock = $("b-stock");
    stock.textContent = "";
    view.stock.forEach(function (item) {
      var chip = document.createElement("span");
      chip.className = "stock-chip";
      var name = document.createElement("span");
      name.textContent = item.label;
      var count = document.createElement("span");
      count.className = "stock-count";
      count.textContent = "× " + item.count;
      chip.appendChild(name);
      chip.appendChild(count);
      stock.appendChild(chip);
    });
    if (!view.stock.length) stock.textContent = "Empty.";
    $("b-stock-text").textContent = view.stock_text;

    var list = $("b-scene-list");
    list.textContent = "";
    view.scenes.forEach(function (scene, index) {
      var li = document.createElement("li");
      li.className = "scene";
      var head = document.createElement("div");
      var label = document.createElement("strong");
      label.textContent = "Transmission " + (index + 1) + " ";
      head.appendChild(label);
      head.appendChild(messageNode(scene.message.split(" ")));
      var what = document.createElement("div");
      what.className = "what";
      what.innerHTML = "The counter: <b></b>";
      what.querySelector("b").textContent = stockDiff(scene.before, scene.after);
      li.appendChild(head);
      li.appendChild(what);
      if (scene.reply) {
        var said = document.createElement("div");
        said.className = "reply";
        said.textContent = "The station says: " + scene.reply;
        li.appendChild(said);
      }
      list.appendChild(li);
    });
    $("b-next-scene-button").disabled = view.scenes.length >= view.scenes_total;
    var status = view.scenes.length + " of " + view.scenes_total + " received.";
    if (view.settled) status += " You have seen enough to work out every small sign. Try one on a thing you were never shown it with.";
    $("b-scene-status").textContent = status;

    var nb = $("b-notebook-list");
    var keep = {};
    nb.querySelectorAll("input[type=checkbox]").forEach(function (box) { if (box.checked) keep[box.dataset.token] = true; });
    nb.textContent = "";
    view.markers.forEach(function (letter) {
      var li = document.createElement("li");
      var box = document.createElement("input");
      box.type = "checkbox";
      box.dataset.token = letter;
      box.checked = Boolean(keep[letter]);
      box.setAttribute("aria-label", "Include this small sign in the check");
      var input = document.createElement("input");
      input.type = "text";
      input.value = view.notebook[letter] || "";
      input.placeholder = "what does this sign do?";
      input.setAttribute("aria-label", "Your guess for this small sign");
      input.addEventListener("change", function () { send({ action: "write", form: letter, gloss: input.value }); });
      li.appendChild(box);
      li.appendChild(markerNode(letter));
      li.appendChild(input);
      nb.appendChild(li);
    });
    if (!view.markers.length) {
      var empty = document.createElement("li");
      empty.className = "note";
      empty.textContent = "Receive a transmission and any small signs in it will appear here.";
      nb.appendChild(empty);
    }

    var out = $("b-outgoing");
    out.textContent = "";
    if (outgoingMessage.length) out.appendChild(messageNode(outgoingMessage)); else out.textContent = "Nothing yet.";
    $("b-send-button").disabled = !outgoingMessage.length;
    $("b-back-button").disabled = !outgoingMessage.length;
    $("b-clear-button").disabled = !outgoingMessage.length;
    var nouns = $("b-noun-buttons");
    nouns.textContent = "";
    view.nouns.forEach(function (glyph) { bridgeButton(nouns, glyphNode(glyph), "Add this thing to your message", glyph); });
    var markers = $("b-marker-buttons");
    markers.textContent = "";
    view.markers.forEach(function (letter) { bridgeButton(markers, markerNode(letter), "Add this small sign to your message", letter); });
    if (!view.markers.length) markers.textContent = "None yet.";
    var numbers = $("b-number-buttons");
    numbers.textContent = "";
    view.numbers.forEach(function (token) { bridgeButton(numbers, tokenNode(token), "Add the number " + describeMarks(token), token); });
  }

  var knownEarned = null;
  function renderAchievements() {
    var list = $("achievements-list");
    list.textContent = "";
    var earnedNow = [];
    (view.achievements || []).forEach(function (a) {
      var li = document.createElement("li");
      li.className = a.earned ? "earned" : "";
      var tick = document.createElement("span");
      tick.className = "tick";
      tick.textContent = a.earned ? "Earned" : "Not yet";
      var name = document.createElement("strong");
      name.textContent = " " + a.label + " ";
      var desc = document.createElement("span");
      desc.textContent = a.description;
      li.appendChild(tick);
      li.appendChild(name);
      li.appendChild(desc);
      list.appendChild(li);
      if (a.earned) earnedNow.push(a.id);
    });
    var done = earnedNow.length;
    $("achievements-toggle-button").textContent = "Achievements (" + done + "/" + (view.achievements || []).length + ")";
    if (knownEarned !== null) {
      earnedNow.filter(function (id) { return knownEarned.indexOf(id) === -1; }).forEach(function (id) {
        var a = view.achievements.filter(function (x) { return x.id === id; })[0];
        $("toast").textContent = "Achievement unlocked: " + a.label;
        setTimeout(function () { if ($("toast").textContent.indexOf(a.label) !== -1) $("toast").textContent = ""; }, 5000);
      });
    }
    knownEarned = earnedNow;
  }

  function render() {
    renderAchievements();
    renderTabs();
    if (currentPlanet === "bridge") { renderBridge(); return; }
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

  function wireBridge() {
    $("tab-bridge").addEventListener("click", function () { currentPlanet = "bridge"; send({ action: "open" }); });
    $("b-next-scene-button").addEventListener("click", function () { send({ action: "next_scene" }); });
    $("b-back-button").addEventListener("click", function () { outgoingMessage.pop(); renderBridge(); });
    $("b-clear-button").addEventListener("click", function () { outgoingMessage = []; renderBridge(); });
    $("b-send-button").addEventListener("click", function () {
      if (!outgoingMessage.length) return;
      var result = send({ action: "speak", message: outgoingMessage.join(" ") });
      if (result && result.reaction) $("b-reaction").textContent = (result.reaction.reply ? "The station says: " : "") + result.reaction.text;
      outgoingMessage = [];
      renderBridge();
    });
    $("b-check-button").addEventListener("click", function () {
      var forms = [];
      $("b-notebook-list").querySelectorAll("input[type=checkbox]").forEach(function (box) { if (box.checked) forms.push(box.dataset.token); });
      var out = $("b-check-result");
      if (!forms.length) { out.textContent = "Tick some entries first."; return; }
      var result = send({ action: "confirm", forms: forms });
      out.textContent = result ? result.right + " of the " + result.chosen + " ticked entries are right." : "";
    });
  }

  var TUTORIAL_STEPS = [
    { title: "Welcome, officer", text: "You are the communications officer on a survey ship. Each planet speaks a language nobody has translated. Your job is to work out what the signals mean, then answer. Skip any time and reopen this from the Tutorial button." },
    { selector: "#goal-line", title: "The crew's request", text: "The crew tells you what they need from each planet. When you manage it, contact is made and the next planet comes into range." },
    { selector: "#transmissions-panel", title: "Watch what happens", text: "Each transmission is a signal and what the station did when it arrived. Compare them: what stays the same, and what changes?" },
    { selector: "#notebook-panel", title: "Write your guesses", text: "Write what you think each group of marks means. Nothing here is marked right or wrong. Ticking entries and pressing Check tells you how many are right, never which." },
    { selector: "#transmit-panel", title: "Answer", text: "Build a signal and send it. The station answers in its own terms, and when it cannot understand you, it says why." },
    { title: "You are ready", text: "Every word can be worked out from what you are shown. Take your time." },
  ];

  function wire() {
    wireCompound();
    wireBridge();
    $("achievements-toggle-button").addEventListener("click", function () {
      var panel = $("achievements-panel");
      panel.hidden = !panel.hidden;
    });
    // The save widget loads a save directly into the engine; this redraws the page afterwards.
    window.lexisRefresh = function () { if (engine) send({ action: "open" }); };
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
    ["next-scene-button", "check-button", "add-0", "add-1", "back-button", "clear-button", "send-button", "c-next-scene-button", "c-check-button", "c-back-button", "c-clear-button", "c-send-button", "b-next-scene-button", "b-check-button", "b-back-button", "b-clear-button", "b-send-button"].forEach(function (id) { $(id).disabled = busy; });
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
    if (window.GameTutorial) window.GameTutorial.init(TUTORIAL_STEPS, { gameId: "lexis" });
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The station could not start (" + err + "). Reload to try again.";
  });
})();
