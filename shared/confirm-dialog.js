/*
 * Shared confirmation dialog — a "are you sure?" step with a persistent
 * "don't ask again" opt-out, for any action a game wants to guard against
 * an accidental click (planning/TODO.md's shared confirmation-dialog
 * goal: C14/F16/J19 all separately asked for this same shape).
 *
 * One script, included unchanged by every game via:
 *   <script src="../../shared/confirm-dialog.js"></script>
 * then, wherever a game currently does:
 *   button.addEventListener("click", () => pythonHandler());
 * wrap the call instead:
 *   button.addEventListener("click", () => {
 *     ConfirmDialog.ask({
 *       id: "gamename-some-action",   // unique per action, used as the
 *                                     // localStorage key for "don't ask
 *                                     // again" — pick something that
 *                                     // won't collide with another
 *                                     // game's or action's id
 *       message: "Retire the last Coal Plant? You can't undo this.",
 *       confirmLabel: "Retire it",   // optional, defaults to "Confirm"
 *       cancelLabel: "Cancel",       // optional
 *       allowSkip: true,             // optional; false hides "don't ask
 *                                    // again" for a destructive action
 *       onConfirm: () => pythonHandler(),
 *     });
 *   });
 *
 * If the player has already checked "don't ask again" for this exact
 * `id`, onConfirm() fires immediately with no dialog shown at all — the
 * whole point of the opt-out. That choice is per-browser (localStorage),
 * matching every other per-browser-only preference on this site (text
 * -scale, reduced-motion, personal-best stats) rather than being part of
 * portable save state.
 *
 * This file owns its own modal markup/styling (injected once, reused for
 * every ask() call) so a game integrating it needs zero new CSS of its
 * own — same self-contained-styling approach save-widget.js already uses.
 * Deliberately NOT a native browser confirm()/alert(): those block the
 * whole page (including Pyodide's event loop) and can't carry a "don't
 * ask again" checkbox or this site's own visual language.
 *
 * The <script> tag above is meant to sit in <head> unmodified, alongside
 * this hub's other un-deferred shared scripts (tutorial.js, mobile-hud.js,
 * mobile-dock.js) -- so the actual overlay DOM is built lazily, on the
 * first real ask()/resetSkip() call, rather than eagerly at script-load
 * time when <body> doesn't exist yet.
 */
(function () {
  const STORAGE_PREFIX = "confirm-dialog:skip:";

  if (!document.getElementById("confirm-dialog-styles")) {
    const style = document.createElement("style");
    style.id = "confirm-dialog-styles";
    style.textContent = `
      #confirm-dialog-overlay {
        position: fixed;
        inset: 0;
        z-index: 10000;
        background: rgba(6, 7, 12, 0.72);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 16px;
        font-family: system-ui, -apple-system, sans-serif;
      }
      #confirm-dialog-overlay[hidden] { display: none !important; }
      #confirm-dialog-box {
        background: #14161f;
        border: 1px solid rgba(140, 160, 255, 0.18);
        border-radius: 12px;
        padding: 20px;
        max-width: 360px;
        width: 100%;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
        color: #eaeaf0;
      }
      #confirm-dialog-message {
        margin: 0 0 14px;
        font-size: 0.92rem;
        line-height: 1.4;
      }
      #confirm-dialog-skip-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
        font-size: 0.8rem;
        color: #b9bec9;
      }
      #confirm-dialog-skip-row input { margin: 0; }
      #confirm-dialog-actions {
        display: flex;
        gap: 10px;
        justify-content: flex-end;
      }
      #confirm-dialog-actions button {
        border: none;
        border-radius: 8px;
        padding: 0.55rem 1rem;
        font-size: 0.85rem;
        font-weight: 600;
        cursor: pointer;
        font-family: inherit;
      }
      #confirm-dialog-cancel { background: #2a3a4c; color: #eaeaf0; }
      #confirm-dialog-confirm { background: #d1483c; color: white; }
    `;
    document.head.appendChild(style);
  }

  // Every game on this site includes this script from a plain, un-deferred
  // <script src="..."> tag sitting in <head> (same convention as
  // tutorial.js/mobile-hud.js/mobile-dock.js) -- which runs it before
  // <body> has been parsed, so `document.body` is still null at this
  // point. tutorial.js/mobile-hud.js dodge this by only touching
  // `document.body` from inside a function invoked later (tutorial's
  // `buildOverlay()`, called on first actual use); this file used to
  // build+appendChild its overlay at top-level IIFE-execution time
  // instead, which threw "Cannot read properties of null (reading
  // 'appendChild')" and aborted before ever reaching the
  // `window.ConfirmDialog = {...}` assignment below -- silently killing
  // the dialog on every page that includes this script. Fixed the same
  // way tutorial.js already does it: defer the DOM-touching setup into
  // `ensureBuilt()`, called lazily on first real use (`ask()`/
  // `resetSkip()`) once `document.body` is guaranteed to exist, instead
  // of eagerly at script-parse time.
  let overlay = null;
  let messageEl = null;
  let skipCheckbox = null;
  let cancelButton = null;
  let confirmButton = null;

  // Set fresh on every ask() call so cancelButton/confirmButton's click
  // handlers always act on the CURRENT request, not a stale one from an
  // earlier ask() -- only one dialog is ever open at a time, so reusing
  // one overlay/one set of buttons is simpler than creating a new DOM
  // subtree per call.
  let pendingId = null;
  let pendingOnConfirm = null;

  function close() {
    overlay.hidden = true;
    pendingId = null;
    pendingOnConfirm = null;
  }

  function ensureBuilt() {
    if (overlay) return;

    overlay = document.getElementById("confirm-dialog-overlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "confirm-dialog-overlay";
      overlay.hidden = true;
      overlay.innerHTML = `
        <div id="confirm-dialog-box" role="alertdialog" aria-modal="true">
          <p id="confirm-dialog-message"></p>
          <label id="confirm-dialog-skip-row">
            <input type="checkbox" id="confirm-dialog-skip-checkbox">
            Don't ask me again for this
          </label>
          <div id="confirm-dialog-actions">
            <button type="button" id="confirm-dialog-cancel">Cancel</button>
            <button type="button" id="confirm-dialog-confirm">Confirm</button>
          </div>
        </div>
      `;
      document.body.appendChild(overlay);
    }

    messageEl = overlay.querySelector("#confirm-dialog-message");
    skipCheckbox = overlay.querySelector("#confirm-dialog-skip-checkbox");
    cancelButton = overlay.querySelector("#confirm-dialog-cancel");
    confirmButton = overlay.querySelector("#confirm-dialog-confirm");

    cancelButton.addEventListener("click", close);
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) close(); // click on the dim backdrop
    });
    confirmButton.addEventListener("click", () => {
      if (pendingId && skipCheckbox.checked && !skipCheckbox.closest('#confirm-dialog-skip-row').hidden) {
        localStorage.setItem(STORAGE_PREFIX + pendingId, "true");
      }
      const onConfirm = pendingOnConfirm;
      close();
      if (onConfirm) onConfirm();
    });
  }

  window.ConfirmDialog = {
    // `allowSkip: false` (default true) hides the "don't ask again" checkbox
    // and ignores any stored skip flag for this id -- for a rare, destructive
    // action (e.g. Trade Empire's "found a new corporation" reset) that must
    // always be confirmed.
    ask({ id, message, confirmLabel, cancelLabel, onConfirm, allowSkip = true }) {
      if (!id) {
        console.error("ConfirmDialog.ask() requires a unique `id`");
        return;
      }
      if (allowSkip && localStorage.getItem(STORAGE_PREFIX + id) === "true") {
        if (onConfirm) onConfirm();
        return;
      }
      ensureBuilt();
      pendingId = id;
      pendingOnConfirm = onConfirm;
      messageEl.textContent = message || "Are you sure?";
      confirmButton.textContent = confirmLabel || "Confirm";
      cancelButton.textContent = cancelLabel || "Cancel";
      skipCheckbox.checked = false;
      const skipRow = overlay.querySelector("#confirm-dialog-skip-row");
      if (skipRow) skipRow.hidden = !allowSkip;
      overlay.hidden = false;
    },

    // Lets a settings/reset UI clear a specific "don't ask again" flag,
    // or every one this module has ever set, without a player needing to
    // know the exact localStorage key shape.
    resetSkip(id) {
      if (id) {
        localStorage.removeItem(STORAGE_PREFIX + id);
        return;
      }
      Object.keys(localStorage)
        .filter((key) => key.startsWith(STORAGE_PREFIX))
        .forEach((key) => localStorage.removeItem(key));
    },
  };
})();
