/*
 * Shared "what's new since you last played" banner — planning/TODO.md's
 * Z24 (site-wide goal), deliberately DISTINCT from each game's own
 * in-game "What's New" changelog PANEL (the "📋 What's New" toggle button
 * built per-game from that same changelog.json, e.g. Loop's own K16 note
 * in games/loop/CLAUDE.md). That panel is opt-in, player-triggered, and
 * always shows the FULL history from scratch, with no memory of what the
 * player has already seen — closer to a changelog page than a
 * notification. This banner is the opposite shape: it appears
 * automatically, unprompted, only for a RETURNING player, and only shows
 * the entries added since their last visit — a real diff, not the whole
 * log — closer to what most software calls a "what's new since you were
 * last here" toast.
 *
 * One script, included unchanged by every game via:
 *   <script src="../../shared/whats-new-banner.js" data-game-id="<slug>"></script>
 * placed AFTER that game's own changelog fetch in the boot sequence (in
 * practice: right alongside shared/save-widget.js and
 * shared/last-played.js, near the end of <body>, after the inline
 * `main();` call that eventually sets `window.CHANGELOG_JSON`) — same
 * data-game-id convention as every other shared script on this hub.
 *
 * Reuses window.CHANGELOG_JSON exactly as each game's own Python-side
 * changelog panel already does (the raw text of changelog.json, fetched
 * once inside that game's own Promise.all() and handed to Pyodide as a
 * window global) rather than fetching changelog.json a second time here
 * — see e.g. games/loop/index.html's `window.CHANGELOG_JSON =
 * changelogJson;` line. Because that global is set from inside an async
 * `main()` that this script's own <script> tag can't block on just by
 * sitting after it in the markup, this file polls for it the same way
 * shared/save-widget.js's own `waitForLoadState()` polls for
 * `window.pyodide`/`load_state()` — see that file's own comment on why a
 * plain load-order assumption isn't safe against an async boot sequence.
 *
 * changelog.json itself ships in two equivalent shapes across this repo's
 * 12 games — a bare array (most games) or `{"changelog": [...]}` (SOL/
 * Canopy/Grid/Tide) — both a flat list of `{"date": "YYYY-MM-DD",
 * "entry": "..."}` objects. Both are handled here.
 *
 * Persistence: `localStorage["whats-new-seen:<slug>"]` stores the DATE
 * STRING of the newest changelog entry the player has already been shown
 * (not a timestamp of when the banner last appeared) — a plain
 * `"YYYY-MM-DD"` string, directly comparable against entry dates. A
 * brand-new player (no key yet) never sees a banner dumping the entire
 * history at them — that would read as noise, not news — instead this
 * silently marks the current newest entry as already-seen the first time
 * the script ever runs for them, so only a genuinely RETURNING player who
 * missed real updates since their last visit sees anything.
 *
 * Defensive by construction, matching every other shared file on this
 * hub: a missing/malformed changelog.json, a `window.CHANGELOG_JSON` that
 * never gets set (fetch failure, a game that hasn't adopted the changelog
 * panel pattern yet), unparseable JSON, or a non-array/non-object shape
 * all fall through to "show nothing" rather than throwing or blocking the
 * rest of the page.
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

  if (!document.getElementById("whats-new-banner-styles")) {
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
        background: rgba(255, 255, 255, 0.14);
        color: #eef0ff;
        align-self: center;
      }
      #whats-new-banner-dismiss:hover { background: rgba(255, 255, 255, 0.24); }
      @media (prefers-reduced-motion: reduce) {
        #whats-new-banner { transition: none; }
      }
    `;
    document.head.appendChild(style);
  }

  // Same shape of async-boot-order problem shared/save-widget.js's own
  // waitForLoadState() solves: window.CHANGELOG_JSON is set from inside
  // each game's async main(), well after this script's own <script> tag
  // runs, so this has to poll rather than assume it's already there.
  // Unlike waitForLoadState() (which rejects on timeout because the save
  // widget has real fallback/logging behavior tied to that failure), a
  // timeout here just means "no changelog data materialized in time" —
  // exactly the same as "no changelog data at all," so it resolves to
  // null instead of rejecting.
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
    // document.body is guaranteed to exist by the time this runs (the
    // <script> tag itself sits near the end of <body>), but guard anyway,
    // matching shared/confirm-dialog.js's own defensive DOMContentLoaded
    // fallback rather than assuming a specific per-game markup position.
    //
    // The banner itself is `position: fixed` (see the injected CSS above)
    // rather than a normal-flow element -- found live, verifying against
    // SOL: several games' own `body { display: flex; align-items: center;
    // justify-content: center; }` shell (centering a single `#game` child)
    // turns into a broken two-item flex row the instant a second in-flow
    // sibling like a plain <div> gets inserted before it. A fixed-position
    // element is removed from its parent's flex layout entirely, so it can
    // be inserted as a body child on ANY of this hub's 12 games regardless
    // of that game's own body/shell layout, the same reasoning
    // achievement-toast/loop-closed-banner-style fixed overlays already
    // rely on elsewhere in this hub.
    const insert = () => {
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
