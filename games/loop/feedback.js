// Milestone 6 feedback prompt (plain JS, not Pyodide): a yes/no plus optional comment posted to the shared ratings API.
(function () {
  const RATINGS_API_BASE = "https://noyvjgames.fastapicloud.dev";
  const yesButton = document.getElementById("feedback-yes-button");
  const noButton = document.getElementById("feedback-no-button");
  const submitButton = document.getElementById("feedback-submit-button");
  const commentBox = document.getElementById("feedback-comment");
  const statusEl = document.getElementById("feedback-status");
  let answer = null;

  function selectAnswer(value) {
    answer = value;
    yesButton.classList.toggle("selected", value === "yes");
    noButton.classList.toggle("selected", value === "no");
    submitButton.disabled = false;
    submitButton.textContent = "Submit feedback";
  }

  yesButton.addEventListener("click", () => selectAnswer("yes"));
  noButton.addEventListener("click", () => selectAnswer("no"));

  submitButton.addEventListener("click", async () => {
    if (!answer) return;
    const comment = commentBox.value.trim();
    const response = comment ? `${answer} — ${comment}` : answer;

    submitButton.disabled = true;
    submitButton.textContent = "Submitting...";
    try {
      const res = await fetch(`${RATINGS_API_BASE}/ratings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ game_slug: "loop", response }),
      });
      if (!res.ok) throw new Error(`status ${res.status}`);
      statusEl.textContent = "Thanks for the feedback!";
      submitButton.textContent = "Submitted — thanks!";
    } catch (err) {
      statusEl.textContent = "Feedback submission failed — try again.";
      submitButton.disabled = false;
      submitButton.textContent = "Submit feedback";
    }
  });
})();
