// Include this script in index.html after the timeline markup.
(function () {
  "use strict";
  var ZOOM_KEY = "heist-timeline-zoom";
  var WRAP, TL;

  function init() {
    WRAP = document.getElementById("timeline-wrap");
    TL = document.getElementById("timeline");
    if (!WRAP || !TL) return;

    function getZoom() {
      try { return parseFloat(localStorage.getItem(ZOOM_KEY)) || 1; } catch(e) { return 1; }
    }
    function setZoom(v) {
      var clamped = Math.max(0.5, Math.min(3, v));
      TL.style.transform = "scale(" + clamped + ")";
      try { localStorage.setItem(ZOOM_KEY, String(clamped)); } catch(e) {}
    }

    // Only a phone held sideways fits the whole timeline on screen. Upright, the cells stay full size
    // (44px touch targets), so nothing is shrunk unless the player pinches on purpose.
    function autoFit() {
      var landscapePhone = window.innerWidth <= 900 && window.innerWidth > window.innerHeight;
      if (!landscapePhone) { TL.style.transform = ""; return; }
      var wrapW = WRAP.clientWidth || 300;
      var tlW = TL.scrollWidth || 400;
      var scale = Math.min(1, wrapW / tlW);
      setZoom(scale);
    }

    window.addEventListener("orientationchange", autoFit);
    window.addEventListener("resize", autoFit);
    autoFit();

    var startX = 0, startY = 0, startDist = 0;
    WRAP.addEventListener("touchstart", function(e) {
      if (e.touches.length === 2) {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
        var dx = e.touches[1].clientX - e.touches[0].clientX;
        var dy = e.touches[1].clientY - e.touches[0].clientY;
        startDist = Math.sqrt(dx*dx + dy*dy);
      }
    }, { passive: true });

    WRAP.addEventListener("touchmove", function(e) {
      if (e.touches.length === 2) {
        var dx = e.touches[1].clientX - e.touches[0].clientX;
        var dy = e.touches[1].clientY - e.touches[0].clientY;
        var dist = Math.sqrt(dx*dx + dy*dy);
        var delta = (dist - startDist) / 200;
        setZoom(getZoom() + delta);
        startDist = dist;
      }
    }, { passive: true });

    WRAP.addEventListener("touchend", function(e) {
      if (e.touches.length < 2) startDist = 0;
    }, { passive: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
