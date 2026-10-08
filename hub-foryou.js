/*
 * Hub "For you" row (TODO Y-5), loaded on index.html after script.js.
 *
 * Rule-based next-game suggestions for a RETURNING player, always with the reason in words
 * ("Because you finished Canopy: also a Climate game."). No model, no server call. The inputs:
 *   - games opened on this device: localStorage["last-played:<slug>"] (shared/last-played.js),
 *     plus claimed account saves and save codes (HubLobby.playedSlugs());
 *   - games "finished": for a signed-in player, at least FINISHED_RATIO of the game's achievements
 *     earned (script.js fills HubLobby.achievementProgress from the account's saves). A signed-out
 *     player has no per-game progress on this device, so their suggestions say "played", never
 *     "finished";
 *   - the tags on the title cards (the shared tags are never changed);
 *   - the first-visit survey answers, through script.js's own pickRecommendedGame() (Z13/Z19).
 * Scoring: every tag of a game you opened adds weight (finished 3, played 1; the Depth tags count
 * half); an unopened game's score is the sum of its tags' weights. The reason names the opened game
 * it shares the most weight with. Games sharing nothing come after, as "you have not opened it yet",
 * the survey's pick first. When every game has been opened, the games with the least achievement
 * progress are suggested instead (signed-in only); otherwise the row stays hidden.
 *
 * It stays out of the way: hidden until the first-visit survey and the tour are closed, hidden for
 * a first-time visitor (the New Player banner covers them), and "Hide for two weeks" is remembered
 * in localStorage["hub-foryou-hidden-until"].
 *
 * window.HubForYou: suggest(input) (pure, tested), FINISHED_RATIO, render().
 */
(function () {
  "use strict";

  const HIDDEN_KEY = "hub-foryou-hidden-until";
  const HIDE_DAYS = 14;
  const FINISHED_RATIO = 0.6;
  const MAX_ITEMS = 3;
  const DEPTH_TAGS = ["quick", "deep-systems"];

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } }

  function tagLabel(tag, labels) {
    return (labels && labels[tag]) || tag.replace(/-/g, " ").replace(/^./, (c) => c.toUpperCase());
  }

  function joinWords(list) {
    if (list.length <= 1) return list.join("");
    return list.slice(0, -1).join(", ") + " and " + list[list.length - 1];
  }

  /**
   * suggest({ games, opened, progress, recommended, labels })
   *   games:       [{ slug, name, tags: [] }] in lobby order
   *   opened:      { slug: lastPlayedMs } (any truthy value counts as opened; larger = more recent)
   *   progress:    { slug: { earned, total } } for a signed-in account (may be empty)
   *   recommended: the survey's pick (slug) or ""; labels: { tag: "Climate" }
   * Returns [{ slug, reason, kind }] with at most MAX_ITEMS entries, best first.
   */
  function suggest(input) {
    const games = input.games || [];
    const opened = input.opened || {};
    const progress = input.progress || {};
    const labels = input.labels || {};
    const bySlug = {};
    games.forEach((g) => { bySlug[g.slug] = g; });
    const isFinished = (slug) => {
      const p = progress[slug];
      return Boolean(p && p.total > 0 && p.earned / p.total >= FINISHED_RATIO);
    };
    const sources = games.filter((g) => opened[g.slug]);
    if (!sources.length) return [];

    const weight = {};
    sources.forEach((g) => {
      const w = isFinished(g.slug) ? 3 : 1;
      g.tags.forEach((t) => { weight[t] = (weight[t] || 0) + (DEPTH_TAGS.includes(t) ? w / 2 : w); });
    });

    const candidates = games.filter((g) => !opened[g.slug]);
    const scored = candidates.map((g, order) => {
      let best = null;
      const score = g.tags.reduce((sum, t) => sum + (weight[t] || 0), 0);
      sources.forEach((s) => {
        const shared = s.tags.filter((t) => g.tags.includes(t));
        if (!shared.length) return;
        const value = shared.reduce((sum, t) => sum + (DEPTH_TAGS.includes(t) ? 0.5 : 1), 0) * (isFinished(s.slug) ? 3 : 1);
        const recency = Number(opened[s.slug]) || 0;
        if (!best || value > best.value || (value === best.value && recency > best.recency)) best = { source: s, shared, value, recency };
      });
      return { game: g, order, score, best };
    });

    const out = [];
    scored
      .filter((c) => c.score > 0 && c.best)
      .sort((a, b) => b.score - a.score || a.order - b.order)
      .forEach((c) => {
        if (out.length >= MAX_ITEMS) return;
        const verb = isFinished(c.best.source.slug) ? "finished" : "played";
        const subjects = c.best.shared.filter((t) => !DEPTH_TAGS.includes(t));
        const shown = (subjects.length ? subjects : c.best.shared).map((t) => tagLabel(t, labels));
        out.push({ slug: c.game.slug, kind: "tags", reason: "Because you " + verb + " " + c.best.source.name + ": also " + joinWords(shown) + "." });
      });

    if (out.length < MAX_ITEMS) {
      const rest = scored.filter((c) => !out.some((o) => o.slug === c.game.slug));
      rest.sort((a, b) => (a.game.slug === input.recommended ? -1 : 0) - (b.game.slug === input.recommended ? -1 : 0) || a.order - b.order);
      rest.forEach((c) => {
        if (out.length >= MAX_ITEMS) return;
        out.push({
          slug: c.game.slug,
          kind: "untouched",
          reason: c.game.slug === input.recommended
            ? "You have not opened it yet, and it fits what you chose in the first-visit questions."
            : "You have not opened it yet.",
        });
      });
    }

    if (!out.length) {
      // Every game has been opened: point at the ones with the least achievement progress.
      games
        .filter((g) => progress[g.slug] && progress[g.slug].total > 0 && !isFinished(g.slug))
        .sort((a, b) => progress[a.slug].earned / progress[a.slug].total - progress[b.slug].earned / progress[b.slug].total)
        .slice(0, MAX_ITEMS)
        .forEach((g) => {
          const p = progress[g.slug];
          out.push({ slug: g.slug, kind: "progress", reason: "You have earned " + p.earned + " of " + p.total + " achievements here." });
        });
    }
    return out;
  }

  // ---- page ------------------------------------------------------------------------------------

  function blockingOverlayOpen() {
    if (document.getElementById("onboarding-survey-overlay")) return true;
    const tour = document.getElementById("tutorial-overlay");
    return Boolean(tour && !tour.hidden);
  }

  function hiddenNow() {
    const until = Number(lsGet(HIDDEN_KEY));
    return Number.isFinite(until) && until > Date.now();
  }

  function pageInput() {
    const lobby = window.HubLobby;
    const games = lobby.cards.map((card) => ({
      slug: lobby.slugOf(card),
      name: lobby.nameOf(card),
      tags: (card.dataset.tags || "").split(/\s+/).filter(Boolean),
    })).filter((g) => g.slug);
    const opened = {};
    try {
      Object.keys(localStorage).forEach((k) => {
        if (k.indexOf("last-played:") === 0) opened[k.slice("last-played:".length)] = Number(localStorage.getItem(k)) || 1;
      });
    } catch (e) { /* storage blocked: nothing to base suggestions on */ }
    lobby.playedSlugs().forEach((slug) => { if (!opened[slug]) opened[slug] = 1; });
    const labels = {};
    document.querySelectorAll("#game-tag-filter option").forEach((o) => { if (o.value) labels[o.value] = o.textContent.trim(); });
    // pickRecommendedGame() falls back to a default game when the survey was skipped; only a pick that
    // came from real answers may be explained as "what you chose".
    const answers = lobby.onboardingAnswers();
    const answered = answers.subjects.length > 0;
    return { games, opened, progress: lobby.achievementProgress, recommended: answered ? lobby.pickRecommendedGame() : "", labels };
  }

  let waitTimer = null;

  function render() {
    const section = document.getElementById("for-you-section");
    const list = document.getElementById("for-you-list");
    const lobby = window.HubLobby;
    if (!section || !list || !lobby) return;
    clearTimeout(waitTimer);
    if (hiddenNow() || lobby.isNewPlayer()) { section.hidden = true; return; }
    if (blockingOverlayOpen()) {
      // Try again once the survey or tour has been closed.
      waitTimer = setTimeout(render, 800);
      return;
    }
    const items = suggest(pageInput());
    list.textContent = "";
    if (!items.length) { section.hidden = true; return; }
    items.forEach((item) => {
      const card = lobby.cards.find((c) => lobby.slugOf(c) === item.slug);
      if (!card) return;
      const li = document.createElement("li");
      li.className = "for-you-item";
      const link = document.createElement("a");
      link.className = "continue-playing-item";
      link.href = lobby.hrefOf(card);
      link.textContent = lobby.nameOf(card);
      const reason = document.createElement("span");
      reason.className = "for-you-reason";
      reason.textContent = item.reason;
      li.append(link, reason);
      list.appendChild(li);
    });
    section.hidden = !list.children.length;
  }

  window.HubForYou = { suggest, FINISHED_RATIO, render };

  function start() {
    const lobby = window.HubLobby;
    if (!lobby) return;
    document.getElementById("for-you-dismiss")?.addEventListener("click", () => {
      lsSet(HIDDEN_KEY, String(Date.now() + HIDE_DAYS * 86400000));
      const section = document.getElementById("for-you-section");
      if (section) section.hidden = true;
      // Keep the keyboard where it was useful: the next block of the lobby.
      document.getElementById("game-search-input")?.focus();
    });
    // Signed-in progress arrives after the account's saves load; suggestions change then.
    window.addEventListener("hub-achievements-progress", render);
    render();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
