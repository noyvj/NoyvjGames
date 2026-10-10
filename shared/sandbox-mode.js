/*
 * Shared practice-sandbox toggle (planning/TODO.md Z-18).
 *
 * A game that offers a "practice sandbox" (no fail states, every tool open, the real save and the
 * achievements untouched) keeps ALL of that logic in its own code. This file is only the plumbing the
 * games share: the button that enters and leaves, the "Sandbox: nothing here is saved" banner, a dashed
 * frame round the window, and the announcements for screen readers. It knows nothing about any game.
 *
 * Adopting it in a game:
 *   1. A button (or several, e.g. one in the Classic toolbar that the Desktop menu then lists) marked
 *        <button id="sandbox-toggle-button" type="button" data-sandbox-toggle>Practice sandbox</button>
 *      The button's own text is the "enter" label and is kept; while the sandbox is on it reads
 *      "Leave sandbox" and it has aria-pressed="true". Clicks are caught by delegation, so a button the
 *      Desktop shell moves into its menu keeps working.
 *   2. One tag, after the game's save widget:
 *        <script src="../../shared/sandbox-mode.js" data-game-id="grid"></script>
 *      with  <link rel="stylesheet" href="../../shared/sandbox-mode.css">  in the head.
 *   3. Three functions in the game's Python (names can be changed with data-enter, data-leave and
 *      data-active on the tag):
 *        sandbox_enter()   -> True when the sandbox is now on (or already was)
 *        sandbox_leave()   -> True when the real game is back
 *        sandbox_is_active() -> True while the sandbox is on
 *      A game that is not written in Pyodide (or a test) passes the same three functions to
 *      NoyvjSandbox.configure({ enter, leave, active }) instead.
 *
 * The rules the GAME must keep (each is tested in every adopting game):
 *   - entering never changes the real game: it is set aside whole and put back unchanged on leaving;
 *   - get_state() answers with the REAL game while the sandbox is on, so the save widget (Save, the
 *     5-minute autosave, the leaderboard hooks) can never write the sandbox;
 *   - nothing in the sandbox earns an achievement, banks a career or ladder, or writes browser storage;
 *   - loading a save leaves the sandbox first (the game then calls NoyvjSandbox.sync()).
 *
 * The sandbox lives in memory only: reloading the page leaves it, and the real game is simply the
 * saved game. Nothing here stores anything.
 *
 * API (window.NoyvjSandbox): enter(), leave(), toggle(), active(), sync(), configure(opts), onChange(fn),
 * bannerText. A change is also announced with a "noyvj-sandbox-change" event on document
 * ({ detail: { active, gameId } }) and html[data-sandbox="true"] is set while it is on, so a game's CSS
 * can react to it.
 */
(function (root) {
  "use strict";
  if (root.NoyvjSandbox) return;

  var doc = root.document;
  var script = doc.currentScript;
  var data = (script && script.dataset) || {};

  var BANNER_ID = "noyvj-sandbox-banner";
  var LIVE_ID = "noyvj-sandbox-live";
  var TOGGLE_SELECTOR = data.toggle || "[data-sandbox-toggle]";
  var LEAVE_LABEL = "Leave sandbox";
  var BANNER_TEXT = "Sandbox: nothing here is saved.";
  var BANNER_SUB = "Your real game is safe and unchanged.";

  var cfg = {
    gameId: data.gameId || "game",
    enter: data.enter || "sandbox_enter",
    leave: data.leave || "sandbox_leave",
    active: data.active || "sandbox_is_active",
    handlers: null,
  };
  var on = false;
  var listeners = [];
  var banner = null;
  var live = null;

  function pyCall(name) {
    var fn = null;
    try {
      var py = root.pyodide;
      fn = py && py.globals ? py.globals.get(name) : null;
    } catch (e) { fn = null; }
    if (!fn) return { ok: false, missing: true };
    try {
      var value = fn();
      if (value && typeof value.toJs === "function") {
        var plain = value.toJs();
        if (value.destroy) value.destroy();
        value = plain;
      }
      return { ok: true, value: value };
    } catch (e) {
      return { ok: false, error: e };
    } finally {
      if (fn.destroy) fn.destroy();
    }
  }

  function run(which) {
    var custom = cfg.handlers && cfg.handlers[which];
    if (typeof custom === "function") {
      try { return { ok: true, value: custom() }; } catch (e) { return { ok: false, error: e }; }
    }
    return pyCall(cfg[which]);
  }

  function say(text) {
    if (!live) {
      live = doc.createElement("div");
      live.id = LIVE_ID;
      live.className = "noyvj-sandbox-live";
      live.setAttribute("role", "status");
      live.setAttribute("aria-live", "polite");
      (doc.body || doc.documentElement).appendChild(live);
    }
    live.textContent = "";
    // A second tick so a repeated message is announced again.
    root.setTimeout(function () { live.textContent = text; }, 30);
  }

  function ensureBanner() {
    if (banner) return banner;
    banner = doc.createElement("div");
    banner.id = BANNER_ID;
    banner.className = "noyvj-sandbox-banner";
    banner.hidden = true;
    var text = doc.createElement("p");
    text.className = "noyvj-sandbox-text";
    var strong = doc.createElement("strong");
    strong.textContent = "Sandbox:";
    text.appendChild(strong);
    text.appendChild(doc.createTextNode(" nothing here is saved."));
    var sub = doc.createElement("span");
    sub.className = "noyvj-sandbox-sub";
    sub.textContent = BANNER_SUB;
    text.appendChild(sub);
    var button = doc.createElement("button");
    button.type = "button";
    button.className = "noyvj-sandbox-leave";
    button.setAttribute("data-sandbox-leave", "");
    button.textContent = LEAVE_LABEL;
    banner.appendChild(text);
    banner.appendChild(button);
    (doc.body || doc.documentElement).appendChild(banner);
    return banner;
  }

  function paintToggles() {
    var nodes = doc.querySelectorAll(TOGGLE_SELECTOR);
    for (var i = 0; i < nodes.length; i += 1) {
      var el = nodes[i];
      if (el.getAttribute("data-sandbox-enter-label") === null) {
        el.setAttribute("data-sandbox-enter-label", (el.textContent || "").trim() || "Practice sandbox");
      }
      el.textContent = on ? LEAVE_LABEL : el.getAttribute("data-sandbox-enter-label");
      el.setAttribute("aria-pressed", on ? "true" : "false");
    }
    var statuses = doc.querySelectorAll("[data-sandbox-status]");
    for (var j = 0; j < statuses.length; j += 1) {
      statuses[j].textContent = on ? "Sandbox on. Nothing you do here is saved." : "";
    }
  }

  function paint() {
    ensureBanner().hidden = !on;
    if (on) doc.documentElement.setAttribute("data-sandbox", "true");
    else doc.documentElement.removeAttribute("data-sandbox");
    paintToggles();
  }

  function broadcast() {
    for (var i = 0; i < listeners.length; i += 1) {
      try { listeners[i](on); } catch (e) { /* a listener must not break the others */ }
    }
    try {
      doc.dispatchEvent(new root.CustomEvent("noyvj-sandbox-change", { detail: { active: on, gameId: cfg.gameId } }));
    } catch (e) { /* very old browser: the listeners above already ran */ }
  }

  // Re-reads the game's answer and repaints; fires the change event only when it really changed.
  function sync() {
    var result = run("active");
    var next = result.ok ? Boolean(result.value) : false;
    var changed = next !== on;
    on = next;
    paint();
    if (changed) broadcast();
    return on;
  }

  function enter() {
    if (on) return true;
    var result = run("enter");
    if (!result.ok) {
      say(result.missing ? "The game is still loading. Try again in a moment." : "The sandbox could not start.");
      var statuses = doc.querySelectorAll("[data-sandbox-status]");
      for (var i = 0; i < statuses.length; i += 1) {
        statuses[i].textContent = result.missing ? "The game is still loading. Try again in a moment." : "The sandbox could not start.";
      }
      return false;
    }
    sync();
    if (on) say("Sandbox on. Nothing you do here is saved. Your real game is unchanged.");
    return on;
  }

  function leave() {
    if (!on) return true;
    var result = run("leave");
    if (!result.ok) {
      say("Could not leave the sandbox. Try again.");
      return false;
    }
    sync();
    if (!on) say("Sandbox off. Your real game is back exactly as you left it.");
    return !on;
  }

  function toggle() { return on ? leave() : enter(); }

  doc.addEventListener("click", function (event) {
    var target = event.target;
    if (!target || !target.closest) return;
    if (target.closest("[data-sandbox-leave]")) {
      leave();
      return;
    }
    var button = target.closest(TOGGLE_SELECTOR);
    if (button && !button.disabled) {
      event.preventDefault();
      toggle();
    }
  });

  root.NoyvjSandbox = {
    enter: enter,
    leave: leave,
    toggle: toggle,
    sync: sync,
    active: function () { return on; },
    configure: function (opts) {
      opts = opts || {};
      if (opts.gameId) cfg.gameId = String(opts.gameId);
      ["enter", "leave", "active"].forEach(function (key) {
        if (typeof opts[key] === "function") {
          cfg.handlers = cfg.handlers || {};
          cfg.handlers[key] = opts[key];
        } else if (typeof opts[key] === "string") {
          cfg[key] = opts[key];
        }
      });
      return root.NoyvjSandbox;
    },
    onChange: function (fn) {
      if (typeof fn === "function") listeners.push(fn);
    },
    bannerText: BANNER_TEXT,
  };

  function ready() {
    paint();
  }
  if (doc.readyState === "loading") doc.addEventListener("DOMContentLoaded", ready);
  else ready();
})(window);
