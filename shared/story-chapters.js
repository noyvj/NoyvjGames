/*
 * Shared "story chapters" (planning/TODO.md section W1): a light narrative
 * thread for games with little story of their own. One include per game:
 *   <script src="../../shared/story-chapters.js" data-game-id="grid"
 *           data-story="story.json"></script>
 * and add "#story-chapters" to that game's story-toggle.js
 * data-story-selectors, so the existing Story on/off pill also hides the
 * chapters (story text is never needed to play).
 *
 * story.json:
 *   { "title": "A small utility",
 *     "chapters": [ { "id": "first_plant", "title": "The first plant",
 *                     "text": "A few sentences of narrative..." }, ... ] }
 * Chapters are unlocked by the game calling
 *   window.NoyvjStory.reach("first_plant")
 * at the matching milestone (from Python: `from js import window`, then
 * `getattr(window, "NoyvjStory", None)`). reach() is idempotent, ignores ids
 * that are not in story.json, and never throws.
 *
 * What it renders: a collapsed "Story" panel inserted after the page's <h1>
 * (or at the top of #game) showing the latest chapter as a short banner and
 * every chapter reached so far in story order, with "N of M" progress. Chapters
 * not yet reached are never shown (no spoilers). Progress lives in this
 * browser's localStorage (`story-chapters:<game>`), not in the save: a story
 * is decoration, so it never changes a save's shape, and the game plays
 * identically with it off. Text is written with textContent only.
 */
(function () {
  const script = document.currentScript;
  const GAME_ID = script && script.dataset.gameId;
  const STORY_URL = (script && script.dataset.story) || "story.json";
  if (!GAME_ID) {
    console.error("story-chapters.js: needs data-game-id");
    return;
  }
  const KEY = `story-chapters:${GAME_ID}`;
  let chapters = [];
  let reachedIds = [];
  let ready = false;
  const pending = [];
  let root = null;
  let banner = null;
  let listEl = null;
  let countEl = null;

  function lsGet(key) { try { return localStorage.getItem(key); } catch (e) { return null; } }
  function lsSet(key, value) { try { localStorage.setItem(key, value); } catch (e) { /* convenience only */ } }

  function knownIds() { return new Set(chapters.map((c) => c.id)); }

  function loadReached() {
    const known = knownIds();
    let stored = [];
    try { stored = JSON.parse(lsGet(KEY) || "[]"); } catch (e) { stored = []; }
    reachedIds = [];
    if (Array.isArray(stored)) {
      for (const id of stored) {
        if (typeof id === "string" && known.has(id) && !reachedIds.includes(id)) reachedIds.push(id);
      }
    }
  }

  function render() {
    if (!root) return;
    // Narrative order (the order in story.json), not the order they were reached
    // in, so a loaded save that unlocks many chapters at once still reads right.
    const shown = chapters.filter((c) => reachedIds.includes(c.id));
    root.hidden = shown.length === 0;
    countEl.textContent = `${shown.length} of ${chapters.length} chapters`;
    if (shown.length) {
      const latest = shown[shown.length - 1];
      banner.textContent = `${latest.title}: ${latest.text.split(/(?<=[.!?])\s/)[0]}`;
    } else {
      banner.textContent = "";
    }
    listEl.textContent = "";
    for (const chapter of shown) {
      const item = document.createElement("li");
      const title = document.createElement("strong");
      title.textContent = chapter.title;
      const text = document.createElement("p");
      text.textContent = chapter.text;
      item.append(title, text);
      listEl.append(item);
    }
  }

  function build() {
    root = document.createElement("details");
    root.id = "story-chapters";
    root.className = "story-chapters section";
    root.hidden = true;
    const summary = document.createElement("summary");
    summary.textContent = "📖 Story";
    countEl = document.createElement("span");
    countEl.className = "story-chapters-count";
    summary.append(" ", countEl);
    banner = document.createElement("p");
    banner.className = "story-chapters-banner";
    listEl = document.createElement("ol");
    listEl.className = "story-chapters-list";
    root.append(summary, banner, listEl);
    const style = document.createElement("style");
    style.textContent =
      "#story-chapters { margin: 0.6rem 0; font-size: 0.9rem; }" +
      "#story-chapters .story-chapters-banner { margin: 0.3rem 0; font-style: italic; opacity: 0.9; }" +
      "#story-chapters .story-chapters-count { opacity: 0.65; font-size: 0.8rem; }" +
      "#story-chapters .story-chapters-list { margin: 0.4rem 0 0; padding-left: 1.2rem; }" +
      "#story-chapters .story-chapters-list p { margin: 0.15rem 0 0.6rem; }";
    document.head.append(style);
    const heading = document.querySelector("h1");
    if (heading && heading.parentNode) heading.after(root);
    else (document.getElementById("game") || document.body).prepend(root);
  }

  function reach(id) {
    try {
      if (typeof id !== "string") return false;
      if (!ready) { pending.push(id); return false; }
      if (!knownIds().has(id) || reachedIds.includes(id)) return false;
      reachedIds.push(id);
      lsSet(KEY, JSON.stringify(reachedIds));
      render();
      return true;
    } catch (e) {
      return false;
    }
  }

  window.NoyvjStory = {
    reach,
    reached: () => reachedIds.slice(),
    reset: () => { reachedIds = []; lsSet(KEY, "[]"); render(); },
  };

  fetch(STORY_URL, { cache: "no-cache" })
    .then((r) => (r.ok ? r.json() : null))
    .then((data) => {
      const list = data && Array.isArray(data.chapters) ? data.chapters : [];
      chapters = list.filter((c) => c && typeof c.id === "string" && typeof c.title === "string" && typeof c.text === "string");
      build();
      loadReached();
      ready = true;
      for (const id of pending.splice(0)) reach(id);
      render();
    })
    .catch(() => { /* no story file: the game is unchanged */ });
})();
