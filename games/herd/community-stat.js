// F18 (planning/TODO.md): an aggregate community stat pulled from the
// existing ratings backend -- plain JS, not Pyodide/game.py, same
// documented exception as the feedback-prompt script above (a trivial
// GET against an endpoint that already exists, not game state, so no
// Python/pytest coverage is needed). No backend changes: GET
// /ratings/{game_slug} already returns every row for this game,
// feedback-prompt rows included (each has a `response` string like
// "yes" / "no — some comment"). Stays hidden until there's a real
// sample size, rather than ever showing an alarming/uninformative 0%.
//

(function () {
  const RATINGS_API_BASE = "https://noyvjgames.fastapicloud.dev";
  const MIN_SAMPLE_SIZE = 3;
  const statEl = document.getElementById("community-stat-display");

  fetch(`${RATINGS_API_BASE}/ratings/herd`)
    .then((res) => (res.ok ? res.json() : []))
    .then((ratings) => {
      const responses = ratings
        .map((r) => r.response)
        .filter((r) => typeof r === "string" && r.length > 0);
      if (responses.length < MIN_SAMPLE_SIZE) return;
      const yesCount = responses.filter((r) => r.toLowerCase().startsWith("yes")).length;
      const pct = Math.round((yesCount / responses.length) * 100);
      statEl.textContent = `${pct}% of ${responses.length} surveyed players said Herd changed how they think about industrial agriculture & methane emissions.`;
      statEl.hidden = false;
    })
    .catch(() => {
      // Silent failure -- an optional community stat, never worth
      // surfacing an error over.
    });
})();
