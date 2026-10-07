/*
 * Shared seeded-run module, browser side (planning/TODO.md Z-1 seeded runs, Z-5 daily seed).
 * The Python twin is shared/seed.py: the SAME algorithm, bit for bit, pinned together by
 * shared/tests/test_seed_browser.py (many seeds, every draw type). API and adoption notes:
 * planning/SHARED-COMPONENTS.md, section "Seeded runs".
 *
 *   <script src="../../shared/seed.js"></script>
 *
 * Seed string:  PREFIX-CODE, e.g. TIDE-K7F2Q. PREFIX is the game slug upper-cased with everything
 * that is not a letter or digit removed (2 to 12 chars); CODE is 5 chars from a 31-symbol alphabet
 * with no 0, 1, I, L or O. The generator is splitmix64 started from the FNV-1a hash of the seed
 * text (like games/chronicle/puzzle.py), done with BigInt so it is exact.
 *
 * window.NoyvjSeed:
 *   rng(seed) / Rng            deterministic generator: next() random() randint(a,b) uniform(a,b)
 *                              chance(p) choice(list) shuffle(list) shuffled(list) sample(list,k)
 *                              weightedChoice(items,weights) below(n) fork(label) getState() setState(s)
 *   newSeed(game[, entropy])   fresh seed (crypto random; entropy = function(n) -> int in [0,n))
 *   dailySeed(game, date)      the one seed for a UTC date ("2026-10-08" or a Date)
 *   normalize(text[, game]) / validate(text[, game]) / isValid / prefixFor / example
 *   current() / set(seed) / clear() / fromUrl(game)    the run's seed, read by shared/info-footer.js
 *   mountCopy(el, opts)        "Copy seed" for a run-end screen
 *   mountStart(el, opts)       "Start from seed" field for a new-game screen
 *   daily.*                    Today's run: daily.mountButton, daily.markCompleted, daily.read, ...
 * Snake_case aliases new_seed / daily_seed exist so Python-minded callers find them.
 *
 * Text is only ever written with textContent. Nothing here calls the network.
 */
(function () {
  "use strict";

  const ALGORITHM_VERSION = "v1";
  const ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ";
  const CODE_LEN = 5;
  const PREFIX_MIN = 2;
  const PREFIX_MAX = 12;
  const MASK = (1n << 64n) - 1n;
  const TWO53 = 9007199254740992;
  const DASHES = /[‐‑‒–—−_]/g;
  const SPACE = /[ \t\r\n\f\v  -​  　﻿]+/g;
  const PREFIX_OK = new RegExp("^[A-Z0-9]{" + PREFIX_MIN + "," + PREFIX_MAX + "}$");
  const DATE_OK = /^\d{4}-\d{2}-\d{2}$/;

  // ---- generator ---------------------------------------------------------------------------
  function fnv1a64(text) {
    let h = 0xcbf29ce484222325n;
    const bytes = new TextEncoder().encode(text);
    for (let i = 0; i < bytes.length; i++) {
      h ^= BigInt(bytes[i]);
      h = (h * 0x100000001b3n) & MASK;
    }
    return h;
  }

  function isInt(n) { return typeof n === "number" && Number.isSafeInteger(n); }

  class Rng {
    constructor(seedText) {
      this.seed = String(seedText);
      this.state = fnv1a64(this.seed);
    }
    /** Next 64-bit unsigned integer, as a BigInt. */
    next() {
      this.state = (this.state + 0x9e3779b97f4a7c15n) & MASK;
      let z = this.state;
      z = ((z ^ (z >> 30n)) * 0xbf58476d1ce4e5b9n) & MASK;
      z = ((z ^ (z >> 27n)) * 0x94d049bb133111ebn) & MASK;
      return z ^ (z >> 31n);
    }
    /** Unbiased integer in [0, n). */
    below(n) {
      if (!isInt(n) || n <= 0) throw new RangeError("below(n) needs an integer n >= 1");
      const bn = BigInt(n);
      const limit = (1n << 64n) - ((1n << 64n) % bn);
      for (;;) {
        const v = this.next();
        if (v < limit) return Number(v % bn);
      }
    }
    /** Float in [0, 1) with 53 random bits. */
    random() { return Number(this.next() >> 11n) / TWO53; }
    /** Integer in [a, b], both included. */
    randint(a, b) {
      if (!isInt(a) || !isInt(b) || b < a) throw new RangeError("randint(a, b) needs integers with b >= a");
      return a + this.below(b - a + 1);
    }
    uniform(a, b) { return a + (b - a) * this.random(); }
    chance(p) { return this.random() < p; }
    choice(items) {
      const list = Array.from(items);
      if (!list.length) throw new RangeError("choice() from an empty sequence");
      return list[this.below(list.length)];
    }
    /** Shuffles the array IN PLACE (Fisher-Yates, back to front) and returns it. */
    shuffle(items) {
      for (let i = items.length - 1; i > 0; i--) {
        const j = this.below(i + 1);
        const t = items[i]; items[i] = items[j]; items[j] = t;
      }
      return items;
    }
    shuffled(items) { return this.shuffle(Array.from(items)); }
    sample(items, k) {
      const list = Array.from(items);
      if (!isInt(k) || k < 0 || k > list.length) throw new RangeError("sample larger than the population");
      const out = [];
      for (let i = 0; i < k; i++) out.push(list.splice(this.below(list.length), 1)[0]);
      return out;
    }
    weightedChoice(items, weights) {
      const list = Array.from(items);
      const w = Array.from(weights);
      if (!list.length || list.length !== w.length) throw new RangeError("weightedChoice needs equal, non-empty items and weights");
      let total = 0;
      for (const x of w) {
        if (!(x >= 0)) throw new RangeError("weights must not be negative");
        total += x;
      }
      if (!(total > 0)) throw new RangeError("weights must add up to more than zero");
      const r = this.random() * total;
      let acc = 0;
      for (let i = 0; i < list.length; i++) {
        acc += w[i];
        if (r < acc) return list[i];
      }
      return list[list.length - 1];
    }
    /** An independent stream for one purpose; depends only on seed and label. */
    fork(label) { return new Rng(this.seed + "#" + label); }
    /** Position as a decimal string (JSON-safe; identical to seed.py's get_state). */
    getState() { return this.state.toString(); }
    setState(text) {
      if (!/^\d+$/.test(String(text))) throw new RangeError("state must be a decimal string");
      const v = BigInt(String(text));
      if (v > MASK) throw new RangeError("state out of range");
      this.state = v;
    }
  }

  function rng(seedText) { return new Rng(seedText); }

  // ---- seed strings --------------------------------------------------------------------------
  function prefixFor(game) {
    const p = String(game).toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, PREFIX_MAX);
    if (p.length < PREFIX_MIN) throw new RangeError("game slug " + JSON.stringify(game) + " is too short to make a seed prefix");
    return p;
  }

  function example(game) { return prefixFor(game) + "-K7F2Q"; }

  function randomCode(below) {
    let out = "";
    for (let i = 0; i < CODE_LEN; i++) out += ALPHABET[below(ALPHABET.length)];
    return out;
  }

  function cryptoBelow(n) {
    const c = typeof crypto !== "undefined" && crypto.getRandomValues ? crypto : null;
    if (!c) return Math.floor(Math.random() * n);
    const limit = 0x100000000 - (0x100000000 % n);
    const buf = new Uint32Array(1);
    for (;;) {
      c.getRandomValues(buf);
      if (buf[0] < limit) return buf[0] % n;
    }
  }

  function newSeed(game, entropy) {
    let below = cryptoBelow;
    if (typeof entropy === "function") below = entropy;
    else if (entropy && typeof entropy.below === "function") below = (n) => entropy.below(n);
    return prefixFor(game) + "-" + randomCode(below);
  }

  function dateString(date) {
    if (date instanceof Date) {
      if (isNaN(date.getTime())) throw new RangeError("dailySeed needs a real date");
      return date.toISOString().slice(0, 10);
    }
    return date;
  }

  function realDate(text) {
    if (typeof text !== "string" || !DATE_OK.test(text)) return false;
    const [y, m, d] = text.split("-").map(Number);
    const t = new Date(Date.UTC(y, m - 1, d));
    return t.getUTCFullYear() === y && t.getUTCMonth() === m - 1 && t.getUTCDate() === d && y >= 1;
  }

  function dailySeed(game, date) {
    const text = dateString(date);
    if (typeof text !== "string" || !DATE_OK.test(text)) throw new RangeError("dailySeed needs a YYYY-MM-DD date");
    if (!realDate(text)) throw new RangeError("dailySeed needs a real calendar date");
    const prefix = prefixFor(game);
    const r = new Rng("noyvj-daily-" + ALGORITHM_VERSION + "|" + prefix + "|" + text);
    return prefix + "-" + randomCode((n) => r.below(n));
  }

  function normalize(text, game) {
    if (typeof text !== "string") return "";
    const hasGame = game !== undefined && game !== null;
    const s = text.replace(DASHES, "-").replace(SPACE, "").toUpperCase();
    if (!s) return "";
    let prefix, code;
    if (s.includes("-")) {
      const at = s.lastIndexOf("-");
      prefix = s.slice(0, at).replace(/-/g, "");
      code = s.slice(at + 1);
    } else if (hasGame && s.length === CODE_LEN) {
      prefix = prefixFor(game); code = s;
    } else if (s.length > CODE_LEN) {
      prefix = s.slice(0, -CODE_LEN); code = s.slice(-CODE_LEN);
    } else {
      return "";
    }
    if (hasGame && prefix === "") prefix = prefixFor(game);
    if (!PREFIX_OK.test(prefix)) return "";
    if (code.length !== CODE_LEN) return "";
    for (const c of code) if (!ALPHABET.includes(c)) return "";
    return prefix + "-" + code;
  }

  function validate(text, game) {
    const hasGame = game !== undefined && game !== null;
    const raw = typeof text === "string" ? text.trim() : "";
    if (!raw) {
      return { ok: false, seed: "", error: "empty", message: "Enter a seed" + (hasGame ? " such as " + example(game) : "") + "." };
    }
    const seed = normalize(raw, game);
    if (!seed) {
      return { ok: false, seed: "", error: "format",
        message: "That is not a seed: use letters and digits (no 0, 1, I, L or O)." + (hasGame ? " Seeds look like " + example(game) + "." : "") };
    }
    if (hasGame && seed.split("-")[0] !== prefixFor(game)) {
      return { ok: false, seed: "", error: "wrong-game", message: "That seed is for " + seed.split("-")[0] + ", not this game." };
    }
    return { ok: true, seed, error: "", message: "" };
  }

  function isValid(text, game) { return validate(text, game).ok; }

  // ---- the run's current seed (read by shared/info-footer.js) ----------------------------------
  let currentSeed = "";

  function emit(name, detail) {
    try { document.dispatchEvent(new CustomEvent(name, { detail })); } catch (e) { /* no DOM events */ }
  }
  function current() { return currentSeed; }
  function setCurrent(seed) {
    const s = typeof seed === "string" ? seed : "";
    if (s === currentSeed) return currentSeed;
    currentSeed = s;
    emit("noyvj-seed-change", { seed: s });
    return currentSeed;
  }
  function clear() { return setCurrent(""); }
  /** A valid seed from ?seed= in the address, or "" (for a shared link; Z-2 builds on this). */
  function fromUrl(game) {
    try {
      const v = validate(new URLSearchParams(location.search).get("seed") || "", game);
      return v.ok ? v.seed : "";
    } catch (e) { return ""; }
  }

  // ---- shared UI plumbing ----------------------------------------------------------------------
  const STYLE_ID = "noyvj-seed-style";
  const CSS = `
:root{--ns-bg:rgba(20,24,42,.78);--ns-fg:#e8e9f0;--ns-muted:#aab0c8;--ns-border:rgba(140,160,255,.5);--ns-accent:#9fe0ab;--ns-on-accent:#0e1a12;--ns-err:#ffb4a8;--ns-focus:#ffd866;--ns-field:rgba(10,12,24,.6)}
html[data-theme="light"]{--ns-bg:rgba(255,255,255,.94);--ns-fg:#1b2033;--ns-muted:#4a5275;--ns-border:rgba(60,85,160,.55);--ns-accent:#1f6b3a;--ns-on-accent:#fff;--ns-err:#9b1c0c;--ns-focus:#8a5a00;--ns-field:#fff}
@media (prefers-color-scheme:light){:root:not([data-theme]){--ns-bg:rgba(255,255,255,.94);--ns-fg:#1b2033;--ns-muted:#4a5275;--ns-border:rgba(60,85,160,.55);--ns-accent:#1f6b3a;--ns-on-accent:#fff;--ns-err:#9b1c0c;--ns-focus:#8a5a00;--ns-field:#fff}}
.noyvj-seed[hidden],.noyvj-seed [hidden]{display:none!important}
.noyvj-seed{box-sizing:border-box;max-width:100%;margin:.5rem 0;padding:.6rem .75rem;border:1px solid var(--ns-border);border-radius:10px;background:var(--ns-bg);color:var(--ns-fg);font:.9rem/1.4 system-ui,sans-serif}
.noyvj-seed *{box-sizing:border-box}
.noyvj-seed-row{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem}
.noyvj-seed-label{font-weight:600}
label.noyvj-seed-label{display:block;margin-bottom:.4rem}
.noyvj-seed-code{padding:.3rem .55rem;border:1px dashed var(--ns-border);border-radius:6px;font:700 1.05rem ui-monospace,Menlo,Consolas,monospace;letter-spacing:.06em;overflow-wrap:anywhere;user-select:all}
.noyvj-seed-btn{min-height:44px;padding:.4rem .9rem;border:2px solid var(--ns-border);border-radius:8px;background:transparent;color:var(--ns-fg);font:600 .9rem system-ui,sans-serif;cursor:pointer}
.noyvj-seed-btn--primary{background:var(--ns-accent);border-color:var(--ns-accent);color:var(--ns-on-accent)}
.noyvj-seed-btn:focus-visible,.noyvj-seed-input:focus-visible{outline:3px solid var(--ns-focus);outline-offset:2px}
.noyvj-seed-input{flex:1 1 11rem;min-width:0;min-height:44px;padding:.4rem .6rem;border:2px solid var(--ns-border);border-radius:8px;background:var(--ns-field);color:var(--ns-fg);font:700 1rem ui-monospace,Menlo,Consolas,monospace;letter-spacing:.06em;text-transform:uppercase}
.noyvj-seed-input[aria-invalid="true"]{border-style:dashed;border-width:3px}
.noyvj-seed-hint,.noyvj-seed-status{margin:.35rem 0 0;color:var(--ns-muted);font-size:.82rem}
.noyvj-seed-error{margin:.35rem 0 0;color:var(--ns-err);font-weight:600;font-size:.85rem}
.noyvj-seed-fallback{width:100%;margin-top:.4rem}
.noyvj-seed--done{border-style:solid;border-width:2px}
.noyvj-seed--open{border-style:dashed}
@media (prefers-reduced-motion:no-preference){html:not([data-reduced-motion="true"]) .noyvj-seed-btn{transition:background-color .15s ease}}
@media (max-width:420px){.noyvj-seed-btn{flex:1 1 100%}}
`;
  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const st = document.createElement("style");
    st.id = STYLE_ID;
    st.textContent = CSS;
    (document.head || document.documentElement).appendChild(st);
  }

  let uid = 0;
  function el(tag, cls, text, attrs) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined && text !== null) n.textContent = text;
    if (attrs) for (const k of Object.keys(attrs)) n.setAttribute(k, attrs[k]);
    return n;
  }
  function target(x) { return typeof x === "string" ? document.querySelector(x) : x; }

  /** Clipboard write with a legacy fallback. Resolves true when the text reached the clipboard. */
  function copyText(text) {
    const legacy = () => {
      try {
        const ta = el("textarea", "", text, { readonly: "", "aria-hidden": "true", tabindex: "-1" });
        ta.style.cssText = "position:fixed;top:0;left:-9999px;opacity:0";
        document.body.appendChild(ta);
        ta.select();
        const ok = document.execCommand && document.execCommand("copy");
        ta.remove();
        return !!ok;
      } catch (e) { return false; }
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(() => true, () => legacy());
    }
    return Promise.resolve(legacy());
  }

  // ---- "Copy seed" (run-end screen) --------------------------------------------------------------
  /**
   * mountCopy(container, { game, seed, label, buttonLabel, onCopy })
   * Shows the seed as text with a Copy button. If the browser refuses the clipboard, a selected
   * read-only box appears with "press Ctrl+C". Returns { update(seed), destroy(), element }.
   * `seed` defaults to NoyvjSeed.current().
   */
  function mountCopy(container, opts) {
    opts = opts || {};
    const host = target(container);
    if (!host) return null;
    injectStyle();
    const id = "noyvj-seed-copy-" + (++uid);
    const root = el("div", "noyvj-seed noyvj-seed-copy", null, { role: "group", "aria-labelledby": id + "-l" });
    const row = el("div", "noyvj-seed-row");
    const label = el("span", "noyvj-seed-label", opts.label || "Seed", { id: id + "-l" });
    const code = el("code", "noyvj-seed-code", "", { id: id + "-c" });
    const btn = el("button", "noyvj-seed-btn", "", { type: "button" });
    row.append(label, code, btn);
    const status = el("p", "noyvj-seed-status", "", { role: "status", "aria-live": "polite" });
    const hint = el("p", "noyvj-seed-hint", "Share this seed to replay the same run.");
    root.append(row, hint, status);
    host.appendChild(root);
    let seed = "";
    let box = null;
    const btnLabel = opts.buttonLabel || "Copy seed";
    function paint() {
      code.textContent = seed || "none yet";
      btn.textContent = "⧉ " + btnLabel;
      btn.disabled = !seed;
      btn.setAttribute("aria-label", seed ? btnLabel + " " + seed.split("").join(" ") : btnLabel);
      hint.hidden = !seed;
    }
    function update(next) {
      seed = typeof next === "string" ? next : (current() || "");
      status.textContent = "";
      if (box) { box.remove(); box = null; }
      paint();
    }
    btn.addEventListener("click", () => {
      if (!seed) return;
      copyText(seed).then((ok) => {
        if (ok) {
          status.textContent = "✓ Copied " + seed;
          if (opts.onCopy) opts.onCopy(seed);
        } else {
          if (!box) {
            box = el("input", "noyvj-seed-input noyvj-seed-fallback", "", { type: "text", readonly: "", "aria-label": "Seed to copy" });
            root.appendChild(box);
          }
          box.value = seed;
          box.focus();
          box.select();
          status.textContent = "Could not copy automatically: press Ctrl+C (or ⌘C) to copy the selected seed.";
        }
      });
    });
    update(opts.seed);
    return { update, destroy() { root.remove(); }, element: root };
  }

  // ---- "Start from seed" (new-game screen) ---------------------------------------------------------
  /**
   * mountStart(container, { game, onStart(seed, info), initial, random, buttonLabel })
   * A labelled field plus a button. Accepts the seed in any case, with or without the prefix.
   * A bad seed is explained in text (a "!" and a dashed border, never colour alone) and focus
   * returns to the field. A good one becomes NoyvjSeed.current() and is passed to onStart.
   * Returns { setValue(text), focus(), destroy(), element }.
   */
  function mountStart(container, opts) {
    opts = opts || {};
    const host = target(container);
    if (!host) return null;
    if (!opts.game) throw new Error("NoyvjSeed.mountStart needs a game slug");
    injectStyle();
    const id = "noyvj-seed-start-" + (++uid);
    const form = el("form", "noyvj-seed noyvj-seed-start", null, { novalidate: "", "aria-labelledby": id + "-l" });
    const label = el("label", "noyvj-seed-label", "Start from seed", { id: id + "-l", for: id + "-i" });
    const row = el("div", "noyvj-seed-row");
    const input = el("input", "noyvj-seed-input", "", {
      id: id + "-i", type: "text", autocomplete: "off", autocapitalize: "characters", spellcheck: "false",
      maxlength: "40", placeholder: example(opts.game), "aria-describedby": id + "-h " + id + "-e",
    });
    const go = el("button", "noyvj-seed-btn noyvj-seed-btn--primary", "▶ " + (opts.buttonLabel || "Start from seed"), { type: "submit" });
    row.append(input, go);
    if (opts.random !== false) {
      const dice = el("button", "noyvj-seed-btn", "⚄ Random seed", { type: "button" });
      dice.addEventListener("click", () => { input.value = newSeed(opts.game); setError(""); input.focus(); });
      row.appendChild(dice);
    }
    const hint = el("p", "noyvj-seed-hint", "Type or paste a seed to replay a run: the same seed gives the same run.", { id: id + "-h" });
    const err = el("p", "noyvj-seed-error", "", { id: id + "-e", role: "alert" });
    err.hidden = true;
    form.append(label, row, hint, err);
    host.appendChild(form);
    function setError(message) {
      err.hidden = !message;
      err.textContent = message ? "! " + message : "";
      if (message) input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid");
    }
    input.addEventListener("input", () => setError(""));
    form.addEventListener("submit", (ev) => {
      ev.preventDefault();
      const v = validate(input.value, opts.game);
      if (!v.ok) { setError(v.message); input.focus(); return; }
      setError("");
      input.value = v.seed;
      setCurrent(v.seed);
      if (opts.onStart) opts.onStart(v.seed, { fromUser: true });
    });
    if (opts.initial) input.value = opts.initial;
    return {
      setValue(t) { input.value = t; setError(""); },
      focus() { input.focus(); },
      destroy() { form.remove(); },
      element: form,
    };
  }

  // ---- Today's run (Z-5) -------------------------------------------------------------------------
  /*
   * localStorage["noyvj-daily-v1"] (per browser; the hub reads it for its Today strip):
   *   { "version": 1,
   *     "date": "2026-10-08",                       // UTC date the `runs` belong to
   *     "runs":    { "tide": { "seed": "TIDE-X54PB", "completed_at": "2026-10-08T14:03:00.000Z", "score": 4210, "text": "4,210 pts" } },
   *     "streaks": { "tide": { "count": 3, "best": 5, "last": "2026-10-08" } } }
   * `runs` only ever holds the stored `date`; reading on a later day treats it as empty and the next
   * write replaces it. Streaks never punish: `count` simply starts again at 1 after a missed day and
   * `best` is kept for good.
   */
  const DAILY_KEY = "noyvj-daily-v1";

  function utcToday(now) {
    const d = now instanceof Date ? now : new Date();
    return d.toISOString().slice(0, 10);
  }
  function addDays(dateText, n) {
    const [y, m, d] = dateText.split("-").map(Number);
    return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10);
  }
  function emptyDaily(date) { return { version: 1, date, runs: {}, streaks: {} }; }

  function sanitizeDaily(raw) {
    const out = emptyDaily("");
    if (!raw || typeof raw !== "object" || raw.version !== 1) return out;
    if (typeof raw.date === "string" && realDate(raw.date)) out.date = raw.date;
    const safeGame = (k) => /^[a-z0-9-]{1,40}$/.test(k);
    if (raw.runs && typeof raw.runs === "object") {
      for (const k of Object.keys(raw.runs)) {
        const r = raw.runs[k];
        if (!safeGame(k) || !r || typeof r !== "object" || typeof r.seed !== "string") continue;
        const run = { seed: r.seed.slice(0, 40), completed_at: typeof r.completed_at === "string" ? r.completed_at.slice(0, 40) : "" };
        if (typeof r.score === "number" && isFinite(r.score)) run.score = r.score;
        if (typeof r.text === "string") run.text = r.text.slice(0, 120);
        out.runs[k] = run;
      }
    }
    if (raw.streaks && typeof raw.streaks === "object") {
      for (const k of Object.keys(raw.streaks)) {
        const s = raw.streaks[k];
        if (!safeGame(k) || !s || typeof s !== "object" || !realDate(s.last)) continue;
        const count = Number.isSafeInteger(s.count) && s.count >= 0 ? s.count : 0;
        const best = Number.isSafeInteger(s.best) && s.best >= count ? s.best : count;
        out.streaks[k] = { count, best, last: s.last };
      }
    }
    return out;
  }

  function dailyRead(now) {
    const today = utcToday(now);
    let data = emptyDaily(today);
    try {
      const raw = JSON.parse(localStorage.getItem(DAILY_KEY));
      const clean = sanitizeDaily(raw);
      data.streaks = clean.streaks;
      if (clean.date === today) data.runs = clean.runs;
    } catch (e) { /* storage blocked or unreadable: behave as empty */ }
    return data;
  }

  function dailyWrite(data) {
    try { localStorage.setItem(DAILY_KEY, JSON.stringify(data)); return true; } catch (e) { return false; }
  }

  function dailyCompleted(game, now) { return !!dailyRead(now).runs[game]; }

  /** Streak facts for one game: { count (0 once a day was missed), best, last, doneToday }. */
  function dailyStreak(game, now) {
    const today = utcToday(now);
    const s = dailyRead(now).streaks[game];
    if (!s) return { count: 0, best: 0, last: "", doneToday: false };
    const alive = s.last === today || s.last === addDays(today, -1);
    return { count: alive ? s.count : 0, best: s.best, last: s.last, doneToday: s.last === today };
  }

  /**
   * Record that today's daily run of `game` was completed. Call it from the run-end screen when the
   * run's seed equals dailySeed(game, today). `info` may carry { score, text }. Counts once per day.
   * Returns the stored run, or null if it had already been recorded (or storage is unavailable).
   */
  function markCompleted(game, info, now) {
    const today = utcToday(now);
    const data = dailyRead(now);
    if (data.runs[game]) return null;
    const run = { seed: dailySeed(game, today), completed_at: (now instanceof Date ? now : new Date()).toISOString() };
    if (info && typeof info.score === "number" && isFinite(info.score)) run.score = info.score;
    if (info && typeof info.text === "string") run.text = info.text.slice(0, 120);
    data.runs[game] = run;
    const prev = data.streaks[game];
    let count = 1;
    if (prev && prev.last === addDays(today, -1)) count = prev.count + 1;
    data.streaks[game] = { count, best: Math.max(count, prev ? prev.best : 0), last: today };
    data.date = today;
    if (!dailyWrite(data)) return null;
    emit("noyvj-daily-change", { game, date: today });
    return run;
  }

  /** True when `seed` is today's daily seed for `game` (use it to decide whether to call markCompleted). */
  function isDaily(game, seed, now) {
    return normalize(String(seed || ""), game) === dailySeed(game, utcToday(now));
  }

  /**
   * daily.mountButton(container, { game, onStart(seed, info), today })
   * "Today's run" button for a start screen. Shows the date's seed, whether it is done today
   * (a check mark and a solid border versus a dashed one) and the streak with kind wording.
   * `today` (Date or function returning one) is for tests. Returns { refresh(), destroy(), element }.
   */
  function mountDailyButton(container, opts) {
    opts = opts || {};
    const host = target(container);
    if (!host) return null;
    if (!opts.game) throw new Error("NoyvjSeed.daily.mountButton needs a game slug");
    injectStyle();
    const nowFn = () => (typeof opts.today === "function" ? opts.today() : (opts.today instanceof Date ? opts.today : new Date()));
    const id = "noyvj-seed-daily-" + (++uid);
    const root = el("div", "noyvj-seed noyvj-seed-daily", null, { role: "group", "aria-labelledby": id + "-t" });
    const row = el("div", "noyvj-seed-row");
    const title = el("span", "noyvj-seed-label", "", { id: id + "-t" });
    const btn = el("button", "noyvj-seed-btn noyvj-seed-btn--primary", "", { type: "button", "aria-describedby": id + "-s" });
    row.append(title, btn);
    const sub = el("p", "noyvj-seed-hint", "", { id: id + "-s" });
    root.append(row, sub);
    host.appendChild(root);
    function refresh() {
      const now = nowFn();
      const day = utcToday(now);
      const seed = dailySeed(opts.game, day);
      const done = dailyCompleted(opts.game, now);
      const st = dailyStreak(opts.game, now);
      title.textContent = done ? "✓ Today's run done" : "Today's run";
      btn.textContent = done ? "↻ Play today's run again" : "📅 Play today's run";
      root.classList.toggle("noyvj-seed--done", done);
      root.classList.toggle("noyvj-seed--open", !done);
      let streak = "";
      if (st.count > 0) streak = " " + st.count + (st.count === 1 ? " day" : " days") + " in a row" + (st.best > st.count ? ", best " + st.best : "") + ".";
      else if (st.best > 0) streak = " Best streak " + st.best + ": a new one starts whenever you like.";
      sub.textContent = "Seed " + seed + " (" + day + " UTC), the same for everyone, changes at 00:00 UTC." + streak;
    }
    btn.addEventListener("click", () => {
      const now = nowFn();
      const seed = dailySeed(opts.game, utcToday(now));
      setCurrent(seed);
      if (opts.onStart) opts.onStart(seed, { daily: true, date: utcToday(now) });
    });
    const onChange = () => refresh();
    document.addEventListener("noyvj-daily-change", onChange);
    window.addEventListener("storage", onChange);
    refresh();
    return {
      refresh,
      destroy() {
        document.removeEventListener("noyvj-daily-change", onChange);
        window.removeEventListener("storage", onChange);
        root.remove();
      },
      element: root,
    };
  }

  window.NoyvjSeed = {
    ALGORITHM_VERSION, ALPHABET, CODE_LEN, DAILY_KEY,
    Rng, rng, fnv1a64,
    prefixFor, example, newSeed, new_seed: newSeed, dailySeed, daily_seed: dailySeed,
    normalize, validate, isValid,
    current, set: setCurrent, clear, fromUrl,
    copyText, mountCopy, mountStart,
    daily: {
      key: DAILY_KEY, today: utcToday, seed: dailySeed, read: dailyRead, completed: dailyCompleted,
      streak: dailyStreak, markCompleted, isDaily, mountButton: mountDailyButton,
    },
  };
})();
