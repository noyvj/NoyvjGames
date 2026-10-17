// Z4 (site-wide goal): "?" shows a keyboard-shortcuts help overlay, Esc closes whichever panel is open. See shared/keyboard-shortcuts.js.
window.KeyboardShortcuts.init({
  panels: [
    { toggle: "howto-toggle-button", panel: "howto-panel" },
    { toggle: "settings-toggle-button", panel: "settings-panel" },
    { toggle: "achievements-toggle-button", panel: "achievements-panel" },
    { toggle: "changelog-toggle-button", panel: "changelog-panel" },
    { toggle: "summary-toggle-button", panel: "summary-panel" },
    { toggle: "weather-log-toggle-button", panel: "weather-log-panel" },
    { toggle: "info-page-toggle-button", panel: "info-page-panel" },
    { toggle: "career-toggle-button", panel: "career-panel" },
  ],
  extra: [
    "Right arrow (focus on a plant) — build one",
    "Left arrow (focus on a plant) — retire one",
    "Up / Down arrow (focus on a plant) — move between plants",
  ],
});
