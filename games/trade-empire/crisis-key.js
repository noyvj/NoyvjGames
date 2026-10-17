/* J-10: R restarts the Trade Crisis being played (the button is only visible while one runs). */
document.addEventListener("keydown", function (e) {
  if (e.key !== "r" && e.key !== "R") return;
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  var t = e.target;
  if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return;
  var b = document.getElementById("crisis-restart-button");
  if (b && !b.hidden && !b.disabled) { e.preventDefault(); b.click(); }
});
