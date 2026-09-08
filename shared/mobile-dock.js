/*
 * Shared mobile dock — pins a game's "act on your current selection"
 * panel to the bottom of the viewport on narrow screens.
 *
 * The problem: several games split their core loop into two panels far
 * apart in the page (e.g. Canopy's #plot-grid up top, #action-panel with
 * Clear/Replant much further down) — on a phone that meant scroll down to
 * select something, scroll further to act on it, then scroll back up to
 * see the result. This physically moves that panel to a fixed bar pinned
 * to the bottom of the screen on mobile, so both halves of the loop are
 * visible/reachable without scrolling — then moves it back to its normal
 * position if the viewport widens back past the breakpoint (e.g. a
 * rotated tablet, or a resized window).
 *
 * One script, included unchanged by every game via:
 *   <script src="../../shared/mobile-dock.js"></script>
 * then, after the game's own Pyodide boot finishes (same timing as
 * GameTutorial.init / MobileHud.init):
 *   MobileDock.init("#action-panel");
 *
 * A plain CSS media query can't move an element between different
 * parents, so this does the reparenting in JS -- but the actual fixed-bar
 * *styling* (position, bottom offset, colors) stays in each game's own
 * style.css media query, same as any other CSS. This file only moves the
 * node; it never restyles it, and never touches game.py or any id/class
 * the game's own render logic depends on -- game.py keeps finding the
 * same element via the same id, wherever in the DOM it currently lives.
 *
 * IMPORTANT for whoever adds a mobile media query for the docked panel:
 * `position: fixed` is positioned relative to the nearest ancestor that
 * has a `transform`/`filter`/`backdrop-filter`/`will-change` property set
 * (a CSS quirk, not a bug in this file) -- if the panel's original parent
 * chain includes such an ancestor (a glass-panel `#game` wrapper with
 * `backdrop-filter` is extremely common across this site's games), a
 * `position: fixed` panel left inside it will be positioned relative to
 * that ancestor's box instead of the real viewport, landing far off
 * -screen. This file avoids that by moving the panel to be a direct
 * child of <body>, which has no such ancestor.
 */
(function () {
  window.MobileDock = {
    init(selector, options) {
      const el = document.querySelector(selector);
      if (!el) return;

      const breakpoint = (options && options.breakpoint) || 640;
      const placeholder = document.createComment(`mobile-dock-anchor:${selector}`);
      el.parentNode.insertBefore(placeholder, el);

      const mql = window.matchMedia(`(max-width: ${breakpoint}px)`);

      function apply(isMobile) {
        if (isMobile) {
          if (el.parentNode !== document.body) {
            document.body.appendChild(el);
          }
          el.classList.add("mobile-docked");
        } else {
          if (el.parentNode === document.body) {
            placeholder.parentNode.insertBefore(el, placeholder.nextSibling);
          }
          el.classList.remove("mobile-docked");
        }
      }

      apply(mql.matches);
      // Older WebKit only supports addListener; both are wired for safety.
      if (mql.addEventListener) {
        mql.addEventListener("change", (e) => apply(e.matches));
      } else if (mql.addListener) {
        mql.addListener((e) => apply(e.matches));
      }
    },
  };
})();
