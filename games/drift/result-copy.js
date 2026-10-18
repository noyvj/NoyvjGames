// The shared Copy result button in the long-horizon outcomes panel: share_result() in game.py supplies the text.
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
