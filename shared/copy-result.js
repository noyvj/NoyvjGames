/*
 * Shared "copy my result as text" helper (planning/TODO.md Z-20). One place formats a Wordle-style
 * one-line result and copies it, so every game's end screen does it the same way:
 *
 *   Tide, 4,210 pts, 3 storms survived (seed TIDE-K7F2Q)
 *
 * Signal keeps its own share text (games/signal/app.js lastShareText) and does not use this.
 * API, adoption snippet and tests: planning/SHARED-COMPONENTS.md ("Copy result"),
 * shared/tests/test_copy_result_browser.py.
 *
 *   <script src="../../shared/copy-result.js"></script>
 *
 *   NoyvjCopyResult.format({ game: "Tide", score: 4210, unit: "pts",
 *                            stats: ["3 storms survived"], seed: "TIDE-K7F2Q" })
 *   NoyvjCopyResult.mountButton("#run-end-actions", { game: "Tide", getResult: () => ({ ... }) })
 *
 * format(fields) -> string. Fields (all optional but `game`):
 *   game      display name ("Tide")
 *   score     number (formatted with thousands separators: 4,210) or string
 *   unit      text after the score ("pts"); omit for none
 *   stats     list of extra pieces: strings, or { n: 3, one: "storm survived", many: "storms survived" }
 *   seed      the run's seed; the "(seed ...)" tail appears ONLY when this is a non-empty string.
 *             `withSeed: true` takes NoyvjSeed.current() instead, when shared/seed.js is loaded
 *   link      true -> adds a second line with this game's page address; or a string to use as the link
 * Everything is flattened to one line (line breaks and runs of spaces become single spaces), capped at
 * 240 characters before the optional link line, and never contains markup: it is plain text.
 *
 * mountButton(container, opts) -> { update(fields), copy(), destroy(), element }
 *   opts: the same fields as format(), or `getResult: () => fields` (called on each click, so the
 *   end screen can compute the result when the player presses the button), plus `label`
 *   ("Copy result"), `onCopy(text)`. The button is at least 44 px high, announces "Copied: <text>"
 *   in a polite live region, and when the browser refuses the clipboard it shows the text in a
 *   selected read-only box with "press Ctrl+C". Light and dark tokens, no colour-only state, and
 *   no transitions when reduced motion is on.
 * copy(text) -> Promise<boolean> is exposed too.
 */
(function () {
  "use strict";
  if (window.NoyvjCopyResult) return;

  const SCRIPT = document.currentScript;
  const MAX_LINE = 240;

  function oneLine(text) {
    return String(text).replace(/\s+/g, " ").trim();
  }

  function formatNumber(n) {
    if (!isFinite(n)) return "";
    return Math.abs(n) >= 1000 || n % 1 === 0
      ? n.toLocaleString("en-US", { maximumFractionDigits: 2 })
      : String(Number(n.toFixed(2)));
  }

  /** "3 storms survived" / "1 storm survived". */
  function plural(n, one, many) {
    return `${formatNumber(n)} ${n === 1 ? one : many}`;
  }

  function piece(p) {
    if (p === null || p === undefined || p === false) return "";
    if (typeof p === "number") return formatNumber(p);
    if (typeof p === "object" && typeof p.n === "number") return plural(p.n, p.one || "", p.many || p.one || "");
    return oneLine(p);
  }

  function gameLink() {
    try {
      const m = SCRIPT && SCRIPT.dataset.gameId;
      if (m && SCRIPT.src) return new URL(`../games/${m}/`, SCRIPT.src).href;
    } catch (e) { /* fall through */ }
    return location.origin + location.pathname.replace(/(index|pc)\.html$/, "");
  }

  function format(fields) {
    const f = fields || {};
    const parts = [];
    const game = piece(f.game);
    if (game) parts.push(game);
    if (f.score !== undefined && f.score !== null && f.score !== "") {
      const score = typeof f.score === "number" ? formatNumber(f.score) : oneLine(f.score);
      if (score) parts.push(f.unit ? `${score} ${oneLine(f.unit)}` : score);
    }
    (Array.isArray(f.stats) ? f.stats : []).forEach((s) => { const t = piece(s); if (t) parts.push(t); });
    let line = parts.join(", ");
    let seed = typeof f.seed === "string" ? oneLine(f.seed) : "";
    if (!seed && f.withSeed && window.NoyvjSeed && typeof window.NoyvjSeed.current === "function") {
      seed = oneLine(window.NoyvjSeed.current() || "");
    }
    if (seed) line += `${line ? " " : ""}(seed ${seed})`;
    if (line.length > MAX_LINE) line = line.slice(0, MAX_LINE - 1).trimEnd() + "…";
    if (f.link) line += "\n" + (typeof f.link === "string" ? f.link : gameLink());
    return line;
  }

  /** Clipboard write with a legacy fallback; resolves true if the text reached the clipboard. */
  function copy(text) {
    const legacy = () => {
      try {
        const ta = document.createElement("textarea");
        ta.value = text;
        ta.setAttribute("readonly", "");
        ta.setAttribute("aria-hidden", "true");
        ta.tabIndex = -1;
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

  // ---- button ---------------------------------------------------------------------------------
  const STYLE_ID = "noyvj-copy-result-style";
  const CSS = `
:root{--cr-bg:rgba(20,24,42,.78);--cr-fg:#e8e9f0;--cr-muted:#aab0c8;--cr-border:rgba(140,160,255,.5);--cr-accent:#9fe0ab;--cr-on-accent:#0e1a12;--cr-focus:#ffd866;--cr-field:rgba(10,12,24,.6)}
html[data-theme="light"]{--cr-bg:rgba(255,255,255,.94);--cr-fg:#1b2033;--cr-muted:#4a5275;--cr-border:rgba(60,85,160,.55);--cr-accent:#1f6b3a;--cr-on-accent:#fff;--cr-focus:#8a5a00;--cr-field:#fff}
@media (prefers-color-scheme:light){:root:not([data-theme]){--cr-bg:rgba(255,255,255,.94);--cr-fg:#1b2033;--cr-muted:#4a5275;--cr-border:rgba(60,85,160,.55);--cr-accent:#1f6b3a;--cr-on-accent:#fff;--cr-focus:#8a5a00;--cr-field:#fff}}
.noyvj-cr{box-sizing:border-box;max-width:100%;margin:.5rem 0;padding:.6rem .75rem;border:1px solid var(--cr-border);border-radius:10px;background:var(--cr-bg);color:var(--cr-fg);font:.9rem/1.4 system-ui,sans-serif}
.noyvj-cr *{box-sizing:border-box}
.noyvj-cr [hidden]{display:none!important}
.noyvj-cr-btn{min-height:44px;padding:.4rem .9rem;border:2px solid var(--cr-accent);border-radius:8px;background:var(--cr-accent);color:var(--cr-on-accent);font:600 .9rem system-ui,sans-serif;cursor:pointer}
.noyvj-cr-btn:focus-visible,.noyvj-cr-box:focus-visible{outline:3px solid var(--cr-focus);outline-offset:2px}
.noyvj-cr-status{margin:.35rem 0 0;color:var(--cr-muted);font-size:.85rem;overflow-wrap:anywhere}
.noyvj-cr-box{display:block;width:100%;margin-top:.4rem;min-height:44px;padding:.4rem .6rem;border:2px dashed var(--cr-border);border-radius:8px;background:var(--cr-field);color:var(--cr-fg);font:.9rem/1.4 ui-monospace,Menlo,Consolas,monospace;resize:vertical}
@media (prefers-reduced-motion:no-preference){html:not([data-reduced-motion="true"]) .noyvj-cr-btn{transition:filter .15s ease}}
@media (max-width:420px){.noyvj-cr-btn{width:100%}}
@media print{.noyvj-cr{display:none}}
`;
  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const st = document.createElement("style");
    st.id = STYLE_ID;
    st.textContent = CSS;
    (document.head || document.documentElement).appendChild(st);
  }

  function mountButton(container, opts) {
    opts = opts || {};
    const host = typeof container === "string" ? document.querySelector(container) : container;
    if (!host) return null;
    injectStyle();
    const root = document.createElement("div");
    root.className = "noyvj-cr";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "noyvj-cr-btn";
    btn.textContent = "⧉ " + (opts.label || "Copy result");
    const status = document.createElement("p");
    status.className = "noyvj-cr-status";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    root.append(btn, status);
    host.appendChild(root);
    let fields = opts;
    let box = null;

    function currentText() {
      const f = typeof opts.getResult === "function" ? opts.getResult() : fields;
      return format(f);
    }

    function doCopy() {
      const text = currentText();
      if (!text) { status.textContent = "Nothing to copy yet."; return Promise.resolve(false); }
      return copy(text).then((ok) => {
        if (ok) {
          if (box) { box.remove(); box = null; }
          status.textContent = "✓ Copied: " + text.split("\n")[0];
          if (opts.onCopy) opts.onCopy(text);
        } else {
          if (!box) {
            box = document.createElement("textarea");
            box.className = "noyvj-cr-box";
            box.readOnly = true;
            box.rows = 2;
            box.setAttribute("aria-label", "Result text to copy");
            root.appendChild(box);
          }
          box.value = text;
          box.focus();
          box.select();
          status.textContent = "Could not copy automatically: press Ctrl+C (or ⌘C) to copy the selected text.";
        }
        return ok;
      });
    }

    btn.addEventListener("click", doCopy);
    return {
      update(next) { fields = next || {}; status.textContent = ""; if (box) { box.remove(); box = null; } },
      copy: doCopy,
      destroy() { root.remove(); },
      element: root,
    };
  }

  window.NoyvjCopyResult = { format, plural, copy, mountButton, formatNumber, MAX_LINE };
})();
