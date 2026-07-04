// Hub-level star rating: visual only, nothing persisted anywhere yet.
// TODO: persistence pending hosting setup
document.querySelectorAll(".star-rating").forEach((widget) => {
  const stars = widget.querySelectorAll(".star");
  stars.forEach((star) => {
    star.addEventListener("click", () => {
      const value = Number(star.dataset.value);
      widget.dataset.rating = String(value);
      stars.forEach((s) => {
        s.classList.toggle("selected", Number(s.dataset.value) <= value);
      });
    });
  });
});
