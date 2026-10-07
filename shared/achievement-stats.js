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
 *
 * Z-15 additions (planning/TODO.md): rarity labels and hidden achievements.
 *   - Rarity: each row whose earned_pct is known gets a Gold / Silver / Bronze label
 *     (rarer = better). The thresholds live in ONE place, RARITY_THRESHOLDS below, and can be
 *     changed at runtime with NoyvjAchievementStats.setRarityThresholds(). The label is text
 *     plus a shape (star, diamond, circle) plus a border style, never colour alone. It is
 *     suppressed exactly when the percentage is: while the whole game is `suppressed`, or an
 *     id is absent from the response (too few players), no label and no guess.
 *   - Hidden: a row is hidden when its element has data-achievement-hidden="true" or its id was
 *     passed to NoyvjAchievementStats.registerCatalog(list) with `hidden: true`
 *     (achievements.json entries may carry "hidden": true). Until the row is earned (its element
 *     has a class ending in "earned", e.g. achievement-card--earned, or
 *     data-achievement-earned="true") its description shows as "???".
 *   - window.NoyvjAchievementStats also lets shared/achievement-share.js (Z-27) read the same
 *     cached numbers. See planning/SHARED-COMPONENTS.md.
 */
(function () {
  // Loaded twice (a page that includes it and a helper that injects it): keep the first.
  if (window.NoyvjAchievementStats) return;

  const SCRIPT = document.currentScript;
  const GAME_ID = SCRIPT && SCRIPT.dataset.gameId;
  const API_BASE = "https://noyvjgames.fastapicloud.dev";

  // ---- Rarity thresholds: THE one place to tune them (Z-15) -------------------------------
  // A label applies when earned_pct is at or below the number, checked rarest first; anything
  // above the last number is Bronze. Percentages come live from the stats endpoint, so as more
  // players arrive the labels move with them; change the numbers here (or call
  // setRarityThresholds) if too many or too few achievements end up Gold.
  const RARITY_THRESHOLDS = { gold: 10, silver: 35 };
  const RARITY_INFO = {
    gold: { glyph: "★", name: "Gold", note: "rare" },        // star
    silver: { glyph: "◆", name: "Silver", note: "uncommon" }, // diamond
    bronze: { glyph: "●", name: "Bronze", note: "common" },   // circle
  };

  function rarityFor(pct) {
    if (typeof pct !== "number" || !isFinite(pct) || pct < 0 || pct > 100) return null;
    if (pct <= RARITY_THRESHOLDS.gold) return "gold";
    if (pct <= RARITY_THRESHOLDS.silver) return "silver";
    return "bronze";
  }

  function setRarityThresholds(next) {
    const gold = next && Number(next.gold);
    const silver = next && Number(next.silver);
    if (!(gold > 0) || !(silver > gold) || silver >= 100) return false;
    RARITY_THRESHOLDS.gold = gold;
    RARITY_THRESHOLDS.silver = silver;
    return true;
  }

  // ---- Fetching, cached per game ------------------------------------------------------------
  // The achievements panel can be toggled closed/open (or re-rendered on every tick, per game)
  // many times in one session; one real network request per page load is plenty, same TTL shape
  // as Grid's C15 window.gridCompare cache.
  const CACHE_TTL_MS = 60000;
  const caches = {}; // gameId -> { at, data, inFlight }

  function slot(gameId) {
    return caches[gameId] || (caches[gameId] = { at: 0, data: null, inFlight: null, loaded: false });
  }

  function getStats(gameId) {
    const c = slot(gameId);
    if (c.loaded && Date.now() - c.at < CACHE_TTL_MS) return Promise.resolve(c.data);
    if (c.inFlight) return c.inFlight;
    c.inFlight = fetch(`${API_BASE}/stats/games/${encodeURIComponent(gameId)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        c.data = data;
        c.at = Date.now();
        c.loaded = true;
        c.inFlight = null;
        return data;
      })
      .catch(() => {
        c.inFlight = null;
        return null;
      });
    return c.inFlight;
  }

  /** The last data fetched for a game, without waiting (undefined until the first answer). */
  function peek(gameId) {
    const c = caches[gameId];
    return c && c.loaded ? c.data : undefined;
  }

  /** earned_pct for one achievement, or null when it must not be shown (suppressed/under-sampled). */
  function earnedPct(data, achievementId) {
    if (!data || data.suppressed) return null;
    const entry = data.achievements && data.achievements[achievementId];
    return entry && typeof entry.earned_pct === "number" && isFinite(entry.earned_pct) ? entry.earned_pct : null;
  }

  function statTextFor(data, achievementId) {
    if (!data || data.suppressed) return null; // too few saves for this game at all -- say nothing
    const pct = earnedPct(data, achievementId);
    if (pct !== null) return `Earned by ${pct}% of players.`;
    return "Not enough data yet on this achievement.";
  }

  // ---- Hidden achievements (Z-15) -------------------------------------------------------------
  const hiddenIds = new Set();

  /** Remember which ids are hidden. `list` is an achievements.json array (or {achievements: [...]}). */
  function registerCatalog(list) {
    const items = Array.isArray(list) ? list : list && Array.isArray(list.achievements) ? list.achievements : [];
    items.forEach((a) => {
      if (a && typeof a.id === "string") {
        if (a.hidden === true) hiddenIds.add(a.id); else hiddenIds.delete(a.id);
      }
    });
  }

  function isHiddenRow(row) {
    return row.dataset.achievementHidden === "true" || hiddenIds.has(row.dataset.achievementId);
  }

  function isEarnedRow(row) {
    if (row.dataset.achievementEarned === "true") return true;
    for (const c of row.classList) if (/earned$/.test(c)) return true;
    return false;
  }

  function descriptionOf(row) {
    return row.querySelector(".achievement-card-description, [data-achievement-description]");
  }

  /** Shows "???" for the description of every hidden, not-yet-earned row under `root`. */
  function maskHidden(root) {
    (root || document).querySelectorAll("[data-achievement-id]").forEach((row) => {
      const desc = descriptionOf(row);
      if (!desc) return;
      if (isHiddenRow(row) && !isEarnedRow(row)) {
        if (desc.dataset.realDescription === undefined) desc.dataset.realDescription = desc.textContent;
        desc.textContent = "???";
        row.setAttribute("data-achievement-masked", "true");
      } else if (desc.dataset.realDescription !== undefined) {
        desc.textContent = desc.dataset.realDescription;
        delete desc.dataset.realDescription;
        row.removeAttribute("data-achievement-masked");
      }
    });
  }

  // ---- Rendering ------------------------------------------------------------------------------
  const STYLE_ID = "noyvj-achievement-rarity-style";
  const CSS = `
.achievement-rarity{display:inline-block;margin:.3rem 0 0;padding:.1rem .5rem;border-radius:6px;font:600 .72rem/1.5 system-ui,sans-serif;font-style:normal;opacity:1;background:#252a40;color:#f2f3f8;border-color:var(--ar-edge,#aaa)}
.achievement-rarity[data-rarity="gold"]{--ar-edge:#e8c84a;border:3px double var(--ar-edge)}
.achievement-rarity[data-rarity="silver"]{--ar-edge:#c4cad8;border:2px dashed var(--ar-edge)}
.achievement-rarity[data-rarity="bronze"]{--ar-edge:#d99a62;border:1px dotted var(--ar-edge)}
html[data-theme="light"] .achievement-rarity{background:#fff;color:#1b2033}
html[data-theme="light"] .achievement-rarity[data-rarity="gold"]{--ar-edge:#8a6a00}
html[data-theme="light"] .achievement-rarity[data-rarity="silver"]{--ar-edge:#566078}
html[data-theme="light"] .achievement-rarity[data-rarity="bronze"]{--ar-edge:#8a4e1c}
@media (prefers-color-scheme:light){
:root:not([data-theme]) .achievement-rarity{background:#fff;color:#1b2033}
:root:not([data-theme]) .achievement-rarity[data-rarity="gold"]{--ar-edge:#8a6a00}
:root:not([data-theme]) .achievement-rarity[data-rarity="silver"]{--ar-edge:#566078}
:root:not([data-theme]) .achievement-rarity[data-rarity="bronze"]{--ar-edge:#8a4e1c}}
@media print{.achievement-rarity{background:#fff;color:#000}}
`;
  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const st = document.createElement("style");
    st.id = STYLE_ID;
    st.textContent = CSS;
    (document.head || document.documentElement).appendChild(st);
  }

  function rarityLabel(kind) {
    const info = RARITY_INFO[kind];
    const span = document.createElement("p");
    span.className = "achievement-rarity";
    span.dataset.rarity = kind;
    span.setAttribute("data-testid", "achievement-rarity");
    const glyph = document.createElement("span");
    glyph.setAttribute("aria-hidden", "true");
    glyph.textContent = info.glyph + " ";
    span.appendChild(glyph);
    span.appendChild(document.createTextNode(`${info.name} · ${info.note}`));
    return span;
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
    // data-testid hooks for automated tests (convention in planning/game-template.md, Z-30).
    // The games render the panel and its rows; this adds the hooks without touching their code.
    if (!panel.hasAttribute("data-testid")) panel.setAttribute("data-testid", "achievements-panel");
    rows.forEach((row) => {
      if (!row.hasAttribute("data-testid")) row.setAttribute("data-testid", `achievement-row-${row.dataset.achievementId}`);
    });
    maskHidden(panel);   // synchronously, so a hidden description is never painted
    getStats(GAME_ID).then((data) => {
      rows.forEach((row) => {
        // The panel is fully rebuilt (innerHTML = "") on every render, so
        // rows here are always freshly created -- but guard anyway in case
        // a future caller appends without clearing first.
        if (row.querySelector(".achievement-earn-rate")) return;
        const text = statTextFor(data, row.dataset.achievementId);
        if (!text) return;
        const stat = document.createElement("p");
        stat.className = "achievement-earn-rate";
        stat.setAttribute("data-testid", "achievement-earn-rate");
        stat.textContent = text;
        row.appendChild(stat);
        const kind = rarityFor(earnedPct(data, row.dataset.achievementId));
        if (kind) {
          injectStyle();
          row.appendChild(rarityLabel(kind));
        }
      });
    });
  };

  window.NoyvjAchievementStats = {
    RARITY_THRESHOLDS, RARITY_INFO, setRarityThresholds, rarityFor,
    getStats, peek, earnedPct, statTextFor,
    registerCatalog, maskHidden, isHiddenRow, isEarnedRow,
    gameId: GAME_ID || "",
  };
})();
