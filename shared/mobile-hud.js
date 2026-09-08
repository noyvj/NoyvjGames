/*
 * Shared mobile HUD bar — always-visible key stats on narrow screens.
 *
 * The problem this fixes: on mobile, a game's stats sit near the top of a
 * long, single-column page, but the buttons that change them (buy, invest,
 * submit) are further down. Pressing one meant scrolling back up just to
 * see whether funds/a resource actually moved. This mirrors 1-3 of a
 * game's own live numbers into a small bar pinned to the top of the
 * viewport, so they're visible no matter how far down the page you've
 * scrolled — without changing where those numbers live or how game.py
 * renders them.
 *
 * One script, included unchanged by every game via:
 *   <script src="../../shared/mobile-hud.js"></script>
 * then, after the game's own Pyodide boot finishes (same timing as
 * GameTutorial.init — after game.py's setup() has run):
 *   MobileHud.init([
 *     { selector: "#resource-count", label: "Iron" },
 *     { selector: "#ecology-percent", label: "Ecology" },
 *   ]);
 * `selector` must point at an element whose text content IS the number to
 * show (not a parent containing other text) — pick the same elements
 * game.py already writes via `.innerText =` on every render/tick.
 *
 * Zero coupling to game.py: this only ever reads already-live DOM text via
 * a MutationObserver, mirroring it into its own bar. It never writes back
 * to the game's own elements, never touches game state or save data, and
 * adds no new ids to the game's own markup. The bar is CSS-hidden above a
 * mobile breakpoint, so desktop play is completely unaffected.
 */
(function () {
  const STYLE_ID = "mobile-hud-styles";
  const BAR_ID = "mobile-hud-bar";

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      #${BAR_ID} {
        display: none;
      }
      @media (max-width: 640px) {
        #${BAR_ID} {
          display: flex;
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          z-index: 9998;
          gap: 0.5rem;
          padding: 0.5rem 0.6rem;
          background: rgba(8, 9, 16, 0.92);
          border-bottom: 1px solid rgba(140, 160, 255, 0.18);
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
          font-family: system-ui, -apple-system, sans-serif;
          overflow-x: auto;
          -webkit-tap-highlight-color: transparent;
        }
        body.has-mobile-hud {
          padding-top: 44px;
        }
      }
      .mobile-hud-chip {
        display: flex;
        align-items: baseline;
        gap: 0.3rem;
        flex: 0 0 auto;
        white-space: nowrap;
        font-size: 0.78rem;
        color: #eaeaf0;
      }
      .mobile-hud-chip-label {
        opacity: 0.6;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-size: 0.65rem;
      }
      .mobile-hud-chip-value {
        font-weight: 600;
        font-variant-numeric: tabular-nums;
      }
    `;
    document.head.appendChild(style);
  }

  function el(tag, props) {
    const node = document.createElement(tag);
    if (props) Object.assign(node, props);
    return node;
  }

  window.MobileHud = {
    init(fields) {
      if (!Array.isArray(fields) || !fields.length) return;
      injectStyles();

      const bar = el("div", { id: BAR_ID });
      bar.setAttribute("aria-hidden", "true");
      bar.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: "smooth" });
      });

      let wiredAny = false;
      fields.forEach((field) => {
        const source = document.querySelector(field.selector);
        if (!source) return;
        wiredAny = true;

        const chip = el("div", { className: "mobile-hud-chip" });
        const label = el("span", { className: "mobile-hud-chip-label", innerText: field.label || "" });
        const value = el("span", { className: "mobile-hud-chip-value", innerText: source.textContent });
        chip.appendChild(label);
        chip.appendChild(value);
        bar.appendChild(chip);

        const sync = () => {
          value.innerText = source.textContent;
        };
        const observer = new MutationObserver(sync);
        observer.observe(source, { characterData: true, childList: true, subtree: true });
      });

      if (!wiredAny) return;
      document.body.appendChild(bar);
      document.body.classList.add("has-mobile-hud");
    },
  };
})();
