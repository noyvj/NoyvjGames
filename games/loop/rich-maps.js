/*
 * Loop -- H25b/H29b rich map helpers: the opt-in visual trade network and
 * circular supply chain map.
 *
 * Like settings.js, deliberately independent of Pyodide: game.py builds the
 * SVG markup from the real game state; this file only provides
 *   1. window.loopVisual -- the tiny bridge game.py reads/writes: SVG
 *      support detection and the per-browser on/off preference (localStorage,
 *      every access try/catch-wrapped so a locked-down browser just forgets
 *      the choice instead of breaking the page);
 *   2. hover / keyboard-focus tooltips for the maps' nodes and flows,
 *      delegated on each .rich-map-panel so they survive game.py rebuilding
 *      the SVG on every render.
 *
 * Reduced motion needs nothing here: the flow animation is pure CSS and is
 * switched off by both the OS setting and the in-game Settings checkbox
 * (html[data-reduced-motion="true"]) -- see style.css.
 */
(function () {
  "use strict";

  function svgSupported() {
    try {
      return !!(
        document.createElementNS &&
        document.createElementNS("http://www.w3.org/2000/svg", "svg").createSVGRect
      );
    } catch (e) {
      return false;
    }
  }

  window.loopVisual = {
    supported: svgSupported,
    get: function (key) {
      try {
        return window.localStorage.getItem(key);
      } catch (e) {
        return null;
      }
    },
    set: function (key, value) {
      try {
        window.localStorage.setItem(key, value);
      } catch (e) {
        // Losing the remembered choice is not worth breaking anything.
      }
    },
  };

  function hit(target) {
    return target && target.closest ? target.closest(".rich-hit[data-tip]") : null;
  }

  function showTip(panel, tip, source, ev) {
    const text = source.getAttribute("data-tip");
    if (!text) return;
    tip.textContent = text;
    tip.hidden = false;
    const box = panel.getBoundingClientRect();
    let x;
    let y;
    if (ev && typeof ev.clientX === "number" && ev.type.indexOf("mouse") === 0) {
      x = ev.clientX - box.left;
      y = ev.clientY - box.top;
    } else {
      const r = source.getBoundingClientRect();
      x = r.left + r.width / 2 - box.left;
      y = r.top + r.height / 2 - box.top;
    }
    // Keep the tooltip inside the panel horizontally, just below the point.
    const width = tip.offsetWidth || 240;
    tip.style.left = Math.max(4, Math.min(x + 12, box.width - width - 4)) + "px";
    tip.style.top = y + 16 + "px";
  }

  function wire(panel) {
    const tip = panel.querySelector(".rich-tooltip");
    if (!tip) return;
    const hide = function () {
      tip.hidden = true;
    };
    panel.addEventListener("mouseover", function (ev) {
      const el = hit(ev.target);
      if (el) showTip(panel, tip, el, ev);
    });
    panel.addEventListener("mousemove", function (ev) {
      const el = hit(ev.target);
      if (el) showTip(panel, tip, el, ev);
    });
    panel.addEventListener("mouseout", function (ev) {
      if (hit(ev.target)) hide();
    });
    panel.addEventListener("focusin", function (ev) {
      const el = hit(ev.target);
      if (el) showTip(panel, tip, el, ev);
    });
    panel.addEventListener("focusout", hide);
    panel.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") hide();
    });
    // game.py rebuilds the SVG on every render; a hovered element vanishing
    // never fires mouseout, so drop the tooltip whenever the body changes.
    const body = panel.querySelector(".rich-map-body");
    if (body && window.MutationObserver) {
      new MutationObserver(function () {
        if (!panel.contains(document.activeElement) || !hit(document.activeElement)) hide();
      }).observe(body, { childList: true });
    }
  }

  function init() {
    document.querySelectorAll(".rich-map-panel").forEach(wire);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
