// R-31: community resilience figure for the Mutual aid setting. Plain JS like the feedback prompt: a
// read-only fetch of the same stats summary the line above uses (GET /stats/games/aftermath), handed to
// game.py's set_community_resilience(mean), which owns every rule (threshold, the fixed event and amount,
// the cached copy). No figure (offline, fewer than three saves, a failed request) hands in nothing at all,
// so the last cached figure keeps standing; a summary that has no usable figure hands in null. Skipped
// while "reduce data" is on (hub setting, or the browser's Data Saver): the cached figure is used instead.
(function () {
  var API = "https://noyvjgames.fastapicloud.dev";
  function reduceData() {
    var choice = null;
    try { choice = localStorage.getItem("hub_reduce_data"); } catch (e) { /* storage blocked */ }
    if (choice === "1") return true;
    if (choice === "0") return false;
    var conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    return Boolean(conn && conn.saveData);
  }
  if (reduceData()) return;
  function hand(mean) {
    var tries = 0;
    var timer = setInterval(function () {
      tries += 1;
      try {
        var fn = window.pyodide && window.pyodide.globals.get("set_community_resilience");
        if (fn) { clearInterval(timer); fn(mean); if (fn.destroy) fn.destroy(); return; }
      } catch (e) { /* the game is not ready yet */ }
      if (tries > 240) clearInterval(timer);
    }, 500);
  }
  fetch(API + "/stats/games/aftermath")
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (summary) {
      if (!summary) return;
      var field = !summary.suppressed && summary.fields && summary.fields.skill_tree_strength;
      hand(field && typeof field.mean === "number" ? field.mean : null);
    })
    .catch(function () { /* keep whatever figure is cached */ });
})();
