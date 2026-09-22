/*
 * shared/keyboard-shortcuts.js
 *
 * Site-wide keyboard-shortcut convention (Z4, planning/TODO.md, decided by
 * the task itself): "?" opens/closes a small keyboard-shortcuts help
 * overlay; "Esc" closes whichever of the game's own panels is currently
 * open. Continuum built this pattern first, independently, before this
 * shared helper existed (its own in-page `#shortcuts-panel`, wired by hand
 * in `games/continuum/index.html` -- see that game's CLAUDE.md, K27) --
 * every other game wires up through this file instead of re-inventing it,
 * so the site has one real shape rather than eleven near-duplicates.
 *
 * Deliberately plain DOM, zero Pyodide/game-state awareness -- this is
 * pure panel show/hide, not game logic. A panel is closed by calling
 * `.click()` on ITS OWN toggle button (never by touching `.hidden`
 * directly), so each panel's own open/close function -- including any
 * button-label swap like "Achievements" <-> "Hide Achievements" -- stays
 * the single source of truth for its own state. This mirrors how
 * `shared/last-played.js`/`shared/whats-new-banner.js` stay narrow, generic
 * helpers that a small per-game config snippet drives, rather than needing
 * per-game forks.
 *
 * Usage -- one script include, then one call after the game's own toolbar
 * buttons/panels exist in the DOM (same "call after boot" spot the other
 * shared UI helpers already use):
 *
 *   <script src="../../shared/keyboard-shortcuts.js"></script>
 *   ...
 *   window.KeyboardShortcuts.init({
 *     panels: [
 *       { toggle: "howto-toggle-button", panel: "howto-panel" },
 *       { toggle: "achievements-toggle-button", panel: "achievements-panel" },
 *       // ...every OTHER real toggle-button + hidden-panel pair this game has
 *     ],
 *     extra: ["N — select the plot a pending request names"], // optional:
 *       // this game's OWN other shortcuts, listed in the help overlay only
 *       // -- KeyboardShortcuts doesn't implement them, the game's own code
 *       // already does (and already has its own focused-input guard).
 *   });
 *
 * Only panels with a real, single toggle button that shows/hides them are
 * listed. A section that's always visible, a one-time end-of-run/epilogue
 * screen with no reopen affordance, or a panel whose visibility is driven
 * by game state rather than a player toggle (a pending request banner, an
 * unlock reveal) has nothing for a generic Esc handler to safely close, so
 * those are left out of each game's own config -- documented per game in
 * that game's own CLAUDE.md note, not silently guessed at here.
 */
(function () {
  "use strict";

  function isTypingTarget(target) {
    if (!target) return false;
    var tag = target.tagName;
    return (
      tag === "INPUT" ||
      tag === "TEXTAREA" ||
      tag === "SELECT" ||
      Boolean(target.isContentEditable)
    );
  }

  function buildHelpOverlay(id, extraLines) {
    var backdrop = document.createElement("div");
    backdrop.id = id + "-backdrop";
    backdrop.setAttribute("aria-hidden", "true");
    backdrop.style.cssText = [
      "position:fixed",
      "inset:0",
      "background:rgba(0,0,0,0.55)",
      "z-index:9998",
      "display:none",
    ].join(";");

    var panel = document.createElement("div");
    panel.id = id;
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "true");
    panel.setAttribute("aria-label", "Keyboard shortcuts");
    panel.hidden = true;
    panel.style.cssText = [
      "position:fixed",
      "top:50%",
      "left:50%",
      "transform:translate(-50%,-50%)",
      "z-index:9999",
      "background:rgba(18,18,30,0.97)",
      "color:#f2f2f7",
      "border:1px solid rgba(255,255,255,0.18)",
      "border-radius:12px",
      "padding:1.25rem 1.5rem",
      "max-width:min(90vw,380px)",
      "max-height:80vh",
      "overflow:auto",
      "box-shadow:0 12px 40px rgba(0,0,0,0.55)",
      "font-size:0.95rem",
      "line-height:1.5",
    ].join(";");

    var heading = document.createElement("h2");
    heading.textContent = "Keyboard shortcuts";
    heading.style.cssText = "margin:0 0 0.6rem;font-size:1.05rem;color:inherit;";
    panel.appendChild(heading);

    var list = document.createElement("ul");
    list.style.cssText = "margin:0;padding-left:1.1rem;list-style:disc;";
    var lines = ["? — show or hide this list"]
      .concat(extraLines || [])
      .concat(["Esc — close this list, or whichever panel is open"]);
    lines.forEach(function (text) {
      var li = document.createElement("li");
      li.textContent = text;
      li.style.cssText = "margin:0.15rem 0;";
      list.appendChild(li);
    });
    panel.appendChild(list);

    var note = document.createElement("p");
    note.textContent = "Shortcuts pause while you're typing in a text field.";
    note.style.cssText = "margin:0.75rem 0 0;font-size:0.8rem;opacity:0.75;";
    panel.appendChild(note);

    document.body.appendChild(backdrop);
    document.body.appendChild(panel);

    function setOpen(open) {
      panel.hidden = !open;
      backdrop.style.display = open ? "block" : "none";
    }
    backdrop.addEventListener("click", function () {
      setOpen(false);
    });

    return { panel: panel, setOpen: setOpen };
  }

  window.KeyboardShortcuts = {
    init: function (config) {
      config = config || {};
      var panels = config.panels || [];
      var helpId = config.helpPanelId || "kb-shortcuts-panel";

      var help;
      var existingPanel = document.getElementById(helpId);
      if (existingPanel) {
        // A game that already built its own help panel (Continuum) --
        // track it rather than building a second, competing one.
        help = {
          panel: existingPanel,
          setOpen: function (open) {
            existingPanel.hidden = !open;
          },
        };
      } else {
        help = buildHelpOverlay(helpId, config.extra);
      }

      document.addEventListener("keydown", function (event) {
        if (isTypingTarget(event.target)) return;
        if (event.ctrlKey || event.metaKey || event.altKey) return;

        if (event.key === "?") {
          help.setOpen(help.panel.hidden);
          event.preventDefault();
          return;
        }

        if (event.key === "Escape") {
          var closedSomething = false;
          if (!help.panel.hidden) {
            help.setOpen(false);
            closedSomething = true;
          }
          panels.forEach(function (entry) {
            var panelEl = document.getElementById(entry.panel);
            var toggleEl = document.getElementById(entry.toggle);
            if (panelEl && !panelEl.hidden && toggleEl) {
              toggleEl.click();
              closedSomething = true;
            }
          });
          if (closedSomething) event.preventDefault();
        }
      });
    },
  };
})();
