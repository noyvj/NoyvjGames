// Z-5c: the "Today's run" button in the Expedition panel. The seed is the UTC date's shared seed; game.py's start_todays_run
// decides what happens (it asks first when a forest would be given up) and its sentence shows in the panel's message line.
(function () {
  if (!window.NoyvjSeed || !window.NoyvjSeed.daily) return;
  window.NoyvjSeed.daily.mountButton("#todays-run-slot", {
    game: "canopy",
    onStart: function (seed) {
      var note = document.getElementById("expedition-seed-message");
      try {
        var fn = window.pyodide.globals.get("start_todays_run");
        fn(seed);
        fn.destroy();
      } catch (e) {
        if (note) note.textContent = "The forest is still starting up. Try again in a moment.";
      }
    }
  });
})();
