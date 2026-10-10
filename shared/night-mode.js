/*
 * Shared warm night colours (planning/TODO.md QI-52). Opt-in: "Warm night colours after 10pm: the hub
 * and games shift to a dimmer, warmer palette automatically." Off by default. Three modes: off, auto
 * (on between a start and an end hour, default 22:00 to 06:00 by the device's own clock) and on. Three
 * strengths: soft, medium, deep. It works by adding one fixed, click-through, aria-hidden overlay that
 * multiplies the page by a warm amber (see night-mode.css), so no game needs its own CSS and no game
 * colour is edited. html[data-night="on"|"off"] and html[data-night-level] are set so a game's own CSS can
 * react, and a "noyvj-night-change" event is fired on document. The clock is read on load, when the tab
 * becomes visible again, on pageshow and on focus: there are no timers or intervals (a page left open
 * through 10pm shifts the next time you come back to it).
 *
 *   <link rel="stylesheet" href="../../shared/night-mode.css">   (optional: the script links it itself)
 *   <script src="../../shared/night-mode.js"></script>
 *
 * API (window.NoyvjNight):
 *   getMode() / setMode("off"|"auto"|"on")     stored in localStorage "noyvj-night:mode"
 *   getLevel() / setLevel("soft"|"medium"|"deep")  stored in "noyvj-night:level" (default medium)
 *   isActive()                                 true while the warm overlay is showing
 *   isNight(date?)                             true when the date falls inside the auto window
 *   configure({start, end, now})               hours 0-23 (default 22 and 6); now() for tests
 *   apply()                                    re-reads the clock and settings and updates the page
 *   mount(container, {title}) -> {refresh, destroy, element}   a settings control (two selects + a
 *                                              status sentence, announced politely)
 *   bindSelect(select, {level})                wire your own <select> (mode, or level) to the setting
 *   onChange(fn)                               fn({mode, level, active}) on every change; returns an unsubscribe function
 * Text is written with textContent only. Nothing here calls the network.
 */
(function () {
  "use strict";
  if (window.NoyvjNight) return;

  const MODE_KEY = "noyvj-night:mode";
  const LEVEL_KEY = "noyvj-night:level";
  const MODES = ["off", "auto", "on"];
  const LEVELS = ["soft", "medium", "deep"];
  const CSS_FILE = "night-mode.css";
  const listeners = [];
  const controls = new Set();
  const config = { start: 22, end: 6, now: () => new Date() };
  let overlay = null;
  let lastState = null;

  function ensureStylesheet() {
    if (typeof document === "undefined" || document.querySelector('link[href*="' + CSS_FILE + '"]')) return;
    const own = document.currentScript || Array.from(document.scripts).find((s) => /night-mode\.js/.test(s.src || ""));
    if (!own || !own.src) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = own.src.replace(/night-mode\.js(\?.*)?$/, CSS_FILE);
    document.head.append(link);
  }
  ensureStylesheet();

  function read(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }
  function write(key, value) {
    try { window.localStorage.setItem(key, value); } catch (e) { /* blocked storage: the choice lasts this page */ }
  }
  const memory = { mode: null, level: null };

  function getMode() {
    const stored = read(MODE_KEY);
    const value = MODES.indexOf(stored) >= 0 ? stored : memory.mode;
    return MODES.indexOf(value) >= 0 ? value : "off";
  }
  function getLevel() {
    const stored = read(LEVEL_KEY);
    const value = LEVELS.indexOf(stored) >= 0 ? stored : memory.level;
    return LEVELS.indexOf(value) >= 0 ? value : "medium";
  }

  function hourOf(date) {
    const d = date instanceof Date ? date : config.now();
    return d.getHours() + d.getMinutes() / 60;
  }
  /** True when `date` is inside the auto window; the window may wrap midnight (22 to 6). */
  function isNight(date) {
    const h = hourOf(date);
    const s = config.start, e = config.end;
    if (s === e) return false;
    return s < e ? h >= s && h < e : h >= s || h < e;
  }
  function isActive() {
    const mode = getMode();
    return mode === "on" || (mode === "auto" && isNight());
  }

  function ensureOverlay() {
    if (overlay && overlay.isConnected) return overlay;
    overlay = document.createElement("div");
    overlay.className = "noyvj-night-overlay";
    overlay.setAttribute("aria-hidden", "true");
    (document.body || document.documentElement).append(overlay);
    return overlay;
  }

  function statusText() {
    const mode = getMode();
    if (mode === "off") return "Warm night colours are off.";
    if (mode === "on") return "Warm night colours are on.";
    return isNight() ? "It is night time here, so the colours are warm now." : "Automatic: the colours turn warm after " + fmt(config.start) + " until " + fmt(config.end) + ".";
  }
  function fmt(h) {
    const hh = Math.floor(h), mm = Math.round((h - hh) * 60);
    return String(hh).padStart(2, "0") + ":" + String(mm).padStart(2, "0");
  }

  function apply() {
    const root = document.documentElement;
    const active = isActive();
    const level = getLevel();
    ensureOverlay();
    root.setAttribute("data-night", active ? "on" : "off");
    root.setAttribute("data-night-level", level);
    const state = { mode: getMode(), level: level, active: active };
    const changed = !lastState || lastState.mode !== state.mode || lastState.level !== state.level || lastState.active !== state.active;
    lastState = state;
    controls.forEach((c) => c.refresh(false));
    if (changed) {
      listeners.slice().forEach((fn) => { try { fn(state); } catch (e) { /* a listener must not break the page */ } });
      document.dispatchEvent(new CustomEvent("noyvj-night-change", { detail: state }));
    }
    return state;
  }

  function setMode(mode) {
    if (MODES.indexOf(mode) < 0) return false;
    memory.mode = mode;
    write(MODE_KEY, mode);
    apply();
    return true;
  }
  function setLevel(level) {
    if (LEVELS.indexOf(level) < 0) return false;
    memory.level = level;
    write(LEVEL_KEY, level);
    apply();
    return true;
  }

  function configure(opts) {
    if (!opts) return;
    const ok = (h) => typeof h === "number" && isFinite(h) && h >= 0 && h < 24;
    if (ok(opts.start)) config.start = opts.start;
    if (ok(opts.end)) config.end = opts.end;
    if (typeof opts.now === "function") config.now = opts.now;
    apply();
  }

  function el(tag, cls, text, attrs) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    if (attrs) for (const k of Object.keys(attrs)) n.setAttribute(k, attrs[k]);
    return n;
  }
  let uid = 0;
  const MODE_LABELS = { off: "Off", auto: "Automatic (after 10pm)", on: "Always on" };
  const LEVEL_LABELS = { soft: "Soft", medium: "Medium", deep: "Deep" };

  function fillSelect(select, values, labels) {
    select.textContent = "";
    values.forEach((v) => select.append(el("option", "", labels[v], { value: v })));
  }

  function mount(container, opts) {
    const host = typeof container === "string" ? document.querySelector(container) : container;
    if (!host) return null;
    opts = opts || {};
    uid += 1;
    const root = el("section", "noyvj-night-control", null, { "aria-labelledby": "noyvj-night-title-" + uid });
    root.append(el("h3", "", opts.title || "Warm night colours", { id: "noyvj-night-title-" + uid }));
    root.append(el("p", "", "A dimmer, warmer palette for late sessions. It is off by default, and it only changes how the screen looks."));
    const modeId = "noyvj-night-mode-" + uid, levelId = "noyvj-night-level-" + uid;
    const modeLabel = el("label", "", "When", { for: modeId });
    const modeSelect = el("select", "", null, { id: modeId });
    fillSelect(modeSelect, MODES, MODE_LABELS);
    const levelLabel = el("label", "", "Strength", { for: levelId });
    const levelSelect = el("select", "", null, { id: levelId });
    fillSelect(levelSelect, LEVELS, LEVEL_LABELS);
    const state = el("p", "noyvj-night-state", "", { role: "status", "aria-live": "polite" });
    root.append(modeLabel, modeSelect, levelLabel, levelSelect, state);
    host.append(root);
    let announce = false;
    const control = {
      element: root,
      refresh(speak) {
        modeSelect.value = getMode();
        levelSelect.value = getLevel();
        const text = statusText();
        if (state.textContent !== text && (speak !== false || announce)) state.textContent = text;
        else if (!state.textContent) state.textContent = text;
      },
      destroy() { controls.delete(control); root.remove(); },
    };
    modeSelect.addEventListener("change", () => { announce = true; setMode(modeSelect.value); control.refresh(true); });
    levelSelect.addEventListener("change", () => { announce = true; setLevel(levelSelect.value); control.refresh(true); });
    controls.add(control);
    control.refresh(false);
    return control;
  }

  function bindSelect(select, opts) {
    const node = typeof select === "string" ? document.querySelector(select) : select;
    if (!node) return null;
    const isLevel = !!(opts && opts.level);
    const values = isLevel ? LEVELS : MODES;
    const sync = () => { node.value = isLevel ? getLevel() : getMode(); };
    const handler = () => { if (values.indexOf(node.value) >= 0) (isLevel ? setLevel : setMode)(node.value); };
    node.addEventListener("change", handler);
    const off = onChange(sync);
    sync();
    return function unbind() { node.removeEventListener("change", handler); off(); };
  }

  /** Subscribes fn; returns a function that unsubscribes it. */
  function onChange(fn) {
    if (typeof fn !== "function") return function () {};
    listeners.push(fn);
    return function off() { const i = listeners.indexOf(fn); if (i >= 0) listeners.splice(i, 1); };
  }

  // The clock is re-read when the person comes back to the page, never on a timer.
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") apply(); });
  window.addEventListener("pageshow", apply);
  window.addEventListener("focus", apply);
  window.addEventListener("storage", (e) => { if (e.key === MODE_KEY || e.key === LEVEL_KEY) apply(); });

  window.NoyvjNight = { getMode, setMode, getLevel, setLevel, isActive, isNight, configure, apply, mount, bindSelect, onChange };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply);
  else apply();
})();
