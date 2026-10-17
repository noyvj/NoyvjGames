// Z-20 / Z-27 / Y-29 / D-3 / GD-5: the shared Copy result buttons, the achievement Share buttons' companions and the Credits links.
(function () {
  // copy_result_fields() in game.py returns the headline numbers; read at click time.
  function fields() {
    try {
      var fn = window.pyodide.globals.get("copy_result_fields");
      var result = fn();
      var out = result.toJs({ dict_converter: Object.fromEntries });
      result.destroy();
      fn.destroy();
      return out;
    } catch (e) {
      return {};
    }
  }
  // Mounts the button inside the summary panel and puts it back if the game rebuilds the panel.
  function mountCopy(panelId, beforeSelector) {
    var panel = document.getElementById(panelId);
    if (!panel || !window.NoyvjCopyResult) return;
    function ensure() {
      if (panel.querySelector(":scope > .run-end-copy")) return;
      var host = document.createElement("div");
      host.className = "run-end-copy";
      host.setAttribute("data-copy-result-for", panelId);
      var anchor = beforeSelector ? panel.querySelector(beforeSelector) : null;
      if (anchor && anchor.parentNode === panel) panel.insertBefore(host, anchor);
      else panel.appendChild(host);
      NoyvjCopyResult.mountButton(host, { getResult: fields });
    }
    ensure();
    new MutationObserver(ensure).observe(panel, { childList: true });
  }
  // A small Credits link at the foot of the how-to and info panels, kept if the game rewrites them.
  function addCredits(panelId) {
    var panel = document.getElementById(panelId);
    if (!panel) return;
    function ensure() {
      if (panel.querySelector(":scope > .game-credits-link")) return;
      var p = document.createElement("p");
      p.className = "game-credits-link";
      p.style.cssText = "margin:0.25rem 0 0;font-size:0.8rem";
      var a = document.createElement("a");
      a.href = "../../credits.html";
      a.textContent = "Credits and thanks";
      a.style.cssText = "display:inline-flex;align-items:center;min-height:44px;color:inherit;text-decoration:underline";
      p.appendChild(a);
      panel.appendChild(p);
    }
    ensure();
    new MutationObserver(ensure).observe(panel, { childList: true });
  }
  mountCopy("session-summary-panel");
  // D-3 / GD-5: one shared Copy result button for the run code and one for a finished Daily Tide line.
  function pyFields(name) {
    return function () {
      try {
        var fn = window.pyodide.globals.get(name);
        var result = fn();
        var out = result.toJs({ dict_converter: Object.fromEntries });
        result.destroy();
        fn.destroy();
        return out;
      } catch (e) {
        return {};
      }
    };
  }
  if (window.NoyvjCopyResult) {
    var CR = window.NoyvjCopyResult;
    CR.mountButton("#run-code-copy", { label: "Copy run code", getResult: pyFields("run_code_copy_fields") });
    CR.mountButton("#daily-copy", { label: "Copy daily result", getResult: pyFields("daily_copy_fields") });
  }
  addCredits("howto-panel");
  addCredits("info-page-panel");
})();
