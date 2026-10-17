// B-15: named local forests (up to three per browser, not signed in). The shared save widget reads window.NoyvjSaveProfiles before it loads.
window.NoyvjSaveProfiles = {
  noun: "forest",
  defaultName: "My forest",
  gameKeys: ["canopy_species_choice_v1"],
  startNew: function () {
    var fn = window.pyodide && window.pyodide.globals.get("start_new_forest");
    if (!fn) throw new Error("start_new_forest is not ready");
    fn();
  },
  afterSwitch: function () {
    var fn = window.pyodide && window.pyodide.globals.get("after_forest_switch");
    if (fn) fn();
  },
};
