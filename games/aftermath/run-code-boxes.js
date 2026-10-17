// E-4: shared run-code boxes. game.py owns every rule (run_code_fields, start_challenge); this only mounts the boxes.
(function () {
  if (!window.NoyvjRunCode) return;
  var modes = {};
  var describe = { unit: "resources", stats: ["adjusted", "damage taken"], modes: modes };
  function py(name) {
    try { return window.pyodide && window.pyodide.globals.get(name); } catch (e) { return null; }
  }
  function plain(proxy) {
    if (proxy == null) return null;
    var value = proxy.toJs ? proxy.toJs({ dict_converter: Object.fromEntries }) : proxy;
    if (proxy.destroy) proxy.destroy();
    return value;
  }
  function currentRun() {
    var fn = py("run_code_fields");
    if (!fn) return {};
    var out = plain(fn());
    fn.destroy();
    return out || {};
  }
  var copy = NoyvjRunCode.mountCopy("#run-end-code", {
    game: "aftermath", describe: describe, label: "Your run code", buttonLabel: "Copy run code",
    getRun: currentRun,
  });
  var lastRun = JSON.stringify(currentRun());
  NoyvjRunCode.mountPaste("#friends-ghost", {
    game: "aftermath", describe: describe, label: "Paste a friend's run code", buttonLabel: "View run",
    onPlaySeed: function (seed, ghost) {
      var fn = py("start_challenge");
      if (fn) { fn(ghost.code); fn.destroy(); }
    },
  });
  // game.py calls this after every render: it refreshes the copy box and fills in the mode names.
  window.aftermathRunCodeUpdate = function () {
    if (!Object.keys(modes).length) {
      var names = py("run_code_mode_names");
      if (names) { Object.assign(modes, plain(names())); names.destroy(); }
    }
    // Only rebuild the box when the run changed, so its "Copied" note is not wiped by every click.
    var now = JSON.stringify(currentRun());
    if (copy && now !== lastRun) { lastRun = now; copy.update(); }
  };
})();
