/*
 * Shared light/dark theme switch (Y11). Sets <html data-theme="dark|light">
 * before first paint (include it in <head>, unmarked as async/defer), from a
 * per-device choice in localStorage["theme"] ("dark" | "light"), falling back
 * to the browser's prefers-color-scheme. Pages opt in to a visible toggle by
 * having an element with id "theme-toggle" (the hub nav gets one); games will
 * get theirs in their Settings panels as each game's stylesheet gains its
 * light palette. window.NoyvjTheme.set()/get()/toggle() are the API.
 *
 * A stylesheet supports the light theme by defining rules under
 * html[data-theme="light"]. A page with no such rules simply stays dark, so
 * including this script is always safe.
 */
(function () {
  const KEY = "theme";
  function stored() {
    try { const v = localStorage.getItem(KEY); return v === "light" || v === "dark" ? v : null; }
    catch (err) { return null; }
  }
  function preferred() {
    try {
      if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) return "light";
    } catch (err) { /* fall through */ }
    return "dark";
  }
  let current = stored() || preferred();

  function refreshToggles() {
    document.querySelectorAll("#theme-toggle, .theme-toggle").forEach((el) => {
      el.textContent = current === "light" ? "🌙 Dark mode" : "☀️ Light mode";
      el.setAttribute("aria-pressed", String(current === "light"));
    });
  }
  function apply() {
    document.documentElement.setAttribute("data-theme", current);
    refreshToggles();
  }
  function set(theme) {
    if (theme !== "light" && theme !== "dark") return;
    current = theme;
    try { localStorage.setItem(KEY, theme); } catch (err) { /* convenience only */ }
    apply();
  }
  window.NoyvjTheme = {
    get: () => current,
    set,
    toggle: () => set(current === "light" ? "dark" : "light"),
  };
  apply();
  // Games have no shared nav, so a script tag with data-floating-toggle gets
  // a small fixed pill (bottom-left, above the story toggle).
  const script = document.currentScript;
  const wantsFloating = Boolean(script && script.hasAttribute("data-floating-toggle"));
  document.addEventListener("DOMContentLoaded", () => {
    if (wantsFloating) {
      const pill = document.createElement("button");
      pill.type = "button";
      pill.id = "theme-toggle-floating";
      pill.className = "theme-toggle";
      document.body.appendChild(pill);
    }
    refreshToggles();
    document.querySelectorAll("#theme-toggle, .theme-toggle").forEach((el) => {
      el.addEventListener("click", () => window.NoyvjTheme.toggle());
    });
  });
})();
