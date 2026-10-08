/*
 * Shared "Report a problem" button and dialog (TODO Z-17).
 *
 * Adopting it in a game is two lines in the game's index.html (and, through the Desktop page
 * generator, pc.html), after the shared includes:
 *
 *   <script src="../../shared/report-problem.js" data-game-id="canopy" data-schema-version="3"></script>
 *
 * and, only if the game wants its own menu entry instead of the small floating button:
 *   data-button="none"  on that tag, then  NoyvjReport.open()  from any button of the game's own.
 * (data-mount="#some-container" puts the button inside an element instead of floating it.)
 *
 * What it does, and the promises it keeps:
 *   * A "Report a problem" button opens a dialog with one text box ("What happened?") and a
 *     PLAIN-TEXT PREVIEW of exactly what will be sent. The preview and the request body are built
 *     from the same object, so they cannot disagree.
 *   * Always sent: the game id, the page's path (no query string, no hash), your note, and the game's
 *     save-schema version when the game gave one. Everything else is an attachment that is OFF until
 *     the player ticks it: the save code, the browser and window size, the last 20 console lines, and
 *     (signed in only) linking the report to the account so it can be deleted with it.
 *   * Nothing is sent until the Send button is pressed. No analytics, no tracking, no background post.
 *   * The console capture is a ring buffer of the last 20 lines (console.log/info/warn/error/debug,
 *     uncaught errors and unhandled rejections), started when this script loads, kept in memory only,
 *     and scrubbed as it is captured: bearer tokens, token=/key=/password= values, save codes and
 *     email addresses are replaced with [removed] (the server scrubs again).
 *   * Text goes in with textContent only. Keyboard: Tab order is the page order, Escape closes the
 *     dialog (native <dialog>, focus is trapped and returns to the opener), Enter in the note box adds
 *     a line as usual and Ctrl/Cmd+Enter sends. Tap targets are at least 44px, the colours follow the
 *     site theme (html[data-theme]) and the OS preference, nothing animates, and it prints as nothing.
 *
 * API: window.NoyvjReport = { open(), close(), configure({gameId, schemaVersion, apiBase, getSaveCode}),
 *   consoleLines(), payload(options), previewText(payload), scrub(text), version }.
 */
(function () {
  "use strict";
  if (window.NoyvjReport) return;

  const SCRIPT = document.currentScript;
  const DATA = (SCRIPT && SCRIPT.dataset) || {};
  const CONSOLE_MAX_LINES = 20;
  const CONSOLE_LINE_MAX = 300;
  const NOTE_MAX = 2000;
  const REDACTED = "[removed]";
  const TOKEN_KEY = "hub_bearer_token";          // shared/hub-auth.js HUB_AUTH_TOKEN_KEY
  const USERNAME_KEY = "hub_account_username";   // script.js AUTH_USERNAME_KEY

  const config = {
    gameId: DATA.gameId || guessGameId(),
    schemaVersion: DATA.schemaVersion || null,
    apiBase: DATA.apiBase || "https://noyvjgames.fastapicloud.dev",
    getSaveCode: null,
  };

  function guessGameId() {
    const m = location.pathname.match(/\/games\/([^/]+)\//);
    return m ? m[1] : "hub";
  }

  function lsGet(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }

  // ---- scrubbing -----------------------------------------------------------------------------
  function scrub(text) {
    return String(text)
      .replace(/Bearer\s+[A-Za-z0-9._~+\/=-]+/gi, "Bearer " + REDACTED)
      .replace(/((?:token|key|secret|password|auth|session)[\w-]*\s*[=:]\s*)[^\s&"',;]+/gi, "$1" + REDACTED)
      .replace(/\b[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}\b/g, REDACTED)
      .replace(/[^@\s]+@[^@\s]+\.[^@\s]+/g, REDACTED);
  }

  // ---- console ring buffer (started now, so errors before the player opens the dialog count) ---
  const ring = [];
  const startedAt = Date.now();

  function formatArg(arg) {
    if (typeof arg === "string") return arg;
    if (arg instanceof Error) return arg.name + ": " + arg.message;
    if (arg === undefined) return "undefined";
    try { const json = JSON.stringify(arg); return json === undefined ? String(arg) : json; } catch (e) { return String(arg); }
  }

  function push(level, text) {
    try {
      const seconds = ((Date.now() - startedAt) / 1000).toFixed(1);
      const line = scrub("+" + seconds + "s [" + level + "] " + String(text).replace(/\s+/g, " ").trim());
      ring.push(line.length > CONSOLE_LINE_MAX ? line.slice(0, CONSOLE_LINE_MAX - 1) + "…" : line);
      while (ring.length > CONSOLE_MAX_LINES) ring.shift();
    } catch (e) { /* capturing must never break the page */ }
  }

  ["log", "info", "warn", "error", "debug"].forEach((level) => {
    const original = console[level];
    if (typeof original !== "function") return;
    console[level] = function () {
      try { push(level, Array.prototype.map.call(arguments, formatArg).join(" ")); } catch (e) { /* ignore */ }
      return original.apply(this, arguments);
    };
  });
  window.addEventListener("error", (event) => {
    if (event && event.message) push("uncaught", event.message);
  });
  window.addEventListener("unhandledrejection", (event) => {
    const reason = event && event.reason;
    push("rejection", reason && reason.message ? reason.message : formatArg(reason));
  });

  // ---- what would be sent --------------------------------------------------------------------
  function saveCode() {
    let code = null;
    try { if (typeof config.getSaveCode === "function") code = config.getSaveCode(); } catch (e) { code = null; }
    if (!code) code = lsGet("savecode:" + config.gameId);
    return typeof code === "string" && /^[2-9A-HJKMNP-Z]{4}-[2-9A-HJKMNP-Z]{4}$/i.test(code.trim()) ? code.trim().toUpperCase() : null;
  }

  function signedInName() {
    return lsGet(TOKEN_KEY) ? (lsGet(USERNAME_KEY) || "your account") : null;
  }

  function browserText() { return String(navigator.userAgent || "unknown").slice(0, 300); }
  function viewportText() {
    return window.innerWidth + "x" + window.innerHeight + " @" + (window.devicePixelRatio || 1) + "x";
  }

  // options: { note, saveCode, browser, console, account } (each attachment a boolean, off by default)
  function payload(options) {
    const o = options || {};
    const code = o.saveCode ? saveCode() : null;
    return {
      game_id: config.gameId,
      page: location.pathname.slice(0, 300),
      note: String(o.note || "").trim().slice(0, NOTE_MAX),
      schema_version: config.schemaVersion ? String(config.schemaVersion).slice(0, 40) : null,
      browser: o.browser ? browserText() : null,
      viewport: o.browser ? viewportText() : null,
      console_log: o.console ? ring.slice() : null,
      attachment: code ? { save_code: code } : null,
      link_account: Boolean(o.account && signedInName()),
    };
  }

  const NOT_ATTACHED = "(not attached)";

  function previewText(p) {
    const lines = [
      "Game: " + p.game_id,
      "Page: " + (p.page || "/"),
      "Save schema version: " + (p.schema_version || "(this game does not say)"),
      "What happened: " + (p.note || "(nothing written yet)"),
      "Save code: " + (p.attachment && p.attachment.save_code ? p.attachment.save_code : NOT_ATTACHED),
      "Browser: " + (p.browser || NOT_ATTACHED),
      "Window size: " + (p.viewport || NOT_ATTACHED),
    ];
    if (p.console_log) {
      lines.push("Console lines (" + p.console_log.length + "):");
      if (!p.console_log.length) lines.push("  (the console has been quiet)");
      p.console_log.forEach((line) => lines.push("  " + line));
    } else {
      lines.push("Console lines: " + NOT_ATTACHED);
    }
    lines.push("Linked to your account: " + (p.link_account ? "yes, as " + signedInName() : "no, sent without your name"));
    return lines.join("\n");
  }

  // ---- the dialog ----------------------------------------------------------------------------
  const STYLE_ID = "noyvj-report-styles";
  const CSS = `
.noyvj-report-button, .noyvj-report-dialog, .noyvj-report-dialog * { box-sizing: border-box; }
.noyvj-report-button, .noyvj-report-dialog {
  --nr-bg: #14161f; --nr-fg: #eaeaf0; --nr-muted: #b9bec9; --nr-line: rgba(140, 160, 255, 0.35);
  --nr-field: #0d0f16; --nr-accent: #8fa8ff; --nr-accent-fg: #0b0d14; --nr-error: #ffb4a8; --nr-ok: #a8e6b5;
  font-family: system-ui, -apple-system, sans-serif;
}
html[data-theme="light"] .noyvj-report-button, html[data-theme="light"] .noyvj-report-dialog {
  --nr-bg: #ffffff; --nr-fg: #1a1c24; --nr-muted: #4a5060; --nr-line: rgba(40, 60, 140, 0.4);
  --nr-field: #f3f4f8; --nr-accent: #2e4bb3; --nr-accent-fg: #ffffff; --nr-error: #9a2a1a; --nr-ok: #1d6b34;
}
@media (prefers-color-scheme: light) {
  html:not([data-theme]) .noyvj-report-button, html:not([data-theme]) .noyvj-report-dialog {
    --nr-bg: #ffffff; --nr-fg: #1a1c24; --nr-muted: #4a5060; --nr-line: rgba(40, 60, 140, 0.4);
    --nr-field: #f3f4f8; --nr-accent: #2e4bb3; --nr-accent-fg: #ffffff; --nr-error: #9a2a1a; --nr-ok: #1d6b34;
  }
}
.noyvj-report-button {
  min-height: 44px; padding: 0 0.9rem; font: inherit; font-size: 0.85rem; color: var(--nr-fg);
  background: var(--nr-bg); border: 1px dashed var(--nr-line); border-radius: 10px; cursor: pointer;
}
.noyvj-report-button.noyvj-report-floating { position: fixed; left: 12px; bottom: 12px; z-index: 900; opacity: 0.92; }
.noyvj-report-button:hover { border-style: solid; }
.noyvj-report-button:focus-visible, .noyvj-report-dialog :focus-visible { outline: 3px solid var(--nr-accent); outline-offset: 2px; }
.noyvj-report-dialog {
  width: min(34rem, calc(100vw - 24px)); max-height: calc(100vh - 24px); max-height: calc(100dvh - 24px);
  padding: 0; color: var(--nr-fg); background: var(--nr-bg); border: 1px solid var(--nr-line); border-radius: 12px;
}
.noyvj-report-dialog::backdrop { background: rgba(6, 7, 12, 0.72); }
.noyvj-report-form { display: flex; flex-direction: column; gap: 0.8rem; padding: 1rem; max-height: inherit; overflow-y: auto; }
.noyvj-report-dialog h2 { margin: 0; font-size: 1.15rem; }
.noyvj-report-dialog p, .noyvj-report-dialog legend { margin: 0; font-size: 0.88rem; line-height: 1.4; }
.noyvj-report-dialog .nr-muted { color: var(--nr-muted); }
.noyvj-report-dialog label.nr-field { display: flex; flex-direction: column; gap: 0.3rem; font-size: 0.9rem; font-weight: 600; }
.noyvj-report-dialog textarea, .noyvj-report-dialog pre {
  width: 100%; margin: 0; font: inherit; font-size: 0.88rem; color: var(--nr-fg); background: var(--nr-field);
  border: 1px solid var(--nr-line); border-radius: 8px; padding: 0.6rem;
}
.noyvj-report-dialog textarea { min-height: 6rem; resize: vertical; font-weight: 400; }
.noyvj-report-dialog pre {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.78rem; line-height: 1.45;
  white-space: pre-wrap; overflow-wrap: anywhere; max-height: 14rem; overflow-y: auto;
}
.noyvj-report-dialog fieldset { margin: 0; padding: 0.6rem 0.8rem 0.4rem; border: 1px solid var(--nr-line); border-radius: 8px; }
.noyvj-report-dialog legend { padding: 0 0.3rem; font-weight: 600; }
.noyvj-report-dialog .nr-check { display: flex; align-items: flex-start; gap: 0.6rem; min-height: 44px; padding: 0.3rem 0; font-size: 0.88rem; }
.noyvj-report-dialog .nr-check input { flex: none; width: 1.3rem; height: 1.3rem; margin: 0.1rem 0 0; }
.noyvj-report-dialog .nr-check small { display: block; color: var(--nr-muted); font-size: 0.78rem; }
.noyvj-report-dialog .nr-check[aria-disabled="true"] { opacity: 0.75; }
.noyvj-report-actions {
  display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: flex-end;
  position: sticky; bottom: 0; padding: 0.5rem 0 0.1rem; background: var(--nr-bg);
}
.noyvj-report-actions button {
  min-height: 44px; padding: 0 1rem; font: inherit; font-size: 0.9rem; font-weight: 600; color: var(--nr-fg);
  background: transparent; border: 1px solid var(--nr-line); border-radius: 8px; cursor: pointer;
}
.noyvj-report-actions button.nr-primary { color: var(--nr-accent-fg); background: var(--nr-accent); border-color: var(--nr-accent); }
.noyvj-report-actions button:disabled { opacity: 0.55; cursor: not-allowed; }
.noyvj-report-status { min-height: 1.3em; font-size: 0.88rem; }
.noyvj-report-status.nr-error { color: var(--nr-error); }
.noyvj-report-status.nr-ok { color: var(--nr-ok); }
.noyvj-report-dialog [hidden], .noyvj-report-button[hidden] { display: none !important; }
@media print { .noyvj-report-button, .noyvj-report-dialog { display: none !important; } }
`;

  let dialog = null;
  let parts = null;
  let opener = null;
  let sending = false;
  let draft = "";

  function el(tag, props, children) {
    const node = document.createElement(tag);
    Object.keys(props || {}).forEach((key) => {
      if (key === "text") node.textContent = props[key];
      else if (key === "class") node.className = props[key];
      else node.setAttribute(key, props[key]);
    });
    (children || []).forEach((child) => node.appendChild(child));
    return node;
  }

  function check(id, label, hint, disabled) {
    const input = el("input", { type: "checkbox", id: id });
    const text = el("span", {}, [document.createTextNode(label), el("small", { text: hint, id: id + "-hint" })]);
    input.setAttribute("aria-describedby", id + "-hint");
    if (disabled) input.disabled = true;
    const row = el("label", { class: "nr-check", for: id }, [input, text]);
    return { row, input, text };
  }

  function build() {
    if (dialog) return;
    if (!document.getElementById(STYLE_ID)) {
      const style = el("style", { id: STYLE_ID });
      style.textContent = CSS;
      document.head.appendChild(style);
    }
    dialog = el("dialog", { class: "noyvj-report-dialog", "aria-labelledby": "noyvj-report-title" });
    const form = el("form", { class: "noyvj-report-form", method: "dialog", novalidate: "" });
    const title = el("h2", { id: "noyvj-report-title", text: "Report a problem" });
    const intro = el("p", { class: "nr-muted",
      text: "Tell us what went wrong. Nothing is sent until you press Send, and the box at the bottom shows exactly what will be." });
    const noteLabel = el("label", { class: "nr-field", for: "noyvj-report-note" }, [document.createTextNode("What happened?")]);
    const note = el("textarea", { id: "noyvj-report-note", maxlength: String(NOTE_MAX), rows: "5" });
    noteLabel.appendChild(note);
    const counter = el("p", { class: "nr-muted", id: "noyvj-report-count", text: "0 / " + NOTE_MAX });

    const fieldset = el("fieldset", {}, [el("legend", { text: "Optional extras (all off unless you tick them)" })]);
    const save = check("noyvj-report-save", "Attach my save code", "Lets us open your save to see the problem. Anyone with a save code can load that save.");
    const browser = check("noyvj-report-browser", "Attach my browser and window size", "For layout and compatibility problems.");
    const consoleBox = check("noyvj-report-console", "Attach the last 20 console lines", "What the page logged just before this. Tokens, save codes and emails are removed.");
    const account = check("noyvj-report-account", "Link this report to my account", "So it is deleted if you delete your account.");
    [save, browser, consoleBox, account].forEach((c) => fieldset.appendChild(c.row));

    const previewLabel = el("p", { id: "noyvj-report-preview-label", text: "Exactly what will be sent:" });
    const preview = el("pre", { id: "noyvj-report-preview", tabindex: "0", role: "region", "aria-labelledby": "noyvj-report-preview-label" });
    const status = el("p", { class: "noyvj-report-status", id: "noyvj-report-status", role: "status", "aria-live": "polite" });

    const copy = el("button", { type: "button", text: "Copy report text" });
    const close = el("button", { type: "button", text: "Close" });
    const send = el("button", { type: "submit", class: "nr-primary", text: "Send report" });
    const actions = el("div", { class: "noyvj-report-actions" }, [copy, close, send]);

    [title, intro, noteLabel, counter, fieldset, previewLabel, preview, status, actions].forEach((n) => form.appendChild(n));
    dialog.appendChild(form);
    document.body.appendChild(dialog);
    parts = { form, note, counter, save, browser, console: consoleBox, account, preview, status, copy, close, send };

    const refresh = () => refreshPreview();
    note.addEventListener("input", () => { draft = note.value; refresh(); });
    [save, browser, consoleBox, account].forEach((c) => c.input.addEventListener("change", refresh));
    note.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) { event.preventDefault(); submit(); }
    });
    form.addEventListener("submit", (event) => { event.preventDefault(); submit(); });
    close.addEventListener("click", () => closeDialog());
    copy.addEventListener("click", () => copyPreview());
    dialog.addEventListener("close", () => {
      if (opener && typeof opener.focus === "function") { try { opener.focus(); } catch (e) { /* gone */ } }
    });
  }

  function currentOptions() {
    return {
      note: parts.note.value,
      saveCode: parts.save.input.checked,
      browser: parts.browser.input.checked,
      console: parts.console.input.checked,
      account: parts.account.input.checked,
    };
  }

  function refreshPreview() {
    const code = saveCode();
    parts.save.input.disabled = !code;
    if (!code) parts.save.input.checked = false;
    parts.save.row.setAttribute("aria-disabled", String(!code));
    parts.save.text.lastChild.textContent = code
      ? "Lets us open your save to see the problem. Anyone with a save code can load that save."
      : "There is no save code on this device for this game yet, so there is nothing to attach.";
    const name = signedInName();
    parts.account.row.hidden = !name;
    if (!name) parts.account.input.checked = false;
    const lines = ring.length;
    parts.console.text.firstChild.textContent = "Attach the last " + CONSOLE_MAX_LINES + " console lines (" + lines + " captured)";
    parts.counter.textContent = parts.note.value.length + " / " + NOTE_MAX;
    parts.preview.textContent = previewText(payload(currentOptions()));
    parts.send.disabled = sending || !parts.note.value.trim();
  }

  function setStatus(text, kind) {
    parts.status.textContent = text;
    parts.status.className = "noyvj-report-status" + (kind ? " nr-" + kind : "");
  }

  async function submit() {
    if (sending || !parts.note.value.trim()) return;
    const body = payload(currentOptions());
    const headers = { "Content-Type": "application/json" };
    const token = lsGet(TOKEN_KEY);
    if (body.link_account && token) headers.Authorization = "Bearer " + token;
    sending = true;
    refreshPreview();
    setStatus("Sending…");
    try {
      const response = await fetch(config.apiBase + "/bug-reports", { method: "POST", headers, body: JSON.stringify(body) });
      if (response.status === 429) throw new Error("rate");
      if (!response.ok) throw new Error("status " + response.status);
      draft = "";
      parts.note.value = "";
      sending = false;
      refreshPreview();
      setStatus("Thank you. Your report was sent.", "ok");
    } catch (err) {
      sending = false;
      refreshPreview();
      setStatus(err && err.message === "rate"
        ? "That is a lot of reports from this device just now. Please try again in a while."
        : "The report could not be sent (the server may be asleep or you may be offline). Nothing was lost: you can try again, or use Copy report text.", "error");
    }
  }

  async function copyPreview() {
    const text = parts.preview.textContent;
    try {
      await navigator.clipboard.writeText(text);
      setStatus("Copied.", "ok");
    } catch (err) {
      const range = document.createRange();
      range.selectNodeContents(parts.preview);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      setStatus("Select and copy the text above (Ctrl or Cmd + C).");
    }
  }

  function open(from) {
    build();
    opener = from || document.activeElement;
    parts.note.value = draft;
    setStatus("");
    refreshPreview();
    if (typeof dialog.showModal === "function") { if (!dialog.open) dialog.showModal(); }
    else dialog.setAttribute("open", "");
    parts.note.focus();
  }

  function closeDialog() {
    if (!dialog) return;
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  }

  // ---- the button ----------------------------------------------------------------------------
  let button = null;
  function mountButton() {
    if (DATA.button === "none" || button) return;
    button = el("button", { type: "button", class: "noyvj-report-button", text: "Report a problem", "data-noyvj-report": "open" });
    if (!document.getElementById(STYLE_ID)) {
      const style = el("style", { id: STYLE_ID });
      style.textContent = CSS;
      document.head.appendChild(style);
    }
    const host = DATA.mount ? document.querySelector(DATA.mount) : null;
    if (host) host.appendChild(button);
    else { button.classList.add("noyvj-report-floating"); document.body.appendChild(button); }
    button.addEventListener("click", () => open(button));
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mountButton);
  else mountButton();

  window.NoyvjReport = {
    version: 1,
    open: () => open(),
    close: closeDialog,
    configure(options) {
      const o = options || {};
      if (o.gameId) config.gameId = String(o.gameId);
      if ("schemaVersion" in o) config.schemaVersion = o.schemaVersion == null ? null : String(o.schemaVersion);
      if (o.apiBase) config.apiBase = String(o.apiBase);
      if ("getSaveCode" in o) config.getSaveCode = typeof o.getSaveCode === "function" ? o.getSaveCode : null;
    },
    consoleLines: () => ring.slice(),
    payload,
    previewText,
    scrub,
  };
})();
