// Milestone 6 feedback prompt (plain JS, not Pyodide).
// Milestone 6 feedback prompt: plain JS, not Pyodide/game.py — same
// documented exception used across the other games (trivial POST to
// the shared ratings API, not game state, so no Python/pytest coverage
// needed). Reuses the schema Canopy already extended with a `response`
// field; no backend changes needed here.
//
// Iteration Pass 3 (Thaw-specific): a second yes/no question was added
// probing whether the intervention lever felt like it was working —
// the design-doc-flagged risk for this game specifically. Both answers
// fold into the single `response` string field rather than requiring a
// schema change.
(function () {
  const RATINGS_API_BASE = "https://noyvjgames.fastapicloud.dev";
  const yesButton = document.getElementById("feedback-yes-button");
  const noButton = document.getElementById("feedback-no-button");
  const interventionYesButton = document.getElementById("feedback-intervention-yes-button");
  const interventionNoButton = document.getElementById("feedback-intervention-no-button");
  const submitButton = document.getElementById("feedback-submit-button");
  const commentBox = document.getElementById("feedback-comment");
  const interventionCommentBox = document.getElementById("feedback-intervention-comment");
  const statusEl = document.getElementById("feedback-status");
  let answer = null;
  let interventionAnswer = null;

  function updateSubmitState() {
    if (answer && interventionAnswer) {
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

  function selectInterventionAnswer(value) {
    interventionAnswer = value;
    interventionYesButton.classList.toggle("selected", value === "yes");
    interventionNoButton.classList.toggle("selected", value === "no");
    updateSubmitState();
  }

  yesButton.addEventListener("click", () => selectAnswer("yes"));
  noButton.addEventListener("click", () => selectAnswer("no"));
  interventionYesButton.addEventListener("click", () => selectInterventionAnswer("yes"));
  interventionNoButton.addEventListener("click", () => selectInterventionAnswer("no"));

  submitButton.addEventListener("click", async () => {
    if (!answer || !interventionAnswer) return;
    const comment = commentBox.value.trim();
    const interventionComment = interventionCommentBox.value.trim();
    // G15: fold in which region is currently doing best as a simple
    // aggregate stat — Python already computes this every render()
    // and writes it into the hidden #best-region-hidden span, so
    // this plain-JS submission script just reads it back out rather
    // than recomputing anything itself.
    const bestRegionEl = document.getElementById("best-region-hidden");
    const bestRegion = bestRegionEl ? bestRegionEl.innerText.trim() : "";
    let summary = `understanding=${answer}; intervention_worked=${interventionAnswer}`;
    if (bestRegion) summary += `; best_region=${bestRegion}`;
    if (interventionComment) summary += ` — intervention_note: ${interventionComment}`;
    const response = comment ? `${summary} — ${comment}` : summary;

    submitButton.disabled = true;
    submitButton.textContent = "Submitting...";
    try {
      const res = await fetch(`${RATINGS_API_BASE}/ratings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ game_slug: "thaw", response }),
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
