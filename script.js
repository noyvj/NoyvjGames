window.__hubScriptRan = true; // read by the compat check in index.html (Y-21)
const RATINGS_API_BASE = "https://noyvjgames.fastapicloud.dev";
// HUB_AUTH_TOKEN_KEY comes from shared/hub-auth.js (loaded before this
// file — see index.html), the same key shared/save-widget.js uses, so both
// files can't drift out of sync on it. Shared across
// every page on the site (localStorage is keyed by origin, not path) —
// this is how a game page's save widget knows whether the player is
// signed in without its own account UI.
const AUTH_USERNAME_KEY = "hub_account_username";

// Small localStorage helpers: storage can throw (private windows, blocked site data), and a throw
// at the top level of this file would stop everything below it from ever running.
function lsGet(key) {
  try { return localStorage.getItem(key); } catch (err) { return null; }
}
function lsSet(key, value) {
  try { localStorage.setItem(key, value); } catch (err) { /* convenience only */ }
}
function lsRemove(key) {
  try { localStorage.removeItem(key); } catch (err) { /* convenience only */ }
}
// shared/hub-auth.js reads localStorage directly; this twin cannot throw.
function signedInToken() {
  return lsGet(HUB_AUTH_TOKEN_KEY);
}
function authHeaders() {
  const token = signedInToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
// Y12: the backend doesn't expose an account-created date yet, so "member
// since" is only known for accounts created on this device (recorded at
// signup); it's simply omitted otherwise rather than guessed.
const AUTH_SINCE_KEY = "hub_account_since";

// R1-L13: the star row is a WAI-ARIA radiogroup with a roving tabindex --
// one Tab stop for the whole row, Left/Right/Up/Down (Home/End) move and
// select, Space/Enter on a focused star selects it (native button click).
function syncStarA11y(ratingWidget) {
  const value = Number(ratingWidget.dataset.rating) || 0;
  const stars = Array.from(ratingWidget.querySelectorAll(".star"));
  stars.forEach((s, i) => {
    const n = Number(s.dataset.value);
    s.setAttribute("role", "radio");
    s.setAttribute("aria-checked", String(n === value));
    s.setAttribute("aria-label", `${n} star${n === 1 ? "" : "s"}`);
    s.tabIndex = n === value || (value === 0 && i === 0) ? 0 : -1;
    s.classList.toggle("selected", n <= value);
  });
}

function bindStarRating(ratingWidget) {
  const stars = Array.from(ratingWidget.querySelectorAll(".star"));
  ratingWidget.setAttribute("role", "radiogroup");
  if (!ratingWidget.hasAttribute("aria-label")) ratingWidget.setAttribute("aria-label", "Your rating");
  const choose = (value, focus) => {
    ratingWidget.dataset.rating = String(value);
    syncStarA11y(ratingWidget);
    if (focus) stars[value - 1].focus();
  };
  stars.forEach((star) => {
    star.addEventListener("click", () => choose(Number(star.dataset.value), false));
    star.addEventListener("keydown", (e) => {
      const cur = Number(star.dataset.value);
      let next = null;
      if (e.key === "ArrowRight" || e.key === "ArrowUp") next = Math.min(stars.length, cur + 1);
      else if (e.key === "ArrowLeft" || e.key === "ArrowDown") next = Math.max(1, cur - 1);
      else if (e.key === "Home") next = 1;
      else if (e.key === "End") next = stars.length;
      if (next === null) return;
      e.preventDefault();
      choose(next, true);
    });
  });
  syncStarA11y(ratingWidget);
}

function resetStarRating(ratingWidget) {
  ratingWidget.dataset.rating = "0";
  syncStarA11y(ratingWidget);
}

// Y6: a five-star glyph row filled to the average's fraction (a
// hard-stop gradient clipped to the text), sitting beside the numeric
// text rather than replacing it -- the number stays the source of truth
// for screen readers and anyone who can't tell partial fills apart.
function setRatingDisplay(widget, average, count) {
  const summary = widget.querySelector(".ratings-summary");
  const card = widget.closest(".title-card");
  summary.classList.remove("is-loading");
  summary.removeAttribute("aria-busy");
  if (!count) {
    summary.textContent = "No reviews yet — be the first.";
    if (card) { card.dataset.avg = "0"; card.dataset.reviewCount = "0"; }
    return;
  }
  if (card) { card.dataset.avg = String(average); card.dataset.reviewCount = String(count); }
  summary.textContent = "";
  const stars = document.createElement("span");
  stars.className = "avg-stars";
  stars.setAttribute("aria-hidden", "true");
  stars.style.setProperty("--fill", `${(average / 5) * 100}%`);
  stars.textContent = "\u2605\u2605\u2605\u2605\u2605";
  summary.appendChild(stars);
  summary.appendChild(
    document.createTextNode(`${average.toFixed(1)} ★ average (${count} review${count === 1 ? "" : "s"})`)
  );
}

// The old per-game listing (GET /ratings/{slug}) also returns per-game text-feedback-prompt rows
// (stars: null, response: "...") alongside this widget's own star submissions -- both share the
// same table. Only star rows belong in a star average. Used only by the fallback below.
function renderSummary(widget, ratings) {
  const starRatings = ratings.filter((r) => typeof r.stars === "number");
  const count = starRatings.length;
  const average = count ? starRatings.reduce((sum, r) => sum + r.stars, 0) / count : 0;
  setRatingDisplay(widget, average, count);
}

function showRatingsUnavailable(widget) {
  const summary = widget.querySelector(".ratings-summary");
  summary.classList.remove("is-loading");
  summary.removeAttribute("aria-busy");
  summary.textContent = "Reviews unavailable right now.";
}

// Y-31: ONE small request (GET /ratings-summary: average, count and distribution per game) replaces
// the one-download-of-every-rating-row-per-game the hub used to make on load. Passing fresh=true
// (after the visitor's own submission) skips the browser's short cache so their star shows at once.
// The review boxes still POST to /ratings exactly as before; the hub never listed comments.
// Until the backend that serves the summary is deployed it answers 404, and then each card falls back
// to its own listing so the stars never go missing during a rollout.
let ratingsSummaryPromise = null;
async function fetchRatingsSummary(fresh) {
  if (!fresh && ratingsSummaryPromise) return ratingsSummaryPromise;
  const request = (async () => {
    const response = await fetch(`${RATINGS_API_BASE}/ratings-summary`, fresh ? { cache: "reload" } : undefined);
    if (response.status === 404) return null;           // older backend: no summary route yet
    if (!response.ok) throw new Error(`status ${response.status}`);
    const body = await response.json();
    return body && typeof body.games === "object" && body.games ? body.games : {};
  })();
  ratingsSummaryPromise = request;
  request.catch(() => { if (ratingsSummaryPromise === request) ratingsSummaryPromise = null; });
  return request;
}

async function loadRatingsLegacy(widget) {
  const slug = widget.dataset.gameSlug;
  try {
    const response = await fetch(`${RATINGS_API_BASE}/ratings/${slug}`);
    if (!response.ok) throw new Error(`status ${response.status}`);
    renderSummary(widget, await response.json());
  } catch (err) {
    console.error(`loadRatings(${slug}) failed:`, err);
    showRatingsUnavailable(widget);
  }
}

// Loads the stars for the given widgets (all of them on page load, or just the one just rated).
async function loadRatings(widgets, fresh) {
  const list = Array.isArray(widgets) ? widgets : [widgets];
  let games;
  try {
    games = await fetchRatingsSummary(Boolean(fresh));
  } catch (err) {
    // Logged so "reviews unavailable" is debuggable from the browser console at all -- the only
    // place this context is ever visible for a personal-site-scale project with no error tracking.
    console.error("loadRatings failed:", err);
    list.forEach(showRatingsUnavailable);
    scheduleSort();
    return;
  }
  if (games === null) {
    await Promise.all(list.map(loadRatingsLegacy));
  } else {
    list.forEach((widget) => {
      const entry = games[widget.dataset.gameSlug];
      const count = entry && Number(entry.count) > 0 ? Number(entry.count) : 0;
      setRatingDisplay(widget, count ? Number(entry.average) || 0 : 0, count);
    });
  }
  // Ratings arriving (or a new submission) can change a rating-sorted order.
  scheduleSort();
}

// All the cards' ratings arrive together; re-sorting (a full re-append of the grid) more than once
// for that burst is wasted layout work.
let sortScheduled = false;
function scheduleSort() {
  if (sortScheduled) return;
  sortScheduled = true;
  setTimeout(() => {
    sortScheduled = false;
    applySort();
  }, 50);
}

async function submitRating(widget) {
  const slug = widget.dataset.gameSlug;
  const stars = Number(widget.querySelector(".star-rating").dataset.rating);
  const comment = widget.querySelector(".comment-box").value.trim();
  const submitButton = widget.querySelector(".comment-submit");

  if (!stars) return;

  submitButton.disabled = true;
  submitButton.textContent = "Submitting...";
  try {
    const response = await fetch(`${RATINGS_API_BASE}/ratings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ game_slug: slug, stars, comment: comment || null }),
    });
    if (!response.ok) throw new Error(`status ${response.status}`);
    widget.querySelector(".comment-box").value = "";
    submitButton.textContent = "Submitted — thanks!";
    await loadRatings(widget, true);
  } catch (err) {
    submitButton.textContent = "Submit failed — try again";
    submitButton.disabled = false;
  }
}

const reviewWidgets = Array.from(document.querySelectorAll(".review-widget"));
reviewWidgets.forEach((widget) => {
  bindStarRating(widget.querySelector(".star-rating"));
  widget.querySelector(".comment-submit").addEventListener("click", () => submitRating(widget));
});
loadRatings(reviewWidgets, false);

// --- "Last updated" badge per title card (L7) ---
// From game-last-updated.json, regenerated from git history by scripts/generate-last-updated.py (see its docstring).
async function loadLastUpdatedBadges() {
  let dates;
  try {
    const res = await fetch("game-last-updated.json");
    if (!res.ok) throw new Error(`status ${res.status}`);
    dates = await res.json();
  } catch (err) {
    // Non-critical — the rest of the hub (reviews, filters, accounts)
    // works fine without this badge, so fail silently past a console line.
    console.error("loadLastUpdatedBadges failed:", err);
    return;
  }
  document.querySelectorAll(".title-card").forEach((card) => {
    const slug = card.querySelector(".review-widget")?.dataset.gameSlug;
    const date = slug && dates[slug];
    if (!date) return;
    const tagsRow = card.querySelector(".title-card-tags");
    const badge = document.createElement("p");
    badge.className = "title-card-updated";
    badge.textContent = `Updated ${date}`;
    if (tagsRow) tagsRow.insertAdjacentElement("afterend", badge);
    else card.querySelector(".title-card-link")?.appendChild(badge);
  });
}

loadLastUpdatedBadges();

// --- "Last played" badge per title card (Z2/Z14) ---
// Read from localStorage["last-played:<slug>"] (stamped by shared/last-played.js), so it is per-browser and absent
// for a game never opened here.
function relativeLastPlayedText(timestampMs) {
  const diffMs = Date.now() - timestampMs;
  const diffMinutes = Math.floor(diffMs / 60000);
  if (diffMinutes < 1) return "Last played just now";
  if (diffMinutes < 60) return `Last played ${diffMinutes} minute${diffMinutes === 1 ? "" : "s"} ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `Last played ${diffHours} hour${diffHours === 1 ? "" : "s"} ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return "Last played yesterday";
  if (diffDays < 30) return `Last played ${diffDays} days ago`;
  const diffMonths = Math.floor(diffDays / 30);
  if (diffMonths < 12) return `Last played ${diffMonths} month${diffMonths === 1 ? "" : "s"} ago`;
  const diffYears = Math.floor(diffMonths / 12);
  return `Last played ${diffYears} year${diffYears === 1 ? "" : "s"} ago`;
}

function loadLastPlayedBadges() {
  document.querySelectorAll(".title-card").forEach((card) => {
    const slug = card.querySelector(".review-widget")?.dataset.gameSlug;
    if (!slug) return;
    let raw;
    try {
      raw = localStorage.getItem("last-played:" + slug);
    } catch (err) {
      // Private-browsing mode or storage disabled -- degrade silently,
      // same as loadLastUpdatedBadges()'s own fetch-failure handling.
      return;
    }
    const timestampMs = raw && Number(raw);
    if (!timestampMs) return;
    // Inserted right after the tags row, same anchor loadLastUpdatedBadges()
    // itself uses -- NOT chained off .title-card-updated, since that badge
    // is filled in asynchronously (after a fetch) and might not exist yet
    // when this runs; anchoring both badges independently off the same
    // synchronous element avoids a render-order race between the two.
    const tagsRow = card.querySelector(".title-card-tags");
    const badge = document.createElement("p");
    badge.className = "title-card-last-played";
    badge.textContent = relativeLastPlayedText(timestampMs);
    if (tagsRow) tagsRow.insertAdjacentElement("afterend", badge);
    else card.querySelector(".title-card-link")?.appendChild(badge);
  });
}

loadLastPlayedBadges();

// --- Hub lobby search/tag filter (L11/L12) ---
// Tags are a space-separated `data-tags` attribute on each `.title-card`, also shown as pills. Two axes:
// subject ("climate", "civilization", "economy", "language-learning", "space") and depth ("quick" for the
// single-mechanic climate games, "deep-systems" for SOL, Continuum, Trade Empire and Le Champ de Mots).
// Search and tag filter combine (AND) in applyGameFilter().
const gameSearchInput = document.getElementById("game-search-input");
const gameTagFilter = document.getElementById("game-tag-filter");
const gameSortSelect = document.getElementById("game-sort");
const gameSortStatus = document.getElementById("game-sort-status");
const gameFilterEmpty = document.getElementById("game-filter-empty");
const gameGrid = document.getElementById("game-grid");
const allTitleCards = Array.from(document.querySelectorAll(".title-card"));

// Y-26: "reduce data". The explicit choice in settings.html wins ("1" reduce, "0" never); with no
// choice the browser's own Data Saver flag (navigator.connection.saveData) decides. While it is on the
// hub skips its community-statistics requests (the highlights line and the sort-leader captions).
// Things the visitor asks for -- ratings, saves, picking "Most saved" -- still load.
const REDUCE_DATA_KEY = "hub_reduce_data";
function hubReduceData() {
  const choice = lsGet(REDUCE_DATA_KEY);
  if (choice === "1") return true;
  if (choice === "0") return false;
  const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  return Boolean(conn && conn.saveData);
}

// U13: collapsible title cards. Compact by default (picture, name, rating
// stars and summary only); "Show details" on a card, or the filter bar's
// toggle for all of them, brings back the blurb, tags, badges, comment box
// and share button. The choice is remembered on this device. The card's
// link, name and picture still open the game in either mode.
const CARDS_COMPACT_KEY = "hub_cards_compact";
let cardsCompact = lsGet(CARDS_COMPACT_KEY) !== "0";

function refreshCardDetailToggles() {
  if (gameGrid) gameGrid.classList.toggle("game-grid--compact", cardsCompact);
  allTitleCards.forEach((card) => {
    const button = card.querySelector(".title-card-expand");
    if (!button) return;
    const expanded = !cardsCompact || card.classList.contains("is-expanded");
    button.textContent = expanded && cardsCompact ? "Hide details" : "Show details";
    button.setAttribute("aria-expanded", String(expanded));
    button.hidden = !cardsCompact;
  });
  const globalToggle = document.getElementById("cards-compact-toggle");
  if (globalToggle) {
    globalToggle.textContent = cardsCompact ? "Show full cards" : "Compact cards";
    globalToggle.setAttribute("aria-pressed", String(cardsCompact));
  }
}

allTitleCards.forEach((card) => {
  const widget = card.querySelector(".review-widget");
  if (!widget) return;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "title-card-expand";
  button.addEventListener("click", () => {
    card.classList.toggle("is-expanded");
    refreshCardDetailToggles();
  });
  card.insertBefore(button, widget);
  // Y-9 / Y-18: the per-card offline download and collections controls (hub-offline.js,
  // hub-collections.js) live in this row, shown with the other card details.
  if (!card.querySelector(".title-card-actions")) {
    const actions = document.createElement("div");
    actions.className = "title-card-actions";
    card.insertBefore(actions, button);
  }
});

const filterBarForCards = document.getElementById("game-filter-bar");
if (filterBarForCards) {
  const globalToggle = document.createElement("button");
  globalToggle.type = "button";
  globalToggle.id = "cards-compact-toggle";
  globalToggle.className = "cards-compact-toggle";
  globalToggle.addEventListener("click", () => {
    cardsCompact = !cardsCompact;
    lsSet(CARDS_COMPACT_KEY, cardsCompact ? "1" : "0");
    allTitleCards.forEach((card) => card.classList.remove("is-expanded"));
    refreshCardDetailToggles();
  });
  filterBarForCards.appendChild(globalToggle);
}
refreshCardDetailToggles();

// Y4: live game count, derived from the cards actually on the page so it
// can never drift from what a visitor can see.
const hubGameCount = document.getElementById("hub-game-count");
if (hubGameCount) hubGameCount.textContent = `${allTitleCards.length} games and counting`;

// Each card's own searchable text: only its link block (name, blurb, tags,
// updated badge) -- not the review widget, share button or notes, which
// would make "share" or "review" match every card.
function cardBaseText(card) {
  const link = card.querySelector(".title-card-link");
  return (link ? link.textContent : card.textContent).toLowerCase();
}

// Y19: deeper search. `extraSearchText` maps card -> lowercase text drawn
// from the update history (BCM114 dev log entries whose "Game:" line names
// the game) and recent commit subjects (game-roadmap-data.json). Loaded
// lazily the first time someone actually searches, so ordinary visits pay
// nothing for it. A match found only there is flagged on the card.
const extraSearchText = new Map();
let extendedSearchRequested = false;

function cardSlug(card) {
  return card.querySelector(".review-widget")?.dataset.gameSlug;
}
function cardName(card) {
  return (card.querySelector(".title-card-name")?.textContent || "").trim().toLowerCase();
}

async function loadExtendedSearchIndex() {
  if (extendedSearchRequested) return;
  extendedSearchRequested = true;
  const addExtra = (card, text) =>
    extraSearchText.set(card, ((extraSearchText.get(card) || "") + " " + text).toLowerCase());
  try {
    const [logRes, roadmapRes] = await Promise.all([
      fetch("BCM114-DEV-LOG.md").catch(() => null),
      fetch("game-roadmap-data.json").catch(() => null),
    ]);
    if (logRes && logRes.ok) {
      const text = await logRes.text();
      text.split(/\n(?=### \d{4}-\d{2}-\d{2})/).forEach((block) => {
        const gameMatch = block.match(/\*\*Game:\*\*\s*(.+)/);
        const didMatch = block.match(/\*\*Did:\*\*\s*([\s\S]*?)(?:\n\*\*|\n---|\n##|$)/);
        if (!gameMatch || !didMatch) return;
        const tokens = gameMatch[1].toLowerCase().split(/[,;/&()—]|\band\b/).map((t) => t.trim()).filter(Boolean);
        allTitleCards.forEach((card) => {
          const name = cardName(card);
          if (tokens.some((t) => t === name || (t.length > 3 && (name.includes(t) || t.includes(name))))) {
            addExtra(card, didMatch[1].replace(/\s+/g, " "));
          }
        });
      });
    }
    if (roadmapRes && roadmapRes.ok) {
      const data = await roadmapRes.json();
      allTitleCards.forEach((card) => {
        const entry = data.games && data.games[cardSlug(card)];
        if (entry && entry.recent_commits) addExtra(card, entry.recent_commits.join(" "));
      });
    }
  } catch (err) {
    console.error("loadExtendedSearchIndex failed:", err);
  }
  applyGameFilter();
}

// Every card gets a small "matched in ..." note (outside the link, so it
// isn't itself searchable), and a sort note (used by "Most saved").
allTitleCards.forEach((card) => {
  const matchNote = document.createElement("p");
  matchNote.className = "title-card-match-note";
  matchNote.hidden = true;
  matchNote.textContent = "Matched in the update history";
  const sortNote = document.createElement("p");
  sortNote.className = "title-card-sortnote";
  sortNote.hidden = true;
  const link = card.querySelector(".title-card-link");
  if (link) link.insertAdjacentElement("afterend", sortNote);
  if (link) link.insertAdjacentElement("afterend", matchNote);

  // Y20: per-card "Share" button, distinct from the review widget. Copies
  // an absolute link to this game (works from any host/subpath).
  const share = document.createElement("button");
  share.type = "button";
  share.className = "account-link-button title-card-share";
  share.textContent = "Share this game";
  share.addEventListener("click", async () => {
    const url = new URL(link.getAttribute("href"), location.href).href;
    let done = false;
    try {
      await navigator.clipboard.writeText(url);
      done = true;
    } catch (err) {
      // Clipboard blocked (insecure context / permissions): fall back to a prompt.
      window.prompt("Copy this link:", url);
    }
    if (done) {
      share.textContent = "Link copied!";
      setTimeout(() => (share.textContent = "Share this game"), 1500);
    }
  });
  card.querySelector(".review-widget")?.insertAdjacentElement("beforebegin", share);
});

// Y2: remember the last search/tag/sort across reloads.
const FILTER_QUERY_KEY = "hub_filter_query";
const FILTER_TAG_KEY = "hub_filter_tag";
const SORT_MODE_KEY = "hub_sort_mode";
const FILTER_SESSION_KEY = "hub_filter_session";

// Y-22: per-card estimated session length ("short" / "medium" / "long"),
// read from the hand-written game-sessions.json (see its _readme). null until
// the file has loaded (or if it cannot), in which case the session filter
// is ignored rather than hiding every card.
let gameSessions = null;
const gameSessionFilter = document.getElementById("game-session-filter");

function cardSession(card) {
  return (gameSessions && gameSessions.games[cardSlug(card)]) || "";
}

function applyGameFilter() {
  const query = gameSearchInput.value.trim().toLowerCase();
  const tag = gameTagFilter.value;
  const sessionWanted = gameSessions && gameSessionFilter ? gameSessionFilter.value : "";
  const collectionSelect = document.getElementById("game-collection-filter");
  const collectionWanted = collectionSelect ? collectionSelect.value : "";
  let visibleCount = 0;
  allTitleCards.forEach((card) => {
    const tags = (card.dataset.tags || "").split(/\s+/);
    const matchesTag = !tag || tags.includes(tag);
    const inBase = !query || cardBaseText(card).includes(query);
    const inExtra = !!query && !inBase && (extraSearchText.get(card) || "").includes(query);
    const matchesSession = !sessionWanted || cardSession(card) === sessionWanted;
    // Y-18: personal collections (hub-collections.js); no collection chosen = every game.
    const matchesCollection = !collectionWanted || (window.HubCollections ? window.HubCollections.includes(collectionWanted, cardSlug(card)) : true);
    const visible = matchesTag && matchesSession && matchesCollection && (inBase || inExtra);
    card.hidden = !visible;
    const note = card.querySelector(".title-card-match-note");
    if (note) note.hidden = !(visible && inExtra);
    if (visible) visibleCount += 1;
  });
  gameFilterEmpty.textContent = collectionWanted
    ? "No games in this collection match your search and filters. Add games from a card's Show details."
    : "No games match your search.";
  gameFilterEmpty.hidden = visibleCount > 0;
  if (calmFilter) calmFilter.refresh();
}

// QI-51: while half-asleep mode is on, the grid shows only the calm games (shared/calm-mode.js; the
// slug list is its CALM_GAMES). The filter runs after the search/tag/session filters above so they
// never un-hide a card it hid.
let calmFilter = null;
function setUpCalmFilter() {
  if (!window.NoyvjCalm || !window.NoyvjCalm.CALM_GAMES) return;
  const calm = new Set(window.NoyvjCalm.CALM_GAMES);
  allTitleCards.forEach((card) => {
    if (calm.has(cardSlug(card))) card.dataset.calm = "true";
  });
  calmFilter = window.NoyvjCalm.filter(document.getElementById("game-grid"), { itemSelector: ".title-card" });
  // Switching calm mode off must not un-hide a card the search/tag/session filter hid: recompute everything.
  window.NoyvjCalm.onChange(() => applyGameFilter());
}

// --- Y21: sort modes (default / highest rated / most saved) ---
// Rating average comes from each card's own review widget
// (data-avg, set by setRatingDisplay). Save count is the more honest
// popularity signal while reviews skew toward test/friend accounts; it's
// read through loadSaveCounts(), kept deliberately isolated so it can be
// repointed without touching the sort code. It reads the public
// GET /stats/achievements, whose per-game save_count the backend withholds
// (null) until a game has enough saves to be anonymous, so a game below that
// threshold counts as 0 here. (The older GET /admin/stats source is
// owner-only now, so it could not work for visitors.) Returns null (graceful
// fallback to default order + a status line) if the endpoint is unreachable.
let saveCountsPromise = null;
function loadSaveCounts() {
  if (!saveCountsPromise) {
    saveCountsPromise = fetch(`${RATINGS_API_BASE}/stats/achievements`)
      .then((res) => {
        if (!res.ok) throw new Error(`status ${res.status}`);
        return res.json();
      })
      .then((body) => {
        const games = body && typeof body.games === "object" && body.games ? body.games : null;
        if (!games) return null;
        const counts = {};
        Object.entries(games).forEach(([slug, info]) => {
          counts[slug] = info && typeof info.save_count === "number" ? info.save_count : 0;
        });
        return counts;
      })
      .catch((err) => {
        console.error("loadSaveCounts failed:", err);
        return null;
      });
  }
  return saveCountsPromise;
}

// Y-23: a caption under the sort dropdown naming each sort's current leader. "Top rated" comes from
// the ratings already on the cards; "Most saved" from the same public save counts the sort uses
// (and, being a community statistic, is skipped while reduce-data is on). There is no per-game
// "most played" statistic anywhere on the backend, so none is shown rather than inventing one.
const gameSortLeaders = document.getElementById("game-sort-leaders");
function renderSortLeaders() {
  if (!gameSortLeaders) return;
  const parts = [];
  const rated = allTitleCards
    .filter((card) => Number(card.dataset.reviewCount || 0) > 0)
    .sort((a, b) =>
      Number(b.dataset.avg || 0) - Number(a.dataset.avg || 0) ||
      Number(b.dataset.reviewCount || 0) - Number(a.dataset.reviewCount || 0));
  if (rated.length) {
    const top = rated[0];
    parts.push(`Top rated: ${cardDisplayName(top)} (${Number(top.dataset.avg).toFixed(1)}\u2605)`);
  }
  if (saveCounts) {
    const saved = allTitleCards
      .map((card) => ({ card, n: Number(saveCounts[cardSlug(card)] || 0) }))
      .filter((x) => x.n > 0)
      .sort((a, b) => b.n - a.n);
    if (saved.length) parts.push(`Most saved: ${cardDisplayName(saved[0].card)} (${saved[0].n} save${saved[0].n === 1 ? "" : "s"})`);
  }
  gameSortLeaders.textContent = parts.join("  \u00b7  ");
  gameSortLeaders.hidden = parts.length === 0;
}
function cardDisplayName(card) {
  return (card.querySelector(".title-card-name")?.textContent || cardSlug(card) || "").trim();
}

let saveCounts = null; // null = not loaded / unavailable
async function applySort() {
  if (!gameSortSelect) return;
  const mode = gameSortSelect.value;
  let ordered = allTitleCards.slice();
  gameSortStatus.hidden = true;
  allTitleCards.forEach((card) => {
    const note = card.querySelector(".title-card-sortnote");
    if (note) note.hidden = true;
  });
  if (mode === "rating") {
    ordered.sort(
      (a, b) =>
        Number(b.dataset.avg || 0) - Number(a.dataset.avg || 0) ||
        Number(b.dataset.reviewCount || 0) - Number(a.dataset.reviewCount || 0)
    );
  } else if (mode === "saves") {
    if (!saveCounts) saveCounts = await loadSaveCounts();
    if (gameSortSelect.value !== "saves") return; // changed while loading
    if (!saveCounts) {
      gameSortStatus.textContent = "Save counts are unavailable right now — showing the default order.";
      gameSortStatus.hidden = false;
    } else {
      const count = (card) => Number(saveCounts[cardSlug(card)] || 0);
      ordered.sort((a, b) => count(b) - count(a));
      ordered.forEach((card) => {
        const note = card.querySelector(".title-card-sortnote");
        if (note) {
          const n = count(card);
          note.textContent = `${n} save${n === 1 ? "" : "s"}`;
          note.hidden = false;
        }
      });
    }
  }
  gameGrid.append(...ordered);
  renderSortLeaders();
}

// Community statistic: skipped while reduce-data is on (picking "Most saved" still loads it).
if (!hubReduceData()) {
  loadSaveCounts().then((counts) => {
    if (counts && !saveCounts) saveCounts = counts;
    renderSortLeaders();
  });
}

if (gameSearchInput && gameTagFilter) {
  const savedQuery = lsGet(FILTER_QUERY_KEY);
  const savedTag = lsGet(FILTER_TAG_KEY);
  if (savedQuery) gameSearchInput.value = savedQuery;
  if (savedTag && Array.from(gameTagFilter.options).some((o) => o.value === savedTag)) {
    gameTagFilter.value = savedTag;
  }
  const savedSort = lsGet(SORT_MODE_KEY);
  if (savedSort && gameSortSelect && Array.from(gameSortSelect.options).some((o) => o.value === savedSort)) {
    gameSortSelect.value = savedSort;
  }
  gameSearchInput.addEventListener("input", () => {
    lsSet(FILTER_QUERY_KEY, gameSearchInput.value);
    loadExtendedSearchIndex();
    applyGameFilter();
  });
  gameSearchInput.addEventListener("focus", loadExtendedSearchIndex, { once: true });
  gameTagFilter.addEventListener("change", () => {
    lsSet(FILTER_TAG_KEY, gameTagFilter.value);
    applyGameFilter();
  });
  if (gameSessionFilter) {
    const savedSession = lsGet(FILTER_SESSION_KEY);
    if (savedSession && Array.from(gameSessionFilter.options).some((o) => o.value === savedSession)) {
      gameSessionFilter.value = savedSession;
    }
    gameSessionFilter.addEventListener("change", () => {
      lsSet(FILTER_SESSION_KEY, gameSessionFilter.value);
      applyGameFilter();
    });
  }
  if (gameSortSelect) {
    gameSortSelect.addEventListener("change", () => {
      lsSet(SORT_MODE_KEY, gameSortSelect.value);
      applySort();
    });
  }
  if (gameSearchInput.value.trim()) loadExtendedSearchIndex();
  setUpCalmFilter();
  applyGameFilter();
  applySort();
}

// --- Y24: "Random game" -- weighted toward titles the visitor hasn't
// started. "Played" = a claimed account save (claimedGameIds, filled in by
// loadContinuePlaying) or a local anonymous save code on this device.
const claimedGameIds = new Set();
function playedSlugs() {
  const played = new Set(claimedGameIds);
  try {
    Object.keys(localStorage)
      .filter((k) => k.startsWith("savecode:"))
      .forEach((k) => played.add(k.slice("savecode:".length)));
  } catch (err) { /* convenience only */ }
  return played;
}
const randomGameButton = document.getElementById("random-game-button");
if (randomGameButton) {
  randomGameButton.addEventListener("click", () => {
    const played = playedSlugs();
    const weighted = allTitleCards.map((card) => ({
      card,
      weight: played.has(cardSlug(card)) ? 1 : 4,
    }));
    let roll = Math.random() * weighted.reduce((sum, w) => sum + w.weight, 0);
    let pick = weighted[weighted.length - 1].card;
    for (const w of weighted) {
      roll -= w.weight;
      if (roll < 0) { pick = w.card; break; }
    }
    location.href = pick.querySelector(".title-card-link").getAttribute("href");
  });
}

// --- QI-50: "How long have you got?" -- 5 minutes, 15 minutes or all night suggests games that fit,
// read from the same hand-written game-sessions.json tiers as the session-length chip (short about 5
// minutes, medium about 20, long = long-form). Games the visitor has not started come first. Nothing is
// stored; the suggestions are plain links.
const TIME_PICKER_CHOICES = {
  "5": { tiers: ["short"], note: "Games that fit in about five minutes:" },
  "15": { tiers: ["short", "medium"], note: "Games you can make real progress in within a quarter of an hour (they save, so stopping early is fine):" },
  night: { tiers: ["long"], note: "Long-form games, built to be played across many sittings:" },
};
const TIME_PICKER_MAX = 6;
const timePickerButton = document.getElementById("time-picker-button");
const timePickerPanel = document.getElementById("time-picker");
const timePickerNote = document.getElementById("time-picker-note");
const timePickerResults = document.getElementById("time-picker-results");
function showTimePickerResults(choiceKey) {
  const choice = TIME_PICKER_CHOICES[choiceKey];
  if (!choice || !timePickerResults || !timePickerNote) return;
  timePickerResults.textContent = "";
  document.querySelectorAll(".time-picker-choice").forEach((b) => {
    b.setAttribute("aria-pressed", b.dataset.time === choiceKey ? "true" : "false");
  });
  if (!gameSessions) {
    timePickerNote.textContent = "Session lengths are unavailable right now, so I can't match games to your time. Try again in a moment.";
    return;
  }
  const played = playedSlugs();
  const fits = allTitleCards.filter((card) => choice.tiers.includes(cardSession(card)));
  const ordered = fits.filter((c) => !played.has(cardSlug(c))).concat(fits.filter((c) => played.has(cardSlug(c))));
  if (!ordered.length) {
    timePickerNote.textContent = "No games are listed for that length yet.";
    return;
  }
  const shown = ordered.slice(0, TIME_PICKER_MAX);
  timePickerNote.textContent = fits.length > shown.length
    ? `${choice.note} showing ${shown.length} of ${fits.length}, ones you haven't started first.`
    : choice.note;
  shown.forEach((card) => {
    const li = document.createElement("li");
    const link = document.createElement("a");
    link.className = "continue-playing-item";
    link.href = card.querySelector(".title-card-link").getAttribute("href");
    const tierLabel = gameSessions.tiers[cardSession(card)] || "";
    link.textContent = `${cardDisplayName(card)}${tierLabel ? ` — ${tierLabel}` : ""}${played.has(cardSlug(card)) ? "" : " (new to you)"}`;
    li.appendChild(link);
    timePickerResults.appendChild(li);
  });
}
if (timePickerButton && timePickerPanel) {
  timePickerButton.addEventListener("click", () => {
    const open = timePickerPanel.hidden;
    timePickerPanel.hidden = !open;
    timePickerButton.setAttribute("aria-expanded", open ? "true" : "false");
  });
  document.querySelectorAll(".time-picker-choice").forEach((b) => {
    b.addEventListener("click", () => showTimePickerResults(b.dataset.time));
  });
}

// --- Y27: "Recently Added" -- the newest couple of games by the date
// their index.html first landed in git (game-added.json, regenerated with
// the last-updated dates by scripts/generate-last-updated.py).
async function loadRecentlyAdded() {
  const section = document.getElementById("recently-added-section");
  const list = document.getElementById("recently-added-list");
  if (!section || !list) return;
  try {
    const res = await fetch("game-added.json");
    if (!res.ok) throw new Error(`status ${res.status}`);
    const added = await res.json();
    const newest = allTitleCards
      .map((card) => ({ card, date: added[cardSlug(card)] }))
      .filter((e) => e.date)
      .sort((a, b) => (a.date < b.date ? 1 : -1))
      .slice(0, 2);
    newest.forEach(({ card, date }) => {
      const link = document.createElement("a");
      link.className = "continue-playing-item";
      link.href = card.querySelector(".title-card-link").getAttribute("href");
      link.textContent = `${card.querySelector(".title-card-name").textContent} — added ${date}`;
      list.appendChild(link);
    });
    section.hidden = newest.length === 0;
  } catch (err) {
    console.error("loadRecentlyAdded failed:", err);
  }
}
loadRecentlyAdded();

// --- Accounts (ACCOUNTS-AND-FEEDBACK-DESIGN.md Phase 2, revised: username
// + password, no email — see main.py for why) ---
const accountSignedOut = document.getElementById("account-signed-out");
const accountSignedIn = document.getElementById("account-signed-in");
const accountUsernameInput = document.getElementById("account-username-input");
const accountPasswordInput = document.getElementById("account-password-input");
const accountLoginButton = document.getElementById("account-login-button");
const accountSignupButton = document.getElementById("account-signup-button");
const accountStatus = document.getElementById("account-status");
const accountUsernameDisplay = document.getElementById("account-username-display");
const accountSignoutButton = document.getElementById("account-signout-button");
const accountMySaves = document.getElementById("account-my-saves");

// UX-7: "Your saves" is collapsible; remembered per device. Starts expanded
// for a new visitor (no stored value). Works whether or not the surrounding
// signed-in block is currently hidden, since it only toggles <details open>.
const SAVES_COLLAPSED_KEY = "hub-saves-collapsed";
const accountSavesDetails = document.getElementById("account-my-saves-details");
if (accountSavesDetails) {
  try {
    if (localStorage.getItem(SAVES_COLLAPSED_KEY) === "1") accountSavesDetails.open = false;
  } catch (e) { /* storage unavailable: stay expanded */ }
  accountSavesDetails.addEventListener("toggle", () => {
    lsSet(SAVES_COLLAPSED_KEY, accountSavesDetails.open ? "0" : "1");
  });
}
const continuePlayingSection = document.getElementById("continue-playing-section");
const continuePlayingList = document.getElementById("continue-playing-list");

// --- "Claim your save" nudge for anonymous players (L15) ---
// Any local `savecode:<slug>` key counts as invested (every save is an explicit action). Hidden once signed in;
// dismissal is permanent. Declared here because showSignedIn/showSignedOut below call it.
const CLAIM_NUDGE_DISMISSED_KEY = "claim_save_nudge_dismissed";
const claimSaveNudge = document.getElementById("claim-save-nudge");
const claimSaveNudgeCta = document.getElementById("claim-save-nudge-cta");
const claimSaveNudgeDismiss = document.getElementById("claim-save-nudge-dismiss");

function anonymousSaveCodeSlugs() {
  try {
    return Object.keys(localStorage)
      .filter((key) => key.startsWith("savecode:"))
      .map((key) => key.slice("savecode:".length));
  } catch (err) {
    return [];
  }
}

function maybeShowClaimSaveNudge() {
  if (!claimSaveNudge) return;
  const alreadySignedIn = Boolean(signedInToken());
  const dismissed = lsGet(CLAIM_NUDGE_DISMISSED_KEY);
  claimSaveNudge.hidden = alreadySignedIn || Boolean(dismissed) || !anonymousSaveCodeSlugs().length;
}

if (claimSaveNudgeCta) {
  claimSaveNudgeCta.addEventListener("click", () => {
    document.getElementById("account-section")?.scrollIntoView({ behavior: "smooth" });
    accountUsernameInput?.focus();
  });
}

if (claimSaveNudgeDismiss) {
  claimSaveNudgeDismiss.addEventListener("click", () => {
    lsSet(CLAIM_NUDGE_DISMISSED_KEY, "1");
    claimSaveNudge.hidden = true;
  });
}

// Y8: a small fixed "signed in as ..." pill, shown only while signed in AND
// the account section itself is scrolled out of view.
const signedInPill = document.getElementById("signed-in-pill");
let signedInPillUsername = null;
let accountSectionVisible = true;
function updateSignedInPill(username) {
  signedInPillUsername = username;
  // The "Owner only" nav dropdown (shared/owner-links.js) follows the sign-in state.
  if (window.NoyvjOwnerLinks) window.NoyvjOwnerLinks.refresh();
  if (!signedInPill) return;
  if (username) signedInPill.textContent = `Signed in as ${username}`;
  signedInPill.hidden = !username || accountSectionVisible;
}
if (signedInPill && "IntersectionObserver" in window) {
  new IntersectionObserver((entries) => {
    accountSectionVisible = entries[0].isIntersecting;
    signedInPill.hidden = !signedInPillUsername || accountSectionVisible;
  }).observe(document.getElementById("account-section"));
}

// One GET /users/me/saves answers the saves list, Continue Playing and the achievements dashboard
// (they used to send three identical requests). Cleared on every sign-in and sign-out.
let mySavesRequest = null;
function fetchMySaves() {
  if (!mySavesRequest) {
    mySavesRequest = fetch(`${RATINGS_API_BASE}/users/me/saves`, { headers: authHeaders() }).then((res) => {
      if (!res.ok) throw new Error(`status ${res.status}`);
      return res.json();
    });
    mySavesRequest.catch(() => {}); // each caller reports its own failure
  }
  return mySavesRequest;
}

function showSignedOut() {
  mySavesRequest = null;
  updateSignedInPill(null);
  accountSignedOut.hidden = false;
  accountSignedIn.hidden = true;
  continuePlayingSection.hidden = true;
  continuePlayingList.innerHTML = "";
  const rarestSection = document.getElementById("rarest-section");
  if (rarestSection) rarestSection.hidden = true;
  maybeShowClaimSaveNudge();
}

// U9: the optional account email. Private to the account and the admin;
// stored and validated server-side (GET/PUT /users/me/email).
async function loadMyEmail() {
  const input = document.getElementById("account-email-input");
  if (!input) return;
  try {
    const res = await fetch(`${RATINGS_API_BASE}/users/me/email`, { headers: authHeaders(), cache: "no-store" });
    if (res.ok) input.value = (await res.json()).email || "";
  } catch (err) { /* offline or not deployed yet: leave the field empty */ }
}

async function saveMyEmail(value) {
  const status = document.getElementById("account-email-status");
  const input = document.getElementById("account-email-input");
  status.textContent = "Saving…";
  try {
    const res = await fetch(`${RATINGS_API_BASE}/users/me/email`, {
      method: "PUT",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ email: value }),
    });
    if (res.status === 422) { status.textContent = "That doesn't look like an email address."; return; }
    if (!res.ok) { status.textContent = "Couldn't save just now — try again later."; return; }
    const saved = (await res.json()).email;
    input.value = saved || "";
    status.textContent = saved ? "Saved." : "Email removed.";
  } catch (err) {
    status.textContent = "Couldn't save just now — try again later.";
  }
}

document.getElementById("account-email-save")?.addEventListener("click", () => {
  saveMyEmail(document.getElementById("account-email-input").value);
});
document.getElementById("account-email-remove")?.addEventListener("click", () => saveMyEmail(""));

function showSignedIn(username) {
  mySavesRequest = null;
  accountSignedOut.hidden = true;
  accountSignedIn.hidden = false;
  accountUsernameDisplay.textContent = `Signed in as ${username}`;
  updateSignedInPill(username);
  const since = lsGet(AUTH_SINCE_KEY);
  const memberSince = document.getElementById("account-member-since");
  if (memberSince) {
    memberSince.hidden = !since;
    if (since) memberSince.textContent = `Member since ${since}`;
  }
  renderEventBadges(null);
  loadMyEmail();
  loadMySaves();
  loadAchievementsDashboard();
  loadContinuePlaying();
  maybeShowClaimSaveNudge();
}

async function loadMySaves() {
  const token = signedInToken();
  accountMySaves.textContent = "Loading your saves…";
  try {
    const saves = await fetchMySaves();
    if (signedInToken() !== token) return; // signed out while the request was in flight
    accountMySaves.innerHTML = "";
    if (!saves.length) {
      accountMySaves.textContent =
        'No claimed saves yet — save progress in a game, then use "Claim this save" there once signed in.';
      return;
    }
    const list = document.createElement("ul");
    list.className = "account-saves-list";
    saves.forEach((save) => {
      const item = document.createElement("li");
      const label = document.createElement("span");
      label.textContent = `${save.game_id}: ${save.save_code}`;
      const copyButton = document.createElement("button");
      copyButton.type = "button";
      copyButton.className = "account-link-button";
      copyButton.textContent = "Copy code";
      copyButton.addEventListener("click", async () => {
        try {
          await navigator.clipboard.writeText(save.save_code);
          copyButton.textContent = "Copied!";
        } catch (err) {
          window.prompt("Copy this save code:", save.save_code); // clipboard blocked
          return;
        }
        setTimeout(() => (copyButton.textContent = "Copy code"), 1500);
      });
      item.appendChild(label);
      item.appendChild(copyButton);
      list.appendChild(item);
    });
    accountMySaves.appendChild(list);
  // Keeps the generic user-facing message (matching every other catch in
  // this file and in save-widget.js — submitAuth() below is the one
  // deliberate exception, since it's the one place a specific backend
  // reason like "wrong password" vs. "username taken" is worth showing).
  // Still logged to the console so a real failure here is debuggable.
  } catch (err) {
    console.error("loadMySaves failed:", err);
    accountMySaves.textContent = "Couldn't load your saves right now.";
  }
}

// --- Achievements dashboard (ACHIEVEMENTS-SYSTEM-DESIGN.md) ---
//
// Which games ship an achievements catalog is auto-discovered from
// game-manifest.json (generated by scripts/generate-last-updated.py —
// GitHub Pages has no directory listing, so a generated file is the only
// way to "discover" games). Re-run that script when a game adds an
// achievements.json. If the manifest can't be fetched, the fallback list
// below keeps the dashboard working.
const ACHIEVEMENT_GAMES_FALLBACK = [
  "sol", "continuum", "canopy", "grid", "trade-empire", "tide",
  "aftermath", "herd", "thaw", "loop", "drift", "champ-de-mots", "signal", "lexis", "heist-committee", "lighthouse", "pocket-bazaar", "dead-reckoning", "logic-gates", "robot-script", "hull-repair", "station-medic", "stranded", "evidence-hunt",
];

async function loadAchievementGameIds() {
  try {
    const res = await fetch("game-manifest.json");
    if (!res.ok) throw new Error(`status ${res.status}`);
    const data = await res.json();
    if (data && Array.isArray(data.achievements) && data.achievements.length) {
      return data.achievements.filter((s) => typeof s === "string" && /^[a-z0-9-]+$/.test(s));
    }
  } catch (err) {
    console.warn("game-manifest.json unavailable, using fallback list:", err);
  }
  return ACHIEVEMENT_GAMES_FALLBACK;
}

// Display label only — falls back to the raw game_id for a game added here
// without an entry (still readable, just not title-cased).
const GAME_DISPLAY_NAMES = {
  sol: "SOL",
  continuum: "Continuum",
  canopy: "Canopy",
  grid: "Grid",
  "trade-empire": "Trade Empire",
  tide: "Tide",
  aftermath: "Aftermath",
  herd: "Herd",
  thaw: "Thaw",
  loop: "Loop",
  drift: "Drift",
  "champ-de-mots": "Le Champ de Mots",
  signal: "Signal",
  lexis: "Lexis",
  "heist-committee": "Heist Committee",
  lighthouse: "Lighthouse",
  "pocket-bazaar": "Pocket Bazaar",
  "dead-reckoning": "Dead Reckoning",
  "logic-gates": "Logic Gates",
  "robot-script": "Robot Script",
  "hull-repair": "Hull Repair",
  "station-medic": "Station Medic",
  stranded: "Stranded",
  "evidence-hunt": "Evidence Hunt",
};

// --- R2-Z23b: earned holiday-event badges (data contract v1) ---
//
// Contract (documented in planning/ACHIEVEMENTS-SYSTEM-DESIGN.md §8): a
// game records an earned event badge as an entry in `event_badges`, an
// array of { id, label, earned_at } where
//   id         lowercase slug, /^[a-z0-9-]{1,64}$/, e.g. "christmas-2026"
//   label      short display text (<= 60 chars), e.g. "Christmas 2026"
//   earned_at  ISO date/datetime string (<= 32 chars)
// in either place (the hub reads both and de-dupes by id):
//   1. the game's save state -- `save_data.event_badges`, same pattern as
//      `save_data.achievements_earned` (travels with the account's saves);
//   2. localStorage key "event_badges_v1" holding
//      { "version": 1, "badges": [ ...same entries... ] } (this device only,
//      for games/events that don't write into a save).
// Unknown versions and malformed entries are ignored, never thrown on.
const EVENT_BADGES_LS_KEY = "event_badges_v1";
const accountEventBadges = document.getElementById("account-event-badges");

function sanitizeEventBadges(list) {
  if (!Array.isArray(list)) return [];
  return list
    .filter(
      (b) =>
        b &&
        typeof b.id === "string" && /^[a-z0-9-]{1,64}$/.test(b.id) &&
        typeof b.label === "string" && b.label.trim() && b.label.length <= 60 &&
        (b.earned_at === undefined || (typeof b.earned_at === "string" && b.earned_at.length <= 32))
    )
    .map((b) => ({ id: b.id, label: b.label.trim(), earned_at: b.earned_at || "" }));
}

function collectEventBadges(saves) {
  const found = [];
  try {
    const raw = lsGet(EVENT_BADGES_LS_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    if (parsed && parsed.version === 1) found.push(...sanitizeEventBadges(parsed.badges));
  } catch (err) { /* malformed or unavailable storage -- ignore */ }
  (Array.isArray(saves) ? saves : []).forEach((save) => {
    if (save && save.save_data) found.push(...sanitizeEventBadges(save.save_data.event_badges));
  });
  const byId = new Map();
  found.forEach((b) => { if (!byId.has(b.id)) byId.set(b.id, b); });
  return Array.from(byId.values());
}

function renderEventBadges(saves) {
  if (!accountEventBadges) return;
  const badges = collectEventBadges(saves);
  accountEventBadges.innerHTML = "";
  accountEventBadges.hidden = badges.length === 0;
  if (!badges.length) return;
  const heading = document.createElement("p");
  heading.className = "achievements-dashboard-heading";
  heading.textContent = "Event badges";
  accountEventBadges.appendChild(heading);
  const list = document.createElement("ul");
  list.className = "event-badge-list";
  badges.forEach((b) => {
    const li = document.createElement("li");
    li.className = "event-badge";
    li.textContent = b.label;
    if (b.earned_at) li.title = `Earned ${b.earned_at.slice(0, 10)}`;
    list.appendChild(li);
  });
  accountEventBadges.appendChild(list);
}

const accountAchievementsDashboard = document.getElementById("account-achievements-dashboard");

function renderProgressBar(container, label, earned, total, listHref) {
  const row = document.createElement("div");
  row.className = "achievements-bar-row";
  const labelEl = document.createElement("p");
  labelEl.className = "achievements-bar-label";
  if (listHref) {
    // Links to the full per-game list on achievements.html.
    const link = document.createElement("a");
    link.href = listHref;
    link.textContent = `${label}: ${earned}/${total}`;
    link.title = `See every ${label} achievement`;
    labelEl.appendChild(link);
  } else {
    labelEl.textContent = `${label}: ${earned}/${total}`;
  }
  const track = document.createElement("div");
  track.className = "achievements-bar-track";
  // Y26: exact fraction on hover (and to assistive tech), not just bar width.
  const pct = total > 0 ? Math.round((earned / total) * 100) : 0;
  track.title = `${earned} of ${total} achievements (${pct}%)`;
  track.setAttribute("role", "progressbar");
  track.setAttribute("aria-valuemin", "0");
  track.setAttribute("aria-valuemax", String(total));
  track.setAttribute("aria-valuenow", String(earned));
  track.setAttribute("aria-label", `${label} achievements`);
  const fill = document.createElement("div");
  fill.className = "achievements-bar-fill";
  fill.style.width = `${total > 0 ? Math.min(100, (earned / total) * 100) : 0}%`;
  track.appendChild(fill);
  row.appendChild(labelEl);
  row.appendChild(track);
  container.appendChild(row);
}

// The most recently updated save for `gameId` out of one account's full
// save list — same "account is the source of truth, most recent wins"
// selection shared/save-widget.js's own autoload already uses for a single
// game; this just repeats it per game for the dashboard.
function mostRecentSaveForGame(saves, gameId) {
  const forGame = saves.filter((s) => s.game_id === gameId);
  if (!forGame.length) return null;
  forGame.sort((a, b) => {
    const aTime = new Date(a.updated_at || a.created_at).getTime();
    const bTime = new Date(b.updated_at || b.created_at).getTime();
    return bTime - aTime;
  });
  return forGame[0];
}

// --- "Continue Playing" (TODO.md L11 + L4, built as one combined feature)
// ---
//
// Pinned above the full game grid for a signed-in player: their claimed
// saves, most-recent-per-game, each linking straight into that game. No
// need to pass the save code through the URL — every game's own
// shared/save-widget.js already autoloads a signed-in user's most recent
// save on page load, so linking to the game's index.html is enough.
function gameHrefForId(gameId) {
  return `games/${gameId}/index.html`;
}

async function loadContinuePlaying() {
  const token = signedInToken();
  try {
    const saves = await fetchMySaves();
    if (signedInToken() !== token) return; // signed out while the request was in flight
    const gameIds = [...new Set(saves.map((s) => s.game_id))];
    gameIds.forEach((id) => claimedGameIds.add(id));
    if (!gameIds.length) {
      continuePlayingSection.hidden = true;
      continuePlayingList.innerHTML = "";
      return;
    }
    const entries = gameIds
      .map((gameId) => ({ gameId, save: mostRecentSaveForGame(saves, gameId) }))
      .filter((e) => e.save)
      .sort((a, b) => {
        const aTime = new Date(a.save.updated_at || a.save.created_at).getTime();
        const bTime = new Date(b.save.updated_at || b.save.created_at).getTime();
        return bTime - aTime;
      });
    continuePlayingList.innerHTML = "";
    entries.forEach(({ gameId }) => {
      const link = document.createElement("a");
      link.className = "continue-playing-item";
      link.href = gameHrefForId(gameId);
      link.textContent = `Continue ${GAME_DISPLAY_NAMES[gameId] || gameId}`;
      continuePlayingList.appendChild(link);
    });
    continuePlayingSection.hidden = false;
  } catch (err) {
    // Silent, non-critical — the full game grid below still works, and a
    // signed-in player without a fetchable saves list just doesn't get
    // this convenience section this load, same failure posture the
    // achievements dashboard and My Saves list already take.
    console.error("loadContinuePlaying failed:", err);
    continuePlayingSection.hidden = true;
  }
}

// Y-5: per-game earned/total for the signed-in account, filled in by loadAchievementsDashboard()
// and read by hub-foryou.js ("because you finished ...").
const hubAchievementProgress = {};

// QI-45: "Rarest things you own" -- the five rarest achievements this account has earned, ranked by the
// public earned_pct numbers (GET /stats/achievements, one request). An achievement whose percentage the
// backend withholds (too few earners to be anonymous) is never ranked, so nothing is shown as 0%. Skipped
// while reduce-data is on. Rarity wording matches shared/achievement-stats.js (Gold up to 10%, Silver up to
// 35%, otherwise Bronze), as text plus a glyph, never colour alone.
const RAREST_COUNT = 5;
function rarityWord(pct) {
  if (pct <= 10) return "\u2605 Gold (rare)";
  if (pct <= 35) return "\u25C6 Silver (uncommon)";
  return "\u25CF Bronze (common)";
}
async function renderRarestStrip(games, token) {
  const section = document.getElementById("rarest-section");
  const list = document.getElementById("rarest-list");
  if (!section || !list) return;
  section.hidden = true;
  if (hubReduceData()) return;
  try {
    const res = await fetch(`${RATINGS_API_BASE}/stats/achievements`);
    if (!res.ok) throw new Error(`status ${res.status}`);
    const stats = await res.json();
    if (signedInToken() !== token) return;
    const rows = [];
    games.forEach(({ gameId, catalog, earned }) => {
      const info = stats && stats.games && stats.games[gameId];
      if (!info || info.suppressed || !catalog || !Array.isArray(catalog.achievements)) return;
      earned.forEach((id) => {
        const stat = info.achievements && info.achievements[id];
        const entry = catalog.achievements.find((a) => a.id === id);
        if (!stat || typeof stat.earned_pct !== "number" || !entry) return;
        rows.push({ gameId, label: entry.label || id, pct: stat.earned_pct });
      });
    });
    rows.sort((a, b) => a.pct - b.pct || a.label.localeCompare(b.label));
    list.textContent = "";
    rows.slice(0, RAREST_COUNT).forEach((r) => {
      const li = document.createElement("li");
      const link = document.createElement("a");
      link.className = "continue-playing-item";
      link.href = `achievements.html#${r.gameId}`;
      link.textContent = `${r.label} \u2014 ${GAME_DISPLAY_NAMES[r.gameId] || r.gameId}: ${r.pct}% of players, ${rarityWord(r.pct)}`;
      li.appendChild(link);
      list.appendChild(li);
    });
    section.hidden = rows.length === 0;
  } catch (err) {
    console.error("renderRarestStrip failed:", err);
  }
}

async function loadAchievementsDashboard() {
  const token = signedInToken();
  const gameIds = await loadAchievementGameIds();
  if (!gameIds.length) {
    accountAchievementsDashboard.innerHTML = "";
    return;
  }
  accountAchievementsDashboard.textContent = "Loading achievement progress…";
  try {
    const [saves, ...catalogResults] = await Promise.all([
      fetchMySaves(),
      ...gameIds.map((gameId) =>
        fetch(`games/${gameId}/achievements.json`)
          .then((res) => (res.ok ? res.json() : null))
          .catch(() => null)
      ),
    ]);
    if (signedInToken() !== token) return; // signed out while the requests were in flight
    renderEventBadges(saves);

    accountAchievementsDashboard.innerHTML = "";
    const heading = document.createElement("p");
    heading.className = "achievements-dashboard-heading";
    heading.textContent = "Achievements";
    accountAchievementsDashboard.appendChild(heading);

    // Per-game bars render into their own collapsed-by-default <details>
    // instead of straight into the dashboard — with achievements now
    // shipped on all 12 games, this section was one bar per game stacked
    // in a signed-in visitor's account panel, which reads as a wall of
    // bars before they've even scrolled to a single game. The one number
    // most visitors actually want at a glance (the Overall bar) stays
    // outside the collapse, right under the heading.
    const perGameDetails = document.createElement("details");
    perGameDetails.className = "achievements-per-game-toggle";
    const perGameSummary = document.createElement("summary");
    perGameDetails.appendChild(perGameSummary);

    let totalEarned = 0;
    let totalPossible = 0;
    let gamesRendered = 0;

    gameIds.forEach((gameId, i) => {
      const catalog = catalogResults[i];
      // A game listed in the manifest whose achievements.json failed to
      // fetch (offline, a typo'd path) is skipped rather than shown as a
      // false "0/0" — the manifest promises a real catalog exists, and if
      // it couldn't be read this pass, silence is more honest than a
      // fabricated total.
      const total = catalog && Array.isArray(catalog.achievements) ? catalog.achievements.length : 0;
      if (!total) return;

      const save = mostRecentSaveForGame(saves, gameId);
      const earnedList =
        save && save.save_data && Array.isArray(save.save_data.achievements_earned)
          ? save.save_data.achievements_earned
          : [];
      const earned = Math.min(earnedList.length, total);
      hubAchievementProgress[gameId] = { earned, total };

      renderProgressBar(
        perGameDetails,
        GAME_DISPLAY_NAMES[gameId] || gameId,
        earned,
        total,
        `achievements.html#${gameId}`
      );
      totalEarned += earned;
      totalPossible += total;
      gamesRendered += 1;
    });

    if (!gamesRendered) {
      const note = document.createElement("p");
      note.className = "achievements-dashboard-empty";
      note.textContent = "No games with achievements yet — check back as more games get them.";
      accountAchievementsDashboard.appendChild(note);
      return;
    }

    const divider = document.createElement("p");
    divider.className = "achievements-dashboard-overall-label";
    divider.textContent = "Overall";
    accountAchievementsDashboard.appendChild(divider);
    renderProgressBar(accountAchievementsDashboard, "All games", totalEarned, totalPossible, "achievements.html");

    renderRarestStrip(gameIds.map((gameId, i) => ({
      gameId,
      catalog: catalogResults[i],
      earned: (() => {
        const save = mostRecentSaveForGame(saves, gameId);
        return save && save.save_data && Array.isArray(save.save_data.achievements_earned) ? save.save_data.achievements_earned : [];
      })(),
    })), token);

    window.dispatchEvent(new CustomEvent("hub-achievements-progress"));
    perGameSummary.textContent = `Per-game breakdown (${gamesRendered} games)`;
    accountAchievementsDashboard.appendChild(perGameDetails);
  } catch (err) {
    console.error("loadAchievementsDashboard failed:", err);
    accountAchievementsDashboard.textContent = "Couldn't load achievement progress right now.";
  }
}

async function submitAuth(endpoint, triggerButton, busyText, idleText) {
  const username = accountUsernameInput.value.trim();
  const password = accountPasswordInput.value;
  if (!username || !password) {
    accountStatus.textContent = "Enter a username and password first.";
    return;
  }
  accountLoginButton.disabled = true;
  accountSignupButton.disabled = true;
  triggerButton.textContent = busyText;
  try {
    const res = await fetch(`${RATINGS_API_BASE}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const body = await res.json();
    if (!res.ok) {
      accountStatus.textContent = body.detail || "Something went wrong — try again.";
      return;
    }
    lsSet(HUB_AUTH_TOKEN_KEY, body.bearer_token);
    lsSet(AUTH_USERNAME_KEY, body.username);
    if (lsGet(HUB_AUTH_TOKEN_KEY) !== body.bearer_token) {
      // Storage is blocked: the page would look signed in but forget it on the next load.
      accountStatus.textContent = "This browser is blocking site storage, so a sign-in cannot be kept here. Allow site data for this site and try again.";
      return;
    }
    if (endpoint === "/auth/signup") lsSet(AUTH_SINCE_KEY, new Date().toISOString().slice(0, 10));
    accountUsernameInput.value = "";
    accountPasswordInput.value = "";
    accountStatus.textContent = "";
    showSignedIn(body.username);
    // R1-L13: the focused Sign In button just left the DOM flow (hidden
    // view) -- put keyboard focus on the new view's heading line instead.
    accountUsernameDisplay.setAttribute("tabindex", "-1");
    accountUsernameDisplay.focus({ preventScroll: true });
  } catch (err) {
    accountStatus.textContent = "Couldn't reach the server — try again.";
  } finally {
    accountLoginButton.disabled = false;
    accountSignupButton.disabled = false;
    triggerButton.textContent = idleText;
  }
}

accountLoginButton.addEventListener("click", () =>
  submitAuth("/auth/login", accountLoginButton, "Signing in...", "Sign In")
);
accountSignupButton.addEventListener("click", () =>
  submitAuth("/auth/signup", accountSignupButton, "Creating...", "Create Account")
);

// R1-L13: Enter in either field signs in (they aren't inside a <form>).
[accountUsernameInput, accountPasswordInput].forEach((input) =>
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !accountLoginButton.disabled) {
      e.preventDefault();
      accountLoginButton.click();
    }
  })
);

accountSignoutButton.addEventListener("click", () => {
  // The session is dropped immediately; only the view switch waits a beat
  // so a "Signed out" confirmation is actually seen (Y18).
  lsRemove(HUB_AUTH_TOKEN_KEY);
  lsRemove(AUTH_USERNAME_KEY);
  lsRemove(AUTH_SINCE_KEY);
  accountSignoutButton.disabled = true;
  accountSignoutButton.textContent = "Signed out \u2713";
  updateSignedInPill(null);
  setTimeout(() => {
    accountSignoutButton.disabled = false;
    accountSignoutButton.textContent = "Sign out";
    showSignedOut();
    accountStatus.textContent = "You've been signed out.";
    accountUsernameInput.focus({ preventScroll: true });
  }, 900);
});

const savedUsername = lsGet(AUTH_USERNAME_KEY);
if (signedInToken() && savedUsername) {
  showSignedIn(savedUsername);
} else {
  showSignedOut();
}

// --- Site-wide feedback (ACCOUNTS-AND-FEEDBACK-DESIGN.md) ---

const siteFeedbackStars = document.getElementById("site-feedback-stars");
const siteFeedbackComment = document.getElementById("site-feedback-comment");
const siteFeedbackSubmit = document.getElementById("site-feedback-submit");
const siteFeedbackStatus = document.getElementById("site-feedback-status");
const siteFeedbackList = document.getElementById("site-feedback-list");

bindStarRating(siteFeedbackStars);

async function loadSiteFeedback() {
  try {
    const res = await fetch(`${RATINGS_API_BASE}/feedback`);
    if (!res.ok) throw new Error(`status ${res.status}`);
    const items = await res.json();
    siteFeedbackList.innerHTML = "";
    if (!items.length) {
      const li = document.createElement("li");
      li.textContent = "No general feedback yet — be the first.";
      siteFeedbackList.appendChild(li);
      return;
    }
    items.forEach((item) => {
      const li = document.createElement("li");
      const parts = [];
      if (item.rating) parts.push(`${item.rating}★`);
      if (item.comment) parts.push(item.comment);
      li.textContent = parts.join(" — ");
      siteFeedbackList.appendChild(li);
    });
  } catch (err) {
    siteFeedbackList.innerHTML = "";
    const li = document.createElement("li");
    li.textContent = "Feedback unavailable right now.";
    siteFeedbackList.appendChild(li);
  }
}

siteFeedbackSubmit.addEventListener("click", async () => {
  const rating = Number(siteFeedbackStars.dataset.rating) || null;
  const comment = siteFeedbackComment.value.trim() || null;
  if (!rating && !comment) {
    siteFeedbackStatus.textContent = "Add a rating or a comment first.";
    return;
  }
  siteFeedbackSubmit.disabled = true;
  siteFeedbackSubmit.textContent = "Submitting...";
  try {
    const res = await fetch(`${RATINGS_API_BASE}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ rating, comment }),
    });
    if (!res.ok) throw new Error(`status ${res.status}`);
    siteFeedbackComment.value = "";
    resetStarRating(siteFeedbackStars);
    siteFeedbackStatus.textContent = "Thanks for the feedback!";
    await loadSiteFeedback();
  } catch (err) {
    siteFeedbackStatus.textContent = "Submit failed — try again.";
  } finally {
    siteFeedbackSubmit.disabled = false;
    siteFeedbackSubmit.textContent = "Submit";
  }
});

loadSiteFeedback();

// "Add to Home Screen" banner (L18): browsers hide their own install UI until `beforeinstallprompt` fires and we
// call .prompt() ourselves. Dismissal is permanent; never shown if the browser never fires the event.
const PWA_INSTALL_DISMISSED_KEY = "pwa_install_banner_dismissed";
const pwaInstallBanner = document.getElementById("pwa-install-banner");
const pwaInstallCta = document.getElementById("pwa-install-cta");
const pwaInstallDismiss = document.getElementById("pwa-install-dismiss");
let deferredInstallPrompt = null;

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  deferredInstallPrompt = event;
  showInstallBannerIfAllowed();
});

// Playtest audit 2026-10-06 (S7): on a first visit this banner used to stack
// with the onboarding survey modal. It now waits until the survey is closed
// (the survey's own close handler calls this again).
function showInstallBannerIfAllowed() {
  if (!pwaInstallBanner || !deferredInstallPrompt) return;
  if (lsGet(PWA_INSTALL_DISMISSED_KEY)) return;
  if (document.getElementById("onboarding-survey-overlay")) return;
  pwaInstallBanner.hidden = false;
}

window.addEventListener("appinstalled", () => {
  deferredInstallPrompt = null;
  if (pwaInstallBanner) pwaInstallBanner.hidden = true;
});

if (pwaInstallCta) {
  pwaInstallCta.addEventListener("click", async () => {
    if (!deferredInstallPrompt) return;
    pwaInstallBanner.hidden = true;
    deferredInstallPrompt.prompt();
    await deferredInstallPrompt.userChoice;
    deferredInstallPrompt = null;
  });
}

if (pwaInstallDismiss) {
  pwaInstallDismiss.addEventListener("click", () => {
    lsSet(PWA_INSTALL_DISMISSED_KEY, "1");
    pwaInstallBanner.hidden = true;
  });
}

// --- Y10: "new since your last visit" badge on the What's New nav link ---
// whats-new.html records the newest entry date it showed
// (hub_whats_new_seen). Here we count dev-log entry headings dated after
// that. A first-ever visitor has no baseline, so no badge -- nothing is
// "new" to someone who has never looked. Fetched after load so it never
// competes with the lobby.
// The logs are append-only, so the newest headings are at the end: ask for just the last 24 KB
// (HTTP Range; the service worker passes Range requests straight through). A server that ignores
// Range answers 200 with the whole file, which is read the same way. When only a tail came back and
// even its oldest heading is newer than `seen`, the true count is unknown, so the badge says "N+".
const WHATS_NEW_TAIL_BYTES = 24576;
async function loadWhatsNewBadge() {
  const badge = document.getElementById("whats-new-badge");
  const seen = lsGet("hub_whats_new_seen");
  if (!badge || !seen) return;
  if (hubReduceData()) return; // the two dev logs are about half a megabyte together
  try {
    const parts = await Promise.all(
      ["BCM114-DEV-LOG.md", "BCM206-DEV-LOG.md"].map((path) =>
        fetch(path, { headers: { Range: `bytes=-${WHATS_NEW_TAIL_BYTES}` } }).then(async (res) => ({
          text: res.ok ? await res.text() : "",
          partial: res.status === 206,
        }))
      )
    );
    let count = 0;
    let truncated = false;
    parts.forEach(({ text, partial }) => {
      const dates = (text.match(/^### \d{4}-\d{2}-\d{2}/gm) || []).map((h) => h.slice(4));
      dates.forEach((d) => { if (d > seen) count += 1; });
      if (partial && dates.length && dates.every((d) => d > seen)) truncated = true;
    });
    if (count > 0) {
      const label = truncated ? `${count}+` : String(count);
      badge.textContent = label;
      badge.title = `${label} update${count === 1 && !truncated ? "" : "s"} since your last visit`;
      badge.hidden = false;
    }
  } catch (err) {
    console.error("loadWhatsNewBadge failed:", err);
  }
}
// Idle time only, so this never competes with the lobby for bandwidth.
if ("requestIdleCallback" in window) requestIdleCallback(loadWhatsNewBadge, { timeout: 4000 });
else setTimeout(loadWhatsNewBadge, 2000);

// --- Y25: dismissible site-wide announcement banner ---
// Driven by announcement.json: { "id": "<unique string>", "message": "...",
// "link": "<optional url>", "linkText": "...", "expires": "YYYY-MM-DD" }.
// An empty/absent id means no announcement. Dismissal is remembered per id
// in localStorage, so a NEW id re-shows the banner. Distinct from What's
// New: this is for time-sensitive notices, not history.
const ANNOUNCEMENT_DISMISSED_KEY = "hub_announcement_dismissed";
async function loadAnnouncement() {
  const banner = document.getElementById("announcement-banner");
  if (!banner) return;
  try {
    const res = await fetch("announcement.json");
    if (!res.ok) return;
    const data = await res.json();
    if (!data || !data.id || !data.message) return;
    if (data.expires && new Date().toISOString().slice(0, 10) > data.expires) return;
    if (lsGet(ANNOUNCEMENT_DISMISSED_KEY) === String(data.id)) return;
    document.getElementById("announcement-text").textContent = data.message;
    const link = document.getElementById("announcement-link");
    if (data.link && /^(https?:\/\/|[\w./#-]+$)/.test(data.link)) {
      link.href = data.link;
      link.textContent = data.linkText || "Learn more";
      link.hidden = false;
    }
    document.getElementById("announcement-dismiss").addEventListener("click", () => {
      lsSet(ANNOUNCEMENT_DISMISSED_KEY, String(data.id));
      banner.hidden = true;
    });
    banner.hidden = false;
  } catch (err) {
    console.error("loadAnnouncement failed:", err);
  }
}
loadAnnouncement();

// --- Y30: floating "back to top" button once scrolled past the fold ---
const backToTop = document.getElementById("back-to-top");
if (backToTop) {
  const update = () => { backToTop.hidden = window.scrollY < window.innerHeight; };
  window.addEventListener("scroll", update, { passive: true });
  backToTop.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
    document.getElementById("hub-header")?.setAttribute("tabindex", "-1");
    document.getElementById("hub-header")?.focus({ preventScroll: true });
  });
  update();
}

// --- Y13: skippable site tour for first-time visitors ---
// Reuses shared/tutorial.js (auto-starts once per gameId, "Take the Tour" re-opens it). A step whose selector is
// missing or hidden falls back to a centred card, so it is safe in any signed-in/out state. Its auto-start waits
// for the onboarding survey to close so two first-visit overlays never stack.
const HUB_TOUR_STEPS = [
  {
    title: "Welcome to NoyvjGames",
    text: "A quick, skippable tour of the hub. Skip anytime — this never blocks the games below.",
  },
  {
    selector: "#game-search-input",
    title: "Search & filter",
    text: "Search by name or description, or narrow by tag. Your last search and filter are remembered across visits.",
  },
  {
    selector: "#game-sort",
    title: "Sort the lobby",
    text: "Sort by highest rated or most saved — most saved is usually the more honest \"popular\" signal.",
  },
  {
    selector: ".title-card",
    title: "Title cards",
    text: "Each game gets its own card: a short blurb, tags, when it was last updated, and a star-rating/comment box right on the card.",
  },
  {
    selector: "#account-section",
    title: "Accounts (optional)",
    text: "Sign in to sync saves and achievement progress across devices — or skip it entirely and just play. Save codes work without an account too.",
  },
  {
    selector: "#community-highlights-section",
    title: "Community Highlights",
    text: "A rotating, anonymized fact drawn from real aggregate player data across the site, once enough saves exist to share one safely.",
  },
  {
    selector: "a[href='whats-new.html']",
    title: "What's New",
    text: "A live changelog of what actually shipped recently, parsed straight from this project's own dev logs.",
  },
  {
    selector: "#site-feedback-section",
    title: "Feedback",
    text: "General feedback about the hub itself (not one specific game) goes here. Thanks for stopping by!",
  },
];
// Z13's onboarding survey (below) is also a first-visit modal -- to avoid
// stacking two overlays on top of each other on someone's very first load,
// the tour's own auto-start is deferred until after the survey closes
// (whether saved or skipped) when the survey is actually going to show.
// `shared/tutorial.js` itself stays untouched: this just controls *when*
// `init()` (which both wires "Take the Tour" and schedules the auto-start)
// gets called, exactly as before for anyone who's already past the survey.
function startHubTourIfNeeded() {
  if (window.GameTutorial) {
    window.GameTutorial.init(HUB_TOUR_STEPS, { gameId: "hub" });
  }
}

// --- Z13/Z19: onboarding survey + "New Player? Start here" recommendation ---
// Z13: a one-time, optional, skippable survey built here (not through shared/tutorial.js, it is a short pills
// form) that feeds the existing tag filter; no new tags. Q1 subjects (multi-select), Q2 depth (single).
// #game-tag-filter holds one value, so the default is: exactly one subject wins, otherwise the depth answer,
// otherwise "All tags". It then behaves like a manual pick (same hub_filter_tag key).
// Z19: a dismissible banner recommending one game to a visitor with no last-played key yet, using the
// survey's subject when there is one.
const ONBOARDING_SEEN_KEY = "hub-onboarding-seen";
const ONBOARDING_INTERESTS_KEY = "hub-onboarding-interests";
const NEW_PLAYER_BANNER_DISMISSED_KEY = "hub-new-player-banner-dismissed";

const ONBOARDING_SUBJECTS = [
  { value: "climate", label: "Climate" },
  { value: "civilization", label: "Civilization" },
  { value: "economy", label: "Economy" },
  { value: "language-learning", label: "Language Learning" },
  { value: "space", label: "Space" },
];
const ONBOARDING_DEPTHS = [
  { value: "quick", label: "Quick games" },
  { value: "deep-systems", label: "Deep systems" },
  { value: "", label: "No preference" },
];

function loadOnboardingAnswers() {
  try {
    const raw = lsGet(ONBOARDING_INTERESTS_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    if (!parsed || typeof parsed !== "object") return { subjects: [], depth: "" };
    return {
      subjects: Array.isArray(parsed.subjects)
        ? parsed.subjects.filter((s) => ONBOARDING_SUBJECTS.some((o) => o.value === s))
        : [],
      depth:
        typeof parsed.depth === "string" && ONBOARDING_DEPTHS.some((o) => o.value === parsed.depth)
          ? parsed.depth
          : "",
    };
  } catch (err) {
    return { subjects: [], depth: "" };
  }
}

function saveOnboardingAnswers(answers) {
  lsSet(ONBOARDING_INTERESTS_KEY, JSON.stringify(answers));
  let defaultTag = "";
  if (answers.subjects.length === 1) defaultTag = answers.subjects[0];
  else if (answers.depth) defaultTag = answers.depth;
  if (defaultTag && gameTagFilter && Array.from(gameTagFilter.options).some((o) => o.value === defaultTag)) {
    gameTagFilter.value = defaultTag;
    lsSet(FILTER_TAG_KEY, defaultTag);
    applyGameFilter();
    applySort();
  }
  // The New Player banner (if showing) was already computed once at page
  // load, before these answers existed -- refresh its pick now so a saved
  // subject interest is reflected immediately, not just on the next visit.
  maybeShowNewPlayerBanner();
}

function buildOnboardingSurvey(onClose) {
  if (document.getElementById("onboarding-survey-overlay")) return;
  if (!document.getElementById("onboarding-survey-styles")) {
    const style = document.createElement("style");
    style.id = "onboarding-survey-styles";
    style.textContent = `
      #onboarding-survey-overlay {
        position: fixed;
        inset: 0;
        z-index: 10500;
        background: rgba(4, 5, 10, 0.65);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1rem;
        font-family: inherit;
      }
      #onboarding-survey-card {
        max-width: min(440px, calc(100vw - 2rem));
        max-height: calc(100vh - 2rem);
        overflow-y: auto;
        background: linear-gradient(165deg, rgba(24, 27, 43, 0.96), rgba(14, 16, 28, 0.98));
        border: 1px solid rgba(140, 160, 255, 0.22);
        border-radius: 18px;
        padding: 1.5rem 1.6rem 1.6rem;
        color: #eaeaf0;
        box-shadow: 0 16px 50px rgba(0, 0, 0, 0.55);
      }
      #onboarding-survey-card h2 {
        font-size: 1.1rem;
        margin: 0 0 0.4rem;
      }
      #onboarding-survey-card .onboarding-intro {
        font-size: 0.82rem;
        opacity: 0.7;
        margin: 0 0 1.2rem;
        line-height: 1.5;
      }
      #onboarding-survey-card .onboarding-question {
        font-size: 0.88rem;
        font-weight: 600;
        margin: 0 0 0.6rem;
      }
      .onboarding-pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 0 0 1.4rem;
      }
      .onboarding-pill {
        font-size: 0.78rem;
        padding: 0.45rem 0.85rem;
        border-radius: 999px;
        background: rgba(140, 160, 255, 0.1);
        border: 1px solid rgba(140, 160, 255, 0.25);
        color: #eaeaf0;
        cursor: pointer;
        transition: background 0.15s ease, border-color 0.15s ease;
      }
      .onboarding-pill:hover { background: rgba(140, 160, 255, 0.2); }
      .onboarding-pill[aria-pressed="true"] {
        background: linear-gradient(135deg, #4a6cb5, #2c4370);
        border-color: rgba(140, 160, 255, 0.6);
        font-weight: 600;
      }
      #onboarding-survey-buttons {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-top: 0.4rem;
      }
      #onboarding-survey-buttons button.secondary {
        width: auto;
      }
      #onboarding-skip-button {
        margin-left: auto;
        background: none !important;
        color: inherit;
        opacity: 0.65;
        box-shadow: none !important;
        border: none !important;
        text-decoration: underline;
        cursor: pointer;
        font-size: 0.8rem;
      }
      #onboarding-skip-button:hover { opacity: 0.9; }
    `;
    document.head.appendChild(style);
  }

  const overlay = document.createElement("div");
  overlay.id = "onboarding-survey-overlay";
  const card = document.createElement("div");
  card.id = "onboarding-survey-card";
  card.setAttribute("role", "dialog");
  card.setAttribute("aria-modal", "true");
  card.setAttribute("aria-labelledby", "onboarding-survey-heading");
  overlay.appendChild(card);

  const heading = document.createElement("h2");
  heading.id = "onboarding-survey-heading";
  heading.textContent = "Welcome! Two quick, optional questions";
  const intro = document.createElement("p");
  intro.className = "onboarding-intro";
  intro.textContent =
    "This just sets the game filter below to match what you're after — skip it any time, and you can always change the filter yourself later.";
  card.appendChild(heading);
  card.appendChild(intro);

  const selectedSubjects = new Set();
  let selectedDepth = "";

  const q1 = document.createElement("p");
  q1.className = "onboarding-question";
  q1.textContent = "What are you interested in? (pick any)";
  card.appendChild(q1);
  const subjectRow = document.createElement("div");
  subjectRow.className = "onboarding-pill-row";
  subjectRow.setAttribute("role", "group");
  subjectRow.setAttribute("aria-label", "Subjects of interest");
  ONBOARDING_SUBJECTS.forEach((opt) => {
    const pill = document.createElement("button");
    pill.type = "button";
    pill.className = "onboarding-pill";
    pill.textContent = opt.label;
    pill.setAttribute("aria-pressed", "false");
    pill.addEventListener("click", () => {
      if (selectedSubjects.has(opt.value)) {
        selectedSubjects.delete(opt.value);
        pill.setAttribute("aria-pressed", "false");
      } else {
        selectedSubjects.add(opt.value);
        pill.setAttribute("aria-pressed", "true");
      }
    });
    subjectRow.appendChild(pill);
  });
  card.appendChild(subjectRow);

  const q2 = document.createElement("p");
  q2.className = "onboarding-question";
  q2.textContent = "Quick games or deep systems?";
  card.appendChild(q2);
  const depthRow = document.createElement("div");
  depthRow.className = "onboarding-pill-row";
  depthRow.setAttribute("role", "radiogroup");
  depthRow.setAttribute("aria-label", "Preferred depth");
  const depthPills = [];
  ONBOARDING_DEPTHS.forEach((opt) => {
    const pill = document.createElement("button");
    pill.type = "button";
    pill.className = "onboarding-pill";
    pill.textContent = opt.label;
    pill.setAttribute("role", "radio");
    pill.setAttribute("aria-checked", "false");
    pill.addEventListener("click", () => {
      selectedDepth = opt.value;
      depthPills.forEach((p) => {
        const active = p.value === opt.value;
        p.el.setAttribute("aria-checked", String(active));
        p.el.setAttribute("aria-pressed", String(active));
      });
    });
    depthPills.push({ el: pill, value: opt.value });
    depthRow.appendChild(pill);
  });
  card.appendChild(depthRow);

  const buttons = document.createElement("div");
  buttons.id = "onboarding-survey-buttons";
  const saveBtn = document.createElement("button");
  saveBtn.type = "button";
  saveBtn.className = "secondary";
  saveBtn.textContent = "Save preferences";
  saveBtn.addEventListener("click", () => {
    saveOnboardingAnswers({ subjects: Array.from(selectedSubjects), depth: selectedDepth });
    finish();
  });
  const skipBtn = document.createElement("button");
  skipBtn.type = "button";
  skipBtn.id = "onboarding-skip-button";
  skipBtn.textContent = "Skip";
  skipBtn.addEventListener("click", finish);
  buttons.appendChild(saveBtn);
  buttons.appendChild(skipBtn);
  card.appendChild(buttons);

  document.body.appendChild(overlay);

  function finish() {
    lsSet(ONBOARDING_SEEN_KEY, "1");
    overlay.remove();
    document.removeEventListener("keydown", onKeydown);
    showInstallBannerIfAllowed();
    if (typeof onClose === "function") onClose();
  }
  function onKeydown(e) {
    if (e.key === "Escape") finish();
  }
  document.addEventListener("keydown", onKeydown);
  // Plain .focus() scrolls its nearest scrollable ancestor (this card,
  // overflow-y: auto) to bring the button into view -- on a short viewport
  // that scrolls straight past the heading/questions to the bottom before
  // the player has read anything. Same preventScroll fix already used
  // elsewhere in this file (e.g. accountUsernameDisplay.focus() above).
  heading.setAttribute("tabindex", "-1");
  heading.focus({ preventScroll: true });
}

function maybeShowOnboardingSurvey() {
  if (lsGet(ONBOARDING_SEEN_KEY)) return false;
  buildOnboardingSurvey(startHubTourIfNeeded);
  return true;
}

// "New" reuses the exact same signal Z2/Z14's last-played badges are built
// on (localStorage "last-played:<slug>", stamped by shared/last-played.js
// on every game page load) rather than inventing a second "is this player
// new" heuristic -- a visitor with even one such key has genuinely opened a
// game here before, whatever the survey did or didn't capture.
const RECOMMENDED_GAME_BY_SUBJECT = {
  climate: "canopy",
  "language-learning": "champ-de-mots",
  economy: "trade-empire",
  space: "sol",
  civilization: "continuum",
};
// Priority when more than one subject was picked, and the pool this falls
// back to for a subject with more than one matching game: favour the games
// with the shortest onboarding curve and no combat/reading load (see root
// CLAUDE.md's "Current games" table) -- the climate quartet's single-plot,
// single-mechanic games read fastest, French vocab needs zero prior
// game-mechanic learning, trading and especially Continuum (seven eras, a
// research tree, a livability score) ask the most of a first-ever visitor.
const RECOMMENDATION_SUBJECT_PRIORITY = ["climate", "language-learning", "economy", "space", "civilization"];
// Fallback pick with no survey signal at all: same one the TODO.md item
// itself suggested, and still the right call on its own merits -- simplest
// onboarding curve of any game on the hub, a clear payoff within a couple
// of minutes, no combat or reading load.
const DEFAULT_RECOMMENDED_GAME = "canopy";

function isNewPlayer() {
  try {
    return !Object.keys(localStorage).some((k) => k.startsWith("last-played:"));
  } catch (err) {
    return false; // storage unavailable -- safest is to not claim "new"
  }
}

function pickRecommendedGame() {
  const answers = loadOnboardingAnswers();
  const picked = RECOMMENDATION_SUBJECT_PRIORITY.find((s) => answers.subjects.includes(s));
  const slug = (picked && RECOMMENDED_GAME_BY_SUBJECT[picked]) || DEFAULT_RECOMMENDED_GAME;
  // Y-22: someone who answered "Quick games" should not be handed a long-form
  // game as their first pick. If the subject's usual pick is long-form and the
  // same subject has a shorter game (session lengths come from
  // game-sessions.json), use that one instead; otherwise keep the usual pick.
  if (answers.depth === "quick" && picked && gameSessions && gameSessions.games[slug] === "long") {
    const shorter = allTitleCards.find(
      (card) =>
        (card.dataset.tags || "").split(/\s+/).includes(picked) &&
        cardSession(card) && cardSession(card) !== "long"
    );
    if (shorter) return cardSlug(shorter);
  }
  return slug;
}

function maybeShowNewPlayerBanner() {
  const banner = document.getElementById("new-player-banner");
  if (!banner) return;
  if (lsGet(NEW_PLAYER_BANNER_DISMISSED_KEY) || !isNewPlayer()) {
    banner.hidden = true;
    return;
  }
  const slug = pickRecommendedGame();
  const card = allTitleCards.find((c) => cardSlug(c) === slug);
  if (!card) {
    banner.hidden = true;
    return;
  }
  const name = card.querySelector(".title-card-name")?.textContent || slug;
  const href = card.querySelector(".title-card-link")?.getAttribute("href") || gameHrefForId(slug);
  const bannerText = document.getElementById("new-player-banner-text");
  if (bannerText) {
    const tier = cardSession(card);
    const tierLabel = tier && gameSessions.tiers[tier] ? gameSessions.tiers[tier].toLowerCase() : "";
    const lengthNote = tierLabel ? (tier === "long" ? " (a long-form game)" : ` (${tierLabel} a sitting)`) : "";
    bannerText.textContent = `New here? Start with ${name}${lengthNote} — a simple, approachable first pick before exploring the rest of the lobby.`;
  }
  const goLink = document.getElementById("new-player-banner-cta");
  if (goLink) {
    goLink.href = href;
    goLink.textContent = `Play ${name}`;
  }
  banner.hidden = false;
}

document.getElementById("new-player-banner-dismiss")?.addEventListener("click", () => {
  lsSet(NEW_PLAYER_BANNER_DISMISSED_KEY, "1");
  const banner = document.getElementById("new-player-banner");
  if (banner) banner.hidden = true;
});

if (!maybeShowOnboardingSurvey()) {
  startHubTourIfNeeded();
}
maybeShowNewPlayerBanner();

// --- Y22 / Z10: difficulty-variant marker on title cards ---
// A small hub-side registry (no per-game manifest format exists yet): a game earns an entry once it ships an
// opt-in difficulty variant. Today only Continuum's hard mode.
const GAMES_WITH_DIFFICULTY_VARIANT = {
  continuum: "Hard Mode available",
};

function loadDifficultyBadges() {
  document.querySelectorAll(".title-card").forEach((card) => {
    const slug = cardSlug(card);
    const label = slug && GAMES_WITH_DIFFICULTY_VARIANT[slug];
    if (!label) return;
    const tagsRow = card.querySelector(".title-card-tags");
    if (!tagsRow || tagsRow.querySelector(".tag-pill--difficulty")) return;
    const pill = document.createElement("span");
    pill.className = "tag-pill tag-pill--difficulty";
    // Icon + text, never color alone, per this repo's own colorblind-safety
    // audit convention (see root CLAUDE.md's "Working notes").
    pill.textContent = `⚔ ${label}`;
    tagsRow.appendChild(pill);
  });
}
loadDifficultyBadges();

// --- Y-22: estimated session length chip + filter ---
// The chip sits right under the game's name (not in the tag row) so it still
// shows on compact cards. Text, not colour, carries the meaning.
async function loadSessionLengths() {
  try {
    const res = await fetch("game-sessions.json");
    if (!res.ok) throw new Error(`status ${res.status}`);
    const data = await res.json();
    if (!data || typeof data.games !== "object" || typeof data.tiers !== "object") throw new Error("bad shape");
    gameSessions = data;
  } catch (err) {
    console.error("loadSessionLengths failed:", err);
    return;
  }
  allTitleCards.forEach((card) => {
    const tier = cardSession(card);
    const label = tier && gameSessions.tiers[tier];
    if (!label) return;
    card.dataset.session = tier;
    const nameEl = card.querySelector(".title-card-name");
    if (!nameEl || card.querySelector(".title-card-session")) return;
    const chip = document.createElement("p");
    chip.className = "title-card-session";
    chip.textContent = `\u23F1 ${label}`;
    chip.title = "Estimated length of one sitting";
    nameEl.insertAdjacentElement("afterend", chip);
  });
  applyGameFilter();
  maybeShowNewPlayerBanner();
}
loadSessionLengths();

// --- Y15: "Community Highlights" ---
// The stats backend never returns an individual save or playthrough (small groups are suppressed), so the
// highlights are real anonymised aggregates: an achievement's earn rate, or a numeric field's community mean.
// Fails to a plain message, like loadRatings().
const communityHighlightsText = document.getElementById("community-highlights-text");
let communityHighlights = [];
let communityHighlightIndex = 0;
let communityHighlightTimer = null;

function formatStatFieldLabel(path) {
  return path.split(".").pop().replace(/_/g, " ");
}

function showCommunityHighlight() {
  if (communityHighlightsText && communityHighlights.length) {
    communityHighlightsText.textContent = communityHighlights[communityHighlightIndex];
  }
}

async function loadCommunityHighlights() {
  if (!communityHighlightsText) return;
  if (hubReduceData()) {
    // Y-26: no statistics requests at all while reduce-data is on.
    communityHighlightsText.textContent =
      "Community highlights are off while \u201creduce data\u201d is on. You can change that in Settings.";
    return;
  }
  try {
    const [achRes, gamesRes] = await Promise.all([
      fetch(`${RATINGS_API_BASE}/stats/achievements`),
      fetch(`${RATINGS_API_BASE}/stats/games`),
    ]);
    if (!achRes.ok || !gamesRes.ok) throw new Error(`status ${achRes.status}/${gamesRes.status}`);
    const achData = await achRes.json();
    const gamesMeta = await gamesRes.json();

    const highlights = [];
    // /stats/achievements answers {min_bucket, games: {slug: {...}}}.
    Object.entries((achData && achData.games) || {}).forEach(([gameId, info]) => {
      if (!info || info.suppressed) return;
      const label = GAME_DISPLAY_NAMES[gameId] || gameId;
      Object.entries(info.achievements || {}).forEach(([achId, stat]) => {
        highlights.push(
          `${stat.earned_pct}% of ${label} players have earned "${achId.replace(/_/g, " ")}" so far.`
        );
      });
    });

    // One extra field-summary highlight, from a single randomly-picked
    // known game — one extra request, not one per game, on every hub load.
    const gameIds = Object.keys((gamesMeta && gamesMeta.games) || {});
    const sampleGame = gameIds.length ? gameIds[Math.floor(Math.random() * gameIds.length)] : null;
    if (sampleGame) {
      try {
        const fieldRes = await fetch(`${RATINGS_API_BASE}/stats/games/${sampleGame}`);
        if (fieldRes.ok) {
          const summary = await fieldRes.json();
          const fields = summary && !summary.suppressed ? Object.entries(summary.fields || {}) : [];
          if (fields.length) {
            const [path, stat] = fields[Math.floor(Math.random() * fields.length)];
            const label = GAME_DISPLAY_NAMES[sampleGame] || sampleGame;
            highlights.push(
              `The average ${label} player has reached ${formatStatFieldLabel(path)} ${stat.mean} across ${stat.count} shared saves.`
            );
          }
        }
      } catch (err) {
        console.error(`loadCommunityHighlights: per-game field fetch failed for ${sampleGame}:`, err);
      }
    }

    if (!highlights.length) {
      communityHighlightsText.textContent =
        "Not enough shared saves yet for a community highlight — check back once more players have saved a run.";
      return;
    }
    communityHighlights = highlights;
    communityHighlightIndex = 0;
    showCommunityHighlight();
    if (communityHighlightTimer) window.clearInterval(communityHighlightTimer);
    if (communityHighlights.length > 1) {
      communityHighlightTimer = window.setInterval(() => {
        communityHighlightIndex = (communityHighlightIndex + 1) % communityHighlights.length;
        showCommunityHighlight();
      }, 9000);
    }
  } catch (err) {
    // Expected right now — Z1 isn't deployed to production yet. Same
    // "fail to a plain message, not an error" stance as every other
    // Z1-dependent feature in this codebase.
    console.error("loadCommunityHighlights failed:", err);
    communityHighlightsText.textContent = "Community highlights aren't available yet — check back soon.";
  }
}
loadCommunityHighlights();

// --- Y29: opt-in pageview counter ---
// Off until the visitor ticks the box (per-device localStorage flag). POST /stats/pageview sends no IP, user agent or
// referrer: the backend only inserts a row with an id and a timestamp. Falls back to a plain message if the
// endpoint is not live yet.
const PAGEVIEW_OPT_IN_KEY = "hub_pageview_opt_in";

function pageviewOptedIn() {
  return lsGet(PAGEVIEW_OPT_IN_KEY) === "1";
}

async function recordAndShowPageview() {
  const countEl = document.getElementById("pageview-count");
  if (!countEl) return;
  try {
    const res = await fetch(`${RATINGS_API_BASE}/stats/pageview`, { method: "POST" });
    if (!res.ok) throw new Error(`status ${res.status}`);
    const data = await res.json();
    const total = typeof data.total === "number" ? data.total.toLocaleString() : "?";
    countEl.textContent = `${total} counted visits.`;
  } catch (err) {
    // Falls back to a plain message rather than erroring -- same stance as
    // Y15 -- covering both a genuinely offline backend and the window
    // before a deploy picks up this endpoint.
    console.error("recordAndShowPageview failed:", err);
    countEl.textContent = "Visitor count isn't available yet — check back soon.";
  }
}

function initPageviewCounter() {
  const checkbox = document.getElementById("pageview-optin-checkbox");
  const countEl = document.getElementById("pageview-count");
  if (!checkbox || !countEl) return;
  checkbox.checked = pageviewOptedIn();
  checkbox.addEventListener("change", () => {
    lsSet(PAGEVIEW_OPT_IN_KEY, checkbox.checked ? "1" : "0");
    if (checkbox.checked) {
      recordAndShowPageview();
    } else {
      countEl.textContent = "Opt in to help count visits.";
    }
  });
  if (pageviewOptedIn()) {
    recordAndShowPageview();
  } else {
    countEl.textContent = "Opt in to help count visits.";
  }
}
initPageviewCounter();

// The small surface the hub-*.js helper scripts (loaded after this file) use, so they do not depend on
// this file's private names. pickRecommendedGame / isNewPlayer are the Z13/Z19 onboarding code.
window.HubLobby = {
  cards: allTitleCards,
  slugOf: cardSlug,
  nameOf: (card) => (card.querySelector(".title-card-name")?.textContent || "").trim(),
  hrefOf: (card) => card.querySelector(".title-card-link")?.getAttribute("href") || "",
  pickRecommendedGame,
  isNewPlayer,
  onboardingAnswers: loadOnboardingAnswers,
  playedSlugs,
  achievementProgress: hubAchievementProgress,
  applyFilter: applyGameFilter,
  sessionOf: cardSession,
};

// A page restored from the browser's back/forward cache (e.g. Back from a
// game, or a tab re-shown) keeps its old DOM and never re-runs any of the
// loaders above, so new achievements/saves/last-played badges only appeared
// after a manual reload. Reload instead of trying to patch each section.
window.addEventListener("pageshow", (event) => {
  if (event.persisted) location.reload();
});
