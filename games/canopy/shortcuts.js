// Keyboard shortcuts: tells the shared ? help overlay and Esc handling which panels exist, and lists the game's own keys.
window.KeyboardShortcuts.init({
  panels: [
    { toggle: "howto-toggle-button", panel: "howto-panel" },
    { toggle: "settings-toggle-button", panel: "settings-panel" },
    { toggle: "achievements-toggle-button", panel: "achievements-panel" },
    { toggle: "changelog-toggle-button", panel: "changelog-panel" },
    { toggle: "example-toggle-button", panel: "example-panel" },
    { toggle: "almanac-toggle-button", panel: "almanac-panel" },
    { toggle: "contracts-toggle-button", panel: "contracts-panel" },
    { toggle: "vault-toggle-button", panel: "vault-panel" },
    { toggle: "expedition-toggle-button", panel: "expedition-panel" },
    { toggle: "session-summary-toggle-button", panel: "session-summary-panel" },
    { toggle: "info-page-toggle-button", panel: "info-page-panel" },
  ],
  extra: [
    "Space — pause or resume time (when no button or plot has the focus)",
    "[ and ] — slower or faster (1x, 2x, 4x)",
    "Arrow keys — move between plots (click or Tab to a plot first, then Enter or Space to select)",
    "N — jump to the plot a pending stakeholder request names",
    "T — tend the plot under the pointer (or the selected plot)",
    "G — catch a golden seedling",
    "U — undo the last clear (just after clearing)",
    "P — drive off the poacher (Poacher Patrol level)",
    "C — clear the selected plot; R — replant the selected plot (select one with Enter or a click first)",
    "K — clear-cut the selected plot: a bonus now for a soil dip that heals over about three seasons",
  ],
});
