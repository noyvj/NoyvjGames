// N-2: the first seasonal event end to end. Halloween (about 25 Oct to 1 Nov, ?event-date=2026-10-31 to test):
// finish one run with resources left, earn the "halloween-<year>" badge. game.py calls
// aftermathRunFinished(resourcesLeft) when a real run completes and keeps the badge list in its save.
(function () {
  if (!window.NoyvjSeasonal) return;
  var PREFIX = "aftermath-season:";
  function count(badgeId) { try { return Number(localStorage.getItem(PREFIX + badgeId)) || 0; } catch (e) { return 0; } }
  function py(name, arg) {
    try {
      var fn = window.pyodide && window.pyodide.globals.get(name);
      if (fn) { fn(arg); if (fn.destroy) fn.destroy(); }
    } catch (e) { /* the badge is still kept on this device */ }
  }
  var events = NoyvjSeasonal.init({
    game: "aftermath",
    events: { halloween: { title: "Night of Storms", text: "The storms are loud this week.", task: "Finish one run with resources left", goal: 1, unit: "run" } },
    progress: function (id, ctx) { return count(ctx.badgeId); },
    onGrant: function (badge, all) { py("set_event_badges", JSON.stringify(all)); },
  });
  window.aftermathRunFinished = function (resourcesLeft) {
    if (!(resourcesLeft > 0)) return;
    events.active().forEach(function (e) {
      if (e.earned) return;
      try { localStorage.setItem(PREFIX + e.badgeId, String(count(e.badgeId) + 1)); } catch (x) { /* storage blocked */ }
    });
    events.refresh();
  };
  window.aftermathAdoptBadges = function (json) { try { events.adoptBadges(JSON.parse(json)); } catch (e) { /* ignore */ } };
})();
