// R4-THMO-7: One-region focus mode for mobile. Toggles a data-focus attribute on #game
// so CSS can show the focused region's card and hide the others. Clicking "A" exits focus mode.
(function () {
  var game = document.getElementById("game");
  var dots = document.querySelectorAll(".focus-dot");

  function setFocus(region) {
    if (!region || region === "a") {
      game.removeAttribute("data-focus");
    } else {
      game.setAttribute("data-focus", region);
    }
    dots.forEach(function (d) {
      d.classList.toggle("focus-dot--active", d.id === "focus-dot-" + region);
    });
  }

  dots.forEach(function (dot) {
    dot.addEventListener("click", function () {
      setFocus(dot.id.replace("focus-dot-", ""));
    });
  });

  // Default to A if not already set by a previous interaction or saved state
  if (!game.getAttribute("data-focus")) {
    setFocus("a");
  }
})();
