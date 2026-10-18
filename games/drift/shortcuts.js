// Z4: the keyboard-shortcuts help overlay and the panels Esc closes (see shared/keyboard-shortcuts.js).
window.KeyboardShortcuts.init({
  extra: [
    "1 / 2 / 3 — buy Housing / Integration Services / Infrastructure",
    "Enter — Advance Round (when no button is focused)",
    "U — reset this round (refund this round's decisions)",
    "P — play 5 rounds",
    "L — open or close the Round Ledger",
    "C — open or close the Region Collection",
  ],
  panels: [
    { toggle: "howto-toggle-button", panel: "howto-panel" },
    { toggle: "achievements-toggle-button", panel: "achievements-panel" },
    { toggle: "changelog-toggle-button", panel: "changelog-panel" },
    { toggle: "ledger-toggle-button", panel: "ledger-panel" },
    { toggle: "collection-toggle-button", panel: "collection-panel" },
    { toggle: "report-toggle-button", panel: "report-panel" },
    { toggle: "settings-toggle-button", panel: "settings-panel" },
    { toggle: "info-page-toggle-button", panel: "info-page-panel" },
    { toggle: "coda-button", panel: "coda-section" },
  ],
});
