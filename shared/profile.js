/*
 * Shared profile helper (TODO Z-7). A game calls ONE function at save time and the player's
 * account profile (total time played, achievements per game, longest streaks, seasonal badges) keeps
 * itself up to date, instead of the hub scraping save blobs:
 *
 *   <script src="../../shared/profile.js" data-game-id="canopy"></script>
 *   ...
 *   NoyvjProfile.update({ game: "canopy", seconds: 312, achievements: 7, streaks: { daily: 4 } });
 *
 * Every field is optional. `game` defaults to the script tag's data-game-id. `seconds` is the time
 * played SINCE THE LAST CALL; leave it out and the helper uses its own count of the seconds this page
 * was open and visible. `achievements` is a count (or an array of earned ids; its length is used) and
 * only ever raises the stored count. `streaks` maps a lowercase label to the player's current or best
 * run; the server keeps the longest.
 *
 * Promises it keeps:
 *   * It NEVER blocks or breaks saving: update() returns at once, does its work in the background and
 *     swallows every error (a blocked localStorage, no network, a server that is asleep).
 *   * It posts only for a SIGNED-IN player (the hub's bearer token). Signed out, it does nothing and
 *     remembers nothing.
 *   * It is throttled: at most one post per game every 5 minutes (a hidden tab or a closing page may
 *     send what is waiting, at most every 30 seconds). Between posts, seconds, the achievements
 *     count and the streaks wait in localStorage ("profile-sync:<game>") and survive a closed tab.
 *     A failed post keeps everything waiting for the next try; a 429 backs off for 15 minutes.
 *   * It sends numbers and ids only: seconds, a count, streak numbers and the seasonal badge ids from
 *     localStorage["event_badges_v1"]. No save data, no names, no text.
 *   * Whether any of it is VISIBLE to others is the player's choice on profile.html (off by default).
 *
 * API: window.NoyvjProfile = { update(info), flush(), pending(game), configure({apiBase, now, minIntervalMs}) }.
 */
(function () {
  "use strict";
  if (window.NoyvjProfile) return;

  const SCRIPT = document.currentScript;
  const DEFAULT_GAME = (SCRIPT && SCRIPT.dataset.gameId) || (location.pathname.match(/\/games\/([^/]+)\//) || [, ""])[1];
  const TOKEN_KEY = "hub_bearer_token";
  const BADGES_KEY = "event_badges_v1";
  const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,63}$/;
  const LABEL_RE = /^[a-z0-9_]{1,40}$/;
  const BADGE_RE = /^[a-z0-9-]{1,64}$/;
  const MAX_POST_SECONDS = 4 * 3600;
  const config = {
    apiBase: "https://noyvjgames.fastapicloud.dev",
    now: () => Date.now(),
    minIntervalMs: 5 * 60 * 1000,
    hideIntervalMs: 30 * 1000,
    backoffMs: 15 * 60 * 1000,
  };

  function lsGet(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function lsSet(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* not remembered */ } }
  function token() { return lsGet(TOKEN_KEY); }

  // ---- seconds this page was open and visible ------------------------------------------------
  let measured = 0;
  let visibleSince = document.visibilityState === "hidden" ? null : config.now();
  function bank() {
    if (visibleSince !== null) { measured += Math.max(0, (config.now() - visibleSince) / 1000); visibleSince = config.now(); }
  }
  function takeMeasured() {
    bank();
    const whole = Math.floor(measured);
    measured -= whole;
    return whole;
  }

  // ---- the waiting state, per game -----------------------------------------------------------
  const storeKey = (game) => "profile-sync:" + game;
  function read(game) {
    let state = null;
    try { state = JSON.parse(lsGet(storeKey(game)) || "null"); } catch (e) { state = null; }
    state = state && typeof state === "object" ? state : {};
    return {
      seconds: Math.max(0, Math.floor(Number(state.seconds) || 0)),
      achievements: Number.isFinite(state.achievements) ? Math.max(0, Math.floor(state.achievements)) : null,
      streaks: state.streaks && typeof state.streaks === "object" ? state.streaks : {},
      lastPost: Number(state.lastPost) || 0,
      nextAllowed: Number(state.nextAllowed) || 0,
    };
  }
  function write(game, state) { lsSet(storeKey(game), JSON.stringify(state)); }
  const memory = {};   // when storage is blocked the state still works for this page's life
  function load(game) { return memory[game] || (memory[game] = read(game)); }
  function save(game) { write(game, memory[game]); }

  function eventBadgeIds() {
    try {
      const parsed = JSON.parse(lsGet(BADGES_KEY) || "null");
      const list = parsed && Array.isArray(parsed.badges) ? parsed.badges : [];
      return list.map((b) => b && b.id).filter((id) => typeof id === "string" && BADGE_RE.test(id)).slice(0, 60);
    } catch (e) { return []; }
  }

  function countOf(value) {
    if (Array.isArray(value)) return value.length;
    const n = Number(value);
    return Number.isFinite(n) && n >= 0 ? Math.floor(n) : null;
  }

  // ---- sending -------------------------------------------------------------------------------
  const sending = {};
  async function send(game, reason) {
    const state = load(game);
    if (sending[game] || !token()) return false;
    const now = config.now();
    const interval = reason === "hide" ? config.hideIntervalMs : config.minIntervalMs;
    if (now < state.nextAllowed || now - state.lastPost < interval) return false;
    const seconds = Math.min(state.seconds, MAX_POST_SECONDS);
    const hasWork = seconds > 0 || state.achievements !== null || Object.keys(state.streaks).length > 0;
    if (!hasWork) return false;
    const progress = { game, add_seconds: seconds };
    if (state.achievements !== null) progress.achievements = Math.min(state.achievements, 1000);
    const streakLabels = Object.keys(state.streaks).slice(0, 10);
    if (streakLabels.length) {
      progress.streaks = {};
      streakLabels.forEach((label) => { progress.streaks[label] = Math.min(Math.floor(state.streaks[label]), 100000); });
    }
    const body = { progress };
    const badges = eventBadgeIds();
    if (badges.length) body.event_badges = badges;
    sending[game] = true;
    try {
      const response = await fetch(config.apiBase + "/users/me/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + token() },
        body: JSON.stringify(body),
        keepalive: true,
      });
      if (response.status === 429) { state.nextAllowed = config.now() + config.backoffMs; save(game); return false; }
      if (response.status === 401 || response.status === 403) { state.nextAllowed = config.now() + config.backoffMs; save(game); return false; }
      if (!response.ok) return false;                      // keep everything waiting for the next try
      // Take off only what was sent: an update() that landed while the request was in flight stays waiting.
      state.seconds = Math.max(0, state.seconds - seconds);
      if (state.achievements !== null && state.achievements <= (progress.achievements === undefined ? -1 : progress.achievements)) state.achievements = null;
      Object.keys(progress.streaks || {}).forEach((label) => {
        if (state.streaks[label] <= progress.streaks[label]) delete state.streaks[label];
      });
      state.lastPost = config.now();
      save(game);
      return true;
    } catch (e) {
      return false;
    } finally {
      sending[game] = false;
    }
  }

  function update(info) {
    try {
      const data = info && typeof info === "object" ? info : {};
      const game = String(data.game || DEFAULT_GAME || "");
      if (!SLUG_RE.test(game)) return;
      const measuredSeconds = takeMeasured();
      if (!token()) return;                                // signed out: nothing is kept or sent
      const state = load(game);
      const given = Number(data.seconds);
      const add = data.seconds !== undefined && Number.isFinite(given) ? Math.max(0, Math.floor(given)) : measuredSeconds;
      state.seconds += add;
      const count = countOf(data.achievements);
      if (count !== null) state.achievements = Math.max(state.achievements === null ? 0 : state.achievements, count);
      if (data.streaks && typeof data.streaks === "object") {
        Object.keys(data.streaks).forEach((label) => {
          const value = Number(data.streaks[label]);
          if (LABEL_RE.test(label) && Number.isFinite(value) && value >= 0) {
            state.streaks[label] = Math.max(state.streaks[label] || 0, Math.floor(value));
          }
        });
      }
      save(game);
      send(game, "update");
    } catch (e) { /* never let the profile break a save */ }
  }

  function flush(reason) {
    try {
      if (!token()) return;
      const game = DEFAULT_GAME;
      if (!SLUG_RE.test(game || "")) return;
      const state = load(game);
      state.seconds += takeMeasured();
      save(game);
      send(game, reason === "hide" ? "hide" : "flush");
    } catch (e) { /* ignore */ }
  }

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") { bank(); visibleSince = null; flush("hide"); }
    else if (visibleSince === null) visibleSince = config.now();
  });
  window.addEventListener("pagehide", () => { bank(); flush("hide"); });

  window.NoyvjProfile = {
    update,
    flush: () => flush("flush"),
    pending: (game) => { const s = read(game || DEFAULT_GAME); return { seconds: s.seconds, achievements: s.achievements, streaks: s.streaks }; },
    configure(options) {
      const o = options || {};
      if (o.apiBase) config.apiBase = String(o.apiBase);
      if (typeof o.now === "function") { config.now = o.now; if (visibleSince !== null) visibleSince = config.now(); measured = 0; }
      if (Number.isFinite(o.minIntervalMs)) config.minIntervalMs = o.minIntervalMs;
    },
  };
})();
