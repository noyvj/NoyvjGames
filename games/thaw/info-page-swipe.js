// R4-THMO-8: on phones "The Real Story" is a row of swipeable cards (the framing, the real-data tie-in, the sources),
// with position dots under it. Everything is in the page and game.py already, so it reads the same offline. The
// layout itself is CSS (style.css, under 600px); Settings > "The Real Story as one scrolling list" turns it off.
(function () {
  "use strict";
  var panel = document.getElementById("info-page-panel");
  var dotsBox = document.getElementById("info-page-dots");
  if (!panel || !dotsBox) return;
  var cards = ["info-page-framing", "info-page-tie-in", "info-page-sources"]
    .map(function (id) { return document.getElementById(id); })
    .filter(Boolean);
  if (cards.length < 2) return;

  cards.forEach(function () {
    var dot = document.createElement("span");
    dot.className = "info-page-dot";
    dotsBox.appendChild(dot);
  });
  var dots = Array.prototype.slice.call(dotsBox.querySelectorAll(".info-page-dot"));

  panel.setAttribute("role", "region");
  panel.setAttribute("aria-label", "The Real Story: scroll sideways for the next card");

  function scrollable() {
    return panel.scrollWidth > panel.clientWidth + 1;
  }

  function sync() {
    // Keyboard users reach a sideways scroller only if it is focusable (and only while it really scrolls).
    if (scrollable()) {
      panel.setAttribute("tabindex", "0");
    } else {
      panel.removeAttribute("tabindex");
    }
    var step = cards[1].offsetLeft - cards[0].offsetLeft;
    var index = step > 0 ? Math.round(panel.scrollLeft / step) : 0;
    index = Math.max(0, Math.min(cards.length - 1, index));
    dots.forEach(function (dot, i) { dot.classList.toggle("active", i === index); });
  }

  panel.addEventListener("scroll", sync, { passive: true });
  window.addEventListener("resize", sync);
  new MutationObserver(sync).observe(panel, { attributes: true, attributeFilter: ["hidden"], childList: true, subtree: true });
  new MutationObserver(sync).observe(document.documentElement, { attributes: true, attributeFilter: ["data-info-list", "data-layout"] });
  sync();
})();
