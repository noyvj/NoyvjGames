// Mounts the shared copy-result button into the Summary panel (loaded from inside #summary-panel, right after
// #summary-copy-result exists). Reads the result through the engine's share_result() once Pyodide is up.
(function () {
  function resultFields() {
    try {
      var f = window.pyodide && window.pyodide.globals.get("share_result");
      if (f) { var text = f(); if (f.destroy) f.destroy(); return JSON.parse(text); }
    } catch (e) { /* engine not ready */ }
    return {};
  }
  if (window.NoyvjCopyResult) NoyvjCopyResult.mountButton("#summary-copy-result", { getResult: resultFields });
})();
