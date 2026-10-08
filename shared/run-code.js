/*
 * Shared compact run code, browser side (planning/TODO.md FY-7). The Python twin is shared/run_code.py:
 * the SAME algorithm, pinned together by shared/tests/test_run_code_browser.py (many inputs, both
 * directions). Format, limits and adoption notes: planning/SHARED-COMPONENTS.md, section "Run codes".
 *
 *   <script src="../../shared/run-code.js"></script>      (stands alone; does not need seed.js)
 *
 * A run code is  RUN-<GAME>-<body in groups of 5>-<CCC>,  for example  RUN-TIDE-7G0F4-1JE0H-M62WK-4Y8G0-630-EPX.
 * The body packs a format version, the seed's 5-character code, a mode token (a-z0-9, up to 8) and
 * an optional result (a score plus up to two whole numbers) in base 32. CCC is a checksum. Nothing a
 * player typed, no name, account or address can be in it. The checksum catches typing mistakes only:
 * a decoded code is something to DISPLAY ("Their run: 4,210 pts, 3 storms"), never a verified score,
 * and nothing in it is ever executed. Every decoded result says verified: false.
 *
 * window.NoyvjRunCode:
 *   encode({game, seed?, mode?, score?, stats?})   -> code text; throws a RangeError with .reason
 *   decode(text[, game])                           -> {ok, error, message, code, game, seed, mode,
 *                                                       score, stats, hasResult, verified:false}; never throws
 *   validate(text[, game]) / isValid / normalize   -> {ok, code, error, message} / bool / canonical text or ""
 *   describe(decoded[, {prefix, unit, stats, modes}]) -> "Their run: 4,210 pts, 3 storms, hard mode"
 *   mountCopy(el, opts)    "Copy run code" for a run-end screen
 *   mountPaste(el, opts)   "Paste a run code" field that shows the friend's ghost summary
 * Text is only ever written with textContent. Nothing here calls the network.
 */
(function () {
  "use strict";
  if (window.NoyvjRunCode) return;

  const FORMAT_VERSION = 1;
  const HEADER = "RUN";
  const B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
  const SEED_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ";
  const SEED_CODE_LEN = 5;
  const SEED_BASE = SEED_ALPHABET.length;
  const SEED_LIMIT = Math.pow(SEED_BASE, SEED_CODE_LEN);
  const PREFIX_MIN = 2;
  const PREFIX_MAX = 12;
  const CHECK_LEN = 3;
  const GROUP = 5;
  const MAX_VALUE = Math.pow(2, 48) - 1;
  const MAX_STATS = 2;
  const MAX_MODE = 8;
  const MAX_COMPACT_LEN = 80;
  const MAX_INPUT_LEN = 400;
  const MASK = (1n << 64n) - 1n;
  const DASHES = /[\u2010\u2011\u2012\u2013\u2014\u2212_]/g;
  const SPACE = /[ \t\r\n\f\v\u00a0\u2000-\u200b\u202f\u205f\u3000\ufeff]+/g;
  const MODE_OK = new RegExp("^[a-z0-9]{1," + MAX_MODE + "}$");
  const PREFIX_OK = new RegExp("^[A-Z0-9]{" + PREFIX_MIN + "," + PREFIX_MAX + "}$");
  const ALIASES = { O: "0", I: "1", L: "1" };
  const MESSAGES = {
    empty: "Paste a run code first.",
    "too-long": "That is too long to be a run code.",
    format: "That does not look like a run code. Run codes start with RUN and use letters and digits.",
    version: "That run code was made by a newer version of the game. Update and try again.",
    checksum: "That run code has a typing mistake: check each character and try again.",
    "wrong-game": "That run code is for {other}, not this game.",
  };

  function fail(reason, message) {
    const e = new RangeError(message);
    e.name = "RunCodeError";
    e.reason = reason;
    return e;
  }

  // ---- small pieces (each mirrors a helper in run_code.py / seed.py) ------------------------------
  function fnv1a64(text) {
    let h = 0xcbf29ce484222325n;
    const bytes = new TextEncoder().encode(text);
    for (let i = 0; i < bytes.length; i++) {
      h ^= BigInt(bytes[i]);
      h = (h * 0x100000001b3n) & MASK;
    }
    return h;
  }

  function prefixFor(game) {
    const p = String(game).toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, PREFIX_MAX);
    if (p.length < PREFIX_MIN) throw new RangeError("game slug is too short to make a seed prefix");
    return p;
  }

  /** Same rules as seed.py normalize(text, game): canonical "PREFIX-CODE" or "". */
  function normalizeSeed(text, game) {
    if (typeof text !== "string") return "";
    const s = text.replace(DASHES, "-").replace(SPACE, "").toUpperCase();
    if (!s) return "";
    let prefix, code;
    if (s.includes("-")) {
      const at = s.lastIndexOf("-");
      prefix = s.slice(0, at).replace(/-/g, "");
      code = s.slice(at + 1);
    } else if (s.length === SEED_CODE_LEN) {
      prefix = prefixFor(game); code = s;
    } else if (s.length > SEED_CODE_LEN) {
      prefix = s.slice(0, -SEED_CODE_LEN); code = s.slice(-SEED_CODE_LEN);
    } else {
      return "";
    }
    if (prefix === "") prefix = prefixFor(game);
    if (!PREFIX_OK.test(prefix)) return "";
    if (code.length !== SEED_CODE_LEN) return "";
    for (const c of code) if (!SEED_ALPHABET.includes(c)) return "";
    return prefix + "-" + code;
  }

  const isInt = (x) => typeof x === "number" && Number.isSafeInteger(x);
  const isValue = (x) => isInt(x) && x >= 0 && x <= MAX_VALUE;

  function varint(n) {
    const out = [];
    for (;;) {
      const low = n % 128;
      n = Math.floor(n / 128);
      out.push(n ? low | 128 : low);
      if (!n) return out;
    }
  }

  function readVarint(data, pos) {
    let value = 0, scale = 1;
    for (let i = 0; i < 7; i++) {
      if (pos + i >= data.length) return null;
      const byte = data[pos + i];
      value += (byte % 128) * scale;
      scale *= 128;
      if (byte < 128) {
        if (i > 0 && byte === 0) return null;
        return [value, pos + i + 1];
      }
    }
    return null;
  }

  function toB32(data) {
    let bits = data.map((b) => b.toString(2).padStart(8, "0")).join("");
    bits += "0".repeat((5 - (bits.length % 5)) % 5);
    let out = "";
    for (let i = 0; i < bits.length; i += 5) out += B32[parseInt(bits.slice(i, i + 5), 2)];
    return out;
  }

  function fromB32(text) {
    let bits = "";
    for (const c of text) bits += B32.indexOf(c).toString(2).padStart(5, "0");
    const whole = Math.floor(bits.length / 8) * 8;
    if (bits.slice(whole).includes("1")) return null;
    const out = [];
    for (let i = 0; i < whole; i += 8) out.push(parseInt(bits.slice(i, i + 8), 2));
    return out;
  }

  function checksum(prefix, body) {
    const h = fnv1a64("run-code-v" + FORMAT_VERSION + "|" + prefix + "|" + body);
    const v = Number((h ^ (h >> 32n)) & 0x7fffn);
    return B32[v >> 10] + B32[(v >> 5) & 31] + B32[v & 31];
  }

  function seedToInt(code) {
    let n = 0;
    for (const ch of code) n = n * SEED_BASE + SEED_ALPHABET.indexOf(ch);
    return n;
  }

  function intToSeed(n) {
    const chars = [];
    for (let i = 0; i < SEED_CODE_LEN; i++) {
      chars.push(SEED_ALPHABET[n % SEED_BASE]);
      n = Math.floor(n / SEED_BASE);
    }
    return chars.reverse().join("");
  }

  function group(body) {
    const parts = [];
    for (let i = 0; i < body.length; i += GROUP) parts.push(body.slice(i, i + GROUP));
    return parts.join("-");
  }

  // ---- encode ------------------------------------------------------------------------------------
  function encode(fields) {
    const f = fields && typeof fields === "object" && !Array.isArray(fields) ? fields : {};
    const game = f.game;
    if (typeof game !== "string") throw fail("game", "A run code needs the game's id.");
    let prefix;
    try { prefix = prefixFor(game); } catch (e) { throw fail("game", "That game id is too short to make a run code."); }

    let flags = FORMAT_VERSION << 5;
    let seedInt = null;
    if (f.seed !== undefined && f.seed !== null && f.seed !== "") {
      const norm = typeof f.seed === "string" ? normalizeSeed(f.seed, game) : "";
      if (!norm) throw fail("seed", "That is not a valid seed.");
      if (norm.split("-")[0] !== prefix) throw fail("wrong-game", "That seed is for " + norm.split("-")[0] + ", not " + prefix + ".");
      seedInt = seedToInt(norm.split("-")[1]);
      flags |= 0x10;
    }

    let mode = f.mode === undefined || f.mode === null ? "" : f.mode;
    if (typeof mode !== "string") throw fail("mode", "The mode must be text.");
    mode = mode.toLowerCase();
    if (mode && !MODE_OK.test(mode)) throw fail("mode", "The mode may use a-z and 0-9, up to " + MAX_MODE + " characters.");

    const score = f.score === undefined ? null : f.score;
    const stats = f.stats === undefined || f.stats === null ? [] : f.stats;
    if (!Array.isArray(stats) || stats.length > MAX_STATS) throw fail("stats", "At most " + MAX_STATS + " stats fit in a run code.");
    if (score === null && stats.length) throw fail("score", "Stats need a score to go with them.");
    if (score !== null) {
      if (!isValue(score)) throw fail("score", "The score must be a whole number from 0 to " + MAX_VALUE + ".");
      for (const s of stats) {
        if (!isValue(s)) throw fail("stats", "Each stat must be a whole number from 0 to " + MAX_VALUE + ".");
      }
      flags |= 0x08 | (stats.length << 1);
    }

    const out = [flags];
    if (seedInt !== null) out.push((seedInt >>> 24) & 255, (seedInt >>> 16) & 255, (seedInt >>> 8) & 255, seedInt & 255);
    out.push(mode.length);
    for (let i = 0; i < mode.length; i++) out.push(mode.charCodeAt(i));
    if (score !== null) {
      out.push(...varint(score));
      for (const s of stats) out.push(...varint(s));
    }
    const body = toB32(out);
    return HEADER + "-" + prefix + "-" + group(body) + "-" + checksum(prefix, body);
  }

  // ---- decode ------------------------------------------------------------------------------------
  function bad(error, other) {
    return { ok: false, error, message: MESSAGES[error].replace("{other}", other || ""), code: "", game: "", seed: "",
      mode: "", score: null, stats: [], hasResult: false, verified: false };
  }

  function split(s, game) {
    if (!s.startsWith(HEADER)) return [null, "format"];
    const parts = s.split("-");
    if (parts[0] === HEADER && parts.length >= 3) return [parts[1], parts.slice(2).join("")];
    if (game !== undefined && game !== null) {
      const p = prefixFor(game);
      const lead = HEADER + p;
      const t = s.replace(/-/g, "");
      if (t.startsWith(lead)) return [p, t.slice(lead.length)];
    }
    return [null, "format"];
  }

  function decode(text, game) {
    if (typeof text !== "string") return bad("empty");
    if (text.length > MAX_INPUT_LEN) return bad("too-long");
    const s = text.replace(DASHES, "-").replace(SPACE, "").toUpperCase();
    if (!s) return bad("empty");
    if (s.replace(/-/g, "").length > MAX_COMPACT_LEN) return bad("too-long");
    const hasGame = game !== undefined && game !== null;
    const [prefix, restRaw] = split(s, hasGame ? game : null);
    if (prefix === null) return bad(restRaw);
    if (!PREFIX_OK.test(prefix)) return bad("format");
    if (hasGame && prefix !== prefixFor(game)) return bad("wrong-game", prefix);
    let rest = "";
    for (const c of restRaw) rest += ALIASES[c] || c;
    if (rest.length <= CHECK_LEN) return bad("format");
    for (const c of rest) if (!B32.includes(c)) return bad("format");
    const body = rest.slice(0, -CHECK_LEN);
    const check = rest.slice(-CHECK_LEN);
    if (check !== checksum(prefix, body)) return bad("checksum");

    const data = fromB32(body);
    if (!data || !data.length) return bad("format");
    const flags = data[0];
    if (flags >> 5 !== FORMAT_VERSION) return bad("version");
    const hasSeed = !!(flags & 0x10), hasResult = !!(flags & 0x08), nStats = (flags >> 1) & 3, reserved = flags & 1;
    if (reserved || nStats > MAX_STATS || (nStats && !hasResult)) return bad("format");
    let pos = 1;
    let seed = "";
    if (hasSeed) {
      if (pos + 4 > data.length) return bad("format");
      const n = data[pos] * 16777216 + data[pos + 1] * 65536 + data[pos + 2] * 256 + data[pos + 3];
      pos += 4;
      if (n >= SEED_LIMIT) return bad("format");
      seed = prefix + "-" + intToSeed(n);
    }
    if (pos >= data.length) return bad("format");
    const mlen = data[pos];
    pos += 1;
    if (mlen > MAX_MODE || pos + mlen > data.length) return bad("format");
    let mode = "";
    for (let i = 0; i < mlen; i++) mode += String.fromCharCode(data[pos + i]);
    pos += mlen;
    if (mode && !MODE_OK.test(mode)) return bad("format");
    let score = null;
    const stats = [];
    if (hasResult) {
      let r = readVarint(data, pos);
      if (r === null || r[0] > MAX_VALUE) return bad("format");
      score = r[0]; pos = r[1];
      for (let i = 0; i < nStats; i++) {
        r = readVarint(data, pos);
        if (r === null || r[0] > MAX_VALUE) return bad("format");
        stats.push(r[0]); pos = r[1];
      }
    }
    if (pos !== data.length) return bad("format");
    return { ok: true, error: "", message: "", code: HEADER + "-" + prefix + "-" + group(body) + "-" + check,
      game: prefix, seed, mode, score, stats, hasResult, verified: false };
  }

  function validate(text, game) {
    const d = decode(text, game);
    return { ok: d.ok, code: d.code, error: d.error, message: d.message };
  }
  const isValid = (text, game) => decode(text, game).ok;
  const normalize = (text, game) => decode(text, game).code;

  // ---- describing a decoded run ------------------------------------------------------------------
  const number = (n) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");

  function describe(decoded, options) {
    const o = options || {};
    const d = decoded && decoded.ok ? decoded : null;
    if (!d) return "";
    const parts = [];
    if (d.hasResult) {
      const score = number(d.score);
      parts.push(o.unit ? score + " " + o.unit : score);
      const labels = o.stats || [];
      d.stats.forEach((value, i) => {
        let label = i < labels.length ? labels[i] : null;
        if (label && typeof label === "object") {
          label = value === 1 ? (label.one || "") : (label.many !== undefined ? label.many : (label.one || ""));
        }
        parts.push(label ? number(value) + " " + label : number(value));
      });
    }
    if (d.mode) {
      const modes = o.modes || {};
      parts.push((Object.prototype.hasOwnProperty.call(modes, d.mode) ? modes[d.mode] : d.mode) + " mode");
    }
    const head = o.prefix !== undefined ? o.prefix : "Their run";
    if (!parts.length) return head + (d.seed ? ": seed " + d.seed : "");
    return head + ": " + parts.join(", ");
  }

  // ---- shared UI plumbing ------------------------------------------------------------------------
  const STYLE_ID = "noyvj-runcode-style";
  const CSS = `
:root{--nrc-bg:rgba(20,24,42,.78);--nrc-fg:#e8e9f0;--nrc-muted:#aab0c8;--nrc-border:rgba(140,160,255,.5);--nrc-accent:#9fe0ab;--nrc-on-accent:#0e1a12;--nrc-err:#ffb4a8;--nrc-focus:#ffd866;--nrc-field:rgba(10,12,24,.6);--nrc-ghost:rgba(110,150,255,.16)}
html[data-theme="light"]{--nrc-bg:rgba(255,255,255,.94);--nrc-fg:#1b2033;--nrc-muted:#4a5275;--nrc-border:rgba(60,85,160,.55);--nrc-accent:#1f6b3a;--nrc-on-accent:#fff;--nrc-err:#9b1c0c;--nrc-focus:#8a5a00;--nrc-field:#fff;--nrc-ghost:rgba(60,100,220,.1)}
@media (prefers-color-scheme:light){:root:not([data-theme]){--nrc-bg:rgba(255,255,255,.94);--nrc-fg:#1b2033;--nrc-muted:#4a5275;--nrc-border:rgba(60,85,160,.55);--nrc-accent:#1f6b3a;--nrc-on-accent:#fff;--nrc-err:#9b1c0c;--nrc-focus:#8a5a00;--nrc-field:#fff;--nrc-ghost:rgba(60,100,220,.1)}}
.noyvj-rc[hidden],.noyvj-rc [hidden]{display:none!important}
.noyvj-rc{box-sizing:border-box;max-width:100%;margin:.5rem 0;padding:.6rem .75rem;border:1px solid var(--nrc-border);border-radius:10px;background:var(--nrc-bg);color:var(--nrc-fg);font:.9rem/1.4 system-ui,sans-serif;text-align:left}
.noyvj-rc *{box-sizing:border-box}
.noyvj-rc-row{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem}
.noyvj-rc-label{font-weight:600}
label.noyvj-rc-label{display:block;margin-bottom:.4rem}
.noyvj-rc-code{flex:1 1 12rem;min-width:0;padding:.3rem .55rem;border:1px dashed var(--nrc-border);border-radius:6px;font:700 .95rem ui-monospace,Menlo,Consolas,monospace;letter-spacing:.04em;overflow-wrap:anywhere;user-select:all}
.noyvj-rc-btn{min-height:44px;min-width:44px;padding:.4rem .9rem;border:2px solid var(--nrc-border);border-radius:8px;background:transparent;color:var(--nrc-fg);font:600 .9rem system-ui,sans-serif;cursor:pointer}
.noyvj-rc-btn--primary{background:var(--nrc-accent);border-color:var(--nrc-accent);color:var(--nrc-on-accent)}
.noyvj-rc-btn[disabled]{opacity:.6;cursor:not-allowed;border-style:dashed}
.noyvj-rc-btn:focus-visible,.noyvj-rc-input:focus-visible{outline:3px solid var(--nrc-focus);outline-offset:2px}
.noyvj-rc-input{flex:1 1 11rem;min-width:0;min-height:44px;padding:.4rem .6rem;border:2px solid var(--nrc-border);border-radius:8px;background:var(--nrc-field);color:var(--nrc-fg);font:700 .95rem ui-monospace,Menlo,Consolas,monospace;letter-spacing:.04em;text-transform:uppercase}
.noyvj-rc-input[aria-invalid="true"]{border-style:dashed;border-width:3px}
.noyvj-rc-hint,.noyvj-rc-status,.noyvj-rc-preview{margin:.35rem 0 0;color:var(--nrc-muted);font-size:.82rem}
.noyvj-rc-preview{color:var(--nrc-fg)}
.noyvj-rc-error{margin:.35rem 0 0;color:var(--nrc-err);font-weight:600;font-size:.85rem}
.noyvj-rc-fallback{width:100%;margin-top:.4rem}
.noyvj-rc-ghost{margin:.5rem 0 0;padding:.55rem .7rem;border:2px solid var(--nrc-border);border-radius:8px;background:var(--nrc-ghost)}
.noyvj-rc-ghost-title{margin:0;font-weight:700}
.noyvj-rc-ghost-line{margin:.25rem 0 0;font-size:1rem}
.noyvj-rc-ghost-note{margin:.35rem 0 0;color:var(--nrc-muted);font-size:.8rem}
.noyvj-rc-ghost .noyvj-rc-row{margin-top:.5rem}
@media (prefers-reduced-motion:no-preference){html:not([data-reduced-motion="true"]) .noyvj-rc-btn{transition:background-color .15s ease}}
@media (max-width:420px){.noyvj-rc-btn{flex:1 1 100%}}
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
  const target = (x) => (typeof x === "string" ? document.querySelector(x) : x);

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

  const NOT_VERIFIED = "Run codes are not checked against a server: anyone can write one with any result, so treat it as a friendly challenge, not proof.";

  // ---- "Copy run code" (run-end screen) -----------------------------------------------------------
  /**
   * mountCopy(container, { game, run | getRun, label, buttonLabel, describe, onCopy })
   * `run` is the fields object for encode() ({seed, mode, score, stats}; `game` is filled in), or
   * `getRun()` returns it (called on mount, on update() and on every click, so it can read the
   * finished run). `describe` is the options for describe() and drives the "A friend will see" line.
   * Returns { update(run), destroy(), element }.
   */
  function mountCopy(container, opts) {
    opts = opts || {};
    const host = target(container);
    if (!host) return null;
    if (!opts.game) throw new Error("NoyvjRunCode.mountCopy needs a game slug");
    injectStyle();
    const id = "noyvj-rc-copy-" + (++uid);
    const root = el("div", "noyvj-rc noyvj-rc-copy", null, { role: "group", "aria-labelledby": id + "-l" });
    const row = el("div", "noyvj-rc-row");
    const label = el("span", "noyvj-rc-label", opts.label || "Run code", { id: id + "-l" });
    const code = el("code", "noyvj-rc-code", "");
    const btn = el("button", "noyvj-rc-btn", "", { type: "button" });
    row.append(label, code, btn);
    const preview = el("p", "noyvj-rc-preview", "");
    const hint = el("p", "noyvj-rc-hint", "Send this to a friend: they can paste it to see your run. " + NOT_VERIFIED);
    const status = el("p", "noyvj-rc-status", "", { role: "status", "aria-live": "polite" });
    root.append(row, preview, hint, status);
    host.appendChild(root);
    let current = "";
    let box = null;
    const btnLabel = opts.buttonLabel || "Copy run code";

    function build(run) {
      const fields = Object.assign({}, run || {}, { game: opts.game });
      try { return { code: encode(fields), error: "" }; } catch (e) { return { code: "", error: e.message }; }
    }
    function source() { return typeof opts.getRun === "function" ? opts.getRun() : opts.run; }
    function paint(r) {
      current = r.code;
      code.textContent = r.code || "none yet";
      btn.textContent = "⧉ " + btnLabel;
      btn.disabled = !r.code;
      btn.setAttribute("aria-label", btnLabel);
      preview.hidden = !r.code;
      preview.textContent = r.code ? "A friend will see: " + describe(decode(r.code, opts.game), opts.describe) : "";
      hint.hidden = !r.code;
      if (r.error) status.textContent = "! Could not make a run code: " + r.error;
    }
    function update(run) {
      status.textContent = "";
      if (box) { box.remove(); box = null; }
      paint(build(run === undefined ? source() : run));
    }
    btn.addEventListener("click", () => {
      const r = build(source());
      paint(r);
      if (!r.code) return;
      copyText(r.code).then((ok) => {
        if (ok) {
          status.textContent = "✓ Copied " + r.code;
          if (opts.onCopy) opts.onCopy(r.code);
        } else {
          if (!box) {
            box = el("input", "noyvj-rc-input noyvj-rc-fallback", "", { type: "text", readonly: "", "aria-label": "Run code to copy" });
            root.appendChild(box);
          }
          box.value = r.code;
          box.focus();
          box.select();
          status.textContent = "Could not copy automatically: press Ctrl+C (or ⌘C) to copy the selected run code.";
        }
      });
    });
    update();
    return { update, destroy() { root.remove(); }, element: root };
  }

  // ---- "Paste a run code" (friend's ghost) --------------------------------------------------------
  /**
   * mountPaste(container, { game, onView(decoded), onPlaySeed(seed, decoded), describe, buttonLabel })
   * A labelled field plus a button. A bad code is explained in text (a "!" and a dashed border,
   * never colour alone) and focus returns to the field. A good one shows the ghost summary only:
   * the line from describe(), the mode and seed, and the reminder that it is not verified. The
   * "Play this seed" button exists only when the code has a seed AND the game passed onPlaySeed.
   * Returns { setValue(text), focus(), clear(), destroy(), element }.
   */
  function mountPaste(container, opts) {
    opts = opts || {};
    const host = target(container);
    if (!host) return null;
    if (!opts.game) throw new Error("NoyvjRunCode.mountPaste needs a game slug");
    injectStyle();
    const id = "noyvj-rc-paste-" + (++uid);
    const form = el("form", "noyvj-rc noyvj-rc-paste", null, { novalidate: "", "aria-labelledby": id + "-l" });
    const label = el("label", "noyvj-rc-label", opts.label || "Paste a run code", { id: id + "-l", for: id + "-i" });
    const row = el("div", "noyvj-rc-row");
    const input = el("input", "noyvj-rc-input", "", {
      id: id + "-i", type: "text", autocomplete: "off", autocapitalize: "characters", spellcheck: "false",
      maxlength: String(MAX_INPUT_LEN), placeholder: "RUN-" + prefixFor(opts.game) + "-...", "aria-describedby": id + "-h " + id + "-e",
    });
    const go = el("button", "noyvj-rc-btn noyvj-rc-btn--primary", "👁 " + (opts.buttonLabel || "View run"), { type: "submit" });
    row.append(input, go);
    const hint = el("p", "noyvj-rc-hint", "A friend's run code shows their run here. Capitals, spaces and dashes do not matter.", { id: id + "-h" });
    const err = el("p", "noyvj-rc-error", "", { id: id + "-e", role: "alert" });
    err.hidden = true;
    const result = el("div", "noyvj-rc-result", "", { role: "status", "aria-live": "polite" });
    form.append(label, row, hint, err, result);
    host.appendChild(form);

    function setError(message) {
      err.hidden = !message;
      err.textContent = message ? "! " + message : "";
      if (message) input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid");
    }
    function clearResult() { result.textContent = ""; }
    function show(d) {
      clearResult();
      const card = el("div", "noyvj-rc-ghost");
      card.append(el("p", "noyvj-rc-ghost-title", "◌ Ghost run"));
      card.append(el("p", "noyvj-rc-ghost-line", describe(d, opts.describe)));
      if (d.seed) card.append(el("p", "noyvj-rc-ghost-note", "Seed " + d.seed));
      card.append(el("p", "noyvj-rc-ghost-note", "Not verified. " + NOT_VERIFIED));
      const actions = el("div", "noyvj-rc-row");
      if (d.seed && typeof opts.onPlaySeed === "function") {
        const play = el("button", "noyvj-rc-btn", "▶ Play this seed", { type: "button" });
        play.addEventListener("click", () => opts.onPlaySeed(d.seed, d));
        actions.append(play);
      }
      const close = el("button", "noyvj-rc-btn", "Clear", { type: "button" });
      close.addEventListener("click", () => { clearResult(); input.value = ""; setError(""); input.focus(); });
      actions.append(close);
      card.append(actions);
      result.append(card);
    }
    input.addEventListener("input", () => setError(""));
    form.addEventListener("submit", (ev) => {
      ev.preventDefault();
      const d = decode(input.value, opts.game);
      if (!d.ok) { clearResult(); setError(d.message); input.focus(); return; }
      setError("");
      input.value = d.code;
      show(d);
      if (opts.onView) opts.onView(d);
    });
    return {
      setValue(t) { input.value = t; setError(""); },
      focus() { input.focus(); },
      clear() { clearResult(); input.value = ""; setError(""); },
      destroy() { form.remove(); },
      element: form,
    };
  }

  window.NoyvjRunCode = {
    FORMAT_VERSION, MAX_VALUE, MAX_STATS, MAX_MODE, B32,
    encode, decode, validate, isValid, normalize, describe,
    mountCopy, mountPaste, copyText,
  };
})();
