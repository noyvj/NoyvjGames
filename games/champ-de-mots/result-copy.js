// Mounts the shared Copy result button in the Review panel's summary; reads share_result() from the Python side.
(function () {
  function resultFields() {
    try {
      var f = window.pyodide && window.pyodide.globals.get("share_result");
      if (f) { var text = f(); if (f.destroy) f.destroy(); return JSON.parse(text); }
    } catch (e) { /* engine not ready */ }
    return {};
  }
  if (window.NoyvjCopyResult) NoyvjCopyResult.mountButton("#result-copy", { getResult: resultFields });
})();
