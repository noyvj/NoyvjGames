// Keyboard shortcuts: tells the shared ? help overlay and Esc handling which panels exist.
window.KeyboardShortcuts.init({
  panels: [
    { toggle: "howto-toggle-button", panel: "howto-panel" },
    { toggle: "achievements-toggle-button", panel: "achievements-panel" },
    { toggle: "changelog-toggle-button", panel: "changelog-panel" },
    { toggle: "community-compare-toggle-button", panel: "community-compare-panel" },
    { toggle: "settings-toggle-button", panel: "settings-panel" },
    { toggle: "info-page-toggle-button", panel: "info-page-panel" },
    { toggle: "worst-case-toggle-button", panel: "worst-case-panel" },
    { toggle: "archive-toggle-button", panel: "archive-panel" },
  ],
});
