/*
 * Shared Ironman switch (planning/TODO.md QI-53): an opt-in hard mode per game, with no restoring and no
 * rewinding, its own badge, never the default and never forced. This file is only the plumbing: the
 * GAME decides what Ironman means (which restore, undo or rewind actions are blocked, what counts as a
 * finished run, when the badge is earned) and wraps those actions in NoyvjIronman.guard(). The switch
 * says in plain words what it does, and why it is locked when it cannot be changed.
 *
 *   <link rel="stylesheet" href="../../shared/ironman.css">   (optional: the script links it itself)
 *   <script src="../../shared/ironman.js"></script>
 *
 *   const sw = NoyvjIronman.mount("#ironman", {
 *     game: "station-medic",
 *     label: "Ironman mode",                       // optional
 *     badgeName: "Ironman",                        // optional: the badge the explanation names
 *     explain: "A fainted crew member stays out.", // optional: one extra game-specific line
 *     canChange: () => !runStarted,                // optional: false locks the switch (default: free)
 *     onChange: (on) => {},                        // fires on every real change, including release()
 *   });
 *   restoreButton.onclick = () => NoyvjIronman.guard("station-medic", () => restoreShift());
 *   header.append(NoyvjIronman.badge("station-medic", { name: "Ironman" }));
 *   NoyvjIronman.release("station-medic");          // the game switches it off (e.g. the run has ended)
 *
 * mount(container, opts) -> { refresh(), isOn(), release(), destroy(), element }
 *   refresh() re-asks canChange(), so call it when the run starts or ends (or fire document
 *   "noyvj-ironman-change" / call NoyvjIronman.refreshAll()).
 * Static API: isOn(game), release(game), onChange(fn(on, game)) -> unsubscribe, guard(game, fn, {message})
 *   (returns false and says "Ironman is on: this cannot be undone." when on; otherwise calls fn and
 *   returns true, or false if fn returned false), badge(game, {name}) -> element, refreshAll().
 * State: localStorage["noyvj-ironman:<game>"] is "on" or absent (absent = off, the default); blocked
 *   storage keeps it in memory for the session. While any switch's game is on, html[data-ironman="true"]
 *   is set (removed when off). Every change fires document "noyvj-ironman-change" (detail: {game, on}).
 * Once on, the player can switch it off only while canChange() allows it (no canChange: always); the game
 * can always call release(). Text is written with textContent only; no timers; no network.
 */
(function () {
  "use strict";
  if (window.NoyvjIronman) return;

  const CSS_FILE = "ironman.css";
  const BLOCKED = "Ironman is on: this cannot be undone.";
  const LOCKED = "Ironman can only be changed before a run starts.";
  const mounts = new Set();
  const listeners = new Set();
  const memory = {};              // game -> boolean, the fallback when storage is blocked

  function ensureStylesheet() {
    if (typeof document === "undefined" || document.querySelector('link[href*="' + CSS_FILE + '"]')) return;
    const own = document.currentScript || Array.from(document.scripts).find((s) => /ironman\.js/.test(s.src || ""));
    if (!own || !own.src) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = own.src.replace(/ironman\.js(\?.*)?$/, CSS_FILE);
    document.head.append(link);
  }
  ensureStylesheet();

  function el(tag, cls, text, attrs) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    if (attrs) for (const k of Object.keys(attrs)) n.setAttribute(k, attrs[k]);
    return n;
  }
  const target = (x) => (typeof x === "string" ? document.querySelector(x) : x);
  const keyOf = (game) => "noyvj-ironman:" + (game || "site");
  const gameOf = (game) => game || "site";

  let writeBlocked = false;
  function isOn(game) {
    const g = gameOf(game);
    if (!writeBlocked) {
      try { return localStorage.getItem(keyOf(g)) === "on"; } catch (e) { /* fall through to memory */ }
    }
    return memory[g] === true;
  }
  function store(game, on) {
    const g = gameOf(game);
    memory[g] = on;
    try {
      if (on) localStorage.setItem(keyOf(g), "on"); else localStorage.removeItem(keyOf(g));
      writeBlocked = false;
    } catch (e) { writeBlocked = true; /* blocked storage: kept in memory for this session */ }
  }

  function applyAttribute(game) {
    if (typeof document === "undefined") return;
    if (isOn(game)) document.documentElement.setAttribute("data-ironman", "true");
    else document.documentElement.removeAttribute("data-ironman");
  }

  function setOn(game, on) {
    const next = !!on;
    if (isOn(game) === next) return false;
    store(game, next);
    applyAttribute(game);
    document.dispatchEvent(new CustomEvent("noyvj-ironman-change", { detail: { game: gameOf(game), on: next } }));
    listeners.forEach((fn) => { try { fn(next, gameOf(game)); } catch (e) { /* a listener must not break the others */ } });
    return true;
  }

  // ---- one shared notice for guard(): visible text plus a polite live region -----------------------
  let notice = null;
  let noticeText = null;
  function showNotice(text) {
    if (!notice || !notice.isConnected) {
      notice = el("div", "noyvj-ironman-notice", null, { role: "status", "aria-live": "polite", "aria-atomic": "true" });
      noticeText = el("p", "noyvj-ironman-notice-text", "");
      const close = el("button", "noyvj-ironman-notice-close", "OK", { type: "button" });
      close.addEventListener("click", () => { notice.hidden = true; noticeText.textContent = ""; });
      notice.append(noticeText, close);
      notice.hidden = true;
      document.body.append(notice);
    }
    noticeText.textContent = "";
    notice.hidden = false;
    Promise.resolve().then(() => { noticeText.textContent = text; });
  }

  function guard(game, fn, o) {
    if (isOn(game)) {
      showNotice((o && o.message) || BLOCKED);
      return false;
    }
    if (typeof fn !== "function") return true;
    return fn() !== false;
  }

  function badge(game, o) {
    const name = (o && o.name ? String(o.name) : "Ironman").trim() || "Ironman";
    const b = el("span", "noyvj-ironman-badge", name, { "data-game": gameOf(game) });
    return b;
  }

  let uid = 0;

  function mount(container, opts) {
    opts = opts || {};
    const host = target(container);
    if (!host) return null;
    ensureStylesheet();
    const id = "noyvj-ironman-" + (++uid);
    const game = gameOf(opts.game);
    const badgeName = (opts.badgeName ? String(opts.badgeName) : "Ironman").trim() || "Ironman";

    const root = el("section", "noyvj-ironman", null, { "aria-labelledby": id + "-t" });
    root.dataset.game = game;
    const row = el("label", "noyvj-ironman-row");
    const input = el("input", "noyvj-ironman-input", null, { type: "checkbox", role: "switch", "aria-describedby": id + "-d " + id + "-n" });
    const track = el("span", "noyvj-ironman-track", null, { "aria-hidden": "true" });
    track.append(el("span", "noyvj-ironman-knob"));
    const title = el("span", "noyvj-ironman-title", opts.label || "Ironman mode", { id: id + "-t" });
    const state = el("span", "noyvj-ironman-state", "");
    row.append(input, track, title, state);
    const explain = el("p", "noyvj-ironman-explain",
      "Ironman means no restoring and no rewinding: what happens in a run stays. It is optional and off by default, and it earns the " +
      badgeName + " badge.", { id: id + "-d" });
    const extra = opts.explain ? el("p", "noyvj-ironman-explain noyvj-ironman-explain--extra", String(opts.explain)) : null;
    const note = el("p", "noyvj-ironman-lock", "", { id: id + "-n" });
    note.hidden = true;
    root.append(row, explain);
    if (extra) root.append(extra);
    root.append(note);
    host.appendChild(root);

    let destroyed = false;
    let shown = null;

    function allowed() {
      if (typeof opts.canChange !== "function") return true;
      try { return !!opts.canChange(); } catch (e) { return false; }
    }

    function refresh() {
      if (destroyed) return;
      const on = isOn(game);
      const can = allowed();
      input.checked = on;
      input.setAttribute("aria-checked", on ? "true" : "false");
      input.disabled = !can;
      state.textContent = on ? "On" : "Off";
      note.hidden = can;
      note.textContent = can ? "" : LOCKED;
      root.classList.toggle("noyvj-ironman--on", on);
      root.classList.toggle("noyvj-ironman--locked", !can);
      if (shown !== null && shown !== on && typeof opts.onChange === "function") {
        try { opts.onChange(on); } catch (e) { /* the game's callback must not break the switch */ }
      }
      shown = on;
    }

    input.addEventListener("change", () => {
      if (!allowed()) { refresh(); return; }       // locked: put the switch back the way it was
      setOn(game, input.checked);
      refresh();
    });

    const onEvent = (ev) => {
      const g = ev && ev.detail && ev.detail.game;
      if (!g || g === game) refresh();
    };
    document.addEventListener("noyvj-ironman-change", onEvent);

    const api = {
      refresh,
      isOn: () => isOn(game),
      release() { setOn(game, false); refresh(); },
      destroy() {
        destroyed = true;
        document.removeEventListener("noyvj-ironman-change", onEvent);
        mounts.delete(api);
        root.remove();
      },
      element: root,
    };
    mounts.add(api);
    applyAttribute(game);
    refresh();
    return api;
  }

  window.NoyvjIronman = {
    mount,
    isOn,
    release(game) { return setOn(game, false); },
    onChange(fn) {
      if (typeof fn !== "function") return () => {};
      listeners.add(fn);
      return () => listeners.delete(fn);
    },
    guard,
    badge,
    refreshAll() { mounts.forEach((m) => m.refresh()); },
  };
})();
