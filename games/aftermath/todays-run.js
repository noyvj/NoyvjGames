// Z-5c: the "Today's run" button. The seed is the UTC date's shared seed; game.py's start_todays_run decides whether a run
// can start now (only between runs) and says so. Finishing the run records it (game.py).
(function () {
  if (!window.NoyvjSeed || !window.NoyvjSeed.daily) return;
  window.NoyvjSeed.daily.mountButton("#todays-run-slot", {
    game: "aftermath",
    onStart: function (seed) {
      var note = document.getElementById("todays-run-note");
      try {
        var fn = window.pyodide.globals.get("start_todays_run");
        note.textContent = fn(seed);
        fn.destroy();
      } catch (e) {
        note.textContent = "The game is still starting up. Try again in a moment.";
      }
    }
  });
})();
