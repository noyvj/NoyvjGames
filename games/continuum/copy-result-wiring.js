// The Copy result buttons of the Civilization Summary and the Challenge runs panels (shared/copy-result.js). Python decides what
// the result says (share_result / challenge_share_result in game.py); this only mounts the buttons.
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

(function () {
  function resultFields() {
    try {
      var f = window.pyodide && window.pyodide.globals.get("challenge_share_result");
      if (f) { var text = f(); if (f.destroy) f.destroy(); return JSON.parse(text); }
    } catch (e) { /* engine not ready */ }
    return {};
  }
  if (window.NoyvjCopyResult) NoyvjCopyResult.mountButton("#challenge-copy-result", { getResult: resultFields });
})();
