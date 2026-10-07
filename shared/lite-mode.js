/*
 * Site-wide "Lite mode" for slow computers (TODO Z-31). One switch for the hub and every game:
 * it sets <html data-lite="true|false"> BEFORE FIRST PAINT (include this script in <head>, not
 * async or deferred), and shared/lite-mode.css then turns off every animation, transition,
 * backdrop blur, animated background and large panel shadow.
 *
 * Storage: localStorage["lite-mode"] = "true" | "false" is the player's own choice. When the key
 * is absent the player has not chosen, and lite mode is switched on only if this device looks
 * slow (navigator.deviceMemory <= 2, navigator.hardwareConcurrency <= 2, or the browser's
 * data-saver / prefers-reduced-data setting). That automatic default is never silent: a small
 * note says so, with a button to turn it off, and either button records a choice so the note
 * does not come back. Signed-in players' choice follows their account through
 * shared/site-settings.js (setting "lite_mode"), the way text scale and theme do.
 *
 * API (window.NoyvjLite):
 *   on()              true while lite mode is active (chosen or automatic)
 *   set(bool)         the player's choice: stores it, applies it, fires the change event
 *   reset()           forget the choice and fall back to the automatic default
 *   refresh()         re-read localStorage (another tab, or a page that edited it directly)
 *   auto()            true while it is on only because of the device hint (not chosen)
 *   chosen()          true | false | null (null = not chosen yet)
 *   reasons()         why the device looks slow (array of short strings; may be empty)
 *   onChange(fn)      fn(on, detail) on every change; returns an unsubscribe function
 *   setFromSync(bool) used by site-settings.js: applies an account value without echoing it back
 * and a document event "noyvj-lite-change" with detail { on, auto, fromSync }.
 *
 * Any element with the attribute data-lite-toggle becomes the switch: a checkbox is kept
 * checked/unchecked, any other element is a button whose label reads "Lite mode: on|off" unless
 * it carries data-lite-label="none". Elements with data-lite-status get a one-line explanation.
 *
 * How the games use it: the shared CSS covers everything declarative. A game with its own costs
 * (a canvas loop, a 3D scene, JS-driven effects) checks NoyvjLite.on() and listens for the event
 * (see games/continuum/render3d.js). The games' own "reduce motion" switches are separate and
 * still work; lite mode is the broader, performance-minded superset and does not change them.
 */
(function () {
  "use strict";
  if (window.NoyvjLite) return;

  const KEY = "lite-mode";
  const NOTE_KEY = "lite-mode-note-seen";
  const root = document.documentElement;

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }
  function lsRemove(k) { try { localStorage.removeItem(k); } catch (e) { /* convenience only */ } }

  function readChoice() {
    const v = lsGet(KEY);
    return v === "true" ? true : v === "false" ? false : null;
  }

  function deviceReasons() {
    const out = [];
    try {
      const mem = navigator.deviceMemory;
      if (typeof mem === "number" && mem > 0 && mem <= 2) out.push(`about ${mem} GB of memory`);
      const cores = navigator.hardwareConcurrency;
      if (typeof cores === "number" && cores > 0 && cores <= 2) out.push(`${cores} processor core${cores === 1 ? "" : "s"}`);
      if (window.matchMedia && window.matchMedia("(prefers-reduced-data: reduce)").matches) out.push("a data-saver setting");
    } catch (e) { /* unknown device: no hint */ }
    return out;
  }

  const hint = deviceReasons();
  let choice = readChoice();
  let current = choice !== null ? choice : hint.length > 0;
  const listeners = [];

  function paint() { root.setAttribute("data-lite", String(current)); }
  paint(); // before first paint: this script runs in <head>

  function isAuto() { return choice === null && current; }

  function describe() {
    if (current && choice === true) return "Lite mode is on. Animations, blurs and moving backgrounds are off everywhere on the site.";
    if (current) return `Lite mode is on because this device looks slow (${hint.join(", ")}). Turn it off if the site feels fine.`;
    if (choice === false && hint.length) return "Lite mode is off. This device looks slow, so turn it on if the site feels sluggish.";
    return "Lite mode is off. Turn it on if the site or a game feels slow: it switches off animations, blurs and moving backgrounds.";
  }

  function syncToggles() {
    document.querySelectorAll("[data-lite-toggle]").forEach((el) => {
      if (el.type === "checkbox") {
        el.checked = current;
      } else {
        if (el.getAttribute("data-lite-label") !== "none") el.textContent = `Lite mode: ${current ? "on" : "off"}`;
        el.setAttribute("aria-pressed", String(current));
        el.title = current ? "Turn lite mode off" : "Turn lite mode on (for slow computers)";
      }
    });
    document.querySelectorAll("[data-lite-status]").forEach((el) => { el.textContent = describe(); });
  }

  function announce(fromSync) {
    paint();
    syncToggles();
    const detail = { on: current, auto: isAuto(), fromSync: Boolean(fromSync) };
    listeners.slice().forEach((fn) => { try { fn(current, detail); } catch (e) { /* a listener must not break the others */ } });
    document.dispatchEvent(new CustomEvent("noyvj-lite-change", { detail }));
  }

  function set(on, fromSync) {
    const next = Boolean(on);
    const changed = next !== current || choice !== next;
    choice = next;
    current = next;
    lsSet(KEY, String(next));
    closeNote(true);
    if (changed) announce(fromSync);
    else syncToggles();
  }

  function refresh() {
    const before = current;
    choice = readChoice();
    current = choice !== null ? choice : hint.length > 0;
    if (current !== before) announce(false);
    else { paint(); syncToggles(); }
  }

  function reset() {
    lsRemove(KEY);
    lsRemove(NOTE_KEY);
    refresh();
  }

  window.NoyvjLite = {
    on: () => current,
    set: (on) => set(on, false),
    reset,
    refresh,
    auto: isAuto,
    chosen: () => choice,
    reasons: () => hint.slice(),
    describe,
    onChange(fn) {
      if (typeof fn !== "function") return () => {};
      listeners.push(fn);
      return () => { const i = listeners.indexOf(fn); if (i >= 0) listeners.splice(i, 1); };
    },
    setFromSync: (on) => set(on, true),
  };

  // Another tab changed it.
  window.addEventListener("storage", (event) => { if (event.key === KEY || event.key === null) refresh(); });

  // ---- the visible note shown when the device hint (not the player) switched it on ----
  let note = null;
  function closeNote(remember) {
    if (remember) lsSet(NOTE_KEY, "1");
    if (note) { note.remove(); note = null; }
  }

  function showNote() {
    if (note || !isAuto() || lsGet(NOTE_KEY) === "1" || !document.body) return;
    note = document.createElement("div");
    note.className = "noyvj-lite-note";
    note.setAttribute("role", "status");
    const text = document.createElement("p");
    text.textContent = `Lite mode is on because this device looks slow (${hint.join(", ")}): animations, blurs and moving backgrounds are off.`;
    const keep = document.createElement("button");
    keep.type = "button";
    keep.textContent = "Keep it on";
    keep.addEventListener("click", () => set(true, false));
    const off = document.createElement("button");
    off.type = "button";
    off.textContent = "Turn it off";
    off.addEventListener("click", () => set(false, false));
    note.append(text, keep, off);
    document.body.appendChild(note);
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-lite-toggle]").forEach((el) => {
      const eventName = el.type === "checkbox" ? "change" : "click";
      el.addEventListener(eventName, () => {
        window.NoyvjLite.set(el.type === "checkbox" ? el.checked : !current);
      });
    });
    syncToggles();
    showNote();
  });
})();
