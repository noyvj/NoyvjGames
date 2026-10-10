/*
 * Hub top-bar dropdowns (TODO GN-14, GN-16), loaded on index.html after script.js.
 *
 * The nav is a row of plain <details class="hub-nav-menu"> dropdowns (Me, Updates, Feedback, Help). They
 * open and close from the keyboard with no script at all (Enter or Space on the summary); this file only
 * adds the habits a menu needs:
 *   - opening one closes the others (one at a time),
 *   - Escape closes the open one and puts focus back on its button,
 *   - a click anywhere else, or tabbing out of the open menu, closes it,
 *   - choosing a link or a button inside a menu closes it (the Feedback menu stays open while you type),
 *   - links to "#site-feedback-section" (the footer's Feedback / Contact) open the Feedback menu and focus
 *     its first field, because the form no longer sits at the bottom of the page.
 * The Feedback menu also holds the shared "Report a problem" button (shared/report-problem.js, mounted
 * into #nav-report-slot with game id "hub"); opening its dialog closes the menu so the dialog's focus
 * return goes somewhere visible.
 *
 * window.HubNav: closeAll(), open(id), menus().
 */
(function () {
  "use strict";

  function menus() { return Array.prototype.slice.call(document.querySelectorAll(".hub-nav-menu")); }

  function closeAll(except, returnFocus) {
    menus().forEach((m) => {
      if (m === except || !m.open) return;
      m.open = false;
      if (returnFocus) { const s = m.querySelector("summary"); if (s) s.focus(); }
    });
  }

  function open(id) {
    const m = document.getElementById(id);
    if (!m) return null;
    closeAll(m);
    m.open = true;
    return m;
  }

  // Opens the Feedback menu at the top of the page and puts focus in its comment box.
  function openFeedback() {
    const m = open("nav-feedback");
    if (!m) return;
    const top = document.getElementById("hub-header");
    if (top) top.scrollIntoView({ block: "start" });
    const field = m.querySelector("#site-feedback-comment") || m.querySelector(".noyvj-report-button");
    if (field) field.focus({ preventScroll: true });
  }

  function start() {
    // Other pages link here as index.html#site-feedback-section; the form now lives in the menu.
    if (location.hash === "#site-feedback-section") openFeedback();
    window.addEventListener("hashchange", () => { if (location.hash === "#site-feedback-section") openFeedback(); });
    menus().forEach((m) => {
      m.addEventListener("toggle", () => { if (m.open) closeAll(m); });
      // Tabbing out of an open menu closes it, so focus never sits behind or beside a stale open panel.
      m.addEventListener("focusout", (ev) => {
        if (m.open && ev.relatedTarget && !m.contains(ev.relatedTarget)) m.open = false;
      });
      // Choosing something inside closes the menu; typing in the feedback form must not.
      m.addEventListener("click", (ev) => {
        const t = ev.target instanceof Element ? ev.target.closest("a, button") : null;
        if (!t || !m.contains(t)) return;
        if (t.closest("#site-feedback-section")) return;
        if (t.classList.contains("noyvj-report-button")) { setTimeout(() => { m.open = false; }, 0); return; }
        if (t.closest("summary")) return;
        m.open = false;
      });
    });

    // The report dialog was opened from a button inside the (now closed) Feedback menu: put focus back on the
    // menu's own button when the dialog closes, rather than letting it fall to the top of the page.
    document.addEventListener("close", (ev) => {
      const t = ev.target;
      if (t instanceof Element && t.classList.contains("noyvj-report-dialog")) {
        // After the report script's own close handler (which tries to focus its now-hidden button).
        setTimeout(() => { const s = document.querySelector("#nav-feedback > summary"); if (s) s.focus(); }, 0);
      }
    }, true);

    // Escape closes the open menu wherever focus is; focus goes back to its button when it was inside it.
    document.addEventListener("keydown", (ev) => {
      if (ev.key !== "Escape") return;
      const openMenu = menus().find((m) => m.open);
      if (!openMenu) return;
      const hadFocus = openMenu.contains(document.activeElement);
      openMenu.open = false;
      if (hadFocus) { const s = openMenu.querySelector("summary"); if (s) s.focus(); }
    });

    document.addEventListener("click", (ev) => {
      const target = ev.target instanceof Element ? ev.target : null;
      const feedbackLink = target && target.closest("a[href='#site-feedback-section']");
      if (feedbackLink) {
        ev.preventDefault();
        openFeedback();
        return;
      }
      if (!target || !target.closest(".hub-nav-menu")) closeAll();
    });
  }

  window.HubNav = { closeAll, open, menus, openFeedback };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
