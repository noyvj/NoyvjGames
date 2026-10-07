/* Lexis view: glue only. The engine (game.py and its modules) holds every rule; this file draws what
   handle() returns and forwards what the player does. No game logic lives here. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["lang.py", "pulse.py", "parse.py", "world.py", "scenes.py", "deduce.py", "notebook.py", "compound.py", "compound_scenes.py", "deduce_compound.py", "glyphs.py", "achievements.py", "bridge.py", "bridge_scenes.py", "deduce_bridge.py", "story.py", "report.py", "info.py"];
  var STORE_KEY = "lexis:state";
  var BRIEF_KEY = "lexis:brief-seen";
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

  // ---- accessibility helpers -------------------------------------------------------------------
  // Live regions only announce when their text really changes, so assign through setText.
  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }
  // A control that cannot be used right now stays focusable (aria-disabled) so focus is never thrown to the
  // page top when the button the player just pressed turns itself off; its click handler checks the flag.
  function setEnabled(id, enabled) {
    var btn = $(id);
    if (enabled) btn.removeAttribute("aria-disabled"); else btn.setAttribute("aria-disabled", "true");
  }
  function isOff(btn) { return btn.disabled || btn.getAttribute("aria-disabled") === "true"; }
  function guard(id, handler) { $(id).addEventListener("click", function () { if (!isOff($(id))) handler(); }); }
  // Said out loud to screen-reader players without moving focus (a new transmission, a contact).
  function announce(text) {
    var live = $("announce");
    live.textContent = "";
    setTimeout(function () { live.textContent = text; }, 40);
  }
  // Rebuild a group of controls only when WHAT it holds changes, so a focused button or field survives the
  // redraw that follows every action. `signature` is any string that changes when the contents should.
  function fillOnce(container, signature, build) {
    if (container.dataset.signature === signature) return false;
    container.textContent = "";
    build(container);
    container.dataset.signature = signature;
    return true;
  }
  // Notebook rows are rebuilt only when the set of entries changes; otherwise each field just takes the
  // engine's stored text, unless the player is typing in it.
  function syncNotebookValues(list) {
    list.querySelectorAll("input[type=text]").forEach(function (input) {
      var stored = (view.notebook || {})[input.dataset.token] || "";
      if (document.activeElement !== input && input.value !== stored) input.value = stored;
    });
  }
  function ordinalIn(list, code) { var i = (list || []).indexOf(code); return i === -1 ? 0 : i + 1; }

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

  // The newest transmission is highlighted (an effect, switchable) and read out; the redraws that follow a
  // notebook edit or a tab change are not new transmissions and stay quiet.
  var shownScenes = { pulse: null, compound: null, bridge: null };
  function noteScenes(planet, list) {
    var count = view.scenes.length, before = shownScenes[planet];
    shownScenes[planet] = count;
    if (before === null || count <= before || !list.lastElementChild) return;
    var last = list.lastElementChild;
    last.classList.add("fresh");
    var said = last.querySelector(".reply");
    announce("Transmission " + count + " received. " + last.querySelector(".what").textContent + (said ? " " + said.textContent : ""));
  }

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
    setText($("lamp-count"), n + " of 7 lit");
    var door = $("door");
    setText(door, "Door: " + view.station.door.toUpperCase());
    door.className = "door " + view.station.door;
    setText($("station-text"), view.station_text);
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
    noteScenes("pulse", list);
    var left = view.scenes_total - view.scenes.length;
    setEnabled("next-scene-button", left !== 0);
    var status = view.scenes.length + " of " + view.scenes_total + " received.";
    if (view.settled) status += " You have seen enough to work out every word. Try sending a signal.";
    setText($("scene-status"), status);
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
        input.addEventListener("change", function () { send({ action: "write", form: token, gloss: input.value }); });
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
    for (var i = 0; i < outgoing.length; i += TOKEN_LEN) {
      var chunk = outgoing.slice(i, i + TOKEN_LEN);
      var token = tokenNode(chunk);
      if (chunk.length < TOKEN_LEN) {
        for (var p = chunk.length; p < TOKEN_LEN; p++) { var pend = document.createElement("span"); pend.className = "mark-pending"; token.appendChild(pend); }
      }
      out.appendChild(token);
    }
    if (!outgoing) { out.textContent = "Nothing yet."; }
    setEnabled("send-button", Boolean(outgoing));
    setEnabled("back-button", Boolean(outgoing));
    setEnabled("clear-button", Boolean(outgoing));
    var tokens = seenTokens();
    fillOnce($("token-buttons"), tokens.join(","), function (holder) {
      tokens.forEach(function (token, index) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.appendChild(tokenNode(token));
        btn.setAttribute("aria-label", "Add group " + (index + 1) + " (" + describeMarks(token) + ")");
        btn.addEventListener("click", function () { addMarks(token); });
        holder.appendChild(btn);
      });
    });
  }

  var knownUnlocked = { pulse: null, compound: null, bridge: null };
  function tabLabel(n, info) {
    return "Planet " + n + (info.unlocked ? (info.contact ? " (contact made)" : "") : " (not in range yet)");
  }

  function renderTabs() {
    var planets = view.planets;
    planetsInfo = planets;
    var tabs = { pulse: $("tab-pulse"), compound: $("tab-compound"), bridge: $("tab-bridge") };
    ["pulse", "compound", "bridge"].forEach(function (id, index) {
      if (knownUnlocked[id] === false && planets[id].unlocked) showToast("Planet " + (index + 1) + " is now in range.");
      knownUnlocked[id] = planets[id].unlocked;
      tabs[id].disabled = !planets[id].unlocked;
      tabs[id].textContent = tabLabel(index + 1, planets[id]);
      tabs[id].setAttribute("aria-pressed", String(currentPlanet === id));
      $("planet-" + id).hidden = currentPlanet !== id;
    });
    var goal = view.goal || "";
    var done = planets[currentPlanet].contact;
    var line = done ? "Contact made. The crew has what it needs from this planet." : "Crew request: " + goal;
    if (done && currentPlanet === "bridge") line += " There are no further planets in range yet.";
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
    var thing = ordinalIn(view.nouns, glyph);       // planet 3: a noun is named by its place in the list of things
    var names = glyph.split("").map(function (code) { var n = ordinalIn(view.letters, code); return n ? "part " + n : "a part"; });
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
    view.tray.forEach(function (label) {
      var item = document.createElement("span");
      item.className = "tray-item";
      item.textContent = label;
      tray.appendChild(item);
    });
    if (!view.tray.length) tray.textContent = "Empty.";
    setText($("c-tray-text"), view.tray_text);

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
    noteScenes("compound", list);
    setEnabled("c-next-scene-button", view.scenes.length < view.scenes_total);
    var status = view.scenes.length + " of " + view.scenes_total + " received.";
    if (view.settled) status += " You have seen enough to work out every part. Try a sign you were never shown.";
    setText($("c-scene-status"), status);

    var nb = $("c-notebook-list");
    fillOnce(nb, view.letters.join(","), function () {
      view.letters.forEach(function (code, index) {
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
    });
    syncNotebookValues(nb);

    var out = $("c-outgoing");
    out.textContent = "";
    if (outgoingGlyph) out.appendChild(glyphNode(outgoingGlyph)); else out.textContent = "Nothing yet.";
    setEnabled("c-send-button", Boolean(outgoingGlyph));
    setEnabled("c-back-button", Boolean(outgoingGlyph));
    setEnabled("c-clear-button", Boolean(outgoingGlyph));
    fillOnce($("c-part-buttons"), view.letters.join(","), function (holder) {
      view.letters.forEach(function (code, index) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.appendChild(partSvg(code));
        btn.setAttribute("aria-label", "Add part " + (index + 1) + " to your sign");
        btn.addEventListener("click", function () { addPart(code); });
        holder.appendChild(btn);
      });
    });
  }

  // ---- planet 3: the bridge language ------------------------------------------------------------
  var NUMBER_TOKEN = /^0[01]{3}$/;
  function markerNode(letter) {
    var span = document.createElement("span");
    span.className = "glyph marker";
    span.setAttribute("role", "img");
    var n = ordinalIn(view.markers, letter);
    span.setAttribute("aria-label", n ? "small sign " + n : "a small sign");
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
    setText($("b-stock-text"), view.stock_text);

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
    noteScenes("bridge", list);
    setEnabled("b-next-scene-button", view.scenes.length < view.scenes_total);
    var status = view.scenes.length + " of " + view.scenes_total + " received.";
    if (view.settled) status += " You have seen enough to work out every small sign. Try one on a thing you were never shown it with.";
    setText($("b-scene-status"), status);

    var nb = $("b-notebook-list");
    fillOnce(nb, view.markers.join(","), function () {
      view.markers.forEach(function (letter, index) {
        var li = document.createElement("li");
        var box = document.createElement("input");
        box.type = "checkbox";
        box.dataset.token = letter;
        box.setAttribute("aria-label", "Include small sign " + (index + 1) + " in the check");
        var input = document.createElement("input");
        input.type = "text";
        input.dataset.token = letter;
        input.placeholder = "what does this sign do?";
        input.setAttribute("aria-label", "Your guess for small sign " + (index + 1));
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
    });
    syncNotebookValues(nb);

    var out = $("b-outgoing");
    out.textContent = "";
    if (outgoingMessage.length) out.appendChild(messageNode(outgoingMessage)); else out.textContent = "Nothing yet.";
    setEnabled("b-send-button", outgoingMessage.length > 0);
    setEnabled("b-back-button", outgoingMessage.length > 0);
    setEnabled("b-clear-button", outgoingMessage.length > 0);
    fillOnce($("b-noun-buttons"), view.nouns.join(","), function (holder) {
      view.nouns.forEach(function (glyph, index) { bridgeButton(holder, glyphNode(glyph), "Add thing " + (index + 1) + " to your message", glyph); });
    });
    fillOnce($("b-marker-buttons"), view.markers.join(",") || "-", function (holder) {
      view.markers.forEach(function (letter, index) { bridgeButton(holder, markerNode(letter), "Add small sign " + (index + 1) + " to your message", letter); });
      if (!view.markers.length) holder.textContent = "None yet.";
    });
    fillOnce($("b-number-buttons"), view.numbers.join(","), function (holder) {
      view.numbers.forEach(function (token) { bridgeButton(holder, tokenNode(token), "Add the number group " + describeMarks(token), token); });
    });
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
        showToast("Achievement unlocked: " + a.label + ".");
      });
    }
    knownEarned = earnedNow;
  }


  // ---- story, contact report and the About page ------------------------------------------------
  function el(tag, text, className) {
    var node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function storyEntry(entry) {
    var wrap = el("article", undefined, "log-entry");
    wrap.appendChild(el("h3", entry.title));
    entry.lines.forEach(function (line) {
      var p = el("p", undefined, "log-line");
      p.appendChild(el("strong", line.speaker + ": "));
      p.appendChild(document.createTextNode(line.text));
      wrap.appendChild(p);
    });
    return wrap;
  }
  var knownBeats = null;
  function showToast(text) {
    var toast = $("toast");
    toast.textContent = toast.textContent ? toast.textContent + " " + text : text;
    setTimeout(function () { if (toast.textContent.indexOf(text) !== -1) toast.textContent = ""; }, 6000);
  }
  function renderStory() {
    var holder = $("crew-log-entries");
    holder.textContent = "";
    var story = view.story || { beats: [] };
    story.beats.forEach(function (beat) { holder.appendChild(storyEntry(beat)); });
    if (story.brief) holder.appendChild(storyEntry(story.brief));    // the oldest entry sits last
    var count = story.beats.length;
    if (knownBeats !== null && count > knownBeats) showToast("New crew log entry: " + story.beats[0].title + ".");
    knownBeats = count;
  }

  var knownReport = null;
  function reportPlanet(p) {
    var wrap = el("section", undefined, "report-planet");
    wrap.appendChild(el("h3", p.name));
    var list = el("ul");
    p.learned.forEach(function (line) { list.appendChild(el("li", line)); });
    wrap.appendChild(list);
    wrap.appendChild(el("p", "Transmissions you needed: " + p.transmissions + " of " + p.transmissions_total +
      ". Messages you sent: " + p.sent + ". Notebook entries right: " + p.right + " of the " + p.written + " you wrote.", "note"));
    return wrap;
  }
  function renderReport() {
    var report = view.report;
    var button = $("report-toggle-button");
    button.hidden = !report;
    if (!report) { $("report-panel").hidden = true; $("report-body").textContent = ""; knownReport = false; return; }
    var body = $("report-body");
    body.textContent = "";
    report.planets.forEach(function (p) { body.appendChild(reportPlanet(p)); });
    var t = report.totals;
    body.appendChild(el("p", "In all: " + t.transmissions + " transmissions received, " + t.sent + " messages sent, and " +
      t.right + " of your " + t.written + " notebook entries were right.", "report-total"));
    body.appendChild(el("h3", "Achievements earned: " + report.achievements.length + " of " + report.achievements_total));
    var ul = el("ul");
    report.achievements.forEach(function (a) { ul.appendChild(el("li", a.label + ": " + a.description)); });
    body.appendChild(ul);
    if (knownReport === false) {      // first contact with planet 3 in this session: show it
      $("report-panel").hidden = false;
      setToggleState("report-toggle-button", "report-panel");
    }
    knownReport = true;
  }

  function renderInfo() {
    var info = view.info;
    if (!info) return;
    $("info-page-framing").textContent = info.framing;
    var list = $("info-page-sources");
    list.textContent = "";
    info.facts.forEach(function (fact) {
      var item = el("li", undefined, "info-page-source");
      if (fact.locked) {
        item.appendChild(el("strong", "Locked"));
        item.appendChild(el("p", "Make contact with planet " + ({ pulse: 1, compound: 2, bridge: 3 })[fact.unlock] + " to read this one.", "info-page-source-note"));
        list.appendChild(item);
        return;
      }
      item.appendChild(el("strong", fact.heading));
      item.appendChild(el("p", fact.fact, "info-page-framing"));
      item.appendChild(el("p", fact.tie_in, "info-page-tie-in"));
      var link = el("a", fact.source.title);
      link.href = fact.source.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      var src = el("p", undefined, "info-page-source-note");
      src.appendChild(document.createTextNode("Source: "));
      src.appendChild(link);
      src.appendChild(document.createTextNode(", " + fact.source.publisher + ". Read on " + fact.source.date_read + "."));
      item.appendChild(src);
      list.appendChild(item);
    });
  }

  // ---- what's new --------------------------------------------------------------------------------
  // The page sets window.CHANGELOG_JSON (the raw text of changelog.json) for shared/whats-new-banner.js, which
  // reads it to show a returning player only what they have not seen; the panel below shows the whole history.
  function renderChangelog(entries) {
    var holder = $("changelog-entries");
    holder.textContent = "";
    entries.forEach(function (entry) {
      var row = el("article", undefined, "changelog-entry");
      row.appendChild(el("div", entry.date, "changelog-date"));
      row.appendChild(el("p", entry.entry, "changelog-text"));
      holder.appendChild(row);
    });
    $("changelog-toggle-button").textContent = "What's New (" + entries.length + ")";
  }
  function loadChangelog() {
    return fetch("changelog.json").then(function (r) { return r.text(); }).then(function (text) {
      window.CHANGELOG_JSON = text;
      var data = JSON.parse(text);
      var list = Array.isArray(data) ? data : (data && data.changelog) || [];
      renderChangelog(list.slice().sort(function (a, b) { return a.date < b.date ? 1 : -1; }));
    }).catch(function () { renderChangelog([]); });
  }

  function setToggleState(buttonId, panelId) {
    $(buttonId).setAttribute("aria-expanded", String(!$(panelId).hidden));
  }
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () {
      $(panelId).hidden = !$(panelId).hidden;
      setToggleState(buttonId, panelId);
    });
  }

  function render() {
    renderAchievements();
    renderStory();
    renderReport();
    renderInfo();
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
  function addPart(code) {
    if (outgoingGlyph.length >= 4) return;
    outgoingGlyph += code;
    renderCompound();
  }
  function checkedForms(listId) {
    var forms = [];
    $(listId).querySelectorAll("input[type=checkbox]").forEach(function (box) { if (box.checked) forms.push(box.dataset.token); });
    return forms;
  }
  function wireCheck(buttonId, listId, resultId) {
    guard(buttonId, function () {
      var forms = checkedForms(listId);
      var out = $(resultId);
      if (!forms.length) { setText(out, "Tick some entries first."); return; }
      var result = send({ action: "confirm", forms: forms });
      var text = result ? result.right + " of the " + result.chosen + " ticked entries are right." : "";
      out.textContent = "";
      setTimeout(function () { out.textContent = text; }, 40);   // re-announced even when the answer is unchanged
    });
  }

  function wireCompound() {
    $("tab-pulse").addEventListener("click", function () { currentPlanet = "pulse"; send({ action: "open" }); });
    $("tab-compound").addEventListener("click", function () { currentPlanet = "compound"; send({ action: "open" }); });
    guard("c-next-scene-button", function () { send({ action: "next_scene" }); });
    guard("c-back-button", function () { outgoingGlyph = outgoingGlyph.slice(0, -1); renderCompound(); });
    guard("c-clear-button", function () { outgoingGlyph = ""; renderCompound(); });
    guard("c-send-button", function () {
      if (!outgoingGlyph) return;
      var result = send({ action: "speak", glyph: outgoingGlyph });
      if (result && result.reaction) $("c-reaction").textContent = result.reaction.text;
      outgoingGlyph = "";
      renderCompound();
    });
    wireCheck("c-check-button", "c-notebook-list", "c-check-result");
  }

  function wireBridge() {
    $("tab-bridge").addEventListener("click", function () { currentPlanet = "bridge"; send({ action: "open" }); });
    guard("b-next-scene-button", function () { send({ action: "next_scene" }); });
    guard("b-back-button", function () { outgoingMessage.pop(); renderBridge(); });
    guard("b-clear-button", function () { outgoingMessage = []; renderBridge(); });
    guard("b-send-button", function () {
      if (!outgoingMessage.length) return;
      var result = send({ action: "speak", message: outgoingMessage.join(" ") });
      if (result && result.reaction) $("b-reaction").textContent = (result.reaction.reply ? "The station says: " : "") + result.reaction.text;
      outgoingMessage = [];
      renderBridge();
    });
    wireCheck("b-check-button", "b-notebook-list", "b-check-result");
  }

  var TUTORIAL_STEPS = [
    { title: "Welcome, officer", text: "You are the communications officer on a survey ship. Each planet speaks a language nobody has translated. Your job is to work out what the signals mean, then answer. Skip any time and reopen this from the Tutorial button." },
    { selector: "#goal-line", title: "The crew's request", text: "The crew tells you what they need from each planet. When you manage it, contact is made and the next planet comes into range." },
    { selector: "#transmissions-panel", title: "Watch what happens", text: "Each transmission is a signal and what the station did when it arrived. Compare them: what stays the same, and what changes?" },
    { selector: "#notebook-panel", title: "Write your guesses", text: "Write what you think each group of marks means. Nothing here is marked right or wrong. Ticking entries and pressing Check tells you how many are right, never which." },
    { selector: "#transmit-panel", title: "Answer", text: "Build a signal and send it. The station answers in its own terms, and when it cannot understand you, it says why." },
    { selector: "#tab-compound", title: "Planet 2", text: "When planet 1 answers, a second world comes into range. Its signs are built from parts, so learning the parts lets you read signs nobody showed you." },
    { selector: "#tab-bridge", title: "Planet 3", text: "The third world builds on the first two: things you learned on planet 2, numbers from planet 1, and a few new marks that change what a message does. Contact here needs a particular result on its counter, and the crew tells you which." },
    { selector: "#crew-log-toggle-button", title: "Crew log", text: "Each contact adds an entry from the crew, newest first, with the mission brief at the bottom. The story never says what a sign means. The Story button, bottom left, hides it." },
    { selector: "#settings-toggle-button", title: "Settings", text: "Text size, reduced motion, an effects switch, high contrast and the light or dark theme. The page follows your system's reduced-motion and theme choices until you pick your own. The What's New button lists every change to Lexis." },
    { selector: "#info-page-toggle-button", title: "About Lexis", text: "Real-world facts behind the game, each with its source named and the date it was read. After you reach planet 3, a Contact report also appears, telling you which of your notebook entries were right." },
    { title: "You are ready", text: "Every word can be worked out from what you are shown. Take your time." },
  ];

  // ---- keyboard ---------------------------------------------------------------------------------
  // Everything is already reachable with Tab (real buttons, tick boxes and fields). These add speed inside a
  // Transmit panel (only while focus is in it, never page-wide) and arrow-key movement along a row of buttons.
  var BUILDERS = {
    pulse: { keys: { s: function () { addMarks("0"); }, l: function () { addMarks("1"); } },
             back: function () { outgoing = outgoing.slice(0, -1); renderTransmit(); },
             clear: function () { outgoing = ""; renderTransmit(); } },
    compound: { keys: {},
                back: function () { outgoingGlyph = outgoingGlyph.slice(0, -1); renderCompound(); },
                clear: function () { outgoingGlyph = ""; renderCompound(); } },
    bridge: { keys: {},
              back: function () { outgoingMessage.pop(); renderBridge(); },
              clear: function () { outgoingMessage = []; renderBridge(); } },
  };
  function focusSibling(button, step) {
    var row = button.closest(".token-buttons, .builder");
    var all = Array.prototype.slice.call(row.querySelectorAll("button"));
    var at = all.indexOf(button);
    var next = step === "first" ? all[0] : step === "last" ? all[all.length - 1] : all[at + step];
    if (next) next.focus();
  }
  function onKey(e) {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    var target = e.target;
    if (!target || !target.closest || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
    var rowKey = { ArrowLeft: -1, ArrowRight: 1, Home: "first", End: "last" }[e.key];
    if (rowKey !== undefined && target.tagName === "BUTTON" && target.closest(".token-buttons, .builder")) {
      e.preventDefault();
      focusSibling(target, rowKey);
      return;
    }
    var panel = target.closest("[data-builder]");
    if (!panel) return;
    var builder = BUILDERS[panel.getAttribute("data-builder")];
    if (!builder) return;
    if (e.key === "Backspace") { e.preventDefault(); builder.back(); return; }
    if (e.key === "Delete") { e.preventDefault(); builder.clear(); return; }
    var add = builder.keys[e.key.toLowerCase()];
    if (add && e.key.length === 1) { e.preventDefault(); add(); }
  }

  function wire() {
    wireCompound();
    wireBridge();
    wirePanelToggle("achievements-toggle-button", "achievements-panel");
    wirePanelToggle("crew-log-toggle-button", "crew-log-panel");
    wirePanelToggle("report-toggle-button", "report-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    // The save widget loads a save directly into the engine; this redraws the page afterwards.
    window.lexisRefresh = function () {
      if (!engine) return;
      shownScenes = { pulse: null, compound: null, bridge: null };   // a loaded save is not a new transmission
      send({ action: "open" });
    };
    guard("next-scene-button", function () { send({ action: "next_scene" }); });
    guard("add-0", function () { addMarks("0"); });
    guard("add-1", function () { addMarks("1"); });
    guard("back-button", BUILDERS.pulse.back);
    guard("clear-button", BUILDERS.pulse.clear);
    guard("send-button", function () {
      if (!outgoing) return;
      var result = send({ action: "speak", marks: outgoing });
      if (result && result.reaction) $("reaction").textContent = result.reaction.text;
      outgoing = "";
      renderTransmit();
    });
    wireCheck("check-button", "notebook-list", "check-result");
    document.addEventListener("keydown", onKey);
  }

  function setBusy(busy) {
    ["next-scene-button", "check-button", "add-0", "add-1", "back-button", "clear-button", "send-button", "c-next-scene-button", "c-check-button", "c-back-button", "c-clear-button", "c-send-button", "b-next-scene-button", "b-check-button", "b-back-button", "b-clear-button", "b-send-button"].forEach(function (id) { $(id).disabled = busy; });
  }

  async function boot() {
    setBusy(true);
    var changelog = loadChangelog();      // the panel and the shared what's-new banner do not need the engine
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
    if (lsGet(BRIEF_KEY) === null) {      // the mission brief opens by itself the first time only
      $("crew-log-panel").hidden = false;
      setToggleState("crew-log-toggle-button", "crew-log-panel");
      lsSet(BRIEF_KEY, "seen");
    }
    await changelog;
    if (window.GameTutorial) window.GameTutorial.init(window.lexisTutorialSteps ? window.lexisTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS, { gameId: "lexis" });
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The station could not start (" + err + "). Reload to try again.";
  });
})();
