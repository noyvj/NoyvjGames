// R-30: community coastline line. Plain JS like the feedback prompt: a read-only fetch of the same stats
// summary the seawall line above uses (GET /stats/games/tide), handed to game.py's
// set_community_coastline(mean, count), which owns every rule and the wording. The field is
// coastline_kept: until app/stats.py lists it the summary has no such field and the line stays hidden.
// Skipped while "reduce data" is on (hub setting, or the browser's Data Saver); every failure leaves the
// line hidden.
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
  function hand(mean, count) {
    var tries = 0;
    var timer = setInterval(function () {
      tries += 1;
      try {
        var fn = window.pyodide && window.pyodide.globals.get("set_community_coastline");
        if (fn) { clearInterval(timer); fn(mean, count); if (fn.destroy) fn.destroy(); return; }
      } catch (e) { /* the game is not ready yet */ }
      if (tries > 240) clearInterval(timer);
    }, 500);
  }
  fetch(API + "/stats/games/tide")
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (summary) {
      if (!summary || summary.suppressed) return;
      var field = summary.fields && summary.fields.coastline_kept;
      if (field && typeof field.mean === "number") hand(field.mean, field.count);
    })
    .catch(function () { /* leave the line hidden */ });
})();
