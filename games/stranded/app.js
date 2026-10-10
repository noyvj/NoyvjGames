/* Stranded view: glue only. The engine (game.py and its modules) holds every rule and the whole story; this file draws what
   handle() returns and forwards what the player does. No story and no game logic live here. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["kit.py", "story_1.py", "story_2.py", "story_3.py", "story_4.py", "story.py", "walker.py", "explore.py", "lore.py", "info.py", "achievements.py", "render.py"];
  var STORE_KEY = "stranded:state";
  var BACKUP_KEY = "stranded:state-backup";

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;
  var view = null;
  var shown = 0;          // how many chat items are showing (all of them unless messages arrive one at a time)

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }
  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }
  function announce(text) {
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
  function showToast(text) {
    var t = $("toast");
    t.textContent = text;
    t.classList.toggle("on", Boolean(text));
  }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : many); }
  function tapMode() { return document.documentElement.getAttribute("data-reveal") === "tap"; }
  // Harbour's day-start log line is text only and off by default (Settings turns it on); the Story pill can also hide it. A hidden line
  // is dropped from the list here, so it never costs a tap in one-at-a-time mode.
  function narratorShown() {
    var root = document.documentElement;
    return root.getAttribute("data-narrator") === "on" && root.getAttribute("data-story-text") !== "off";
  }
  function listOf(transcript) {
    var keep = narratorShown();
    return transcript.filter(function (t) { return t.kind !== "narrator" || keep; });
  }

  // ---- panels --------------------------------------------------------------------------------------
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () {
      $(panelId).hidden = !$(panelId).hidden;
      $(buttonId).setAttribute("aria-expanded", String(!$(panelId).hidden));
    });
  }
  function renderAbout() {
    var about = view.about;
    if (!about || $("pledge-list").dataset.done) return;
    $("pledge-list").dataset.done = "1";
    setText($("info-page-framing"), about.framing);
    setText($("info-page-notice"), about.notice);
    setText($("pledge-heading"), about.pledge_heading);
    setText($("how-heading"), about.how_heading);
    setText($("facts-heading"), about.facts_heading);
    about.pledge.forEach(function (line) { $("pledge-list").appendChild(el("li", null, line)); });
    about.how.forEach(function (line) { $("how-list").appendChild(el("li", null, line)); });
    about.facts.forEach(function (f) {
      var li = el("li");
      li.appendChild(el("span", "fact-head", f.heading));
      li.appendChild(el("span", null, f.fact + " "));
      li.appendChild(el("span", "note", f.tie_in));
      var src = el("span", "fact-source", "Source: ");
      var link = el("a", null, f.source.title);
      link.href = f.source.url; link.target = "_blank"; link.rel = "noopener noreferrer";
      src.appendChild(link);
      src.appendChild(document.createTextNode(", " + f.source.publisher + ". Read on " + f.source.date_read + "."));
      li.appendChild(src);
      $("facts-list").appendChild(li);
    });
  }
  function renderChangelog(entries) {
    var holder = $("changelog-entries");
    holder.textContent = "";
    entries.forEach(function (entry) {
      var row = el("article", "changelog-entry");
      row.appendChild(el("div", "changelog-date", entry.date));
      row.appendChild(el("p", "changelog-text", entry.entry));
      holder.appendChild(row);
    });
    document.querySelector("#changelog-toggle-button .btn-long").textContent = "What's New (" + entries.length + ")";
  }
  function loadChangelog() {
    return fetch("changelog.json").then(function (r) { return r.text(); }).then(function (text) {
      window.CHANGELOG_JSON = text;
      var data = JSON.parse(text);
      var list = Array.isArray(data) ? data : (data && data.changelog) || [];
      renderChangelog(list.slice().sort(function (a, b) { return a.date < b.date ? 1 : -1; }));
    }).catch(function () { renderChangelog([]); });
  }

  // ---- numbers -------------------------------------------------------------------------------------
  function bumpValue(id, value) {
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
    var r = view.run;
    bumpValue("stat-day-value", r.day + "/" + r.days);
    setText($("stat-day-word"), r.day_title);
    view.stats.forEach(function (s) {
      bumpValue("stat-" + s.id + "-value", s.value);
      setText($("stat-" + s.id + "-word"), s.word);
      $("stat-" + s.id + "-fill").style.width = Math.round(100 * s.value / s.max) + "%";
      $("stat-" + s.id).setAttribute("aria-label", s.name + " " + s.value + " of " + s.max + ", " + s.word);
    });
    var p = view.progress;
    bumpValue("stat-scenes", p.scenes[0] + "/" + p.scenes[1]);
    bumpValue("stat-paths", p.tried[0] + "/" + p.tried[1]);
    bumpValue("stat-endings", p.endings[0] + "/" + p.endings[1]);
    bumpValue("stat-archive", p.archive[0] + "/" + p.archive[1]);
    setText($("percent-label"), "Completion " + p.percent + "%");
    $("percent-fill").style.width = p.percent + "%";
  }

  // ---- the conversation ----------------------------------------------------------------------------
  function bubble(item) {
    var node;
    if (item.kind === "day") return el("div", "day-sep", item.text);
    if (item.kind === "narrator") return el("div", "narrator", item.text);
    if (item.kind === "action") return el("div", "action", item.text);
    if (item.kind === "delta") return el("div", "chip", item.text);
    if (item.kind === "found") return el("div", "chip found", item.text);
    if (item.kind === "ines") {
      node = el("div", "msg ines");
      node.appendChild(el("span", "msg-who", "Ines"));
      node.appendChild(document.createTextNode(item.text));
      return node;
    }
    node = el("div", "msg you");
    node.appendChild(el("span", "msg-who", "You"));
    node.appendChild(document.createTextNode(item.text));
    var b = el("button", "rewind-btn", "Rewind to here");
    b.type = "button";
    b.dataset.testid = "stranded-rewind-" + item.step;
    b.setAttribute("aria-label", "Rewind to before this reply: " + item.text);
    b.addEventListener("click", function () { shown = 1e9; send({ action: "rewind", step: item.step }); });
    node.appendChild(b);
    return node;
  }
  function renderChat() {
    var chat = $("chat");
    var items = listOf(view.transcript);
    var count = Math.min(shown, items.length);
    chat.textContent = "";
    for (var i = 0; i < count; i++) chat.appendChild(bubble(items[i]));
    if (count < items.length) {
      var next = el("button", "next-msg primary", "Next message");
      next.type = "button";
      next.dataset.testid = "stranded-next";
      next.addEventListener("click", function () { shown = Math.min(items.length, shown + 1); renderChat(); renderChoices(); renderPeek(); focusNext(); });
      chat.appendChild(next);
    }
    chat.scrollTop = chat.scrollHeight;
  }
  function focusNext() {
    var n = document.querySelector(".next-msg");
    if (n) n.focus();
  }
  function renderChoices() {
    var holder = $("choices");
    holder.textContent = "";
    var waiting = shown < listOf(view.transcript).length;
    if (waiting || view.ending) return;
    view.choices.forEach(function (c) {
      var b = el("button", "choice" + (c.ok ? "" : " locked"));
      b.type = "button";
      b.dataset.testid = "stranded-choice-" + c.i;
      b.appendChild(el("span", "num", String(c.i + 1)));
      b.appendChild(document.createTextNode(c.text));
      if (c.tried) b.appendChild(el("span", "tag", "Tried"));
      if (!c.ok) {
        b.setAttribute("aria-disabled", "true");
        b.appendChild(el("span", "why", c.why));
      }
      b.setAttribute("aria-label", (c.i + 1) + ". " + c.text + (c.tried ? ". Tried before" : "") + (c.ok ? "" : ". Shut for now: " + c.why));
      b.addEventListener("click", function () { choose(c.i); });
      holder.appendChild(b);
    });
  }
  function renderEnding() {
    var e = view.ending;
    $("ending-card").hidden = !e;
    if (e) setText($("ending-title"), e.title);
  }
  function renderHead() {
    if ($("scene-holder").dataset.sig !== view.art.length + ":" + view.run.scene + view.run.flags.join(",")) {
      $("scene-holder").dataset.sig = view.art.length + ":" + view.run.scene + view.run.flags.join(",");
      $("scene-holder").innerHTML = view.art;
    }
    if (!$("who-portrait").dataset.done) { $("who-portrait").innerHTML = view.portrait; $("who-portrait").dataset.done = "1"; }
    setText($("who-line"), "Day " + view.run.day + " · " + view.run.title);
  }

  // ---- goals, hints, the Archive -------------------------------------------------------------------
  function renderGoals() {
    var list = $("goals-list");
    var sig = view.goals.map(function (g) { return g.id + g.have; }).join(",");
    if (list.dataset.sig === sig) return;
    list.dataset.sig = sig;
    list.textContent = "";
    if (!view.goals.length) { list.appendChild(el("li", null, "Every goal is done. Thank you for taking the whole line.")); return; }
    view.goals.forEach(function (g) {
      var li = el("li");
      li.appendChild(el("strong", null, g.label + ": "));
      li.appendChild(document.createTextNode(g.description + " "));
      var bar = el("span", "bar");
      bar.setAttribute("aria-hidden", "true");
      var fill = el("span", "bar-fill");
      fill.style.width = Math.round(100 * g.have / g.need) + "%";
      bar.appendChild(fill);
      li.appendChild(bar);
      li.appendChild(el("span", "goal-count", " " + g.have + "/" + g.need));
      list.appendChild(li);
    });
  }
  function renderHints() {
    var h = view.hint;
    var btn = $("hint-button");
    btn.hidden = h.rung >= 3;
    setText(btn, h.rung === 0 ? "Would you like a suggestion?" : (h.rung === 1 ? "Another hint" : "Another hint: the answer"));
    $("hint-nudge").hidden = !h.nudge;
    setText($("hint-nudge"), h.nudge ? "Nudge: " + h.nudge : "");
    $("hint-hint").hidden = !h.hint;
    setText($("hint-hint"), h.hint ? "Hint: " + h.hint : "");
    $("hint-answer").hidden = !h.answer;
    if (h.answer) {
      setText($("hint-answer-text"), "Answer: " + h.answer);
      setText($("hint-do-button"), h.do || "Take me there");
      $("hint-do-button").hidden = h.kind === "none";
    }
  }
  var knownEarned = null;
  function renderAchievements() {
    var list = $("achievements-list");
    var earnedNow = [];
    var sig = view.achievements.map(function (a) { return a.id + a.have; }).join(",");
    if (list.dataset.sig !== sig) {
      list.dataset.sig = sig;
      list.textContent = "";
      view.achievements.forEach(function (a) {
        var li = el("li", a.earned ? "earned" : "");
        li.setAttribute("data-achievement-id", a.id);
        li.appendChild(el("span", "tick", a.earned ? "Earned" : a.have + "/" + a.need));
        var name = el("strong", null, " " + a.label + " ");
        name.setAttribute("data-achievement-label", "");
        li.appendChild(name);
        li.appendChild(el("span", null, a.description));
        list.appendChild(li);
      });
    }
    view.achievements.forEach(function (a) { if (a.earned) earnedNow.push(a.id); });
    $("achievements-toggle-button").textContent = "Achievements (" + earnedNow.length + "/" + view.achievements.length + ")";
    if (knownEarned !== null) {
      earnedNow.filter(function (id) { return knownEarned.indexOf(id) === -1; }).forEach(function (id) {
        var a = view.achievements.filter(function (x) { return x.id === id; })[0];
        showToast("Achievement unlocked: " + a.label + ".");
        announce("Achievement unlocked: " + a.label + ".");
      });
    }
    knownEarned = earnedNow;
  }
  function renderTally() {
    var t = view.tally;
    bumpValue("stat-sent", t.sent);
    bumpValue("stat-rewinds", t.rewinds);
    bumpValue("stat-peeks", t.peeks);
    bumpValue("stat-jumps", t.jumps);
    bumpValue("stat-hints", t.hints);
  }
  function renderArchive() {
    var p = view.progress;
    var sig = p.archive[0] + ":" + p.archive[1];
    if ($("archive-body").dataset.sig === sig) return;
    $("archive-body").dataset.sig = sig;
    setText($("archive-summary"), p.archive[0] + " of " + p.archive[1] + " pages filed. Pages are found by playing: nothing can be missed for good, and rewinding never takes one away. A page you have not found shows where to look.");
    var body = $("archive-body");
    body.textContent = "";
    view.archive.forEach(function (sec) {
      var d = el("details", "archive-section");
      d.appendChild(el("summary", null, sec.name + " (" + sec.found + "/" + sec.total + ")"));
      var ul = el("ul", "archive-list");
      sec.entries.forEach(function (e) {
        var li = el("li", e.found ? "filed" : "unfiled");
        li.appendChild(el("strong", null, e.title));
        li.appendChild(el("span", "rtext", e.found ? e.text : "Where to look: " + e.text));
        ul.appendChild(li);
      });
      d.appendChild(ul);
      body.appendChild(d);
    });
  }

  // ---- the what-if peek ----------------------------------------------------------------------------
  function renderPeek() {
    var p = view.peek;
    var btn = $("peek-button");
    var list = $("peek-list");
    var visible = !view.ending && view.choices.length > 0 && shown >= listOf(view.transcript).length;
    $("under-choices").hidden = !visible;
    list.hidden = !(visible && p.showing);
    btn.setAttribute("aria-expanded", String(visible && p.showing));
    btn.classList.toggle("locked", !p.open);
    btn.setAttribute("aria-disabled", p.open ? "false" : "true");
    setText($("peek-note"), p.open ? "" : "Opens once you have tried " + plural(p.need, "more different reply", "more different replies") + " in this scene.");
    list.textContent = "";
    if (!p.showing) return;
    p.rows.forEach(function (r) {
      var c = view.choices[r.i];
      var li = el("li");
      li.appendChild(el("strong", null, (r.i + 1) + ". "));
      li.appendChild(document.createTextNode(c.text + " \u2192 " + (r.locked ? "shut for now: " + r.locked : r.to) + (r.tried ? " (tried)" : " (not tried)")));
      list.appendChild(li);
    });
  }

  // ---- the branch map ------------------------------------------------------------------------------
  function renderMap() {
    var p = view.progress;
    setText($("map-summary"), plural(p.scenes[0], "scene", "scenes") + " seen of " + p.scenes[1] + ", " + p.tried[0] + " of " + p.tried[1] + " paths walked.");
    $("map-overview").innerHTML = view.map_svg;
    setText($("endings-count"), "(" + p.endings[0] + "/" + p.endings[1] + ")");
    var ends = $("endings-list");
    ends.textContent = "";
    view.endings.forEach(function (e) {
      var li = el("li", e.seen ? "seen" : "unseen");
      li.appendChild(el("span", null, e.seen ? e.title : "Not found yet"));
      if (e.seen) li.appendChild(goButton(e.scene, e.title));
      ends.appendChild(li);
    });
    var body = $("map-body");
    var open = {};
    Array.prototype.forEach.call(body.querySelectorAll("details"), function (d) { open[d.dataset.day] = d.open; });
    body.textContent = "";
    view.map.forEach(function (d) {
      var here = d.nodes.some(function (n) { return n.current; });
      var loose = d.nodes.some(function (n) { return n.loose; });
      var det = el("details", "map-day-block");
      det.dataset.day = String(d.day);
      det.open = open[d.day] !== undefined ? open[d.day] : here;
      var found = d.nodes.length - d.unseen;
      det.appendChild(el("summary", null, "Day " + d.day + ": " + d.title + " (" + found + "/" + d.nodes.length + " scenes" + (loose ? ", loose ends" : "") + ")"));
      d.nodes.forEach(function (n) {
        var row = el("div", "map-scene" + (n.seen ? "" : " unseen"));
        var head = el("div", "map-scene-head");
        head.appendChild(el("span", "map-scene-title", n.seen ? n.title + (n.end ? " (ending)" : "") : "Not found yet"));
        if (n.current) head.appendChild(el("span", "here-tag", "You are here"));
        else if (n.seen) head.appendChild(goButton(n.id, n.title));
        row.appendChild(head);
        if (n.seen && n.choices.length) {
          var ul = el("ul", "map-choices");
          n.choices.forEach(function (c) {
            var li = el("li", c.tried ? "tried" : "untried");
            if (c.tried) li.textContent = "Reply " + (c.i + 1) + ", walked: " + c.text + (c.to.length ? " \u2192 " + c.to.join(" / ") : "") + (c.paths_left ? " (another path from this reply is not walked yet)" : "");
            else li.textContent = "Reply " + (c.i + 1) + ": not tried yet";
            ul.appendChild(li);
          });
          row.appendChild(ul);
        }
        det.appendChild(row);
      });
      body.appendChild(det);
    });
  }
  function goButton(sceneId, title) {
    var b = el("button", "map-go", "Go there");
    b.type = "button";
    b.dataset.testid = "stranded-go-" + sceneId;
    b.setAttribute("aria-label", "Go to " + title);
    b.addEventListener("click", function () {
      shown = 1e9;
      send({ action: "goto", scene: sceneId });
      $("map-panel").hidden = true;
      $("map-toggle-button").setAttribute("aria-expanded", "false");
      $("comms-panel").scrollIntoView && $("comms-panel").scrollIntoView({ block: "start" });
    });
    return b;
  }

  function render() {
    renderAbout();
    renderStats();
    renderHead();
    renderChat();
    renderChoices();
    renderEnding();
    renderPeek();
    renderMap();
    renderGoals();
    renderHints();
    renderTally();
    renderArchive();
    renderAchievements();
  }

  // ---- talking to the engine -----------------------------------------------------------------------
  function persist() {
    try {
      var proxy = engine.getState();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(STORE_KEY, JSON.stringify(obj));
    } catch (e) { /* the save widget keeps the real copy */ }
  }
  function send(request) {
    if (!engine) return null;
    var result = JSON.parse(engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    view = result;
    showToast(result.ok ? "" : result.message);
    render();
    setText($("action-line"), result.ok ? (result.message || "") : "");
    if (result.message) announce(result.message);
    persist();
    return result;
  }
  function choose(i) {
    var before = view ? listOf(view.transcript).length : 0;
    var oldShown = shown;
    shown = 1e9;
    var result = send({ action: "choose", i: i });
    if (result && result.ok) {
      var items = listOf(result.transcript);
      var added = items.slice(before).filter(function (t) { return t.kind === "ines" || t.kind === "action" || t.kind === "narrator"; }).map(function (t) { return t.text; });
      if (added.length) announce(added.join(" "));
      if (tapMode()) { shown = Math.min(items.length, before + 1); render(); focusNext(); }
    } else {
      shown = oldShown;
    }
  }

  // ---- keyboard ------------------------------------------------------------------------------------
  function onKey(e) {
    if (!view || e.ctrlKey || e.metaKey || e.altKey) return;
    var tag = e.target && e.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (document.querySelector("dialog[open], .confirm-dialog, [role='dialog']")) return;
    var n = parseInt(e.key, 10);
    if (e.key.length === 1 && n >= 1 && n <= view.choices.length && $("choices").children.length) choose(n - 1);
  }

  function askThen(id, message, confirmLabel, go) {
    if (window.ConfirmDialog) window.ConfirmDialog.ask({ id: id, message: message, confirmLabel: confirmLabel, allowSkip: false, onConfirm: go });
    else go();
  }

  function wire() {
    $("toast").addEventListener("click", function () { showToast(""); });
    wirePanelToggle("settings-toggle-button", "settings-panel");
    wirePanelToggle("map-toggle-button", "map-panel");
    wirePanelToggle("archive-toggle-button", "archive-panel");
    wirePanelToggle("achievements-toggle-button", "achievements-panel");
    wirePanelToggle("changelog-toggle-button", "changelog-panel");
    wirePanelToggle("info-page-toggle-button", "info-page-panel");
    $("hint-button").addEventListener("click", function () { send({ action: "hint" }); });
    $("hint-do-button").addEventListener("click", function () { shown = 1e9; send({ action: "hint_do" }); });
    $("peek-button").addEventListener("click", function () { send({ action: "peek" }); });
    $("loose-button").addEventListener("click", function () {
      shown = 1e9;
      var r = send({ action: "loose" });
      if (r && r.ok) {
        $("map-panel").hidden = true;
        $("map-toggle-button").setAttribute("aria-expanded", "false");
        $("comms-panel").scrollIntoView && $("comms-panel").scrollIntoView({ block: "start" });
      }
    });
    $("restart-button").addEventListener("click", function () { shown = 1e9; send({ action: "restart" }); });
    $("reset-button").addEventListener("click", function () {
      askThen("stranded-reset", "Start the whole story over? Your map, archive, endings and counts will be erased.", "Erase it", function () { shown = 1e9; send({ action: "reset" }); });
    });
    document.addEventListener("keydown", onKey);
    document.addEventListener("stranded-narrator-change", function () { if (view) { shown = 1e9; render(); } });
    new MutationObserver(function () { if (view) { shown = 1e9; render(); } }).observe(document.documentElement, { attributes: true, attributeFilter: ["data-story-text"] });
    document.addEventListener("stranded-reveal-change", function () { if (view && !tapMode()) { shown = 1e9; render(); } });
    // The save widget loads a save straight into the engine; this redraws afterwards.
    window.strandedRefresh = function () { if (engine) { shown = 1e9; knownEarned = null; send({ action: "open" }); } };
  }

  var TUTORIAL_STEPS = [
    { title: "Welcome to the line", text: "You are Harbour, the plain voice on a thin text line to Ines, a stubborn field engineer stuck on a small moon. Every reply you send gets an answer. Nothing is timed, and you can go back to any choice for free. Skip any time and reopen this from the Tutorial button." },
    { selector: "#chat", title: "The conversation", text: "Ines speaks on the left, you on the right. Each of your messages has a Rewind to here button: it takes you back to just before that reply, and nothing you found or tried is lost." },
    { selector: "#stats", title: "Trust, Supplies and Hope", text: "Your replies move these three numbers. They are always shown as a number, a word and a bar. They can open or shut some replies, and they help decide which of the ten endings you reach." },
    { selector: "#comms-panel", title: "Your replies", text: "Pick one of two to four replies. A reply marked Tried is one you have sent before. A shut reply says why it is shut: a different earlier choice can open it. After two different tries in a scene, What if? shows where each reply leads." },
    { selector: "#map-toggle-button", title: "The branch map", text: "Every day, scene and path. A day lists the scenes you have seen with a Go there button, and Show me a loose end takes you to the nearest path you have not walked." },
    { selector: "#goals", title: "Your goals", text: "Three goals stay in view, in any order. Every reply, rewind and find counts toward something on the screen." },
    { selector: "#archive-toggle-button", title: "The Archive", text: "Ines's log entries, the things she finds and her recordings are filed here as you play. Nothing can be missed for good." },
    { selector: "#hint-box", title: "Need a nudge?", text: "Only when you ask: a nudge, a hint, then the answer, and a button that takes you there." },
    { title: "You are ready", text: "Take your time. Your map and archive are saved as you go." }
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
    engine = { handle: pyodide.globals.get("handle"), getState: pyodide.globals.get("get_state"), loadState: pyodide.globals.get("load_state") };
    var saved = lsGet(STORE_KEY);
    if (saved && saved !== "{}") {
      lsSet(BACKUP_KEY, saved);      // kept until the next good save, so a load problem can never cost the player a game
      try { engine.loadState(pyodide.toPy(JSON.parse(saved))); } catch (e) { /* a bad save never blocks play */ }
    }
    $("engine-status").textContent = "";
    shown = 1e9;
    send({ action: "open" });
    await changelog;
    if (window.GameTutorial) window.GameTutorial.init(window.strandedTutorialSteps ? window.strandedTutorialSteps(TUTORIAL_STEPS) : TUTORIAL_STEPS, { gameId: "stranded" });
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The line could not open (" + err + "). Reload to try again.";
  });
})();
