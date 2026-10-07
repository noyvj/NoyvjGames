/*
 * Shared error boundary (TODO Z-25). Catches anything the page itself did not (an uncaught
 * JavaScript error, an unhandled promise rejection, and the PythonError Pyodide raises when a
 * game's Python code throws inside an event handler) and shows ONE small, friendly panel instead
 * of leaving a silently broken page:
 *
 *   "Something went wrong. Your saved game has not been touched."  [Copy details] [Reload] [Dismiss]
 *
 * It only reads: it never writes, clears or reloads a save, and "Copy details" puts a plain-text
 * report (game, page, browser, window size, time, lite mode, and the error messages and stacks)
 * on the clipboard for the player to paste into the site's feedback form. No save code and no
 * account data is included.
 *
 * Not reported (they are noise, not bugs in the game): cross-origin "Script error." lines, the
 * harmless "ResizeObserver loop" notice, ad-script failures (an ad blocker causes these), network
 * failures from fetch (offline, or the backend asleep: every caller already handles those), and
 * aborted requests.
 *
 * The panel is built with textContent only, owns its styles (no per-game CSS), never steals
 * focus, and follows the site theme. API: window.NoyvjErrors.report(error, source), .list(),
 * .clear(). A game can call report() itself for an error it caught but wants the player to see.
 */
(function () {
  "use strict";
  if (window.NoyvjErrors) return;

  const SCRIPT = document.currentScript;
  const GAME_ID = (SCRIPT && SCRIPT.dataset.gameId) || guessGameId();
  const MAX_KEPT = 10;
  const errors = [];
  let total = 0;
  let panel = null;

  function guessGameId() {
    const m = location.pathname.match(/\/games\/([^/]+)\//);
    return m ? m[1] : "hub";
  }

  const NOISE_MESSAGE = [
    /^script error\.?$/i,
    /resizeobserver loop/i,
    /adsbygoogle/i,
    /^(failed to fetch|load failed|networkerror)/i,
    /networkerror when attempting to fetch/i,
    /the user aborted a request|the operation was aborted|aborterror/i,
  ];
  const NOISE_FILE = /googlesyndication|doubleclick|adservice|pagead|googletagmanager/i;

  function describe(value) {
    if (value && typeof value === "object") {
      const name = value.name && value.name !== "Error" ? `${value.name}: ` : "";
      return { message: `${name}${value.message || String(value)}`.slice(0, 600), stack: String(value.stack || "").slice(0, 2500) };
    }
    return { message: String(value).slice(0, 600), stack: "" };
  }

  function isNoise(info, filename) {
    if (filename && NOISE_FILE.test(filename)) return true;
    if (info.stack && NOISE_FILE.test(info.stack.split("\n").slice(0, 3).join("\n"))) return true;
    return NOISE_MESSAGE.some((re) => re.test(info.message));
  }

  function report(error, source) {
    const info = describe(error);
    if (isNoise(info, "")) return false;
    add(info, source || "manual");
    return true;
  }

  function add(info, source) {
    total += 1;
    const last = errors[errors.length - 1];
    if (last && last.message === info.message && last.source === source) {
      last.count += 1;
    } else {
      errors.push({ message: info.message, stack: info.stack, source, count: 1, at: new Date().toISOString() });
      if (errors.length > MAX_KEPT) errors.shift();
    }
    if (typeof console !== "undefined" && console.warn) console.warn(`[noyvj-errors] ${source}: ${info.message}`);
    render();
  }

  window.addEventListener("error", (event) => {
    // A failing <img>/<script> tag fires "error" on the element, not the window: ignore those.
    if (!(event instanceof ErrorEvent)) return;
    const info = describe(event.error || event.message);
    if (!event.error && event.message) info.message = String(event.message).slice(0, 600);
    if (event.filename && event.lineno) info.stack = info.stack || `at ${event.filename}:${event.lineno}:${event.colno || 0}`;
    if (isNoise(info, event.filename || "")) return;
    add(info, "script");
  });
  window.addEventListener("unhandledrejection", (event) => {
    const info = describe(event.reason);
    if (isNoise(info, "")) return;
    add(info, "promise");
  });

  // ---------- the panel ----------

  function detailsText() {
    const lines = [
      `NoyvjGames error report`,
      `game: ${GAME_ID}`,
      `page: ${location.origin}${location.pathname}`,
      `time: ${new Date().toISOString()}`,
      `browser: ${navigator.userAgent}`,
      `window: ${window.innerWidth}x${window.innerHeight} at ${window.devicePixelRatio || 1}x`,
      `lite mode: ${window.NoyvjLite ? (window.NoyvjLite.on() ? "on" : "off") : "n/a"}`,
      `errors: ${total}${total > errors.length ? ` (last ${errors.length} shown)` : ""}`,
      "",
    ];
    errors.forEach((e, i) => {
      lines.push(`#${i + 1} [${e.source}]${e.count > 1 ? ` x${e.count}` : ""} ${e.at}`, e.message);
      if (e.stack) lines.push(e.stack);
      lines.push("");
    });
    return lines.join("\n");
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(() => true, () => fallbackCopy(text));
    }
    return Promise.resolve(fallbackCopy(text));
  }
  function fallbackCopy(text) {
    try {
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.cssText = "position:fixed;left:-9999px;top:0";
      document.body.appendChild(area);
      area.select();
      const ok = document.execCommand("copy");
      area.remove();
      return ok;
    } catch (e) { return false; }
  }

  function injectStyle() {
    if (document.getElementById("noyvj-error-style")) return;
    const style = document.createElement("style");
    style.id = "noyvj-error-style";
    style.textContent = `
      #noyvj-error-panel { position: fixed; right: 12px; bottom: 12px; z-index: 2147483001; box-sizing: border-box;
        width: min(420px, calc(100vw - 24px)); padding: 12px 14px; border: 2px solid #e0a64c; border-radius: 10px;
        background: #1a1722; color: #f1ecff; font: 14px/1.45 system-ui, sans-serif; box-shadow: 0 6px 24px rgba(0,0,0,.45); }
      #noyvj-error-panel h2 { margin: 0 0 4px; font-size: 1rem; }
      #noyvj-error-panel p { margin: 0 0 8px; }
      #noyvj-error-panel .noyvj-error-last { font: 12px/1.35 ui-monospace, Menlo, Consolas, monospace; opacity: .85; word-break: break-word; max-height: 3.9em; overflow: hidden; }
      #noyvj-error-panel .noyvj-error-actions { display: flex; flex-wrap: wrap; gap: 8px; }
      #noyvj-error-panel button { min-height: 40px; padding: 4px 12px; border: 1px solid #e0a64c; border-radius: 6px;
        background: #2a2433; color: inherit; font: inherit; cursor: pointer; touch-action: manipulation; }
      #noyvj-error-panel button:focus-visible { outline: 3px solid #fff; outline-offset: 2px; }
      html[data-theme="light"] #noyvj-error-panel { background: #fff8ec; color: #2b2112; border-color: #b87a12; box-shadow: 0 6px 24px rgba(0,0,0,.2); }
      html[data-theme="light"] #noyvj-error-panel button { background: #ffeccb; border-color: #b87a12; }
      @media print { #noyvj-error-panel { display: none; } }
    `;
    document.head.appendChild(style);
  }

  function build() {
    injectStyle();
    panel = document.createElement("section");
    panel.id = "noyvj-error-panel";
    panel.setAttribute("role", "alert");
    panel.setAttribute("aria-label", "Something went wrong");
    const h = document.createElement("h2");
    h.textContent = "Something went wrong";
    const p = document.createElement("p");
    p.textContent = "Your saved game has not been touched. You can keep playing, or reload the page. If it keeps happening, copy the details and paste them into the feedback form.";
    const last = document.createElement("p");
    last.className = "noyvj-error-last";
    last.id = "noyvj-error-last";
    const actions = document.createElement("div");
    actions.className = "noyvj-error-actions";
    const copy = document.createElement("button");
    copy.type = "button";
    copy.id = "noyvj-error-copy";
    copy.textContent = "Copy details";
    copy.addEventListener("click", () => {
      copyText(detailsText()).then((ok) => { copy.textContent = ok ? "Copied" : "Could not copy"; setTimeout(() => { copy.textContent = "Copy details"; }, 2500); });
    });
    const reload = document.createElement("button");
    reload.type = "button";
    reload.id = "noyvj-error-reload";
    reload.textContent = "Reload page";
    reload.addEventListener("click", () => location.reload());
    const dismiss = document.createElement("button");
    dismiss.type = "button";
    dismiss.id = "noyvj-error-dismiss";
    dismiss.textContent = "Dismiss";
    dismiss.addEventListener("click", () => { if (panel) { panel.remove(); panel = null; } });
    actions.append(copy, reload, dismiss);
    panel.append(h, p, last, actions);
    document.body.appendChild(panel);
  }

  function render() {
    if (!document.body) { document.addEventListener("DOMContentLoaded", render, { once: true }); return; }
    // A dismissed panel comes back only when another error arrives.
    if (!panel) build();
    else if (!panel.isConnected) document.body.appendChild(panel);
    const last = errors[errors.length - 1];
    const el = panel.querySelector("#noyvj-error-last");
    if (el && last) el.textContent = last.message + (total > 1 ? ` (${total} errors)` : "");
  }

  window.NoyvjErrors = {
    report,
    list: () => errors.map((e) => Object.assign({}, e)),
    count: () => total,
    clear() { errors.length = 0; total = 0; if (panel) { panel.remove(); panel = null; } },
    details: detailsText,
  };
})();
