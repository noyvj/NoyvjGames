(function () {
  "use strict";
  var KEY = "lighthouse-battery-saver";
  var html = document.documentElement;
  var enabled = false;

  function apply(on) {
    enabled = on;
    html.setAttribute("data-battery-saver", on ? "true" : "false");
    try { window.localStorage.setItem(KEY, on ? "1" : "0"); } catch (e) {}
  }

  function init() {
    var val = null;
    try { val = window.localStorage.getItem(KEY); } catch (e) {}
    apply(val === "1");
  }

  function toggle() { apply(!enabled); }

  if (typeof NoyvjBatterySaver !== "undefined") {
    throw new Error("NoyvjBatterySaver already defined");
  }
  window.NoyvjBatterySaver = { init: init, toggle: toggle };

  document.addEventListener("DOMContentLoaded", function () {
    init();
  });
})();
