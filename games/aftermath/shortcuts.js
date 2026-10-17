// Z4: the keyboard-shortcuts help overlay and the panels Esc closes (see shared/keyboard-shortcuts.js).
window.KeyboardShortcuts.init({
  extra: [
    "1 / 2 — invest in Resilience / Growth (at the chosen step)",
    "Enter — Face Next Event (when no button is focused)",
    "U — undo your last investment click",
    "T — jump to the skill tree",
    "M — open the skill map (arrows move between skills, Enter selects, + and - zoom, 0 fits, Esc clears)",
    "Up / Down arrows — move between skills in the tree; Enter unlocks, P pins",
    "H — open or close Past Runs",
    "C — open or close the Disaster Codex",
    "S — open or close Lifetime Stats",
  ],
  panels: [
    { toggle: "howto-toggle-button", panel: "howto-panel" },
    { toggle: "settings-toggle-button", panel: "settings-panel" },
    { toggle: "info-page-toggle-button", panel: "info-page-panel" },
    { toggle: "achievements-toggle-button", panel: "achievements-panel" },
    { toggle: "past-runs-toggle-button", panel: "past-runs-panel" },
    { toggle: "codex-toggle-button", panel: "codex-panel" },
    { toggle: "stats-toggle-button", panel: "stats-panel" },
    { toggle: "changelog-toggle-button", panel: "changelog-panel" },
  ],
});
