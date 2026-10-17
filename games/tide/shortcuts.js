// Z4 (site-wide goal): "?" shows a keyboard-shortcuts help overlay,
// Esc closes whichever panel is open. See shared/keyboard-shortcuts.js.
window.KeyboardShortcuts.init({
  extra: [
    "A — advance one season",
    "X — advance up to 5 quiet seasons",
    "1 / 2 / 3 — invest in Output / Acidity Reduction / Adaptation",
    "R — open or close the session report",
    "L — open or close the Harbor Ledger",
    "Arrow keys — move around the coastline tiles (when a tile is focused)",
    "Left / Right on a graph — read each season (hover or tap works too)",
  ],
  panels: [
    { toggle: "howto-toggle-button", panel: "howto-panel" },
    { toggle: "settings-toggle-button", panel: "settings-panel" },
    { toggle: "achievements-toggle-button", panel: "achievements-panel" },
    { toggle: "changelog-toggle-button", panel: "changelog-panel" },
    { toggle: "session-summary-toggle-button", panel: "session-summary-panel" },
    { toggle: "ledger-toggle-button", panel: "ledger-panel" },
    { toggle: "planner-toggle-button", panel: "planner-panel" },
    { toggle: "library-toggle-button", panel: "library-panel" },
    { toggle: "almanac-toggle-button", panel: "almanac-panel" },
    { toggle: "daily-toggle-button", panel: "daily-panel" },
    { toggle: "info-page-toggle-button", panel: "info-page-panel" },
    { toggle: "dashboard-toggle-button", panel: "dashboard-panel" },
  ],
});
