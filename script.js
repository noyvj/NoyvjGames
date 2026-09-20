const RATINGS_API_BASE = "https://noyvjgames.fastapicloud.dev";
// HUB_AUTH_TOKEN_KEY/hubGetBearerToken()/hubAuthHeaders() come from
// shared/hub-auth.js (loaded before this file — see index.html), the same
// bearer-token helpers shared/save-widget.js uses, so both files can't
// drift out of sync on the localStorage key or header shape. Shared across
// every page on the site (localStorage is keyed by origin, not path) —
// this is how a game page's save widget knows whether the player is
// signed in without its own account UI.
const AUTH_USERNAME_KEY = "hub_account_username";
// Y12: the backend doesn't expose an account-created date yet, so "member
// since" is only known for accounts created on this device (recorded at
// signup); it's simply omitted otherwise rather than guessed.
const AUTH_SINCE_KEY = "hub_account_since";

function bindStarRating(ratingWidget) {
  const stars = ratingWidget.querySelectorAll(".star");
  stars.forEach((star) => {
    star.addEventListener("click", () => {
      const value = Number(star.dataset.value);
      ratingWidget.dataset.rating = String(value);
      stars.forEach((s) => {
        s.classList.toggle("selected", Number(s.dataset.value) <= value);
      });
    });
  });
}

function resetStarRating(ratingWidget) {
  ratingWidget.dataset.rating = "0";
  ratingWidget.querySelectorAll(".star").forEach((s) => s.classList.remove("selected"));
}

// Y6: a five-star glyph row filled to the average's fraction (a
// hard-stop gradient clipped to the text), sitting beside the numeric
// text rather than replacing it -- the number stays the source of truth
// for screen readers and anyone who can't tell partial fills apart.
function renderSummary(widget, ratings) {
  const summary = widget.querySelector(".ratings-summary");
  const card = widget.closest(".title-card");
  summary.classList.remove("is-loading");
  summary.removeAttribute("aria-busy");
  // /ratings/{slug} also returns per-game text-feedback-prompt rows
  // (stars: null, response: "...") alongside this widget's own star
  // submissions — both share the same table, filtered only by game_slug.
  // Only star rows belong in a star average.
  const starRatings = ratings.filter((r) => typeof r.stars === "number");
  if (!starRatings.length) {
    summary.textContent = "No reviews yet — be the first.";
    if (card) { card.dataset.avg = "0"; card.dataset.reviewCount = "0"; }
    return;
  }
  const average = starRatings.reduce((sum, r) => sum + r.stars, 0) / starRatings.length;
  const count = starRatings.length;
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

async function loadRatings(widget) {
  const slug = widget.dataset.gameSlug;
  const summary = widget.querySelector(".ratings-summary");
  try {
    const response = await fetch(`${RATINGS_API_BASE}/ratings/${slug}`);
    if (!response.ok) throw new Error(`status ${response.status}`);
    renderSummary(widget, await response.json());
  } catch (err) {
    // Logged so "reviews unavailable" is debuggable from the browser
    // console at all — the only place this context is ever visible for a
    // personal-site-scale project with no server-side error tracking.
    console.error(`loadRatings(${slug}) failed:`, err);
    summary.classList.remove("is-loading");
    summary.removeAttribute("aria-busy");
    summary.textContent = "Reviews unavailable right now.";
  }
  // Ratings arriving (or a new submission) can change a rating-sorted order.
  if (typeof applySort === "function") applySort();
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
    await loadRatings(widget);
  } catch (err) {
    submitButton.textContent = "Submit failed — try again";
    submitButton.disabled = false;
  }
}

document.querySelectorAll(".review-widget").forEach((widget) => {
  bindStarRating(widget.querySelector(".star-rating"));
  widget.querySelector(".comment-submit").addEventListener("click", () => submitRating(widget));
  loadRatings(widget);
});

// --- "Last updated" badge per title card (TODO.md L7) ---
//
// Sourced from real git history, not a hand-maintained date — with a
// dozen-plus games on the hub, a hand-typed date would go stale the first
// time anyone touched a game without also remembering to update it here.
// `game-last-updated.json` is a small committed file (sibling to
// index.html) regenerated by `scripts/generate-last-updated.py`, which
// runs `git log -1 --date=format:"%Y-%m-%d" -- games/<slug>/` per game —
// see that script's own docstring for when to re-run it. Each title card
// already carries its slug on its `.review-widget[data-game-slug]` child,
// so no extra markup is needed to find the right date per card.
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

// --- Hub lobby search/tag filter (TODO.md "hub lobby improvements", L11/L12) ---
//
// Tag taxonomy decision (documented here rather than left implicit, same
// as the L5 dark/light-theme call in TODO.md): two independent axes, not
// an arbitrary free-for-all tag set.
//   - Subject-area (what the game is actually about): "climate" for all 8
//     climate-quartet games, "civilization" for Continuum (spans many
//     subjects/SDGs across its seven eras, not just climate), "economy"
//     for Trade Empire (trading/market sim), "language-learning" for Le
//     Champ de Mots, "space" for SOL (the one game with no real-world
//     teaching subject behind it).
//   - Depth ("quick" vs "deep systems", L12's original suggestion): the
//     8 climate-quartet games are each a single focused session-length
//     mechanic ("quick"); SOL, Continuum, Trade Empire, and Le Champ de
//     Mots each layer multiple interacting systems/progression trees
//     built over many milestones ("deep systems").
// Tags live as a space-separated `data-tags` attribute on each
// `.title-card` article and are also rendered as visible pills (see
// `.title-card-tags` in style.css) per L12's "tags per title card" ask.
// Search and tag filter combine (AND) and share one mechanism.
const gameSearchInput = document.getElementById("game-search-input");
const gameTagFilter = document.getElementById("game-tag-filter");
const gameSortSelect = document.getElementById("game-sort");
const gameSortStatus = document.getElementById("game-sort-status");
const gameFilterEmpty = document.getElementById("game-filter-empty");
const gameGrid = document.getElementById("game-grid");
const allTitleCards = Array.from(document.querySelectorAll(".title-card"));

// Small localStorage helpers: storage can throw (private windows, blocked
// site data), and every use here is a convenience, never required state.
function lsGet(key) {
  try { return localStorage.getItem(key); } catch (err) { return null; }
}
function lsSet(key, value) {
  try { localStorage.setItem(key, value); } catch (err) { /* convenience only */ }
}

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

function applyGameFilter() {
  const query = gameSearchInput.value.trim().toLowerCase();
  const tag = gameTagFilter.value;
  let visibleCount = 0;
  allTitleCards.forEach((card) => {
    const tags = (card.dataset.tags || "").split(/\s+/);
    const matchesTag = !tag || tags.includes(tag);
    const inBase = !query || cardBaseText(card).includes(query);
    const inExtra = !!query && !inBase && (extraSearchText.get(card) || "").includes(query);
    const visible = matchesTag && (inBase || inExtra);
    card.hidden = !visible;
    const note = card.querySelector(".title-card-match-note");
    if (note) note.hidden = !(visible && inExtra);
    if (visible) visibleCount += 1;
  });
  gameFilterEmpty.hidden = visibleCount > 0;
}

// --- Y21: sort modes (default / highest rated / most saved) ---
// Rating average comes from each card's own review widget
// (data-avg, set by renderSummary). Save count is the more honest
// popularity signal while reviews skew toward test/friend accounts; it's
// read through loadSaveCounts(), kept deliberately isolated so it can be
// repointed at a dedicated public per-game count endpoint without touching
// the sort code. Currently it uses the public GET /admin/stats
// `saves_by_game` map, and returns null (graceful fallback to default
// order + a status line) if that's unreachable.
let saveCountsPromise = null;
function loadSaveCounts() {
  if (!saveCountsPromise) {
    saveCountsPromise = fetch(`${RATINGS_API_BASE}/admin/stats`)
      .then((res) => {
        if (!res.ok) throw new Error(`status ${res.status}`);
        return res.json();
      })
      .then((body) => (body && typeof body.saves_by_game === "object" ? body.saves_by_game : null))
      .catch((err) => {
        console.error("loadSaveCounts failed:", err);
        return null;
      });
  }
  return saveCountsPromise;
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
  if (gameSortSelect) {
    gameSortSelect.addEventListener("change", () => {
      lsSet(SORT_MODE_KEY, gameSortSelect.value);
      applySort();
    });
  }
  if (gameSearchInput.value.trim()) loadExtendedSearchIndex();
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
// hubGetBearerToken()/hubAuthHeaders() come from shared/hub-auth.js.

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
const continuePlayingSection = document.getElementById("continue-playing-section");
const continuePlayingList = document.getElementById("continue-playing-list");

// --- "Claim your save" nudge for anonymous players (TODO.md L15) ---
//
// Threshold deliberately kept cheap per the TODO note: any local save
// code at all counts as "clearly invested real time" — every
// shared/save-widget.js save is an explicit, player-initiated action
// (there's no autosave to trigger this from a single accidental click),
// so one `savecode:<slug>` key already means someone chose to save
// progress in a game. Not shown at all once signed in — a signed-in
// player's saves are either already claimed or trivially claimable from
// each game's own "Claim this save" button, so the nudge would just be
// noise. Dismissal is permanent (a hub-wide localStorage flag), same
// "respect the player's choice, don't re-nag" posture as every other
// dismissible bit of hub UI. Declared here, ahead of showSignedIn/
// showSignedOut below, since both call maybeShowClaimSaveNudge() and are
// themselves invoked (from the bottom of this file) before any code
// further down would otherwise have run.
const CLAIM_NUDGE_DISMISSED_KEY = "claim_save_nudge_dismissed";
const claimSaveNudge = document.getElementById("claim-save-nudge");
const claimSaveNudgeCta = document.getElementById("claim-save-nudge-cta");
const claimSaveNudgeDismiss = document.getElementById("claim-save-nudge-dismiss");

function anonymousSaveCodeSlugs() {
  return Object.keys(localStorage)
    .filter((key) => key.startsWith("savecode:"))
    .map((key) => key.slice("savecode:".length));
}

function maybeShowClaimSaveNudge() {
  if (!claimSaveNudge) return;
  const alreadySignedIn = Boolean(hubGetBearerToken());
  const dismissed = localStorage.getItem(CLAIM_NUDGE_DISMISSED_KEY);
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
    localStorage.setItem(CLAIM_NUDGE_DISMISSED_KEY, "1");
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

function showSignedOut() {
  updateSignedInPill(null);
  accountSignedOut.hidden = false;
  accountSignedIn.hidden = true;
  continuePlayingSection.hidden = true;
  continuePlayingList.innerHTML = "";
  maybeShowClaimSaveNudge();
}

function showSignedIn(username) {
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
  loadMySaves();
  loadAchievementsDashboard();
  loadContinuePlaying();
  maybeShowClaimSaveNudge();
}

async function loadMySaves() {
  accountMySaves.textContent = "Loading your saves…";
  try {
    const res = await fetch(`${RATINGS_API_BASE}/users/me/saves`, { headers: hubAuthHeaders() });
    if (!res.ok) throw new Error(`status ${res.status}`);
    const saves = await res.json();
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
      copyButton.addEventListener("click", () => {
        navigator.clipboard.writeText(save.save_code);
        copyButton.textContent = "Copied!";
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
  "aftermath", "herd", "thaw", "loop", "drift", "champ-de-mots",
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
};

const accountAchievementsDashboard = document.getElementById("account-achievements-dashboard");

function renderProgressBar(container, label, earned, total) {
  const row = document.createElement("div");
  row.className = "achievements-bar-row";
  const labelEl = document.createElement("p");
  labelEl.className = "achievements-bar-label";
  labelEl.textContent = `${label}: ${earned}/${total}`;
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
  try {
    const res = await fetch(`${RATINGS_API_BASE}/users/me/saves`, { headers: hubAuthHeaders() });
    if (!res.ok) throw new Error(`status ${res.status}`);
    const saves = await res.json();
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

async function loadAchievementsDashboard() {
  const gameIds = await loadAchievementGameIds();
  if (!gameIds.length) {
    accountAchievementsDashboard.innerHTML = "";
    return;
  }
  accountAchievementsDashboard.textContent = "Loading achievement progress…";
  try {
    const [savesRes, ...catalogResults] = await Promise.all([
      fetch(`${RATINGS_API_BASE}/users/me/saves`, { headers: hubAuthHeaders() }),
      ...gameIds.map((gameId) =>
        fetch(`games/${gameId}/achievements.json`)
          .then((res) => (res.ok ? res.json() : null))
          .catch(() => null)
      ),
    ]);
    if (!savesRes.ok) throw new Error(`status ${savesRes.status}`);
    const saves = await savesRes.json();

    accountAchievementsDashboard.innerHTML = "";
    const heading = document.createElement("p");
    heading.className = "achievements-dashboard-heading";
    heading.textContent = "Achievements";
    accountAchievementsDashboard.appendChild(heading);

    let totalEarned = 0;
    let totalPossible = 0;
    let anyGameRendered = false;

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

      renderProgressBar(
        accountAchievementsDashboard,
        GAME_DISPLAY_NAMES[gameId] || gameId,
        earned,
        total
      );
      totalEarned += earned;
      totalPossible += total;
      anyGameRendered = true;
    });

    if (!anyGameRendered) {
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
    renderProgressBar(accountAchievementsDashboard, "All games", totalEarned, totalPossible);
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
    localStorage.setItem(HUB_AUTH_TOKEN_KEY, body.bearer_token);
    localStorage.setItem(AUTH_USERNAME_KEY, body.username);
    if (endpoint === "/auth/signup") lsSet(AUTH_SINCE_KEY, new Date().toISOString().slice(0, 10));
    accountUsernameInput.value = "";
    accountPasswordInput.value = "";
    accountStatus.textContent = "";
    showSignedIn(body.username);
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

accountSignoutButton.addEventListener("click", () => {
  // The session is dropped immediately; only the view switch waits a beat
  // so a "Signed out" confirmation is actually seen (Y18).
  localStorage.removeItem(HUB_AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USERNAME_KEY);
  try { localStorage.removeItem(AUTH_SINCE_KEY); } catch (err) { /* convenience only */ }
  accountSignoutButton.disabled = true;
  accountSignoutButton.textContent = "Signed out \u2713";
  updateSignedInPill(null);
  setTimeout(() => {
    accountSignoutButton.disabled = false;
    accountSignoutButton.textContent = "Sign out";
    showSignedOut();
    accountStatus.textContent = "You've been signed out.";
  }, 900);
});

const savedUsername = localStorage.getItem(AUTH_USERNAME_KEY);
if (hubGetBearerToken() && savedUsername) {
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
      headers: { "Content-Type": "application/json", ...hubAuthHeaders() },
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

// "Add to Home Screen" install prompt banner (TODO.md L18) — browsers
// suppress their own install UI until `beforeinstallprompt` fires and we
// call .prompt() on it ourselves; without this, installability is real
// (the manifest/service worker already qualify) but invisible unless a
// visitor already knows to check their browser's own menu for it.
// Dismissal is permanent (a hub-wide localStorage flag), same
// "respect the player's choice, don't re-nag" posture as the claim-save
// nudge above. Never shown at all if the browser doesn't fire the event
// (e.g. Safari, or an already-installed instance of the site).
const PWA_INSTALL_DISMISSED_KEY = "pwa_install_banner_dismissed";
const pwaInstallBanner = document.getElementById("pwa-install-banner");
const pwaInstallCta = document.getElementById("pwa-install-cta");
const pwaInstallDismiss = document.getElementById("pwa-install-dismiss");
let deferredInstallPrompt = null;

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault();
  deferredInstallPrompt = event;
  if (pwaInstallBanner && !localStorage.getItem(PWA_INSTALL_DISMISSED_KEY)) {
    pwaInstallBanner.hidden = false;
  }
});

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
    localStorage.setItem(PWA_INSTALL_DISMISSED_KEY, "1");
    pwaInstallBanner.hidden = true;
  });
}

// --- Y10: "new since your last visit" badge on the What's New nav link ---
// whats-new.html records the newest entry date it showed
// (hub_whats_new_seen). Here we count dev-log entry headings dated after
// that. A first-ever visitor has no baseline, so no badge -- nothing is
// "new" to someone who has never looked. Fetched after load so it never
// competes with the lobby.
async function loadWhatsNewBadge() {
  const badge = document.getElementById("whats-new-badge");
  const seen = lsGet("hub_whats_new_seen");
  if (!badge || !seen) return;
  try {
    const texts = await Promise.all(
      ["BCM114-DEV-LOG.md", "BCM206-DEV-LOG.md"].map((path) =>
        fetch(path).then((res) => (res.ok ? res.text() : ""))
      )
    );
    let count = 0;
    texts.forEach((text) => {
      (text.match(/^### \d{4}-\d{2}-\d{2}/gm) || []).forEach((h) => {
        if (h.slice(4) > seen) count += 1;
      });
    });
    if (count > 0) {
      badge.textContent = String(count);
      badge.title = `${count} update${count === 1 ? "" : "s"} since your last visit`;
      badge.hidden = false;
    }
  } catch (err) {
    console.error("loadWhatsNewBadge failed:", err);
  }
}
loadWhatsNewBadge();

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

// --- Y13: light, skippable "site tour" onboarding for first-time hub
// visitors ---
//
// Reuses `shared/tutorial.js` unchanged (the same spotlight-walkthrough
// engine every game's own "How to Play"/tutorial-restart button already
// uses — see games/aftermath/index.html for the per-game pattern), just
// pointed at the hub's own DOM instead of a game's. `GameTutorial.init`
// only auto-starts once per `gameId` (localStorage `tutorial-seen:hub`)
// and is always optional: it never blocks the page, Escape/"Skip tutorial"
// dismiss it immediately, and the "Take the Tour" nav button (auto-wired
// by tutorial.js via its `tutorial-restart-button` id) re-opens it anytime.
// A step whose selector doesn't currently exist on the page just falls
// back to a centered card instead of erroring (see tutorial.js's own
// currentTarget()), so this stays safe across signed-in/out states and
// which optional sections happen to be visible.
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
if (window.GameTutorial) {
  window.GameTutorial.init(HUB_TOUR_STEPS, { gameId: "hub" });
}

// --- Y22 / Z10: difficulty/challenge-variant marker on title cards ---
//
// Z10's own framing ("reads each game's own difficulty flag") assumes a
// per-game manifest convention that doesn't exist yet — today exactly one
// hub-linked game actually ships an opt-in difficulty variant (Continuum's
// K18 hard mode; see root CLAUDE.md's "Current games" table). Rather than
// inventing a speculative per-game file format for a population of one,
// this is a small hub-side registry (the same shape as
// game-manifest.json/GAME_DISPLAY_NAMES above) that a game earns an
// entry in once it actually ships a variant. Deliberately does NOT touch
// games/continuum/ or any other game's own folder — purely a hub-level
// label describing already-public, already-shipped functionality.
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

// --- Y15: "Community Highlights" ---
//
// Z1's stats backend (planning/TODO.md Z1; app/stats.py) is built but not
// yet deployed to production, same caveat as every other "(needs Z1)" item
// in TODO.md — this degrades to a plain "not available yet" message
// instead of erroring, exactly like loadRatings()'s "Reviews unavailable
// right now." fallback above.
//
// Z1's privacy rules (stats.py's own docstring) mean no individual save or
// playthrough is ever returned — no min/max, nothing below MIN_BUCKET
// saves, no strings from a save. So there is no real "notable playthrough"
// in this backend's data model to feature. The honest analog built here
// instead: real anonymized aggregate facts (an achievement's real earn
// rate across everyone who's played that game, or a numeric field's real
// community mean) rotating through as "highlights" — still a genuine,
// live, privacy-respecting community fact, just aggregate rather than
// per-player.
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
  try {
    const [achRes, gamesRes] = await Promise.all([
      fetch(`${RATINGS_API_BASE}/stats/achievements`),
      fetch(`${RATINGS_API_BASE}/stats/games`),
    ]);
    if (!achRes.ok || !gamesRes.ok) throw new Error(`status ${achRes.status}/${gamesRes.status}`);
    const achData = await achRes.json();
    const gamesMeta = await gamesRes.json();

    const highlights = [];
    Object.entries(achData).forEach(([gameId, info]) => {
      if (!info || info.suppressed) return;
      const label = GAME_DISPLAY_NAMES[gameId] || gameId;
      Object.entries(info.achievements || {}).forEach(([achId, stat]) => {
        highlights.push(
          `Only ${stat.earned_pct}% of ${label} players have earned "${achId.replace(/_/g, " ")}" so far.`
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

// --- Y29: privacy-respecting, self-hosted pageview counter (opt-in) ---
//
// Off by default — a visit is only ever counted once someone explicitly
// opts in here, and the choice lives in localStorage (per-device, not
// per-account) so it's never assumed from an account or a previous visit.
// No IP, user agent, or referrer is collected by this code; the backend
// endpoint (POST /stats/pageview, app/main.py) only ever sees "one more
// opted-in visit happened," nothing that identifies who — a plain insert
// into a table with no columns beyond an id and a timestamp. Real
// first-party evidence of public availability for BCM206, without a
// third-party tracker. Still degrades gracefully below if that endpoint
// isn't live yet on the deployed backend (a fresh commit here can land
// before the next FastAPI Cloud deploy picks it up).
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
