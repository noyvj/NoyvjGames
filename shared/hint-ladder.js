/*
 * Shared graded hint ladder for puzzle games (planning/TODO.md QI-54): a nudge, then a hint, then the
 * answer, so a player never has to leave the game to look it up. One button reveals the next rung each
 * press; the answer rung asks one inline question first (not a modal). Revealed rungs stay on screen with
 * a text label ("Nudge", "Hint", "Answer"). The component never decides a rule and never reads a game's
 * state: it only shows the rungs the GAME supplies for the puzzle the GAME names. Nothing is timed, nothing
 * is lost and a hint is never shown unless the player presses the button.
 *
 *   <link rel="stylesheet" href="../../shared/hint-ladder.css">   (optional: the script links it itself)
 *   <script src="../../shared/hint-ladder.js"></script>
 *
 *   const ladder = NoyvjHints.mount("#hints", {
 *     game: "logic-gates",
 *     getPuzzle: () => ({ id: "L12", nudge: "Look at the right-hand wire.", hint: "An AND gate comes first.",
 *                         answer: "AND, then NOT." }),     // or null when there is no puzzle on screen
 *     onReveal: (rung, puzzleId) => {},                    // rung is "nudge" | "hint" | "answer"
 *     confirmAnswer: true,                                 // default true: ask once before the answer
 *   });
 *   ladder.refresh();   // after the game moves to another puzzle (a different id resets the ladder silently)
 *
 * Puzzle fields: id (string or number, required), nudge, hint, answer (strings; any may be missing, the
 * ladder just has fewer rungs).
 *
 * mount(container, opts) -> { refresh(), reset(), rungShown(), used(), setEnabled(on, {persist}),
 *                             isEnabled(), focus(), destroy(), element }
 *   rungShown()  how many rungs are revealed for the current puzzle (0 to 3)
 *   used()       the names of those rungs, in order, e.g. ["nudge", "hint"]
 *   reset()      hide this puzzle's rungs again (silent; the per-game counts are not touched)
 * NoyvjHints.stats(game) -> { nudges, hints, answers, puzzles }: how many puzzles reached each rung (counted
 *   as "reached at least this rung"), kept in localStorage["noyvj-hints:<game>"] = {puzzles:{id:maxRung},
 *   order:[ids]} (1 nudge, 2 hint, 3 answer), the 500 most recent puzzle ids; blocked storage keeps the
 *   counts in memory for the session.
 * Settings switch: setEnabled(false) hides the ladder entirely (remembered per game in
 *   localStorage["noyvj-hints-pref:<game>"], "on"/"off", default on); NoyvjHints.bindCheckbox(panel, box)
 *   keeps a settings checkbox in step. Every reveal also fires  document "noyvj-hints-reveal"
 *   (detail: {game, id, rung}) so a game can score or log it. document "noyvj-hints-change" (detail.game
 *   optional) or NoyvjHints.refreshAll() refreshes every mounted ladder. Text is written with textContent
 *   only; no timers; no network.
 */
(function () {
  "use strict";
  if (window.NoyvjHints) return;

  const CSS_FILE = "hint-ladder.css";
  const KEYS = ["nudge", "hint", "answer"];
  const LABELS = { nudge: "Nudge", hint: "Hint", answer: "Answer" };
  const CAP = 500;
  const ladders = new Set();
  const memory = {};               // game -> stats object, the fallback when storage is blocked

  function ensureStylesheet() {
    if (typeof document === "undefined" || document.querySelector('link[href*="' + CSS_FILE + '"]')) return;
    const own = document.currentScript || Array.from(document.scripts).find((s) => /hint-ladder\.js/.test(s.src || ""));
    if (!own || !own.src) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = own.src.replace(/hint-ladder\.js(\?.*)?$/, CSS_FILE);
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

  /** One puzzle in the shape the ladder uses, or null when it is unusable. */
  function normalizePuzzle(p) {
    if (!p || typeof p !== "object") return null;
    if (p.id === undefined || p.id === null || p.id === "") return null;
    const id = String(p.id);
    const rungs = [];
    for (const key of KEYS) {
      const v = p[key];
      if ((typeof v === "string" || typeof v === "number") && String(v).trim()) {
        rungs.push({ key, label: LABELS[key], text: String(v).trim() });
      }
    }
    return { id, rungs };
  }

  // ---- per-game counts -------------------------------------------------------------------------
  const statsKey = (game) => "noyvj-hints:" + (game || "site");
  const prefKey = (game) => "noyvj-hints-pref:" + (game || "site");

  function cleanStats(raw) {
    const out = { puzzles: {}, order: [] };
    if (!raw || typeof raw !== "object" || !raw.puzzles || typeof raw.puzzles !== "object") return out;
    const ids = Array.isArray(raw.order) ? raw.order.map(String) : [];
    for (const id of Object.keys(raw.puzzles)) if (ids.indexOf(id) < 0) ids.push(id);
    for (const id of ids) {
      const r = raw.puzzles[id];
      if (Object.prototype.hasOwnProperty.call(raw.puzzles, id) && Number.isInteger(r) && r >= 1 && r <= 3) {
        out.puzzles[id] = r;
        out.order.push(id);
      }
    }
    while (out.order.length > CAP) delete out.puzzles[out.order.shift()];
    return out;
  }
  function readStats(game) {
    try {
      const v = localStorage.getItem(statsKey(game));
      if (v !== null) return cleanStats(JSON.parse(v));
      return memory[game || "site"] ? cleanStats(memory[game || "site"]) : cleanStats(null);
    } catch (e) {
      return memory[game || "site"] ? cleanStats(memory[game || "site"]) : cleanStats(null);
    }
  }
  function writeStats(game, data) {
    memory[game || "site"] = data;
    try { localStorage.setItem(statsKey(game), JSON.stringify(data)); } catch (e) { /* blocked storage: kept in memory only */ }
  }
  function record(game, id, rungNumber) {
    const data = readStats(game);
    const had = Object.prototype.hasOwnProperty.call(data.puzzles, id);
    if (had && data.puzzles[id] >= rungNumber) return;
    if (!had) {
      data.order.push(id);
      while (data.order.length > CAP) delete data.puzzles[data.order.shift()];
    }
    data.puzzles[id] = rungNumber;
    writeStats(game, data);
  }
  function stats(game) {
    const data = readStats(game);
    const out = { nudges: 0, hints: 0, answers: 0, puzzles: 0 };
    for (const id of data.order) {
      const r = data.puzzles[id];
      out.puzzles++;
      if (r >= 1) out.nudges++;
      if (r >= 2) out.hints++;
      if (r >= 3) out.answers++;
    }
    return out;
  }

  function readPref(game) {
    try {
      const v = localStorage.getItem(prefKey(game));
      return v === "on" ? true : v === "off" ? false : null;
    } catch (e) { return null; }
  }
  function writePref(game, on) {
    try { localStorage.setItem(prefKey(game), on ? "on" : "off"); } catch (e) { /* blocked storage: the choice just is not remembered */ }
  }

  let uid = 0;

  function mount(container, opts) {
    opts = opts || {};
    const host = target(container);
    if (!host) return null;
    ensureStylesheet();
    const id = "noyvj-hints-" + (++uid);
    const askFirst = opts.confirmAnswer !== false;

    const root = el("section", "noyvj-hints", null, { "aria-labelledby": id + "-t", tabindex: "-1" });
    if (opts.game) root.dataset.game = String(opts.game);
    const head = el("div", "noyvj-hints-head");
    const title = el("p", "noyvj-hints-title", opts.title || "Hints", { id: id + "-t" });
    const tally = el("p", "noyvj-hints-tally", "");
    head.append(title, tally);
    const list = el("ol", "noyvj-hints-list", null, { "aria-labelledby": id + "-t" });
    const ask = el("button", "noyvj-hints-ask", "Need a hint?", { type: "button" });
    const confirm = el("div", "noyvj-hints-confirm", null, { role: "group", "aria-labelledby": id + "-q" });
    const question = el("p", "noyvj-hints-question", "Show the answer? Seeing it takes the challenge out of this puzzle.", { id: id + "-q" });
    const yes = el("button", "noyvj-hints-yes", "Yes, show it", { type: "button" });
    const no = el("button", "noyvj-hints-no", "Not yet", { type: "button" });
    const choices = el("div", "noyvj-hints-choices");
    choices.append(yes, no);
    confirm.append(question, choices);
    confirm.hidden = true;
    list.hidden = true;
    const live = el("div", "noyvj-hints-sr", "", { role: "status", "aria-live": "polite", "aria-atomic": "true" });
    root.append(head, list, ask, confirm, live);
    root.hidden = true;
    host.appendChild(root);

    let enabled = typeof opts.enabled === "boolean" ? opts.enabled : (readPref(opts.game) !== null ? readPref(opts.game) : true);
    let puzzleId = null;              // the id the current state belongs to
    let rungs = [];                   // the current puzzle's available rungs
    let revealed = 0;                 // how many of them are shown
    let confirming = false;
    let destroyed = false;
    let paintedSig = "";

    function source() {
      const s = opts.getPuzzle !== undefined ? opts.getPuzzle : opts.puzzle;
      try { return typeof s === "function" ? s() : s; } catch (e) { return null; }
    }

    function say(text) {
      live.textContent = "";
      Promise.resolve().then(() => { if (!destroyed) live.textContent = text; });
    }

    function paint() {
      const shown = rungs.slice(0, revealed);
      const sig = shown.map((r) => r.key + "|" + r.text).join("\n");
      if (sig !== paintedSig) {
        paintedSig = sig;
        list.textContent = "";
        for (const r of shown) {
          const li = el("li", "noyvj-hints-item", null, { "data-rung": r.key, tabindex: "-1" });
          li.append(el("span", "noyvj-hints-label", r.label), el("span", "noyvj-hints-text", r.text));
          list.append(li);
        }
      }
      list.hidden = !shown.length;
      tally.textContent = revealed + " of " + rungs.length + " shown";
      const next = rungs[revealed];
      if (confirming && !(next && next.key === "answer")) confirming = false;
      confirm.hidden = !confirming;
      ask.hidden = !next || confirming;
      if (next) ask.textContent = next.key === "answer" && revealed > 0 ? "Show the answer" : revealed === 0 ? "Need a hint?" : "Another hint";
    }

    function refresh() {
      if (destroyed) return;
      const p = normalizePuzzle(source());
      if (p && p.id !== puzzleId) {          // a different puzzle: start clean, silently
        puzzleId = p.id;
        revealed = 0;
        confirming = false;
      }
      if (p) rungs = p.rungs;
      if (revealed > rungs.length) revealed = rungs.length;
      if (!p || !enabled || !rungs.length) { root.hidden = true; return; }
      root.hidden = false;
      paint();
    }

    function reveal(rung) {
      const number = KEYS.indexOf(rung.key) + 1;
      revealed++;
      confirming = false;
      record(opts.game, puzzleId, number);
      paint();
      say(rung.label + ": " + rung.text);
      document.dispatchEvent(new CustomEvent("noyvj-hints-reveal", { detail: { game: opts.game || null, id: puzzleId, rung: rung.key } }));
      if (typeof opts.onReveal === "function") { try { opts.onReveal(rung.key, puzzleId); } catch (e) { /* the game's callback must not break the ladder */ } }
      if (ask.hidden) {                       // the button went away: keep keyboard focus on the new text
        const item = list.lastElementChild;
        if (item) item.focus();
      }
    }

    // a press first re-reads the game's puzzle: if the game moved on without a refresh(), the ladder resets
    // and shows its fresh state instead of revealing a rung of a puzzle the player is no longer on
    function stale() {
      const before = puzzleId;
      refresh();
      return puzzleId !== before;
    }

    ask.addEventListener("click", () => {
      if (destroyed || stale()) return;
      const next = rungs[revealed];
      if (!next) return;
      if (next.key === "answer" && askFirst) {
        confirming = true;
        paint();
        no.focus();
      } else {
        reveal(next);
      }
    });
    yes.addEventListener("click", () => {
      if (destroyed || stale()) return;
      const next = rungs[revealed];
      if (next && next.key === "answer") reveal(next);
    });
    function cancel() {
      confirming = false;
      paint();
      ask.focus();
    }
    no.addEventListener("click", cancel);
    confirm.addEventListener("keydown", (ev) => { if (ev.key === "Escape") { ev.preventDefault(); cancel(); } });

    function setEnabled(on, o) {
      const next = !!on;
      enabled = next;
      if (!o || o.persist !== false) writePref(opts.game, enabled);
      refresh();
    }

    const onEvent = (ev) => {
      const g = ev && ev.detail && ev.detail.game;
      if (!g || !opts.game || g === opts.game) refresh();
    };
    document.addEventListener("noyvj-hints-change", onEvent);

    const api = {
      refresh,
      reset() {
        revealed = 0;
        confirming = false;
        if (!destroyed) refresh();
      },
      rungShown: () => revealed,
      used: () => rungs.slice(0, revealed).map((r) => r.key),
      setEnabled,
      isEnabled: () => enabled,
      focus() { root.focus(); },
      destroy() {
        destroyed = true;
        document.removeEventListener("noyvj-hints-change", onEvent);
        ladders.delete(api);
        root.remove();
      },
      element: root,
    };
    ladders.add(api);
    refresh();
    return api;
  }

  /** Keep a settings checkbox and the ladder's on/off in step. Returns a function that unbinds it. */
  function bindCheckbox(ladder, checkbox) {
    const box = target(checkbox);
    if (!ladder || !box) return () => {};
    box.checked = ladder.isEnabled();
    const onChange = () => ladder.setEnabled(box.checked);
    box.addEventListener("change", onChange);
    return () => box.removeEventListener("change", onChange);
  }

  window.NoyvjHints = { RUNGS: KEYS.slice(), mount, bindCheckbox, stats, normalizePuzzle, refreshAll() { ladders.forEach((l) => l.refresh()); } };
})();
