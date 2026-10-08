/* Dead Reckoning view: glue only. The engine (game.py and its modules) holds every rule; this file draws what
   handle() returns and forwards what the player does. No game logic lives here. */
(function () {
  "use strict";
  var ENGINE_MODULES = ["geom.py", "sim.py", "charts.py", "render.py"];
  var STORE_KEY = "dead-reckoning:state";

  var $ = function (id) { return document.getElementById(id); };
  var engine = null;   // { handle, getState, loadState }
  var view = null;

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }

  // Live regions only announce when their text really changes, so assign through setText.
  function setText(node, text) { if (node.textContent !== text) node.textContent = text; }

  function renderChart() {
    var holder = $("chart-holder");
    if (holder.dataset.signature !== view.svg) {
      holder.innerHTML = view.svg;           // the engine's own markup: no player text goes in
      holder.dataset.signature = view.svg;
    }
    var list = $("chart-notes-list");
    list.textContent = "";
    view.notes.forEach(function (line) {
      var li = document.createElement("li");
      li.textContent = line;
      list.appendChild(li);
    });
    setText($("chart-title"), view.chart.name);
  }

  function render() { renderChart(); }

  function persist() {
    try {
      var proxy = engine.getState();
      var obj = proxy.toJs({ dict_converter: Object.fromEntries });
      if (proxy.destroy) proxy.destroy();
      lsSet(STORE_KEY, JSON.stringify(obj));
    } catch (e) { /* the save widget is the real save */ }
  }
  function send(request) {
    var result = JSON.parse(engine.handle(JSON.stringify(request)));
    if (result.error) { $("engine-status").textContent = "Something went wrong: " + result.error; return null; }
    view = result;
    render();
    persist();
    return result;
  }

  async function boot() {
    var pyodide = await window.loadPyodide();
    for (var i = 0; i < ENGINE_MODULES.length; i++) {
      var source = await (await fetch(ENGINE_MODULES[i])).text();
      pyodide.FS.writeFile(ENGINE_MODULES[i], source, { encoding: "utf8" });
    }
    await pyodide.runPythonAsync(await (await fetch("game.py")).text());
    window.pyodide = pyodide;   // the shared save widget looks for it
    engine = { handle: pyodide.globals.get("handle"), getState: pyodide.globals.get("get_state"), loadState: pyodide.globals.get("load_state") };
    $("engine-status").textContent = "";
    send({ action: "open" });
  }

  boot().catch(function (err) {
    $("engine-status").textContent = "The chart table could not start (" + err + "). Reload to try again.";
  });
})();
