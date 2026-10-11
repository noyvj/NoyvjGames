/*
 * Shared difficulty choice (planning/TODO.md AN-17, owner answer Pq10): one start-of-game choice, Easy / Normal / Hard,
 * Normal by default, remembered per browser per game. The component never decides a rule: a game reads
 * NoyvjDifficulty.get("<slug>") (and listens with onChange) and decides what each level changes. House rules for a
 * game that uses it:
 *   - Normal is the game as designed. Easy and Hard change only the help you are given and the bar for medals, never the
 *     rules or whether a puzzle can be finished; nothing is locked by choosing either; achievements stay reachable on Normal.
 *   - The choice is the player's, never adaptive, and can be changed at any time unless the game says otherwise (setGuard).
 *
 *   <link rel="stylesheet" href="../../shared/difficulty.css">   (optional: the script links it itself)
 *   <script src="../../shared/difficulty.js"></script>
 *
 *   NoyvjDifficulty.get("logic-gates")            -> "easy" | "normal" | "hard" (a missing or bad stored value is "normal")
 *   NoyvjDifficulty.has("logic-gates")            -> true once the player has made a choice on this browser
 *   NoyvjDifficulty.set("logic-gates", "hard")    -> true when stored (or already that level); false for a bad level or when
 *                                                    the game's guard refuses; {force:true} as a third argument skips the guard
 *   NoyvjDifficulty.clear("logic-gates")          -> forget the choice (back to Normal, "has" is false again)
 *   const off = NoyvjDifficulty.onChange(({game, level, previous, source}) => {...})   // source "set", "clear" or "storage"
 *                                                    (another tab changed it); returns the unsubscribe function. The same
 *                                                    information is also sent as document event "noyvj-difficulty-change".
 *   NoyvjDifficulty.setGuard("logic-gates", (next) => true | false | {allowed:false, reason:"..."})   // may a change happen now?
 *   NoyvjDifficulty.canChange("logic-gates", next?) -> {allowed, reason}; a guard that throws allows the change.
 *   const ui = NoyvjDifficulty.mount("#difficulty-slot", {
 *     game: "logic-gates",
 *     descriptions: {easy: "...", normal: "...", hard: "..."},   // plain words: what each level changes in THIS game
 *     canChange: () => true,                                     // optional: same as setGuard
 *     collapsible: true,                                         // optional: a details block, open until a choice is made
 *     title: "Difficulty",                                       // optional
 *   });                                                          // -> {refresh(), select(level), destroy(), element}
 *
 * Storage: localStorage["difficulty:<slug>"] = "easy" | "normal" | "hard"; blocked storage keeps the choice in memory for the
 * session. Text is written with textContent only; no timers; no network.
 */
(function () {
  "use strict";
  if (window.NoyvjDifficulty) return;

  var LEVELS = ["easy", "normal", "hard"];
  var DEFAULT = "normal";
  var LABELS = { easy: "Easy", normal: "Normal", hard: "Hard" };
  var DEFAULT_DESCRIPTIONS = {
    easy: "More help and friendlier medal bars.",
    normal: "The game as designed.",
    hard: "Less help and tighter medal bars.",
  };
  var NOTE = "Normal is the game as designed and is always enough to finish everything and earn every achievement. " +
    "Easy and Hard only change the help you get and the bar for medals; nothing is locked and you can change your mind.";
  var CSS_FILE = "difficulty.css";
  var PREFIX = "difficulty:";
  var SLUG_RE = /^[a-z0-9][a-z0-9-]{0,39}$/;

  var memory = {};            // game -> level, used when storage is blocked and kept in step otherwise
  var memoryChosen = {};      // game -> true once chosen this session
  var listeners = [];
  var guards = {};
  var mounts = [];
  var uid = 0;

  function ensureStylesheet() {
    if (typeof document === "undefined" || document.querySelector('link[href*="' + CSS_FILE + '"]')) return;
    var own = document.currentScript || Array.prototype.slice.call(document.scripts).filter(function (s) { return /difficulty\.js/.test(s.src || ""); })[0];
    if (!own || !own.src) return;
    var link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = own.src.replace(/difficulty\.js(\?.*)?$/, CSS_FILE);
    document.head.appendChild(link);
  }
  ensureStylesheet();

  function validSlug(slug) { return typeof slug === "string" && SLUG_RE.test(slug); }
  function clean(level) { return typeof level === "string" && LEVELS.indexOf(level) >= 0 ? level : null; }

  function readStored(slug) {
    try { return localStorage.getItem(PREFIX + slug); } catch (e) { return undefined; }   // undefined: storage unavailable
  }
  function writeStored(slug, level) {
    try {
      if (level === null) localStorage.removeItem(PREFIX + slug);
      else localStorage.setItem(PREFIX + slug, level);
    } catch (e) { /* blocked storage: the memory copy still holds it for this session */ }
  }

  function get(slug) {
    if (!validSlug(slug)) return DEFAULT;
    var stored = readStored(slug);
    if (stored === undefined) return clean(memory[slug]) || DEFAULT;
    return clean(stored) || DEFAULT;
  }
  function has(slug) {
    if (!validSlug(slug)) return false;
    var stored = readStored(slug);
    if (stored === undefined) return !!memoryChosen[slug];
    return clean(stored) !== null;
  }

  function canChange(slug, next) {
    var guard = guards[slug];
    if (typeof guard !== "function") return { allowed: true, reason: "" };
    var verdict;
    try { verdict = guard(next === undefined ? null : next); } catch (e) { return { allowed: true, reason: "" }; }
    if (verdict === false) return { allowed: false, reason: "" };
    if (verdict && typeof verdict === "object" && verdict.allowed === false) {
      return { allowed: false, reason: typeof verdict.reason === "string" ? verdict.reason : "" };
    }
    return { allowed: true, reason: "" };
  }
  function setGuard(slug, fn) {
    if (!validSlug(slug)) return;
    if (typeof fn === "function") guards[slug] = fn; else delete guards[slug];
    refreshAll();
  }

  function notify(detail) {
    listeners.slice().forEach(function (fn) { try { fn(detail); } catch (e) { /* one listener must not break the others */ } });
    try { document.dispatchEvent(new CustomEvent("noyvj-difficulty-change", { detail: detail })); } catch (e) { /* old browser */ }
    refreshAll();
  }
  function onChange(fn) {
    if (typeof fn !== "function") return function () {};
    listeners.push(fn);
    return function () { var i = listeners.indexOf(fn); if (i >= 0) listeners.splice(i, 1); };
  }

  function set(slug, level, opts) {
    var next = clean(level);
    if (!validSlug(slug) || next === null) return false;
    var previous = get(slug);
    var wasChosen = has(slug);
    if (next !== previous && !(opts && opts.force) && !canChange(slug, next).allowed) return false;
    memory[slug] = next;
    memoryChosen[slug] = true;
    writeStored(slug, next);
    if (next !== previous) notify({ game: slug, level: next, previous: previous, source: "set" });
    else if (!wasChosen) refreshAll();
    return true;
  }
  function clear(slug) {
    if (!validSlug(slug)) return false;
    var previous = get(slug);
    delete memory[slug];
    delete memoryChosen[slug];
    writeStored(slug, null);
    if (previous !== DEFAULT) notify({ game: slug, level: DEFAULT, previous: previous, source: "clear" });
    else refreshAll();
    return true;
  }

  // another tab changed the choice
  if (typeof window.addEventListener === "function") {
    window.addEventListener("storage", function (ev) {
      if (!ev || typeof ev.key !== "string" || ev.key.indexOf(PREFIX) !== 0) return;
      var slug = ev.key.slice(PREFIX.length);
      if (!validSlug(slug)) return;
      var now = clean(ev.newValue) || DEFAULT;
      var before = clean(ev.oldValue) || DEFAULT;
      memory[slug] = now;
      if (now !== before) notify({ game: slug, level: now, previous: before, source: "storage" });
      else refreshAll();
    });
  }

  // ---- the radio group -------------------------------------------------------------------------------------------
  function el(tag, cls, text, attrs) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    if (attrs) Object.keys(attrs).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    return n;
  }
  function target(x) { return typeof x === "string" ? document.querySelector(x) : x; }

  function mount(container, opts) {
    opts = opts || {};
    var host = target(container);
    var slug = opts.game;
    if (!host || !validSlug(slug)) return null;
    ensureStylesheet();
    if (typeof opts.canChange === "function") guards[slug] = opts.canChange;
    var descriptions = {};
    LEVELS.forEach(function (lv) {
      var d = opts.descriptions && typeof opts.descriptions[lv] === "string" && opts.descriptions[lv].trim();
      descriptions[lv] = d || DEFAULT_DESCRIPTIONS[lv];
    });
    var id = "noyvj-diff-" + (++uid);
    var title = typeof opts.title === "string" && opts.title.trim() ? opts.title.trim() : "Difficulty";
    var root = el("div", "noyvj-diff", null, { "data-game": slug });
    var body = root;
    var current = null;
    var details = null;
    if (opts.collapsible) {
      details = el("details", "noyvj-diff-details");
      var summary = el("summary", "noyvj-diff-summary");
      summary.appendChild(el("span", "noyvj-diff-summary-label", title + ": "));
      current = el("b", "noyvj-diff-current", LABELS[get(slug)]);
      summary.appendChild(current);
      details.appendChild(summary);
      body = el("div", "noyvj-diff-body");
      details.appendChild(body);
      details.open = !has(slug);
      root.appendChild(details);
    }
    var fieldset = el("fieldset", "noyvj-diff-set", null, { "aria-describedby": id + "-note" });
    fieldset.appendChild(el("legend", "noyvj-diff-legend", title));
    var inputs = {};
    var options = {};
    LEVELS.forEach(function (lv) {
      var label = el("label", "noyvj-diff-opt", null, { "data-level": lv });
      var input = el("input", "noyvj-diff-input", null, { type: "radio", name: id, value: lv });
      var text = el("span", "noyvj-diff-text");
      var name = el("span", "noyvj-diff-name", LABELS[lv] + (lv === DEFAULT ? " (recommended)" : ""));
      var desc = el("span", "noyvj-diff-desc", descriptions[lv]);
      text.appendChild(name);
      text.appendChild(desc);
      label.appendChild(input);
      label.appendChild(text);
      fieldset.appendChild(label);
      inputs[lv] = input;
      options[lv] = label;
      // "click" also fires for a keyboard arrow and for pressing the level that is already chosen (which confirms it)
      input.addEventListener("click", function () {
        if (!set(slug, lv)) paint();                 // refused: put the group back to what is really chosen
        else say("Difficulty set to " + LABELS[lv] + ".");
      });
    });
    body.appendChild(fieldset);
    var lock = el("p", "noyvj-diff-lock", "");
    lock.hidden = true;
    body.appendChild(lock);
    body.appendChild(el("p", "noyvj-diff-note", opts.note || NOTE, { id: id + "-note" }));
    var live = el("div", "noyvj-diff-sr", "", { role: "status", "aria-live": "polite", "aria-atomic": "true" });
    root.appendChild(live);
    host.appendChild(root);

    var destroyed = false;
    function say(text) {
      live.textContent = "";
      Promise.resolve().then(function () { if (!destroyed) live.textContent = text; });
    }
    function paint() {
      if (destroyed) return;
      var level = get(slug);
      var verdict = canChange(slug, null);
      LEVELS.forEach(function (lv) {
        inputs[lv].checked = lv === level;
        inputs[lv].disabled = !verdict.allowed;
        options[lv].setAttribute("data-selected", lv === level ? "true" : "false");
      });
      if (current) current.textContent = LABELS[level];
      lock.hidden = verdict.allowed;
      lock.textContent = verdict.allowed ? "" : (verdict.reason || "The difficulty cannot be changed right now.");
      root.setAttribute("data-level", level);
    }
    var api = {
      refresh: paint,
      select: function (level) { return set(slug, level); },
      destroy: function () {
        destroyed = true;
        var i = mounts.indexOf(api);
        if (i >= 0) mounts.splice(i, 1);
        root.remove();
      },
      element: root,
    };
    mounts.push(api);
    paint();
    return api;
  }
  function refreshAll() { mounts.slice().forEach(function (m) { m.refresh(); }); }

  window.NoyvjDifficulty = {
    LEVELS: LEVELS.slice(),
    DEFAULT: DEFAULT,
    LABELS: Object.assign({}, LABELS),
    get: get,
    has: has,
    set: set,
    clear: clear,
    onChange: onChange,
    setGuard: setGuard,
    canChange: canChange,
    mount: mount,
  };
})();
