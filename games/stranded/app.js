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

  // ---- panels --------------------------------------------------------------------------------------
  function wirePanelToggle(buttonId, panelId) {
    $(buttonId).addEventListener("click", function () {
      $(panelId).hidden = !$(panelId).hidden;
      $(buttonId).setAttribute("aria-expanded", String(!$(panelId).hidden));
    });
  }
  function loadChangelog() {
    return fetch("changelog.json").then(function (r) { return r.text(); }).then(function (text) {
      window.CHANGELOG_JSON = text;
    }).catch(function () { /* the panel just stays empty */ });
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
    var items = view.transcript;
    var count = Math.min(shown, items.length);
    chat.textContent = "";
    for (var i = 0; i < count; i++) chat.appendChild(bubble(items[i]));
    if (count < items.length) {
      var next = el("button", "next-msg primary", "Next message");
      next.type = "button";
      next.dataset.testid = "stranded-next";
      next.addEventListener("click", function () { shown = Math.min(items.length, shown + 1); renderChat(); renderChoices(); focusNext(); });
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
    var waiting = shown < view.transcript.length;
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

  function render() {
    renderStats();
    renderHead();
    renderChat();
    renderChoices();
    renderEnding();
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
    var before = view ? view.transcript.length : 0;
    var oldShown = shown;
    shown = 1e9;
    var result = send({ action: "choose", i: i });
    if (result && result.ok) {
      var items = result.transcript;
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
    $("restart-button").addEventListener("click", function () { shown = 1e9; send({ action: "restart" }); });
    $("reset-button").addEventListener("click", function () {
      askThen("stranded-reset", "Start the whole story over? Your map, archive, endings and counts will be erased.", "Erase it", function () { shown = 1e9; send({ action: "reset" }); });
    });
    document.addEventListener("keydown", onKey);
    document.addEventListener("stranded-reveal-change", function () { if (view && !tapMode()) { shown = 1e9; render(); } });
    // The save widget loads a save straight into the engine; this redraws afterwards.
    window.strandedRefresh = function () { if (engine) { shown = 1e9; send({ action: "open" }); } };
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
  }

  wire();
  boot().catch(function (err) {
    $("engine-status").textContent = "The line could not open (" + err + "). Reload to try again.";
  });
})();
