/*
 * Shared "three goals at all times" panel (planning/TODO.md FY-53). A compact panel that shows at most
 * three goals from a queue the GAME supplies, each with a progress bar plus text ("Reach 5 Smelters:
 * 3 of 5") and a reward line; finishing one promotes the next. The panel never decides a rule: the
 * game says what the goals are, how far along each one is and whether it is done. No timers, no
 * countdowns, nothing to lose; it hides itself when the game has no goals.
 * API, adoption snippet and tests: planning/SHARED-COMPONENTS.md ("Goals panel"),
 * shared/tests/test_goals_panel_browser.py.
 *
 *   <link rel="stylesheet" href="../../shared/goals-panel.css">   (optional: the script links it itself)
 *   <script src="../../shared/goals-panel.js"></script>
 *
 *   const panel = NoyvjGoals.mount("#goals", {
 *     game: "sol",
 *     goals: () => [{ id: "smelters", label: "Reach 5 Smelters", current: 3, target: 5,
 *                     reward: "Unlocks the Foundry", done: false }, ...],   // or a plain array
 *   });
 *   panel.refresh();            // after the game's state changes (cheap: it only touches what changed)
 *
 * Goal fields: id (string, unique), label, current / target (or progress: {current, target}; a goal with
 * no target is a plain tick), reward (text, optional), done (boolean; if absent, current >= target).
 * The first `maxVisible` (default 3, never more than 3) goals that are not done are shown, in the
 * order given. A goal that turns done is announced politely (aria-live) with its reward and the next
 * goal, and a short "Done" note stays under the list until dismissed or replaced.
 *
 * mount(container, opts) -> { refresh(), setEnabled(on, {persist}), isEnabled(), focus(), destroy(),
 *                             element, visibleIds() }
 *   opts: game, goals | getGoals (array or function), title ("Goals"), maxVisible, enabled (initial; else
 *   the stored choice; else on), onChange(visibleGoals), onEnabledChange(on).
 * bindCheckbox(panel, checkbox) wires a settings checkbox to setEnabled (and back).
 * Any code can also fire  document.dispatchEvent(new CustomEvent("noyvj-goals-change"))  to refresh
 * every mounted panel (detail.game limits it to one game). Text is written with textContent only.
 * Nothing here calls the network.
 */
(function () {
  "use strict";
  if (window.NoyvjGoals) return;

  const MAX_VISIBLE = 3;
  const panels = new Set();
  const CSS_FILE = "goals-panel.css";

  function ensureStylesheet() {
    if (typeof document === "undefined" || document.querySelector('link[href*="' + CSS_FILE + '"]')) return;
    const own = document.currentScript || Array.from(document.scripts).find((s) => /goals-panel\.js/.test(s.src || ""));
    if (!own || !own.src) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = own.src.replace(/goals-panel\.js(\?.*)?$/, CSS_FILE);
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
  const num = (n) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const finite = (x) => typeof x === "number" && isFinite(x);

  /** One goal in the shape the panel uses, or null when it is unusable. */
  function normalizeGoal(g) {
    if (!g || typeof g !== "object") return null;
    const id = g.id === undefined || g.id === null ? "" : String(g.id);
    const label = g.label === undefined || g.label === null ? "" : String(g.label).replace(/\s+/g, " ").trim();
    if (!id || !label) return null;
    const prog = g.progress && typeof g.progress === "object" ? g.progress : g;
    const tgt = finite(prog.target) && prog.target > 0 ? prog.target : 0;
    const cur = finite(prog.current) && prog.current > 0 ? prog.current : 0;
    const done = typeof g.done === "boolean" ? g.done : (tgt > 0 && cur >= tgt);
    const reward = g.reward === undefined || g.reward === null ? "" : String(g.reward).replace(/\s+/g, " ").trim();
    return { id, label, current: tgt ? Math.min(cur, tgt) : 0, target: tgt, reward, done };
  }

  function goalText(g) {
    return g.target ? g.label + ": " + num(g.current) + " of " + num(g.target) : g.label;
  }

  function storageKey(game) { return "noyvj-goals:" + (game || "site"); }
  function readStored(game) {
    try {
      const v = localStorage.getItem(storageKey(game));
      return v === "on" ? true : v === "off" ? false : null;
    } catch (e) { return null; }
  }
  function writeStored(game, on) {
    try { localStorage.setItem(storageKey(game), on ? "on" : "off"); } catch (e) { /* blocked storage: the choice just is not remembered */ }
  }

  let uid = 0;

  function mount(container, opts) {
    opts = opts || {};
    const host = target(container);
    if (!host) return null;
    ensureStylesheet();
    const id = "noyvj-goals-" + (++uid);
    const max = Math.max(1, Math.min(MAX_VISIBLE, Number.isInteger(opts.maxVisible) ? opts.maxVisible : MAX_VISIBLE));

    const root = el("section", "noyvj-goals", null, { "aria-labelledby": id + "-t", tabindex: "-1" });
    if (opts.game) root.dataset.game = String(opts.game);
    const head = el("div", "noyvj-goals-head");
    const title = el("p", "noyvj-goals-title", opts.title || "Goals", { id: id + "-t" });
    const tally = el("p", "noyvj-goals-tally", "");
    head.append(title, tally);
    const list = el("ul", "noyvj-goals-list", null, { "aria-labelledby": id + "-t" });
    const allDone = el("p", "noyvj-goals-done", "✓ Every goal is done. Nice work.");
    allDone.hidden = true;
    const note = el("div", "noyvj-goals-note");
    const noteText = el("p", "noyvj-goals-note-text", "");
    const dismiss = el("button", "noyvj-goals-dismiss", "×", { type: "button", "aria-label": "Dismiss the finished-goal note" });
    note.append(noteText, dismiss);
    note.hidden = true;
    const live = el("div", "noyvj-goals-sr", "", { role: "status", "aria-live": "polite", "aria-atomic": "true" });
    root.append(head, list, allDone, note, live);
    root.hidden = true;
    host.appendChild(root);

    let enabled = typeof opts.enabled === "boolean" ? opts.enabled : (readStored(opts.game) !== null ? readStored(opts.game) : true);
    let known = null;                 // id -> done, from the previous refresh (null before the first)
    let shownIds = new Set();         // ids that were visible after the previous refresh
    const items = new Map();          // id -> { li, text, fill, bar, reward }
    let lastSig = "";
    let destroyed = false;

    function source() {
      const s = opts.getGoals !== undefined ? opts.getGoals : opts.goals;
      try { return typeof s === "function" ? s() : s; } catch (e) { return []; }
    }

    function makeItem(g) {
      const li = el("li", "noyvj-goals-item");
      const text = el("p", "noyvj-goals-text", "");
      const bar = el("div", "noyvj-goals-bar", null, { "aria-hidden": "true" });
      const fill = el("div", "noyvj-goals-fill");
      bar.append(fill);
      const reward = el("p", "noyvj-goals-reward", "");
      li.append(text, bar, reward);
      return { li, text, bar, fill, reward };
    }

    function paintItem(it, g) {
      const t = goalText(g);
      if (it.text.textContent !== t) it.text.textContent = t;
      it.bar.hidden = !g.target;
      if (g.target) it.fill.style.width = (g.current / g.target * 100).toFixed(1) + "%";
      const r = g.reward ? "Reward: " + g.reward : "";
      if (it.reward.textContent !== r) it.reward.textContent = r;
      it.reward.hidden = !r;
    }

    function refresh() {
      if (destroyed) return;
      const seen = new Set();
      const all = [];
      let raw = source();
      raw = Array.isArray(raw) ? raw : [];
      for (const r of raw) {
        const g = normalizeGoal(r);
        if (g && !seen.has(g.id)) { seen.add(g.id); all.push(g); }
      }
      const pending = all.filter((g) => !g.done);
      const visible = pending.slice(0, max);
      const doneCount = all.length - pending.length;

      // completions: done now, known as not done before (the very first refresh is silent)
      const completed = known ? all.filter((g) => g.done && known.get(g.id) === false) : [];
      const promoted = known ? visible.filter((g) => !shownIds.has(g.id)) : [];
      known = new Map(all.map((g) => [g.id, g.done]));

      if (!enabled || !all.length) {
        root.hidden = true;
        shownIds = new Set(visible.map((g) => g.id));
        return;
      }
      root.hidden = false;
      tally.textContent = doneCount + " of " + all.length + " done";
      allDone.hidden = pending.length > 0;
      list.hidden = !visible.length;

      // keyed, in-place update so a screen reader's position and any animation survive a refresh
      const want = new Set(visible.map((g) => g.id));
      for (const [gid, it] of items) {
        if (!want.has(gid)) { it.li.remove(); items.delete(gid); }
      }
      visible.forEach((g, i) => {
        let it = items.get(g.id);
        if (!it) {
          it = makeItem(g);
          items.set(g.id, it);
          if (known && promoted.some((p) => p.id === g.id)) it.li.classList.add("noyvj-goals-item--new");
        }
        paintItem(it, g);
        if (list.children[i] !== it.li) list.insertBefore(it.li, list.children[i] || null);
      });
      for (const [gid, it] of items) {
        if (!promoted.some((p) => p.id === gid)) it.li.classList.remove("noyvj-goals-item--new");
      }
      shownIds = new Set(visible.map((g) => g.id));

      if (completed.length) {
        const last = completed[completed.length - 1];
        noteText.textContent = "✓ Done: " + last.label + (last.reward ? ". Reward: " + last.reward : "");
        note.hidden = false;
        const bits = completed.map((g) => "Goal complete: " + g.label + "." + (g.reward ? " Reward: " + g.reward + "." : ""));
        const next = promoted.filter((g) => !g.done);
        if (next.length) bits.push((next.length === 1 ? "New goal: " : "New goals: ") + next.map((g) => g.label).join("; ") + ".");
        else if (!pending.length) bits.push("Every goal is done.");
        live.textContent = "";
        // set on the next frame-free microtask so repeated identical text is still announced
        Promise.resolve().then(() => { live.textContent = bits.join(" "); });
      }

      const sig = visible.map((g) => g.id + "|" + g.current + "|" + g.target + "|" + g.done).join(";") + "#" + doneCount;
      if (sig !== lastSig) {
        lastSig = sig;
        if (typeof opts.onChange === "function") { try { opts.onChange(visible.slice()); } catch (e) { /* the game's callback must not break the panel */ } }
      }
    }

    dismiss.addEventListener("click", () => { note.hidden = true; noteText.textContent = ""; });

    function setEnabled(on, o) {
      const next = !!on;
      const changed = next !== enabled;
      enabled = next;
      if (!o || o.persist !== false) writeStored(opts.game, enabled);
      refresh();
      if (changed && typeof opts.onEnabledChange === "function") opts.onEnabledChange(enabled);
    }

    const onEvent = (ev) => {
      const g = ev && ev.detail && ev.detail.game;
      if (!g || !opts.game || g === opts.game) refresh();
    };
    document.addEventListener("noyvj-goals-change", onEvent);

    const api = {
      refresh,
      setEnabled,
      isEnabled: () => enabled,
      focus() { root.focus(); },
      visibleIds: () => Array.from(shownIds),
      destroy() {
        destroyed = true;
        document.removeEventListener("noyvj-goals-change", onEvent);
        panels.delete(api);
        root.remove();
      },
      element: root,
    };
    panels.add(api);
    refresh();
    return api;
  }

  /** Keep a settings checkbox and the panel's on/off in step. Returns a function that unbinds it. */
  function bindCheckbox(panel, checkbox) {
    const box = target(checkbox);
    if (!panel || !box) return () => {};
    box.checked = panel.isEnabled();
    const onChange = () => panel.setEnabled(box.checked);
    box.addEventListener("change", onChange);
    return () => box.removeEventListener("change", onChange);
  }

  window.NoyvjGoals = { MAX_VISIBLE, mount, bindCheckbox, normalizeGoal, refreshAll() { panels.forEach((p) => p.refresh()); } };
})();
