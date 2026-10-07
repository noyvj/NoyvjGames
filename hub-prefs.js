/*
 * Loaded in <head> on every hub page, before first paint. Applies the one hub-only preference that
 * has to be in place early: "reduce motion" (settings.html), which switches off the decorative
 * background drift and card transitions. Theme is handled by shared/theme.js.
 */
(function () {
  try {
    if (localStorage.getItem("hub_reduced_motion") === "true") {
      document.documentElement.setAttribute("data-hub-reduced-motion", "true");
    }
  } catch (err) { /* storage blocked: leave motion as it is */ }
})();
