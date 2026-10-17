// Milestone 6 feedback prompt: plain JS, not Pyodide/game.py — same
// documented exception used across the other games (trivial POST to
// the shared ratings API, not game state, so no Python/pytest coverage
// needed). Reuses the schema Canopy already extended with a `response`
// field; no backend changes needed here.
//

(function () {
  const RATINGS_API_BASE = "https://noyvjgames.fastapicloud.dev";
  const yesButton = document.getElementById("feedback-yes-button");
  const noButton = document.getElementById("feedback-no-button");
  const strategyButton = document.getElementById("feedback-decoupling-strategy-button");
  const taxButton = document.getElementById("feedback-decoupling-tax-button");
  const submitButton = document.getElementById("feedback-submit-button");
  const commentBox = document.getElementById("feedback-comment");
  const statusEl = document.getElementById("feedback-status");
  let answer = null;
  let decouplingAnswer = null;

  function updateSubmitState() {
    if (answer && decouplingAnswer) {
      submitButton.disabled = false;
      submitButton.textContent = "Submit feedback";
    }
  }

  function selectAnswer(value) {
    answer = value;
    yesButton.classList.toggle("selected", value === "yes");
    noButton.classList.toggle("selected", value === "no");
    updateSubmitState();
  }

  function selectDecoupling(value) {
    decouplingAnswer = value;
    strategyButton.classList.toggle("selected", value === "strategy");
    taxButton.classList.toggle("selected", value === "tax");
    updateSubmitState();
  }

  yesButton.addEventListener("click", () => selectAnswer("yes"));
  noButton.addEventListener("click", () => selectAnswer("no"));
  strategyButton.addEventListener("click", () => selectDecoupling("strategy"));
  taxButton.addEventListener("click", () => selectDecoupling("tax"));

  submitButton.addEventListener("click", async () => {
    if (!answer || !decouplingAnswer) return;
    const comment = commentBox.value.trim();
    const summary = `understanding=${answer}; decoupling=${decouplingAnswer}`;
    const response = comment ? `${summary} — ${comment}` : summary;

    submitButton.disabled = true;
    submitButton.textContent = "Submitting...";
    try {
      const res = await fetch(`${RATINGS_API_BASE}/ratings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ game_slug: "herd", response }),
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
