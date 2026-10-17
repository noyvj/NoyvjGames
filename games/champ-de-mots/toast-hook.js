// The achievement toast's auto-hide timer: scheduled here, not from Python (see the note above this script in index.html).
window.scheduleAchievementToastHide = function (ms) {
  clearTimeout(window._achievementToastTimer);
  window._achievementToastTimer = setTimeout(function () {
    const toast = document.getElementById("achievement-toast");
    if (!toast) return;
    toast.classList.remove("achievement-toast--visible");
    toast.hidden = true;
  }, ms);
};
