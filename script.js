const RATINGS_API_BASE = "https://noyvjgames.fastapicloud.dev";

function renderSummary(widget, ratings) {
  const summary = widget.querySelector(".ratings-summary");
  // /ratings/{slug} also returns per-game text-feedback-prompt rows
  // (stars: null, response: "...") alongside this widget's own star
  // submissions — both share the same table, filtered only by game_slug.
  // Only star rows belong in a star average.
  const starRatings = ratings.filter((r) => typeof r.stars === "number");
  if (!starRatings.length) {
    summary.textContent = "No reviews yet — be the first.";
    return;
  }
  const average = starRatings.reduce((sum, r) => sum + r.stars, 0) / starRatings.length;
  const count = starRatings.length;
  summary.textContent = `${average.toFixed(1)} ★ average (${count} review${count === 1 ? "" : "s"})`;
}

async function loadRatings(widget) {
  const slug = widget.dataset.gameSlug;
  const summary = widget.querySelector(".ratings-summary");
  try {
    const response = await fetch(`${RATINGS_API_BASE}/ratings/${slug}`);
    if (!response.ok) throw new Error(`status ${response.status}`);
    renderSummary(widget, await response.json());
  } catch (err) {
    summary.textContent = "Reviews unavailable right now.";
  }
}

async function submitRating(widget) {
  const slug = widget.dataset.gameSlug;
  const stars = Number(widget.querySelector(".star-rating").dataset.rating);
  const comment = widget.querySelector(".comment-box").value.trim();
  const submitButton = widget.querySelector(".comment-submit");

  if (!stars) return;

  submitButton.disabled = true;
  submitButton.textContent = "Submitting...";
  try {
    const response = await fetch(`${RATINGS_API_BASE}/ratings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ game_slug: slug, stars, comment: comment || null }),
    });
    if (!response.ok) throw new Error(`status ${response.status}`);
    widget.querySelector(".comment-box").value = "";
    submitButton.textContent = "Submitted — thanks!";
    await loadRatings(widget);
  } catch (err) {
    submitButton.textContent = "Submit failed — try again";
    submitButton.disabled = false;
  }
}

document.querySelectorAll(".review-widget").forEach((widget) => {
  const ratingWidget = widget.querySelector(".star-rating");
  const stars = ratingWidget.querySelectorAll(".star");
  stars.forEach((star) => {
    star.addEventListener("click", () => {
      const value = Number(star.dataset.value);
      ratingWidget.dataset.rating = String(value);
      stars.forEach((s) => {
        s.classList.toggle("selected", Number(s.dataset.value) <= value);
      });
    });
  });

  widget.querySelector(".comment-submit").addEventListener("click", () => submitRating(widget));

  loadRatings(widget);
});
