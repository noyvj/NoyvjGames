// R4-THMO-4: Escalating haptic feedback on threshold crossings.
(function () {
  if (typeof navigator === "undefined" || !navigator.vibrate) return;

  const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  function isReducedMotion() {
    return mediaQuery.matches || document.documentElement.dataset.reducedMotion === "true";
  }
  if (isReducedMotion()) return;

  let lastCrossedThreshold = -1;
  const thresholds = [10, 15];
  const patterns = { 10: [200], 15: [200, 100, 300] };

  function triggerHaptic(temp) {
    for (const t of thresholds) {
      if (temp >= t && lastCrossedThreshold < t) {
        navigator.vibrate(patterns[t]);
        lastCrossedThreshold = t;
        const el = document.getElementById("temperature-display");
        if (el) {
          el.classList.add("threshold-crossed-pulse");
          setTimeout(() => el.classList.remove("threshold-crossed-pulse"), 900);
        }
      }
    }
  }

  const el = document.getElementById("temperature-display");
  if (!el) return;

  const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
      const text = m.target.textContent || "";
      const match = text.match(/[\+\-]?\d+\.?\d*/);
      if (match) {
        const val = parseFloat(match[0]);
        if (!isNaN(val)) triggerHaptic(val);
      }
    }
  });

  observer.observe(el, { characterData: true, subtree: true, childList: true });
})();
