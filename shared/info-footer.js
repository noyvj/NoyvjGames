/*
 * Self-identifying footer for the info and help panels (TODO Z-29), so a screenshot or a printout
 * of "How to Play" or "The Real Story" says where it came from and how fresh it is:
 *
 *   NoyvjGames · Thaw · updated 2026-10-07 · seed THAW-K7F2Q · https://example.github.io/NoyvjGames/
 *
 * It adds one <p class="noyvj-info-footer"> as the last child of each panel named in
 * data-panels (default "#howto-panel, #info-page-panel"). The games write those panels with
 * innerHTML from Python, which would wipe a footer, so a MutationObserver puts it back and keeps
 * the text current. A panel with no content yet (hidden, empty) gets no footer.
 *
 *   game name    the page's <h1> (or the folder name)
 *   updated      the newest "date" in the game's changelog (window.CHANGELOG_JSON, which every
 *                game's boot script sets); omitted until that is available
 *   seed         only when the game has one: window.NoyvjSeed.current(), window.NOYVJ_SEED, the
 *                <html data-seed> attribute, or ?seed= in the address (Z-1 will supply these)
 *   site URL     this site's address, worked out from where this script itself was loaded
 *
 * The text is set with textContent; the footer prints (it is the point) and has its own styles.
 */
(function () {
  "use strict";
  if (window.NoyvjInfoFooter) return;

  const SCRIPT = document.currentScript;
  const SELECTOR = (SCRIPT && SCRIPT.dataset.panels) || "#howto-panel, #info-page-panel";
  const SLUG = (SCRIPT && SCRIPT.dataset.gameId) || (location.pathname.match(/\/games\/([^/]+)\//) || [, ""])[1];

  function siteUrl() {
    try { return new URL("../", SCRIPT.src).href; } catch (e) { return location.origin + "/"; }
  }

  function gameName() {
    const h1 = document.querySelector("h1");
    const text = h1 && h1.textContent.trim();
    if (text) return text;
    return SLUG ? SLUG.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "";
  }

  // The newest date, parsed once per distinct changelog (the footer text is rebuilt on every panel
  // mutation and on every poll tick; re-parsing and sorting the whole changelog each time was waste).
  let cachedSource = null;
  let cachedDate = "";
  function changelogDate() {
    const source = window.CHANGELOG_JSON;
    if (!source) return "";
    if (source === cachedSource) return cachedDate;
    let data = source;
    let date = "";
    if (typeof data === "string") { try { data = JSON.parse(data); } catch (e) { data = null; } }
    if (data) {
      const list = Array.isArray(data) ? data : Array.isArray(data.changelog) ? data.changelog : [];
      const dates = list.map((e) => e && e.date).filter((d) => typeof d === "string" && /^\d{4}-\d{2}-\d{2}/.test(d));
      date = dates.sort().pop() || "";
    }
    cachedSource = source;
    cachedDate = date;
    return date;
  }

  function seed() {
    try {
      if (window.NoyvjSeed && typeof window.NoyvjSeed.current === "function") {
        const s = window.NoyvjSeed.current();
        if (s) return String(s);
      }
    } catch (e) { /* no seed */ }
    if (window.NOYVJ_SEED) return String(window.NOYVJ_SEED);
    if (document.documentElement.dataset.seed) return document.documentElement.dataset.seed;
    return new URLSearchParams(location.search).get("seed") || "";
  }

  function footerText() {
    const parts = ["NoyvjGames"];
    const name = gameName();
    if (name) parts.push(name);
    const date = changelogDate();
    if (date) parts.push(`updated ${date.slice(0, 10)}`);
    const s = seed();
    if (s) parts.push(`seed ${s.slice(0, 40)}`);
    parts.push(siteUrl());
    return parts.join(" · ");
  }

  function injectStyle() {
    if (document.getElementById("noyvj-info-footer-style")) return;
    const style = document.createElement("style");
    style.id = "noyvj-info-footer-style";
    style.textContent = ".noyvj-info-footer { margin: 1rem 0 0; padding-top: 0.5rem; border-top: 1px solid currentColor; " +
      "font-size: 0.72rem; line-height: 1.4; opacity: 0.7; word-break: break-word; } " +
      "@media (prefers-contrast: more) { .noyvj-info-footer { opacity: 1; } }";
    document.head.appendChild(style);
  }

  function hasContent(panel) {
    return Array.prototype.some.call(panel.childNodes, (n) =>
      n.nodeType === 1 ? !n.classList.contains("noyvj-info-footer") : n.nodeType === 3 && n.textContent.trim() !== "");
  }

  function place(panel) {
    if (!hasContent(panel)) return;
    let footer = panel.querySelector(":scope > .noyvj-info-footer");
    if (!footer) {
      footer = document.createElement("p");
      footer.className = "noyvj-info-footer";
      footer.setAttribute("data-noyvj-footer", "");
    }
    const text = footerText();
    if (footer.textContent !== text) footer.textContent = text;
    if (panel.lastElementChild !== footer) panel.appendChild(footer);
  }

  const watched = new WeakSet();
  function watch(panel) {
    if (watched.has(panel)) return;
    watched.add(panel);
    place(panel);
    new MutationObserver(() => place(panel)).observe(panel, { childList: true, attributes: true, attributeFilter: ["hidden"] });
  }

  function scan() {
    injectStyle();
    document.querySelectorAll(SELECTOR).forEach(watch);
  }

  // Every comma-separated part of the selector matches something on the page.
  const PARTS = SELECTOR.split(",").map((p) => p.trim()).filter(Boolean);
  function everyPanelPresent() {
    return PARTS.every((sel) => { try { return document.querySelector(sel) !== null; } catch (e) { return true; } });
  }

  function start() {
    scan();
    // Panels some games create late, and the changelog arriving after the boot script finishes.
    // Polling ends as soon as both have happened (every panel exists and the date is known), instead
    // of always running for 60 seconds; the observers keep each footer current after that.
    let tries = 0;
    const timer = setInterval(() => {
      scan();
      document.querySelectorAll(SELECTOR).forEach(place);
      tries += 1;
      if (tries > 120 || (everyPanelPresent() && changelogDate())) clearInterval(timer);
    }, 500);
  }

  window.NoyvjInfoFooter = { text: footerText, refresh: scan };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
