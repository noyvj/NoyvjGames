/*
 * Shared "what's new since you last played" banner (planning/TODO.md Z24). Distinct from each
 * game's own in-game "What's New" panel, which is opt-in and always shows the full history: this
 * appears on its own, only for a RETURNING player, and lists only the entries newer than the last
 * one they were shown.
 *
 *   <script src="../../shared/whats-new-banner.js" data-game-id="<slug>"></script>
 *
 * Placed near the end of <body>. It reuses window.CHANGELOG_JSON (the raw text of the game's
 * changelog.json, set by the game's own boot script) instead of fetching it again, and polls for
 * it because that global appears only after the async boot. Both changelog shapes are accepted: a
 * bare array, or {"changelog": [...]}, of {"date": "YYYY-MM-DD", "entry": "..."}.
 *
 * localStorage["whats-new-seen:<slug>"] holds the date of the newest entry already shown. A
 * brand-new player (no key) never gets the whole history: the first run silently marks the newest
 * entry seen. A missing, malformed or never-set changelog shows nothing.
 */
(function () {
  const SCRIPT = document.currentScript;
  const GAME_ID = SCRIPT && SCRIPT.dataset.gameId;
  if (!GAME_ID) {
    console.error("whats-new-banner.js: missing required data-game-id attribute on its <script> tag");
    return;
  }

  const STORAGE_KEY = `whats-new-seen:${GAME_ID}`;
  const MAX_ENTRIES_SHOWN = 5;

  // Only a returning player with missed entries ever sees the banner, so the stylesheet is added
  // when it is mounted, not on every page load.
  function injectStyles() {
    if (document.getElementById("whats-new-banner-styles")) return;
    const style = document.createElement("style");
    style.id = "whats-new-banner-styles";
    style.textContent = `
      #whats-new-banner {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        z-index: 600;
        padding: 0.65rem 1rem;
        background: linear-gradient(165deg, rgba(58, 78, 168, 0.95), rgba(24, 30, 56, 0.97));
        border-bottom: 1px solid rgba(140, 160, 255, 0.35);
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
        color: #eef0ff;
        font-family: system-ui, -apple-system, sans-serif;
        box-sizing: border-box;
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        flex-wrap: wrap;
      }
      #whats-new-banner[hidden] { display: none !important; }
      #whats-new-banner-body { flex: 1 1 240px; min-width: 0; text-align: left; }
      #whats-new-banner-heading {
        margin: 0 0 0.3rem;
        font-size: 0.85rem;
        font-weight: 700;
      }
      #whats-new-banner-list {
        margin: 0;
        padding-left: 1.1rem;
        font-size: 0.8rem;
        line-height: 1.4;
      }
      #whats-new-banner-list li { margin-bottom: 0.15rem; }
      #whats-new-banner-list li:last-child { margin-bottom: 0; }
      #whats-new-banner-more {
        margin: 0.25rem 0 0;
        font-size: 0.75rem;
        opacity: 0.8;
        font-style: italic;
      }
      #whats-new-banner-dismiss {
        flex: 0 0 auto;
        border: none;
        border-radius: 8px;
        padding: 0.45rem 0.9rem;
        font-size: 0.8rem;
        font-weight: 600;
        font-family: inherit;
        cursor: pointer;
        background: rgba(0, 0, 0, 0.3);
        color: #eef0ff;
        align-self: center;
      }
      #whats-new-banner-dismiss:hover { background: rgba(0, 0, 0, 0.45); }
      @media (prefers-reduced-motion: reduce) {
        #whats-new-banner { transition: none; }
      }
    `;
    document.head.appendChild(style);
  }

  // window.CHANGELOG_JSON is set from inside each game's async main(), after this script ran, so
  // poll for it (as save-widget.js does for window.pyodide). A timeout resolves null, which is the
  // same as "no changelog": show nothing.
  function waitForChangelogJson(timeoutMs = 15000, intervalMs = 150) {
    return new Promise((resolve) => {
      const start = Date.now();
      (function check() {
        if (typeof window.CHANGELOG_JSON === "string") return resolve(window.CHANGELOG_JSON);
        if (Date.now() - start > timeoutMs) return resolve(null);
        setTimeout(check, intervalMs);
      })();
    });
  }

  function parseEntries(rawJson) {
    if (typeof rawJson !== "string") return [];
    let parsed;
    try {
      parsed = JSON.parse(rawJson);
    } catch (err) {
      console.error(`whats-new-banner.js (${GAME_ID}): malformed changelog.json`, err);
      return [];
    }
    // Two equivalent shapes ship across this repo's games: a bare array,
    // or `{"changelog": [...]}` (SOL/Canopy/Grid/Tide).
    let list = Array.isArray(parsed) ? parsed
      : (parsed && Array.isArray(parsed.changelog)) ? parsed.changelog
      : null;
    if (!list) return [];
    list = list.filter((item) => item && typeof item.date === "string" && typeof item.entry === "string");
    // Stable sort, newest first. Every changelog.json in this repo already
    // ships newest-first, but this doesn't assume that -- it's the same
    // defensive stance the per-game Python-side changelog panels take.
    list.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
    return list;
  }

  function buildBanner(newEntries, onDismiss) {
    const banner = document.createElement("div");
    banner.id = "whats-new-banner";
    banner.setAttribute("role", "status");

    const body = document.createElement("div");
    body.id = "whats-new-banner-body";

    const heading = document.createElement("p");
    heading.id = "whats-new-banner-heading";
    heading.textContent = "🆕 What's new since you last played:";
    body.appendChild(heading);

    const list = document.createElement("ul");
    list.id = "whats-new-banner-list";
    const shown = newEntries.slice(0, MAX_ENTRIES_SHOWN);
    shown.forEach((item) => {
      const li = document.createElement("li");
      li.textContent = `${item.date} — ${item.entry}`;
      list.appendChild(li);
    });
    body.appendChild(list);

    if (newEntries.length > shown.length) {
      const more = document.createElement("p");
      more.id = "whats-new-banner-more";
      more.textContent = `...and ${newEntries.length - shown.length} more update${newEntries.length - shown.length === 1 ? "" : "s"}.`;
      body.appendChild(more);
    }

    banner.appendChild(body);

    const dismissButton = document.createElement("button");
    dismissButton.id = "whats-new-banner-dismiss";
    dismissButton.type = "button";
    dismissButton.textContent = "Got it";
    dismissButton.addEventListener("click", () => {
      onDismiss();
      banner.remove();
    });
    banner.appendChild(dismissButton);

    return banner;
  }

  function mountBanner(newEntries, newestDate) {
    // The banner is `position: fixed` on purpose: several games' `body { display: flex }` shells
    // center a single #game child, and an in-flow sibling inserted before it broke that layout.
    // A fixed element is out of the flex flow, so it works on every game.
    const insert = () => {
      injectStyles();
      const banner = buildBanner(newEntries, () => {
        try {
          localStorage.setItem(STORAGE_KEY, newestDate);
        } catch (err) {
          console.error(`whats-new-banner.js (${GAME_ID}): localStorage.setItem failed on dismiss`, err);
        }
      });
      document.body.insertBefore(banner, document.body.firstChild);
    };
    if (document.body) insert();
    else document.addEventListener("DOMContentLoaded", insert);
  }

  async function init() {
    const rawJson = await waitForChangelogJson();
    const entries = parseEntries(rawJson);
    if (entries.length === 0) return; // missing/malformed/never-set -- show nothing

    const newestDate = entries[0].date;

    let lastSeen;
    try {
      lastSeen = localStorage.getItem(STORAGE_KEY);
    } catch (err) {
      // Private-browsing mode, storage quota, or a locked-down browser --
      // same "fail silently, this is a nice-to-have" stance as
      // shared/last-played.js.
      console.error(`whats-new-banner.js (${GAME_ID}): localStorage.getItem failed`, err);
      return;
    }

    if (lastSeen === null) {
      // First-ever visit for this browser/game -- mark everything seen
      // now rather than dumping the whole history on a brand-new player,
      // who has no "last visit" to diff against anyway.
      try {
        localStorage.setItem(STORAGE_KEY, newestDate);
      } catch (err) {
        console.error(`whats-new-banner.js (${GAME_ID}): localStorage.setItem failed on first visit`, err);
      }
      return;
    }

    const newEntries = entries.filter((item) => item.date > lastSeen);
    if (newEntries.length === 0) return; // nothing missed since last visit

    mountBanner(newEntries, newestDate);
  }

  init();
})();
