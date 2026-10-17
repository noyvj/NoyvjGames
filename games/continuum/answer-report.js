// Z16 audit: the info-panel report button's actual network call, the
// exact same split and endpoint Le Champ de Mots' report button already
// uses (see that game's index.html and its CLAUDE.md Milestone 9 build
// note) — Python (game.py) decides what to send, this owns the fetch().
// Fire-and-forget: a dropped report is a "let a human know" nicety, not
// core gameplay, so failures are swallowed rather than surfaced.
window.submitAnswerReport = function (jsonPayload) {
  fetch("https://noyvjgames.fastapicloud.dev/answer-reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: jsonPayload,
  }).catch(function () {});
};
