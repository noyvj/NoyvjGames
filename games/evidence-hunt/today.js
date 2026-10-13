/* Evidence Hunt, "Today's run" (TODO Z-5c). A button in the Practice panel opens the one practice house everybody gets that UTC day: the
   house is a pure function of the date's shared seed text (gen.py daily_house), so the same text always makes the same house.
   Solving that house counts once for the day in the shared record the hub's Today strip reads (noyvj-daily-v1). A house opened from
   an older day's seed, or an ordinary practice house, never counts. Nothing here changes a seal, a hint or a save, and a missed day
   costs nothing. The engine (game.py) knows only the seed text; which text is today's is decided here, by shared/seed.js.
   app.js tells this file what the engine answered through the "evidence-hunt-view" event. */
(function () {
  "use strict";
  var GAME = "evidence-hunt";

  function seedApi() {
    var S = window.NoyvjSeed;
    return S && S.daily ? S : null;
  }

  function mount() {
    var S = seedApi();
    if (!S || !document.getElementById("practice-today")) return;
    S.daily.mountButton("#practice-today", {
      game: GAME,
      hideStreak: true,   // the pledge bans streaks (FY-60): the shared button must not print "N days in a row"
      onStart: function (text) {
        if (window.evidenceHuntStartPractice) window.evidenceHuntStartPractice({ action: "practice", today: text });
      },
    });
  }

  function onView(e) {
    var S = seedApi();
    var v = e && e.detail;
    if (!S || !v || !v.case) return;
    var text = v.case.today_seed || "";
    try { S.set(text); } catch (err) { /* the info footer's seed line is a courtesy */ }
    if (!v.result || !v.case.practice || !text || !S.daily.isDaily(GAME, text)) return;
    try {
      S.daily.markCompleted(GAME, { text: "Today's house " + v.case.code + ": " + v.result.grade_name });
    } catch (err) { /* the shared record is a courtesy and must never break the page */ }
  }

  document.addEventListener("evidence-hunt-view", onView);
  mount();
})();
