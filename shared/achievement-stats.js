/*
 * Shared "% of players who've earned this" stat (planning/TODO.md Z27b, Z-15), built on the
 * cross-game stats backend (GET /stats/games/<game_id>, app/stats.py), which returns per
 * achievement id that at least MIN_BUCKET saves have earned:
 *   {"achievements": {"<id>": {"earned_pct": 12.5, "earned_count": 4}}, "suppressed": bool, ...}
 * An id that is absent has too few earners (or the whole game is `suppressed`): that is never
 * shown as 0%, which would misreport an under-sampled achievement as unearnable.
 *
 *   <script src="../../shared/achievement-stats.js" data-game-id="<slug>"></script>
 *
 * game.py calls window.applyAchievementStats() (through the optional-hook pattern
 * `getattr(window, "applyAchievementStats", None)`) after its achievements panel has rendered;
 * this script never touches Pyodide or game state. It needs each row in #achievements-panel to
 * carry data-achievement-id, and writes plain text into it. Every failure (network, missing
 * panel or row) leaves the row exactly as the game rendered it.
 *
 * Rarity (Z-15): a row whose earned_pct is known gets a Gold / Silver / Bronze label (rarer is
 * better), as text plus a shape plus a border style, never colour alone. The thresholds live in
 * RARITY_THRESHOLDS below (setRarityThresholds() changes them at runtime). No label while the
 * percentage is suppressed.
 *
 * Hidden: a row is hidden when it has data-achievement-hidden="true" or its id was passed to
 * registerCatalog(list) with `hidden: true` (achievements.json entries may carry it). Until it is
 * earned (a class ending in "earned", or data-achievement-earned="true") its description reads
 * "???".
 *
 * window.NoyvjAchievementStats also lets shared/achievement-share.js read the same cached numbers.
 * See planning/SHARED-COMPONENTS.md.
 */
(function () {
  // Loaded twice (a page that includes it and a helper that injects it): keep the first.
  if (window.NoyvjAchievementStats) return;

  const SCRIPT = document.currentScript;
  const GAME_ID = SCRIPT && SCRIPT.dataset.gameId;
  const API_BASE = "https://noyvjgames.fastapicloud.dev";

  // Z-13: the words on the achievements panel (earn rate, rarity names) come from shared/i18n.js when it
  // is on the page and a language other than English is chosen; the English text passed here is the
  // default and the fallback. RARITY_INFO below stays the English reference.
  function tr(key, english, vars) {
    const i18n = window.NoyvjI18n;
    if (i18n) return i18n.t(key, english, vars);
    return vars ? english.replace(/\{(\w+)\}/g, (m, name) => (name in vars ? String(vars[name]) : m)) : english;
  }

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
    if (pct !== null) return tr("ach.earnedBy", "Earned by {pct}% of players.", { pct });
    return tr("ach.notEnoughData", "Not enough data yet on this achievement.");
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
    span.appendChild(document.createTextNode(`${tr("ach." + kind, info.name)} · ${tr("ach." + kind + "Note", info.note)}`));
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

  // A language file that arrives after the panel was drawn: redraw the lines this script added.
  document.addEventListener("noyvj-i18n-change", () => {
    const panel = document.getElementById("achievements-panel");
    if (!panel || !GAME_ID || !panel.querySelector(".achievement-earn-rate")) return;
    panel.querySelectorAll(".achievement-earn-rate, .achievement-rarity").forEach((el) => el.remove());
    window.applyAchievementStats();
  });

  window.NoyvjAchievementStats = {
    RARITY_THRESHOLDS, RARITY_INFO, setRarityThresholds, rarityFor,
    getStats, peek, earnedPct, statTextFor,
    registerCatalog, maskHidden, isHiddenRow, isEarnedRow,
    gameId: GAME_ID || "",
  };
})();
