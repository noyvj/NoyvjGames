// Z4 (site-wide goal): "?" shows a keyboard-shortcuts help overlay, Esc closes whichever panel is open. See shared/keyboard-shortcuts.js.
window.KeyboardShortcuts.init({
  extra: [
    "Up / Down arrow: move between the buy buttons (Home and End jump to the first or last)",
    "Left / Right arrow on x1, x5, Max: choose how many units each purchase buys",
  ],
  panels: [
    { toggle: "howto-toggle-button", panel: "howto-panel" },
    { toggle: "achievements-toggle-button", panel: "achievements-panel" },
    { toggle: "report-card-toggle-button", panel: "report-card-panel" },
    { toggle: "changelog-toggle-button", panel: "changelog-panel" },
    { toggle: "settings-toggle-button", panel: "settings-panel" },
    { toggle: "info-page-toggle-button", panel: "info-page-panel" },
  ],
});
