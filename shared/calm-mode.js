/*
 * Shared half-asleep ("calm") mode (planning/TODO.md QI-51): "large buttons, dimmed screen, calm games
 * only, one-handed layout." Opt-in and off by default; the choice is kept per browser in
 * localStorage "noyvj-calm" ("on"; absent = off). While on, html[data-calm="true"] is set and
 * calm-mode.css enlarges targets (56 px) and text, stops motion and dims the screen with a fixed
 * click-through layer. It also offers a thumb dock for the one-handed layout and a helper that hides
 * games that are not calm. It never changes a game's rules.
 *
 *   <link rel="stylesheet" href="../../shared/calm-mode.css">   (optional: the script links it itself)
 *   <script src="../../shared/calm-mode.js"></script>
 *
 * API (window.NoyvjCalm):
 *   isOn() / setOn(bool) / toggle()          the switch
 *   getHand() / setHand("right"|"left")      which thumb the dock favours (default right)
 *   setDock([{id, label, onClick}])          a fixed bottom bar of big buttons, shown only while calm is
 *                                            on (the game passes its two or three main actions);
 *                                            clearDock() removes it; at most 4 buttons
 *   filter(container, {itemSelector, getTags, calmTags})   hides items that are not calm while it is on
 *                                            (an item is calm when its tags include one of calmTags,
 *                                            default ["calm"]; an item with data-calm="true" is calm too).
 *                                            Returns {refresh(), shown(), total(), destroy()}; hidden items
 *                                            use the hidden attribute and are restored when calm is off.
 *   CALM_GAMES                               a suggested list of calm game slugs for the hub to start from
 *   mount(container, {title}) -> {refresh, destroy, element}   a settings control (a labelled switch, a
 *                                            hand select and a plain list of what changes)
 *   bindCheckbox(checkbox)                   wire your own checkbox to the switch
 *   onChange(fn)                             fn({on, hand}); returns an unsubscribe function
 * A "noyvj-calm-change" event is fired on document. Text is written with textContent only. There are no
 * timers and no network.
 */
(function () {
  "use strict";
  if (window.NoyvjCalm) return;

  const KEY = "noyvj-calm";
  const HAND_KEY = "noyvj-calm:hand";
  const CSS_FILE = "calm-mode.css";
  const MAX_DOCK = 4;
  const CALM_GAMES = ["canopy", "tide", "signal", "lexis", "hull-repair", "robot-script", "pocket-bazaar", "lighthouse",
    "stranded", "logic-gates", "dead-reckoning", "station-medic", "evidence-hunt", "champ-de-mots"];
  const listeners = [];
  const controls = new Set();
  const filters = new Set();
  let dim = null;
  let dock = null;
  let dockItems = [];
  const memory = { on: null, hand: null };
  let lastState = null;

  function ensureStylesheet() {
    if (typeof document === "undefined" || document.querySelector('link[href*="' + CSS_FILE + '"]')) return;
    const own = document.currentScript || Array.from(document.scripts).find((s) => /calm-mode\.js/.test(s.src || ""));
    if (!own || !own.src) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = own.src.replace(/calm-mode\.js(\?.*)?$/, CSS_FILE);
    document.head.append(link);
  }
  ensureStylesheet();

  function read(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }
  function write(key, value) {
    try { if (value === null) window.localStorage.removeItem(key); else window.localStorage.setItem(key, value); } catch (e) { /* blocked */ }
  }
  function isOn() {
    const stored = read(KEY);
    if (stored === "on") return true;
    if (stored === null && memory.on !== null) return memory.on;
    return false;
  }
  function getHand() {
    const stored = read(HAND_KEY);
    const v = stored === "left" || stored === "right" ? stored : memory.hand;
    return v === "left" ? "left" : "right";
  }

  function el(tag, cls, text, attrs) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    if (attrs) for (const k of Object.keys(attrs)) n.setAttribute(k, attrs[k]);
    return n;
  }

  function renderDock() {
    const show = isOn() && dockItems.length > 0;
    if (!show) {
      if (dock) { dock.remove(); dock = null; }
      document.body && document.body.classList.remove("noyvj-calm-has-dock");
      return;
    }
    if (!dock) {
      dock = el("div", "noyvj-calm-dock", null, { role: "toolbar", "aria-label": "Main actions" });
      document.body.append(dock);
    }
    dock.setAttribute("data-hand", getHand());
    dock.textContent = "";
    dockItems.forEach((item) => {
      const b = el("button", "", item.label, { type: "button", "data-dock-id": item.id });
      b.addEventListener("click", () => { try { item.onClick && item.onClick(); } catch (e) { /* the game's own error */ } });
      dock.append(b);
    });
    document.body.classList.add("noyvj-calm-has-dock");
  }

  function isCalmItem(node, opts) {
    if (node.getAttribute && node.getAttribute("data-calm") === "true") return true;
    const tags = (opts.getTags ? opts.getTags(node) : (node.getAttribute("data-tags") || "").split(/[\s,]+/)) || [];
    const calm = opts.calmTags || ["calm"];
    return Array.from(tags).some((t) => calm.indexOf(String(t).toLowerCase()) >= 0);
  }

  function applyFilters() {
    filters.forEach((f) => f.refresh());
  }

  function apply() {
    const root = document.documentElement;
    const on = isOn();
    if (!dim || !dim.isConnected) {
      dim = el("div", "noyvj-calm-dim", null, { "aria-hidden": "true" });
      (document.body || root).append(dim);
    }
    root.setAttribute("data-calm", on ? "true" : "false");
    renderDock();
    applyFilters();
    const state = { on: on, hand: getHand() };
    const changed = !lastState || lastState.on !== state.on || lastState.hand !== state.hand;
    lastState = state;
    controls.forEach((c) => c.refresh());
    if (changed) {
      listeners.slice().forEach((fn) => { try { fn(state); } catch (e) { /* a listener must not break the page */ } });
      document.dispatchEvent(new CustomEvent("noyvj-calm-change", { detail: state }));
    }
    return state;
  }

  function setOn(value) {
    const on = !!value;
    memory.on = on;
    write(KEY, on ? "on" : null);
    apply();
    return on;
  }
  function toggle() { return setOn(!isOn()); }
  function setHand(hand) {
    if (hand !== "left" && hand !== "right") return false;
    memory.hand = hand;
    write(HAND_KEY, hand);
    apply();
    return true;
  }

  function setDock(items) {
    dockItems = (Array.isArray(items) ? items : [])
      .filter((i) => i && typeof i === "object" && i.label !== undefined && i.label !== null && String(i.label).trim())
      .slice(0, MAX_DOCK)
      .map((i, n) => ({ id: i.id === undefined ? "action-" + n : String(i.id), label: String(i.label).replace(/\s+/g, " ").trim(), onClick: i.onClick }));
    renderDock();
    return dockItems.length;
  }
  function clearDock() { dockItems = []; renderDock(); }

  function filter(container, opts) {
    const host = typeof container === "string" ? document.querySelector(container) : container;
    if (!host) return null;
    opts = opts || {};
    const selector = opts.itemSelector || "[data-tags]";
    const hiddenByUs = new Set();
    let note = null;
    const api = {
      refresh() {
        const items = Array.from(host.querySelectorAll(selector));
        const on = isOn();
        let shown = 0;
        items.forEach((node) => {
          const calm = isCalmItem(node, opts);
          if (on && !calm) {
            if (!node.hidden) { node.hidden = true; hiddenByUs.add(node); }
          } else if (hiddenByUs.has(node)) {
            node.hidden = false;
            hiddenByUs.delete(node);
          }
          if (!node.hidden) shown += 1;
        });
        api._total = items.length;
        api._shown = shown;
        if (on && opts.note !== false) {
          if (!note) { note = el("p", "noyvj-calm-count", "", { role: "status" }); host.parentNode.insertBefore(note, host); }
          note.textContent = "Calm games only: showing " + shown + " of " + items.length + ".";
        } else if (note) { note.remove(); note = null; }
      },
      shown() { return api._shown || 0; },
      total() { return api._total || 0; },
      destroy() {
        hiddenByUs.forEach((n) => { n.hidden = false; });
        hiddenByUs.clear();
        if (note) note.remove();
        filters.delete(api);
      },
    };
    filters.add(api);
    api.refresh();
    return api;
  }

  const CHANGES = [
    "Buttons and form controls are at least 56 pixels tall, and text is a little bigger.",
    "The screen is dimmed and all motion stops.",
    "A bar of big buttons along the bottom edge (where a game provides one) keeps its main actions under your thumb.",
    "Where a list of games is shown, only calm games are listed.",
  ];
  let uid = 0;
  function mount(container, opts) {
    const host = typeof container === "string" ? document.querySelector(container) : container;
    if (!host) return null;
    opts = opts || {};
    uid += 1;
    const root = el("section", "noyvj-calm-control", null, { "aria-labelledby": "noyvj-calm-title-" + uid });
    root.append(el("h3", "", opts.title || "Half-asleep mode", { id: "noyvj-calm-title-" + uid }));
    root.append(el("p", "", "For tired late-night play. It is off by default and only changes how things look and how big they are:"));
    const list = el("ul");
    CHANGES.forEach((t) => list.append(el("li", "", t)));
    root.append(list);
    const checkId = "noyvj-calm-check-" + uid, handId = "noyvj-calm-hand-" + uid;
    const label = el("label", "", null, { for: checkId });
    const check = el("input", "", null, { type: "checkbox", id: checkId });
    label.append(check, el("span", "", "Half-asleep mode"));
    const handLabel = el("label", "", null, { for: handId });
    const hand = el("select", "", null, { id: handId });
    hand.append(el("option", "", "Right hand", { value: "right" }), el("option", "", "Left hand", { value: "left" }));
    handLabel.append(el("span", "", "Thumb bar favours"), hand);
    const status = el("p", "", "", { role: "status", "aria-live": "polite" });
    root.append(label, handLabel, status);
    host.append(root);
    const control = {
      element: root,
      refresh() {
        check.checked = isOn();
        hand.value = getHand();
        const text = isOn() ? "Half-asleep mode is on." : "Half-asleep mode is off.";
        if (status.textContent !== text) status.textContent = text;
      },
      destroy() { controls.delete(control); root.remove(); },
    };
    check.addEventListener("change", () => setOn(check.checked));
    hand.addEventListener("change", () => setHand(hand.value));
    controls.add(control);
    control.refresh();
    return control;
  }

  function bindCheckbox(checkbox) {
    const node = typeof checkbox === "string" ? document.querySelector(checkbox) : checkbox;
    if (!node) return null;
    const handler = () => setOn(node.checked);
    node.addEventListener("change", handler);
    const off = onChange(() => { node.checked = isOn(); });
    node.checked = isOn();
    return function unbind() { node.removeEventListener("change", handler); off(); };
  }

  function onChange(fn) {
    if (typeof fn !== "function") return function () {};
    listeners.push(fn);
    return function off() { const i = listeners.indexOf(fn); if (i >= 0) listeners.splice(i, 1); };
  }

  window.addEventListener("storage", (e) => { if (e.key === KEY || e.key === HAND_KEY) apply(); });

  window.NoyvjCalm = { isOn, setOn, toggle, getHand, setHand, setDock, clearDock, filter, mount, bindCheckbox, onChange, apply, CALM_GAMES };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply);
  else apply();
})();
