/* Lighthouse view: glue only. The engine (game.py and its modules) holds every rule; this file draws what
   handle() returns and forwards what the player does. No game logic lives here (the one exception is the oil
   estimate in the evening plan, which only repeats the engine's published burn rates as a hint). */
/* The page script is cut into six classic scripts that share ONE object, window.LighthouseApp (see the File map in
   CLAUDE.md). They load in this order and each is its own function, so no new global names exist:
     app-1-core.js      constants, helpers, shared state set-up (creates window.LighthouseApp)
     app-2-scene.js     scene palettes, the SVG scene, ships, status strip, goals
     app-3-story.js     letters, sailors, gifts, the room, the notebook, odd lights
     app-4-phases.js    the evening, night, morning and day panels, the supply order
     app-5-render.js    year end, station, log, About, achievements, changelog, phases, render(), sound
     app.js             talking to the engine, seeds, settings, wiring, tutorial, keys, boot (loads last)
   State that more than one part uses lives on the object: A.view, A.knownEarned, A.lastPhase, A.lastLogCount,
   A.orderDraft, A.reducedMotion, A.knownUnread. A function another part calls is exported as A.name at the end of
   its own part. */
(function () {
  "use strict";

  var A = window.LighthouseApp = {};
  A.view = null;
  A.knownEarned = null;
  A.lastPhase = null;
  A.lastLogCount = 0;
  A.orderDraft = null;
  A.reducedMotion = false;

  var ENGINE_MODULES = ["rng.py", "data.py", "clock.py", "weather.py", "ships.py", "state.py", "sim.py", "day.py", "achievements.py", "goals.py", "lore.py", "cast.py", "story.py", "mysteries.py", "unease.py", "info.py", "view.py"];
  var STORE_KEY = "lighthouse:state";
  var QUIET_KEY = "lighthouse-quiet";
  var EERIE_KEY = "lighthouse-eerie";
  var NOTE_KEY = "lighthouse-content-note";
  var HUM_KEY = "lighthouse-sfx-hum";
  var GAME_ID = "lighthouse";
  var BASE_MS = 4000;
  var SVG_NS = "http://www.w3.org/2000/svg";

  var $ = function (id) { return document.getElementById(id); };
  var busy = false;

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }
  function lsRemove(k) { try { localStorage.removeItem(k); } catch (e) { /* convenience only */ } }

  // ---- small helpers ---------------------------------------------------------------------------------
  function el(tag, text, className) {
    var node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function svgEl(tag, attrs) {
    var node = document.createElementNS(SVG_NS, tag);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    return node;
  }
  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }
  function setEnabled(node, enabled) {
    if (typeof node === "string") node = $(node);
    if (enabled) node.removeAttribute("aria-disabled"); else node.setAttribute("aria-disabled", "true");
  }
  function isOff(btn) { return btn.disabled || btn.getAttribute("aria-disabled") === "true"; }
  function guard(id, handler) { $(id).addEventListener("click", function () { if (!isOff($(id))) handler(); }); }
  function announce(text) {
    var live = $("announce");
    live.textContent = "";
    setTimeout(function () { live.textContent = text; }, 40);
  }
  function showToast(text) {
    var toast = $("toast");
    toast.textContent = toast.textContent ? toast.textContent + " " + text : text;
    setTimeout(function () { if (toast.textContent.indexOf(text) !== -1) toast.textContent = ""; }, 6000);
  }
  // Rebuild a group only when WHAT it holds changes, so a focused control survives the redraw that follows
  // every tick and every action.
  function fillOnce(container, signature, build) {
    if (container.dataset.signature === signature) return false;
    container.textContent = "";
    build(container);
    container.dataset.signature = signature;
    return true;
  }
  function plural(n, one, many) { return n + " " + (n === 1 ? one : (many || one + "s")); }
  function clockLabel(startMin, tickMin, tick) {
    var m = (startMin + tick * tickMin) % 1440;
    return ("0" + Math.floor(m / 60)).slice(-2) + ":" + ("0" + (m % 60)).slice(-2);
  }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function hexToRgb(h) { return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]; }
  function mix(h1, h2, t) {
    var a = hexToRgb(h1), b = hexToRgb(h2);
    return "#" + [0, 1, 2].map(function (i) { return ("0" + Math.round(lerp(a[i], b[i], t)).toString(16)).slice(-2); }).join("");
  }
  function isLight() { return document.documentElement.getAttribute("data-theme") === "light"; }

  // what the other parts use (see the File map in CLAUDE.md)
  A.$ = $; A.BASE_MS = BASE_MS; A.EERIE_KEY = EERIE_KEY; A.ENGINE_MODULES = ENGINE_MODULES;
  A.GAME_ID = GAME_ID; A.HUM_KEY = HUM_KEY; A.NOTE_KEY = NOTE_KEY; A.QUIET_KEY = QUIET_KEY;
  A.STORE_KEY = STORE_KEY; A.announce = announce; A.clockLabel = clockLabel; A.el = el; A.fillOnce = fillOnce;
  A.guard = guard; A.isLight = isLight; A.isOff = isOff; A.lsGet = lsGet; A.lsRemove = lsRemove;
  A.lsSet = lsSet; A.mix = mix; A.plural = plural; A.setEnabled = setEnabled; A.setText = setText;
  A.showToast = showToast; A.svgEl = svgEl;
})();
