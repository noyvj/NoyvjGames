/*
 * Hub mobile app shell (TODO Y-16), loaded on index.html after script.js.
 *
 *  - Bottom bar (#app-nav, phones only, CSS hides it above 640px): Games and Today scroll to their
 *    sections, More opens a short list (Settings, Help, Credits, Achievements). There is no Profile
 *    target because no profile page exists yet. The bar sits above the ad bar and clears the
 *    installed-app safe area; the page reserves matching space so nothing hides behind it.
 *  - Pull to refresh: only where the browser has no pull-to-refresh of its own, i.e. when the hub is
 *    installed as an app (display-mode: standalone, or iOS navigator.standalone). Pulling down from
 *    the top past a threshold asks the service worker to check for a new version (registration
 *    update) and then reloads; the worker serves the network first, so the reload revalidates.
 *    It never starts inside a dialog, a field, a scrolling panel or the More list, and reduced
 *    motion removes the indicator's animation (the text stays).
 *
 * window.HubShell: setActive(name), standalone(), PULL_THRESHOLD.
 */
(function () {
  "use strict";

  const PULL_THRESHOLD = 80;
  const nav = document.getElementById("app-nav");
  const moreBtn = document.getElementById("app-nav-more");
  const sheet = document.getElementById("app-nav-sheet");
  const indicator = document.getElementById("pull-refresh");

  function standalone() {
    try {
      return Boolean(window.navigator.standalone) || (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches);
    } catch (e) { return false; }
  }

  // ---- bottom bar -------------------------------------------------------------------------------

  function setActive(name) {
    if (!nav) return;
    nav.querySelectorAll("[data-nav]").forEach((a) => {
      if (a.dataset.nav === name) a.setAttribute("aria-current", "true"); else a.removeAttribute("aria-current");
    });
  }

  function closeSheet(returnFocus) {
    if (!sheet || sheet.hidden) return;
    sheet.hidden = true;
    moreBtn.setAttribute("aria-expanded", "false");
    if (returnFocus) moreBtn.focus();
  }

  function initNav() {
    if (!nav) return;
    nav.querySelectorAll("a[data-nav]").forEach((a) => {
      a.addEventListener("click", (ev) => {
        const target = document.querySelector(a.getAttribute("href"));
        closeSheet(false);
        if (!target) return;
        ev.preventDefault();
        target.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
        if (target.hasAttribute("tabindex")) target.focus({ preventScroll: true });
        setActive(a.dataset.nav);
      });
    });
    moreBtn.addEventListener("click", () => {
      const open = sheet.hidden;
      sheet.hidden = !open;
      moreBtn.setAttribute("aria-expanded", String(open));
      if (open) { const first = sheet.querySelector("a"); if (first) first.focus(); }
    });
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && !sheet.hidden) { ev.preventDefault(); closeSheet(true); }
    });
    document.addEventListener("click", (ev) => {
      if (!sheet.hidden && !nav.contains(ev.target)) closeSheet(false);
    });
    // Tab out of the list closes it so the focus order never gets stuck behind an open panel.
    sheet.addEventListener("focusout", (ev) => {
      if (!sheet.hidden && ev.relatedTarget && !nav.contains(ev.relatedTarget)) closeSheet(false);
    });

    // Which section is on screen: the Today strip counts while any of it is in the top half.
    const today = document.getElementById("today-strip");
    const grid = document.getElementById("game-grid");
    if ("IntersectionObserver" in window && today && grid) {
      const seen = { today: false, games: false };
      const io = new IntersectionObserver((entries) => {
        entries.forEach((e) => { seen[e.target === today ? "today" : "games"] = e.isIntersecting; });
        setActive(seen.games && !seen.today ? "games" : seen.today && !seen.games ? "today" : seen.games ? "games" : "");
      }, { rootMargin: "0px 0px -50% 0px" });
      io.observe(today);
      io.observe(grid);
    }
  }

  // ---- pull to refresh --------------------------------------------------------------------------

  function setIndicator(text, pull) {
    if (!indicator) return;
    indicator.hidden = !text;
    indicator.textContent = text;
    indicator.style.setProperty("--pull", String(Math.min(pull || 0, PULL_THRESHOLD * 1.4)) + "px");
  }

  async function refresh() {
    setIndicator("Refreshing…", PULL_THRESHOLD);
    try {
      if ("serviceWorker" in navigator) {
        const reg = await navigator.serviceWorker.getRegistration();
        if (reg) await Promise.race([reg.update(), new Promise((r) => setTimeout(r, 3000))]);
      }
    } catch (e) { /* the reload below still revalidates */ }
    location.reload();
  }

  function blocked(target) {
    if (!(target instanceof Element)) return true;
    if (document.getElementById("onboarding-survey-overlay") || (document.getElementById("tutorial-overlay") && !document.getElementById("tutorial-overlay").hidden)) return true;
    if (target.closest("input, textarea, select, button, [contenteditable], #app-nav, dialog, [role='dialog']")) return true;
    // Inside something that can itself scroll: the gesture belongs to it.
    for (let n = target; n && n !== document.body; n = n.parentElement) {
      const oy = getComputedStyle(n).overflowY;
      if ((oy === "auto" || oy === "scroll") && n.scrollHeight > n.clientHeight) return true;
    }
    return false;
  }

  function initPull() {
    if (!standalone()) return;
    let startY = null; let pull = 0; let armed = false;
    document.addEventListener("touchstart", (ev) => {
      startY = null; pull = 0; armed = false;
      if (ev.touches.length !== 1 || window.scrollY > 0 || blocked(ev.target)) return;
      startY = ev.touches[0].clientY;
    }, { passive: true });
    document.addEventListener("touchmove", (ev) => {
      if (startY === null) return;
      if (window.scrollY > 0) { startY = null; setIndicator("", 0); return; }
      pull = ev.touches[0].clientY - startY;
      if (pull <= 8) { setIndicator("", 0); armed = false; return; }
      armed = pull >= PULL_THRESHOLD;
      setIndicator(armed ? "Release to refresh" : "Pull down to refresh", pull);
    }, { passive: true });
    document.addEventListener("touchend", () => {
      if (startY === null) return;
      const go = armed;
      startY = null; pull = 0; armed = false;
      if (go) refresh(); else setIndicator("", 0);
    }, { passive: true });
    document.addEventListener("touchcancel", () => { startY = null; setIndicator("", 0); }, { passive: true });
  }

  window.HubShell = { setActive, standalone, PULL_THRESHOLD, closeSheet };

  function start() { initNav(); initPull(); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
