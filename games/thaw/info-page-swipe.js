// R4-THMO-8: swipeable cards for The Real Story on mobile.
(function () {
  const panel = document.getElementById("info-page-panel");
  if (!panel) return;
  const children = Array.from(panel.children).filter((c) => !c.classList.contains("info-page-dots"));
  const dotsContainer = panel.querySelector(".info-page-dots");
  if (!dotsContainer) return;

  children.forEach(() => {
    const dot = document.createElement("span");
    dot.className = "info-page-dot";
    dotsContainer.appendChild(dot);
  });
  const dots = dotsContainer.querySelectorAll(".info-page-dot");

  function updateDots() {
    const scrollLeft = panel.scrollLeft;
    const width = panel.clientWidth;
    const index = Math.round(scrollLeft / width);
    dots.forEach((d, i) => d.classList.toggle("active", i === index));
  }

  panel.addEventListener("scroll", updateDots, { passive: true });
  window.addEventListener("resize", updateDots);
})();
