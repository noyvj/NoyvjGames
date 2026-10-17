// FY-53: mounts the three-goals list (shared/goals-panel.js); the queue comes from game.py's goals_json().
(function () {
  if (!window.NoyvjGoals) return;
  var panel = NoyvjGoals.mount("#goals", {
    game: "sol",
    getGoals: function () {
      try {
        var fn = window.pyodide && window.pyodide.globals.get("goals_json");
        if (!fn) return [];
        var text = fn();
        if (fn.destroy) fn.destroy();
        return JSON.parse(text);
      } catch (e) { return []; }
    },
  });
  window.SOL_GOALS = panel;
  NoyvjGoals.bindCheckbox(panel, "#goals-checkbox");
})();
