/*
 * The hub's game list, read from the lobby page itself so there is exactly one list to keep up to
 * date. settings.html and help.html use it: it fetches index.html (the service worker serves it
 * offline), reads every title card and returns
 *   [{ slug, name, blurb, tags: ["climate", ...], href }]
 * in lobby order. Resolves to [] if the page cannot be read.
 */
(function () {
  "use strict";
  let pending = null;

  function parse(html) {
    const doc = new DOMParser().parseFromString(html, "text/html");
    return Array.from(doc.querySelectorAll(".title-card")).map((card) => {
      const link = card.querySelector(".title-card-link");
      const widget = card.querySelector(".review-widget");
      const text = (selector) => ((card.querySelector(selector) || {}).textContent || "").trim();
      return {
        slug: widget ? widget.dataset.gameSlug : "",
        name: text(".title-card-name"),
        blurb: text(".title-card-blurb"),
        tags: (card.dataset.tags || "").split(/\s+/).filter(Boolean),
        href: link ? link.getAttribute("href") : "",
      };
    }).filter((g) => g.slug && g.name && g.href);
  }

  window.HubGames = {
    parse,
    load() {
      if (!pending) {
        pending = fetch("index.html")
          .then((res) => (res.ok ? res.text() : ""))
          .then(parse)
          .catch(() => []);
      }
      return pending;
    },
  };
})();
