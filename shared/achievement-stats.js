/*
 * Shared "% of players who've earned this" stat — planning/TODO.md's Z27b,
 * built on top of Z1's cross-game aggregate-stats backend (app/stats.py,
 * GET /stats/games/<game_id>) which already returns, per achievement id
 * that at least MIN_BUCKET (3) saves have earned:
 *   {"achievements": {"<id>": {"earned_pct": 12.5, "earned_count": 4}, ...},
 *    "suppressed": bool, "save_count": N, ...}
 * An id simply absent from that dict means too few saves have earned it
 * yet (or the whole game is `suppressed` for having too few saves at all)
 * -- never treated as "0%", since that would misreport an under-sampled
 * achievement as unearnable. See app/stats.py's own privacy-rules comment.
 *
 * One script, included unchanged by every game via:
 *   <script src="../../shared/achievement-stats.js" data-game-id="<slug>"></script>
 * (same data-game-id convention as shared/last-played.js and
 * shared/whats-new-banner.js) placed alongside those two, near the end of
 * <body>.
 *
 * Deliberately a SINGLE shared helper rather than 12 copy-pasted
 * window.<gameId>AchievementStats hooks (unlike Grid's C15
 * window.gridCompare, which is one bespoke comparison line per game) --
 * every game's achievements panel already renders potentially a dozen-plus
 * rows in one pass, and every one of those rows needs the same "look up
 * this row's achievement id in the fetched blob, write in a line of text"
 * treatment, generic enough that one shared function can do it for any
 * game's panel. It relies on each achievement row in the DOM carrying a
 * `data-achievement-id` attribute set to that achievement's own id --
 * already added to every game's achievement-card (or, for Le Champ de
 * Mots' tiered earned/next rows, achievement-earned/achievement-next)
 * element alongside this rollout.
 *
 * Same Python-decides/JS-fetches division of labor as every other
 * community-comparison feature on this hub: game.py calls this function
 * (via the same `getattr(window, "applyAchievementStats", None)` optional-
 * hook pattern as Grid's C15) once its own achievements panel has finished
 * rendering into the DOM; this script never touches Pyodide or game state,
 * it only reads the already-rendered panel and writes plain text into it.
 * Fails soft everywhere: a network error, a missing panel, or a missing
 * data-achievement-id row all just leave that row exactly as game.py
 * rendered it, no visible error.
 */
(function () {
  const SCRIPT = document.currentScript;
  const GAME_ID = SCRIPT && SCRIPT.dataset.gameId;
  const API_BASE = "https://noyvjgames.fastapicloud.dev";

  // Per-page in-memory cache -- the achievements panel can be toggled
  // closed/open (or re-rendered on every tick, per game) many times in one
  // session; one real network request per page load is plenty, same TTL
  // shape as Grid's C15 window.gridCompare cache.
  const CACHE_TTL_MS = 60000;
  let cachedAt = 0;
  let cachedData = null;
  let inFlight = null;

  function fetchStats() {
    if (cachedData && Date.now() - cachedAt < CACHE_TTL_MS) {
      return Promise.resolve(cachedData);
    }
    if (inFlight) return inFlight;
    inFlight = fetch(`${API_BASE}/stats/games/${encodeURIComponent(GAME_ID)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        cachedData = data;
        cachedAt = Date.now();
        inFlight = null;
        return data;
      })
      .catch(() => {
        inFlight = null;
        return null;
      });
    return inFlight;
  }

  function statTextFor(data, achievementId) {
    if (!data || data.suppressed) return null; // too few saves for this game at all -- say nothing
    const entry = data.achievements && data.achievements[achievementId];
    if (entry && typeof entry.earned_pct === "number") {
      return `Earned by ${entry.earned_pct}% of players.`;
    }
    return "Not enough data yet on this achievement.";
  }

  window.applyAchievementStats = function () {
    if (!GAME_ID) {
      console.error("achievement-stats.js: missing required data-game-id attribute on its <script> tag");
      return;
    }
    const panel = document.getElementById("achievements-panel");
    if (!panel) return;
    const rows = panel.querySelectorAll("[data-achievement-id]");
    if (!rows.length) return;
    fetchStats().then((data) => {
      rows.forEach((row) => {
        // The panel is fully rebuilt (innerHTML = "") on every render, so
        // rows here are always freshly created -- but guard anyway in case
        // a future caller appends without clearing first.
        if (row.querySelector(".achievement-earn-rate")) return;
        const text = statTextFor(data, row.dataset.achievementId);
        if (!text) return;
        const stat = document.createElement("p");
        stat.className = "achievement-earn-rate";
        stat.textContent = text;
        row.appendChild(stat);
      });
    });
  };
})();
