// Keyboard shortcuts: the shared ? help overlay and Esc handling, plus Loop's own Space / 1 / 2 / 3 / T keys.
window.KeyboardShortcuts.init({
  panels: [
    { toggle: "howto-toggle-button", panel: "howto-panel" },
    { toggle: "achievements-toggle-button", panel: "achievements-panel" },
    { toggle: "changelog-toggle-button", panel: "changelog-panel" },
    { toggle: "settings-toggle-button", panel: "settings-panel" },
    { toggle: "info-page-toggle-button", panel: "info-page-panel" },
  ],
  extra: [
    "Space — advance the cycle",
    "1 / 2 / 3 — buy Repair Networks / Reuse Systems / Recycling Loops",
    "T — buy a Trade Link",
  ],
});

// H-13: game shortcuts. They only click the buttons the page already has (so the same rules,
// costs and disabled states apply), and stay quiet while a dialog, the opening screen, a
// Desktop window or a text field has the keyboard, or while a button/link has focus (Space
// already activates it).
(function () {
  const KEYS = {
    " ": "advance-cycle-button",
    "1": "repair-invest-button",
    "2": "reuse-invest-button",
    "3": "recycle-invest-button",
    t: "trade-link-invest-button",
  };
  const BLOCKERS = "#opening-screen, #tutorial-overlay:not([hidden]), #confirm-dialog-overlay:not([hidden]), " +
    ".confirm-dialog-overlay, #kb-shortcuts-panel:not([hidden]), #pc-backdrop:not([hidden]), #pc-menu-panel:not([hidden])";
  document.addEventListener("keydown", function (event) {
    const id = KEYS[event.key.length === 1 ? event.key.toLowerCase() : event.key];
    if (!id || event.ctrlKey || event.metaKey || event.altKey || event.repeat) return;
    const tag = event.target && event.target.tagName;
    if (/^(INPUT|TEXTAREA|SELECT|BUTTON|A|SUMMARY)$/.test(tag || "") || (event.target && event.target.isContentEditable)) return;
    if (Array.prototype.some.call(document.querySelectorAll(BLOCKERS), function (n) { return n.getBoundingClientRect().width > 0; })) return;
    const button = document.getElementById(id);
    if (!button || button.disabled) return;
    event.preventDefault();
    button.click();
  });
})();
