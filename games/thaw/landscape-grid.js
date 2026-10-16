// R4-THMO-5: Landscape comparison board. Toggles data-landscape on #game so CSS can
// rearrange the layout reliably during orientation changes without relying solely on
// media queries that sometimes lag during rapid rotation.
(function () {
  function updateLandscape() {
    const isLandscape = window.matchMedia("(orientation: landscape)").matches;
    document.getElementById("game").dataset.landscape = isLandscape ? "true" : "";
  }
  window.addEventListener("resize", updateLandscape);
  window.addEventListener("orientationchange", updateLandscape);
  updateLandscape();
})();
