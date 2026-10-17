// Z4: the keyboard-shortcuts help overlay and the panels Esc closes (see shared/keyboard-shortcuts.js).
window.KeyboardShortcuts.init({
  extra: ["Space — pause or resume time", "[ and ] — slower or faster (1x, 2x, 4x)"],
  panels: [
    { toggle: "howto-toggle-button", panel: "howto-panel" },
    { toggle: "settings-toggle-button", panel: "settings-panel" },
    { toggle: "achievements-toggle-button", panel: "achievements-panel" },
    { toggle: "stats-toggle-button", panel: "stats-panel" },
    { toggle: "governor-report-toggle-button", panel: "governor-report-panel" },
    { toggle: "changelog-toggle-button", panel: "changelog-panel" },
    { toggle: "overview-toggle-button", panel: "overview-panel" },
    { toggle: "build-plan-toggle-button", panel: "build-plan-panel" },
    { toggle: "chains-toggle-button", panel: "chains-panel" },
    { toggle: "splits-toggle-button", panel: "splits-panel" },
    { toggle: "charter-toggle-button", panel: "charter-panel" },
    { toggle: "observatory-toggle-button", panel: "observatory-panel" },
    { toggle: "capsules-toggle-button", panel: "capsules-panel" },
    { toggle: "scarcity-toggle-button", panel: "scarcity-panel" },
    { toggle: "doctrine-toggle-button", panel: "doctrine-panel" },
    { toggle: "prestige-tree-toggle-button", panel: "prestige-tree-panel" },
    { toggle: "epilogue-button", panel: "epilogue-panel" },
  ],
});
