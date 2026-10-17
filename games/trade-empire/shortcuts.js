// Keyboard shortcuts: tells the shared ? help overlay and Esc handling which panels exist.
window.KeyboardShortcuts.init({
  extra: ["Space — pause or resume time", "[ and ] — slower or faster (1x, 2x, 4x)", "R — restart the Trade Crisis you are playing"],
  panels: [
    { toggle: "howto-toggle-button", panel: "howto-panel" },
    { toggle: "achievements-toggle-button", panel: "achievements-panel" },
    { toggle: "changelog-toggle-button", panel: "changelog-panel" },
    { toggle: "settings-toggle-button", panel: "settings-panel" },
    { toggle: "summary-toggle-button", panel: "summary-panel" },
    { toggle: "charter-toggle-button", panel: "charter-panel" },
    { toggle: "captains-toggle-button", panel: "captains-panel" },
    { toggle: "lab-toggle-button", panel: "lab-panel" },
    { toggle: "desk-toggle-button", panel: "desk-panel" },
    { toggle: "chain-toggle-button", panel: "chain-panel" },
  ],
});
