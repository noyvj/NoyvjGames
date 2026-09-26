/*
 * Shared tutorial / "How to Play" engine.
 *
 * One script, included unchanged by every game via:
 *   <script src="../../shared/tutorial.js"></script>
 * then, after the game's own Pyodide boot finishes (game.py's setup() has
 * run and the real DOM is in place, not "Loading..." placeholders):
 *   GameTutorial.init(STEPS, { gameId: "<slug>" });
 * where STEPS is a plain array the game's own index.html defines inline,
 * each entry shaped:
 *   { selector: "#click-button", title: "Mine Iron", text: "..." }
 * `selector` is optional — omit it for a centered intro/outro card with no
 * spotlight. Every step needs `title` and `text`.
 *
 * One array of content drives two features, matching what was asked for:
 * a step-by-step spotlight walkthrough (skippable, re-openable any time),
 * and a full read-through "How to Play" page for players who'd rather
 * read than click through steps — so the two can never drift out of sync
 * with each other the way hand-duplicated copy would.
 *
 * Zero coupling to game.py / Pyodide: this only ever reads already-live
 * DOM state (getBoundingClientRect for the spotlight) and never touches
 * game state, save data, or anything Python owns. A game's own id/class
 * names are never renamed or added to by this file.
 *
 * Per-game wiring, all optional and auto-detected by element id so a game
 * only has to define STEPS and call init() — nothing else is required:
 *   #tutorial-restart-button  -- if present, wired to GameTutorial.start()
 *   #howto-toggle-button      -- if present, wired to toggle #howto-panel
 *   #howto-panel              -- if present, filled with the read-through
 *                                the first time it's opened
 *
 * Buttons this file creates for the walkthrough overlay itself (Back/
 * Next/Skip/Done) all reuse the page's own `button.secondary` class rather
 * than defining a new button look — `.secondary` is the one button class
 * confirmed present in every game's style.css (`.primary` isn't; several
 * games never defined it), so it's the only safe one to depend on here.
 * That means every game's own bevel/nameplate/LED button treatment applies
 * for free, with no per-game tutorial styling needed. The Next/Done button
 * gets one small additional accent (a blue fill) from this file's own
 * injected styles, layered on top of `.secondary`, so it's visually
 * distinguishable as the primary action without needing a second
 * site-wide button convention to exist.
 */
(function () {
  const STYLE_ID = "tutorial-widget-styles";
  const Z_OVERLAY = 10000;

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      #tutorial-overlay {
        position: fixed;
        inset: 0;
        z-index: ${Z_OVERLAY};
        background: rgba(4, 5, 10, 0.6);
        font-family: system-ui, -apple-system, sans-serif;
      }
      #tutorial-overlay[hidden] { display: none; }
      #tutorial-spotlight {
        position: absolute;
        border-radius: 12px;
        box-shadow: 0 0 0 9999px rgba(4, 5, 10, 0.72), 0 0 0 3px rgba(140, 190, 255, 0.85), 0 0 24px 4px rgba(140, 190, 255, 0.45);
        pointer-events: none;
        transition: top 0.18s ease, left 0.18s ease, width 0.18s ease, height 0.18s ease;
      }
      @media (prefers-reduced-motion: reduce) {
        #tutorial-spotlight { transition: none; }
      }
      #tutorial-card {
        position: absolute;
        max-width: min(360px, calc(100vw - 2rem));
        background: linear-gradient(165deg, rgba(26, 29, 46, 0.98), rgba(14, 16, 28, 0.98));
        border: 1px solid rgba(140, 160, 255, 0.22);
        border-radius: 14px;
        padding: 1.1rem 1.2rem 1.2rem;
        color: #eaeaf0;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
      }
      #tutorial-card.centered {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
      }
      #tutorial-step-counter {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        opacity: 0.55;
        margin: 0 0 0.4rem;
      }
      #tutorial-title {
        font-size: 1.05rem;
        font-weight: 600;
        margin: 0 0 0.5rem;
      }
      #tutorial-text {
        font-size: 0.88rem;
        line-height: 1.5;
        opacity: 0.9;
        margin: 0 0 1rem;
      }
      #tutorial-card-buttons {
        display: flex;
        gap: 0.5rem;
        align-items: center;
      }
      #tutorial-card-buttons button {
        width: auto;
        flex: 0 0 auto;
        padding: 0.55rem 1rem;
        font-size: 0.82rem;
      }
      #tutorial-skip-button {
        margin-left: auto;
        background: none !important;
        color: inherit;
        opacity: 0.6;
        box-shadow: none !important;
        border: none !important;
        text-decoration: underline;
        cursor: pointer;
      }
      #tutorial-skip-button:hover { opacity: 0.9; }
      #tutorial-card-buttons .tutorial-next-button {
        background: linear-gradient(135deg, #4a6cb5, #2c4370) !important;
        color: white !important;
        font-weight: 600;
      }
      .game-toolbar {
        display: flex;
        gap: 0.5rem;
        justify-content: center;
        margin: 0 0 1.25rem;
        flex-wrap: wrap;
      }
      .game-toolbar button {
        width: auto;
        padding: 0.5rem 0.9rem;
        font-size: 0.8rem;
      }
      #howto-panel {
        text-align: left;
      }
      #howto-panel h3 {
        font-size: 0.95rem;
        margin: 0 0 0.3rem;
      }
      #howto-panel .howto-step {
        margin: 0 0 1.1rem;
      }
      #howto-panel .howto-step p {
        margin: 0;
        font-size: 0.85rem;
        line-height: 1.5;
        opacity: 0.85;
      }
      #howto-panel .howto-step-number {
        display: inline-block;
        opacity: 0.5;
        font-size: 0.75rem;
        margin-right: 0.35rem;
      }
    `;
    document.head.appendChild(style);
  }

  function el(tag, props) {
    const node = document.createElement(tag);
    if (props) Object.assign(node, props);
    return node;
  }

  function GameTutorialFactory() {
    let steps = [];
    let gameId = "";
    let index = 0;
    let overlay = null;
    let spotlight = null;
    let card = null;
    let reposition = null;

    function storageKey() {
      return `tutorial-seen:${gameId}`;
    }

    function markSeen() {
      try {
        localStorage.setItem(storageKey(), "1");
      } catch (e) {
        /* localStorage unavailable (private browsing etc.) — non-fatal,
           the tutorial just re-offers itself next visit. */
      }
    }

    function hasSeen() {
      try {
        return localStorage.getItem(storageKey()) === "1";
      } catch (e) {
        return false;
      }
    }

    function buildOverlay() {
      overlay = el("div", { id: "tutorial-overlay" });
      overlay.hidden = true;
      spotlight = el("div", { id: "tutorial-spotlight" });
      card = el("div", { id: "tutorial-card" });
      overlay.appendChild(spotlight);
      overlay.appendChild(card);
      document.body.appendChild(overlay);

      document.addEventListener("keydown", (e) => {
        if (overlay.hidden) return;
        if (e.key === "Escape") close(true);
        else if (e.key === "ArrowRight") next();
        else if (e.key === "ArrowLeft") back();
      });
    }

    function currentTarget() {
      const step = steps[index];
      if (!step || !step.selector) return null;
      const target = document.querySelector(step.selector);
      if (!target) return null;
      // A step whose target is currently hidden (e.g. a mechanic not
      // unlocked yet, like a travel button before its research tier) falls
      // back to a centered card instead of spotlighting a zero-size box.
      if (target.hidden || target.offsetParent === null) return null;
      const rect = target.getBoundingClientRect();
      if (rect.width === 0 && rect.height === 0) return null;
      return target;
    }

    function renderStep() {
      const step = steps[index];
      if (!step) {
        close(false);
        return;
      }
      const target = currentTarget();

      if (target) {
        // `behavior: "smooth"` used to run here, with positioning deferred
        // to a fixed 260ms timeout plus a 'scroll' listener meant to catch
        // up once the animation finished. For a target far down a long
        // page, the smooth-scroll animation can genuinely take longer than
        // that (and, in at least one real environment, stopped dispatching
        // 'scroll' events before the animation visually settled) -- either
        // way, positionNow() below ran once against a mid-scroll rect and
        // then never got a correcting call, leaving the card stuck exactly
        // where that one bad reading put it: fully off-screen. An instant
        // jump removes the whole race -- there's no animation left to
        // outrun, so the very next positionNow() call always sees the
        // final, settled rect.
        target.scrollIntoView({ behavior: "auto", block: "center" });
      }

      const positionNow = () => {
        card.classList.remove("centered");
        if (target) {
          // #tutorial-overlay is `position: fixed`, which makes it the
          // containing block for its `position: absolute` children
          // (spotlight/card) -- their top/left are relative to the
          // VIEWPORT, exactly like getBoundingClientRect()'s own numbers
          // already are. Adding window.scrollX/scrollY here double-counts
          // the scroll offset once the page has actually scrolled (which
          // target.scrollIntoView() below routinely causes), pushing the
          // card further down/right the more the page is scrolled -- a
          // real bug (not a hypothetical one) that pushed step 2's card
          // fully off-screen on a short mobile viewport. Fixed by using
          // the viewport-relative rect directly, with no scroll offset.
          const rect = target.getBoundingClientRect();
          const pad = 6;
          spotlight.style.display = "block";
          spotlight.style.top = `${rect.top - pad}px`;
          spotlight.style.left = `${rect.left - pad}px`;
          spotlight.style.width = `${rect.width + pad * 2}px`;
          spotlight.style.height = `${rect.height + pad * 2}px`;

          // Horizontal first: the card's width (and so how its text wraps,
          // and so its height) depends on `left`, so it has to be applied
          // before the height is measured below.
          let cardLeft = rect.left;
          const maxLeft = document.documentElement.clientWidth - 340;
          cardLeft = Math.max(12, Math.min(cardLeft, maxLeft));
          card.style.left = `${cardLeft}px`;

          // Measure the card's real height (it varies with each step's
          // text) instead of assuming ~200px: prefer below the target if it
          // fits, else above, and in every case clamp into the viewport so
          // a tall target can't push the card past either edge.
          const cardHeight = card.offsetHeight;
          const spaceBelow = window.innerHeight - rect.bottom;
          const spaceAbove = rect.top;
          let cardTop;
          if (spaceBelow >= cardHeight + 26) {
            cardTop = rect.bottom + 14;
          } else if (spaceAbove >= cardHeight + 26) {
            cardTop = rect.top - cardHeight - 14;
          } else {
            cardTop = rect.bottom + 14;
          }
          cardTop = Math.max(12, Math.min(cardTop, window.innerHeight - cardHeight - 12));
          card.style.top = `${cardTop}px`;
        } else {
          spotlight.style.display = "none";
          // The `.centered` rule positions via top/left 50% + a translate;
          // an inline top/left left over from the previous (targeted) step
          // would override it and drag the card partly off-screen.
          card.style.top = "";
          card.style.left = "";
          card.classList.add("centered");
        }
      };

      if (reposition) {
        window.removeEventListener("scroll", reposition, true);
        window.removeEventListener("resize", reposition);
      }
      reposition = positionNow;
      window.addEventListener("scroll", reposition, true);
      window.addEventListener("resize", reposition);
      window.setTimeout(positionNow, target ? 260 : 0);

      card.innerHTML = "";
      const counter = el("p", {
        id: "tutorial-step-counter",
        innerText: `Step ${index + 1} of ${steps.length}`,
      });
      const title = el("p", { id: "tutorial-title", innerText: step.title });
      const text = el("p", { id: "tutorial-text", innerText: step.text });
      const buttons = el("div", { id: "tutorial-card-buttons" });

      if (index > 0) {
        const backBtn = el("button", { className: "secondary", innerText: "Back" });
        backBtn.type = "button";
        backBtn.addEventListener("click", back);
        buttons.appendChild(backBtn);
      }
      const nextBtn = el("button", {
        className: "secondary tutorial-next-button",
        innerText: index === steps.length - 1 ? "Done" : "Next",
      });
      nextBtn.type = "button";
      nextBtn.addEventListener("click", next);
      buttons.appendChild(nextBtn);

      const skipBtn = el("button", { id: "tutorial-skip-button", innerText: "Skip tutorial" });
      skipBtn.type = "button";
      skipBtn.addEventListener("click", () => close(true));
      buttons.appendChild(skipBtn);

      card.appendChild(counter);
      card.appendChild(title);
      card.appendChild(text);
      card.appendChild(buttons);
    }

    function next() {
      if (index >= steps.length - 1) {
        close(true);
        return;
      }
      index += 1;
      renderStep();
    }

    function back() {
      if (index <= 0) return;
      index -= 1;
      renderStep();
    }

    function close(seen) {
      if (seen) markSeen();
      if (overlay) overlay.hidden = true;
      if (reposition) {
        window.removeEventListener("scroll", reposition, true);
        window.removeEventListener("resize", reposition);
        reposition = null;
      }
    }

    function start() {
      if (!steps.length) return;
      index = 0;
      if (!overlay) buildOverlay();
      overlay.hidden = false;
      renderStep();
    }

    function renderHowTo(containerId) {
      const container = document.getElementById(containerId);
      if (!container || container.dataset.tutorialRendered) return;
      container.dataset.tutorialRendered = "1";
      steps.forEach((step, i) => {
        const wrap = el("div", { className: "howto-step" });
        const h3 = el("h3");
        h3.appendChild(el("span", { className: "howto-step-number", innerText: `${i + 1}.` }));
        h3.appendChild(document.createTextNode(step.title));
        const p = el("p", { innerText: step.text });
        wrap.appendChild(h3);
        wrap.appendChild(p);
        container.appendChild(wrap);
      });
    }

    function wireChrome(options) {
      const restartBtn = document.getElementById(options.restartButtonId || "tutorial-restart-button");
      if (restartBtn) {
        restartBtn.addEventListener("click", start);
      }

      const howtoBtn = document.getElementById(options.howtoButtonId || "howto-toggle-button");
      const howtoPanel = document.getElementById(options.howtoPanelId || "howto-panel");
      if (howtoBtn && howtoPanel) {
        const openLabel = howtoBtn.innerText;
        howtoBtn.addEventListener("click", () => {
          const willOpen = howtoPanel.hidden;
          if (willOpen) renderHowTo(options.howtoPanelId || "howto-panel");
          howtoPanel.hidden = !willOpen;
          howtoBtn.innerText = willOpen ? `Hide ${openLabel}` : openLabel;
        });
      }
    }

    return {
      init(stepList, options) {
        options = options || {};
        if (!options.gameId) {
          console.error("GameTutorial.init: missing required options.gameId");
          return;
        }
        steps = Array.isArray(stepList) ? stepList : [];
        gameId = options.gameId;
        injectStyles();
        wireChrome(options);
        if (!hasSeen() && steps.length) {
          window.setTimeout(start, 500);
        }
      },
      start,
      renderHowTo,
    };
  }

  window.GameTutorial = GameTutorialFactory();
})();
