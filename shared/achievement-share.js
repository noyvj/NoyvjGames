/*
 * Shared achievement "Share" button (planning/TODO.md Z-27). Copies one line plus the game's link:
 *
 *   I earned Cleanup Crew in Tide, 12.5% of players have it
 *   https://example.github.io/NoyvjGames/games/tide/
 *
 * The percentage is the live earned_pct from the stats endpoint (the same numbers
 * shared/achievement-stats.js shows). While the game is small-group suppressed, or the achievement
 * has too few earners to be listed, the percentage is left out and the line is just
 * "I earned Cleanup Crew in Tide" plus the link: never a guess, never 0%.
 * Docs and tests: planning/SHARED-COMPONENTS.md ("Achievement share"),
 * shared/tests/test_achievement_share_browser.py.
 *
 *   <script src="../../shared/achievement-stats.js" data-game-id="tide"></script>  <!-- shares its cache -->
 *   <script src="../../shared/achievement-share.js" data-game-id="tide" data-game-name="Tide"></script>
 *
 * With data-game-id present, a Share button is added automatically to every EARNED row of
 * #achievements-panel (rows carry data-achievement-id and an earned class, as the games already
 * render them) and kept there as the game rebuilds the panel. Without it, call:
 *   NoyvjAchievementShare.mountButton(container, { game: "tide", gameName: "Tide",
 *                                                  achievementId: "first_reduction", label: "Cleanup Crew" })
 *   NoyvjAchievementShare.text({ label, gameName, earnedPct, url })       // pure
 *   NoyvjAchievementShare.share({ game, gameName, achievementId, label }) // copy now -> Promise<{ok, text}>
 *
 * Fails soft: no network, no clipboard permission or no stats just means a line without a percentage
 * or a selected text box to copy by hand. Nothing is sent anywhere except the one read-only stats
 * request the achievement panel already makes.
 */
(function () {
  "use strict";
  if (window.NoyvjAchievementShare) return;

  const SCRIPT = document.currentScript;
  const GAME_ID = (SCRIPT && SCRIPT.dataset.gameId) || "";
  const GAME_NAME = (SCRIPT && SCRIPT.dataset.gameName) || "";
  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  const WAIT_MS = 1500;   // how long a click waits for stats that have not arrived yet

  // Z-13: the button and its messages come from shared/i18n.js when it is on the page and a language other
  // than English is chosen. The line that is COPIED ("I earned X in Y") stays English: it goes to other people.
  function tr(key, english, vars) {
    const i18n = window.NoyvjI18n;
    if (i18n) return i18n.t(key, english, vars);
    return vars ? english.replace(/\{(\w+)\}/g, (m, name) => (name in vars ? String(vars[name]) : m)) : english;
  }

  function oneLine(t) { return String(t).replace(/\s+/g, " ").trim(); }

  function prettyName(slug) {
    return String(slug || "").replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function percentText(pct) {
    return `${Number(pct.toFixed(2))}%`;
  }

  function gameUrl(game) {
    try {
      if (SCRIPT && SCRIPT.src && game) return new URL(`../games/${game}/`, SCRIPT.src).href;
    } catch (e) { /* fall through */ }
    return location.origin + location.pathname.replace(/(index|pc)\.html$/, "");
  }

  /** The text to copy. earnedPct must be a finite number to be mentioned; anything else leaves it out. */
  function text(opts) {
    const o = opts || {};
    const label = oneLine(o.label || "an achievement");
    const game = oneLine(o.gameName || prettyName(o.game) || "NoyvjGames");
    const pct = typeof o.earnedPct === "number" && isFinite(o.earnedPct) && o.earnedPct >= 0 && o.earnedPct <= 100 ? o.earnedPct : null;
    const line = `I earned ${label} in ${game}` + (pct !== null ? `, ${percentText(pct)} of players have it` : "");
    const url = o.url || gameUrl(o.game);
    return url ? `${line}\n${url}` : line;
  }

  // ---- live percentage (shares shared/achievement-stats.js's cache when it is on the page) ----------
  const own = {};   // fallback cache per game when achievement-stats.js is absent

  function statsFor(game) {
    const shared = window.NoyvjAchievementStats;
    if (shared && typeof shared.getStats === "function") return shared.getStats(game);
    if (!own[game]) {
      own[game] = fetch(`${API_BASE}/stats/games/${encodeURIComponent(game)}`)
        .then((r) => (r.ok ? r.json() : null)).catch(() => null)
        .then((d) => { own[game].value = d; own[game].done = true; return d; });
    }
    return own[game];
  }

  /** Stats already in hand, synchronously: { ready, data }. */
  function statsNow(game) {
    const shared = window.NoyvjAchievementStats;
    if (shared && typeof shared.peek === "function") {
      const d = shared.peek(game);
      return { ready: d !== undefined, data: d || null };
    }
    const c = own[game];
    return { ready: !!(c && c.done), data: c && c.done ? c.value : null };
  }

  function pctFrom(data, id) {
    const shared = window.NoyvjAchievementStats;
    if (shared && typeof shared.earnedPct === "function") return shared.earnedPct(data, id);
    if (!data || data.suppressed) return null;
    const e = data.achievements && data.achievements[id];
    return e && typeof e.earned_pct === "number" ? e.earned_pct : null;
  }

  function copy(t) {
    if (window.NoyvjCopyResult && typeof window.NoyvjCopyResult.copy === "function") return window.NoyvjCopyResult.copy(t);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(t).then(() => true, () => false);
    }
    try {
      const ta = document.createElement("textarea");
      ta.value = t;
      ta.style.cssText = "position:fixed;left:-9999px";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand && document.execCommand("copy");
      ta.remove();
      return Promise.resolve(!!ok);
    } catch (e) { return Promise.resolve(false); }
  }

  function buildText(o, data) {
    return text({ label: o.label, gameName: o.gameName, game: o.game, url: o.url, earnedPct: pctFrom(data, o.achievementId) });
  }

  /** Copies the share line now. Resolves { ok, text } (ok false when the clipboard refused). */
  function share(opts) {
    const o = opts || {};
    const now = statsNow(o.game);
    const settle = (data) => {
      const t = buildText(o, data);
      return copy(t).then((ok) => ({ ok, text: t }));
    };
    if (now.ready) return settle(now.data);       // the common case: copy inside the click, no waiting
    const timeout = new Promise((res) => setTimeout(() => res(null), WAIT_MS));
    return Promise.race([statsFor(o.game), timeout]).then(settle);
  }

  // ---- button ------------------------------------------------------------------------------------
  const STYLE_ID = "noyvj-achievement-share-style";
  const CSS = `
.noyvj-as{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem;margin:.4rem 0 0;--as-fg:#e8e9f0;--as-border:rgba(140,160,255,.65);--as-muted:#aab0c8;--as-bg:#252a40;--as-focus:#ffd866}
html[data-theme="light"] .noyvj-as{--as-fg:#1b2033;--as-border:rgba(60,85,160,.7);--as-muted:#4a5275;--as-bg:#fff;--as-focus:#8a5a00}
@media (prefers-color-scheme:light){:root:not([data-theme]) .noyvj-as{--as-fg:#1b2033;--as-border:rgba(60,85,160,.7);--as-muted:#4a5275;--as-bg:#fff;--as-focus:#8a5a00}}
.noyvj-as-btn{min-height:44px;padding:.3rem .8rem;border:2px solid var(--as-border);border-radius:8px;background:var(--as-bg);color:var(--as-fg);font:600 .8rem system-ui,sans-serif;font-style:normal;opacity:1;cursor:pointer}
.noyvj-as-btn:focus-visible,.noyvj-as-box:focus-visible{outline:3px solid var(--as-focus);outline-offset:2px}
.noyvj-as-status{color:var(--as-muted);font:.78rem/1.3 system-ui,sans-serif;font-style:normal;opacity:1;overflow-wrap:anywhere}
.noyvj-as-box{flex:1 1 100%;min-height:44px;padding:.4rem .6rem;border:2px dashed var(--as-border);border-radius:8px;background:var(--as-bg);color:var(--as-fg);font:.8rem/1.4 ui-monospace,Menlo,Consolas,monospace}
@media (prefers-reduced-motion:no-preference){html:not([data-reduced-motion="true"]) .noyvj-as-btn{transition:filter .15s ease}}
@media print{.noyvj-as{display:none}}
`;
  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const st = document.createElement("style");
    st.id = STYLE_ID;
    st.textContent = CSS;
    (document.head || document.documentElement).appendChild(st);
  }

  /**
   * mountButton(container, { game, gameName, achievementId, label, url, onShare })
   * Prefetches the stats so the click can copy at once. Returns { destroy(), element }.
   */
  function mountButton(container, opts) {
    const o = opts || {};
    const host = typeof container === "string" ? document.querySelector(container) : container;
    if (!host) return null;
    if (!o.game || !o.achievementId) throw new Error("NoyvjAchievementShare.mountButton needs game and achievementId");
    injectStyle();
    const root = document.createElement("div");
    root.className = "noyvj-as";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "noyvj-as-btn";
    btn.textContent = tr("share.button", "↗ Share");
    btn.setAttribute("aria-label", tr("share.aria", "Share: {label}", { label: oneLine(o.label || o.achievementId) }));
    const status = document.createElement("span");
    status.className = "noyvj-as-status";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    root.append(btn, status);
    host.appendChild(root);
    let box = null;
    statsFor(o.game);   // warm the cache
    btn.addEventListener("click", () => {
      share(o).then((r) => {
        if (r.ok) {
          if (box) { box.remove(); box = null; }
          status.textContent = tr("share.copied", "✓ Copied to your clipboard");
          if (o.onShare) o.onShare(r.text);
        } else {
          if (!box) {
            box = document.createElement("textarea");
            box.className = "noyvj-as-box";
            box.readOnly = true;
            box.rows = 3;
            box.setAttribute("aria-label", tr("share.boxAria", "Share text to copy"));
            root.appendChild(box);
          }
          box.value = r.text;
          box.focus();
          box.select();
          status.textContent = tr("share.pressCopy", "Press Ctrl+C (or ⌘C) to copy the selected text.");
        }
      });
    });
    return { destroy() { root.remove(); }, element: root };
  }

  // ---- automatic buttons on earned rows of the game's own achievements panel ---------------------------
  function isEarned(row) {
    if (row.dataset.achievementEarned === "true") return true;
    for (const c of row.classList) if (/earned$/.test(c)) return true;
    return false;
  }

  function labelOf(row) {
    const el = row.querySelector(".achievement-card-label, [data-achievement-label]");
    const t = el ? el.textContent : row.dataset.achievementId;
    return oneLine(String(t).replace(/^[\u{1F3C6}✓★\s]+/u, ""));
  }

  function decorate(panel, game, gameName) {
    panel.querySelectorAll("[data-achievement-id]").forEach((row) => {
      if (!isEarned(row) || row.querySelector(".noyvj-as")) return;
      mountButton(row, { game, gameName, achievementId: row.dataset.achievementId, label: labelOf(row) });
    });
  }

  /** Keeps Share buttons on the earned rows of `panel` (default #achievements-panel) across rebuilds. */
  function attach(opts) {
    const o = opts || {};
    const game = o.game || GAME_ID;
    if (!game) return null;
    const gameName = o.gameName || GAME_NAME || prettyName(game);
    const find = () => (typeof o.panel === "string" ? document.querySelector(o.panel) : o.panel) || document.getElementById("achievements-panel");
    let observed = null;
    let observer = null;
    let busy = false;
    const run = () => {
      const panel = find();
      if (!panel) return;
      if (panel !== observed) {
        if (observer) observer.disconnect();
        observed = panel;
        observer = new MutationObserver(() => { if (!busy) run(); });
        observer.observe(panel, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] });
      }
      busy = true;   // our own insertions must not retrigger us
      try { decorate(panel, game, gameName); } finally { busy = false; }
      // MutationObserver callbacks arrive after this function returns, so `busy` alone never caught our
      // own insertions: drop them here so they do not trigger a second, pointless pass.
      if (observer) observer.takeRecords();
    };
    run();
    const timer = setInterval(run, 1000);   // the panel is often created late
    const stop = setTimeout(() => clearInterval(timer), 120000);
    return { refresh: run, destroy() { clearInterval(timer); clearTimeout(stop); if (observer) observer.disconnect(); } };
  }

  window.NoyvjAchievementShare = { text, share, mountButton, attach, gameUrl };

  if (GAME_ID) {
    const go = () => attach({ game: GAME_ID, gameName: GAME_NAME || prettyName(GAME_ID) });
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go, { once: true });
    else go();
  }
})();
