/* Lexis, part 3 of 5: planet 3 (the bridge language), achievements, story, contact report, the About page and what's new. */
(function () {
  "use strict";

  var A = window.LexisApp;
  var $ = A.$, MAX_MESSAGE = A.MAX_MESSAGE, attachLongPress = A.attachLongPress, describeMarks = A.describeMarks,
      fillOnce = A.fillOnce, glyphNode = A.glyphNode, noteScenes = A.noteScenes, ordinalIn = A.ordinalIn,
      partSvg = A.partSvg, setEnabled = A.setEnabled, setText = A.setText,
      syncNotebookValues = A.syncNotebookValues, tokenNode = A.tokenNode;

  // ---- planet 3: the bridge language ------------------------------------------------------------
  var NUMBER_TOKEN = /^0[01]{3}$/;
  function markerNode(letter) {
    var span = document.createElement("span");
    span.className = "glyph marker";
    span.dataset.sign = letter;
    span.setAttribute("role", "img");
    var n = ordinalIn(A.view.markers, letter);
    span.setAttribute("aria-label", n ? "small sign " + n : "a small sign");
    span.appendChild(partSvg(letter));
    return span;
  }
  // One token of a message: a noun (two-part sign), a small sign (marker), or a number (pulses).
  function tokenOfMessage(token) {
    if (NUMBER_TOKEN.test(token)) return tokenNode(token);
    if (token.length === 1 && (A.view.components || {})[token] && "pnq".indexOf(token) !== -1) return markerNode(token);
    if ((A.view.components || {})[token[0]] !== undefined) return glyphNode(token);
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
    if (A.outgoingMessage.length >= MAX_MESSAGE) return;
    A.outgoingMessage.push(token);
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
    A.view.stock.forEach(function (item) {
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
    if (!A.view.stock.length) stock.textContent = "Empty.";
    setText($("b-stock-text"), A.view.stock_text);

    var list = $("b-scene-list");
    list.textContent = "";
    A.view.scenes.forEach(function (scene, index) {
      var li = document.createElement("li");
      li.className = "scene";
      var head = document.createElement("div");
      var label = document.createElement("strong");
      label.textContent = "Transmission " + (index + 1) + " ";
      head.appendChild(label);
      var msg = messageNode(scene.message.split(" "));
      head.appendChild(msg);
      attachLongPress(msg, scene.message);
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
    setEnabled("b-next-scene-button", A.view.scenes.length < A.view.scenes_total);
    var status = A.view.scenes.length + " of " + A.view.scenes_total + " received.";
    if (A.view.settled) status += " You have seen enough to work out every small sign. Try one on a thing you were never shown it with.";
    setText($("b-scene-status"), status);

    var nb = $("b-notebook-list");
    fillOnce(nb, A.view.markers.join(","), function () {
      A.view.markers.forEach(function (letter, index) {
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
        input.addEventListener("change", function () { A.send({ action: "write", form: letter, gloss: input.value }); });
        li.appendChild(box);
        li.appendChild(markerNode(letter));
        li.appendChild(input);
        nb.appendChild(li);
      });
      if (!A.view.markers.length) {
        var empty = document.createElement("li");
        empty.className = "note";
        empty.textContent = "Receive a transmission and any small signs in it will appear here.";
        nb.appendChild(empty);
      }
    });
    syncNotebookValues(nb);

    var out = $("b-outgoing");
    out.textContent = "";
    if (A.outgoingMessage.length) out.appendChild(messageNode(A.outgoingMessage)); else out.textContent = "Nothing yet.";
    setEnabled("b-send-button", A.outgoingMessage.length > 0);
    setEnabled("b-back-button", A.outgoingMessage.length > 0);
    setEnabled("b-clear-button", A.outgoingMessage.length > 0);
    fillOnce($("b-noun-buttons"), A.view.nouns.join(","), function (holder) {
      A.view.nouns.forEach(function (glyph, index) { bridgeButton(holder, glyphNode(glyph), "Add thing " + (index + 1) + " to your message", glyph); });
    });
    fillOnce($("b-marker-buttons"), A.view.markers.join(",") || "-", function (holder) {
      A.view.markers.forEach(function (letter, index) { bridgeButton(holder, markerNode(letter), "Add small sign " + (index + 1) + " to your message", letter); });
      if (!A.view.markers.length) holder.textContent = "None yet.";
    });
    fillOnce($("b-number-buttons"), A.view.numbers.join(","), function (holder) {
      A.view.numbers.forEach(function (token) { bridgeButton(holder, tokenNode(token), "Add the number group " + describeMarks(token), token); });
    });
  }

  var knownEarned = null;
  function renderAchievements() {
    var list = $("achievements-list");
    list.textContent = "";
    var earnedNow = [];
    (A.view.achievements || []).forEach(function (a) {
      var li = document.createElement("li");
      li.className = a.earned ? "earned" : "";
      li.setAttribute("data-achievement-id", a.id);
      var tick = document.createElement("span");
      tick.className = "tick";
      tick.textContent = a.earned ? "Earned" : "Not yet";
      var name = document.createElement("strong");
      name.setAttribute("data-achievement-label", "");
      name.textContent = " " + a.label + " ";
      var desc = document.createElement("span");
      desc.textContent = a.description;
      li.appendChild(tick);
      li.appendChild(name);
      li.appendChild(desc);
      if (a.riddle) {
        var riddleEl = document.createElement("p");
        riddleEl.className = "achievement-riddle";
        riddleEl.textContent = "Riddle: " + a.riddle;
        riddleEl.hidden = !a.earned;
        li.appendChild(riddleEl);
      }
      list.appendChild(li);
      if (a.earned) earnedNow.push(a.id);
    });
    var done = earnedNow.length;
    $("achievements-toggle-button").textContent = "Achievements (" + done + "/" + (A.view.achievements || []).length + ")";
    if (knownEarned !== null) {
      earnedNow.filter(function (id) { return knownEarned.indexOf(id) === -1; }).forEach(function (id) {
        var a = A.view.achievements.filter(function (x) { return x.id === id; })[0];
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
    var story = A.view.story || { beats: [] };
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
    var report = A.view.report;
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
    var info = A.view.info;
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

  // what the other parts use (see the File map in CLAUDE.md)
  A.addToMessage = addToMessage; A.loadChangelog = loadChangelog; A.renderAchievements = renderAchievements;
  A.renderBridge = renderBridge; A.renderInfo = renderInfo; A.renderReport = renderReport;
  A.renderStory = renderStory; A.setToggleState = setToggleState; A.showToast = showToast;
  A.tokenOfMessage = tokenOfMessage; A.wirePanelToggle = wirePanelToggle;
})();
