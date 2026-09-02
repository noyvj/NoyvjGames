const RATINGS_API_BASE = "https://noyvjgames.fastapicloud.dev";
// Shared across every page on the site (localStorage is keyed by origin,
// not path) — this is how a game page like SOL's save bridge knows
// whether the player is signed in without its own account UI.
const AUTH_STORAGE_KEY = "hub_bearer_token";
const AUTH_USERNAME_KEY = "hub_account_username";

function bindStarRating(ratingWidget) {
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
}

function resetStarRating(ratingWidget) {
  ratingWidget.dataset.rating = "0";
  ratingWidget.querySelectorAll(".star").forEach((s) => s.classList.remove("selected"));
}

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
  // REVIEW(observability): err/status discarded, no console.error — a user
  // reporting "reviews unavailable" gives no way to tell network failure
  // from a backend 5xx from a JSON parse error, and this is the only place
  // such context would ever be visible for a personal-site-scale project.
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
  bindStarRating(widget.querySelector(".star-rating"));
  widget.querySelector(".comment-submit").addEventListener("click", () => submitRating(widget));
  loadRatings(widget);
});

// --- Accounts (ACCOUNTS-AND-FEEDBACK-DESIGN.md Phase 2, revised: username
// + password, no email — see main.py for why) ---

// REVIEW(reuse): getBearerToken/authHeaders duplicate shared/save-widget.js's
// own authHeaders() — both independently hardcode the bearer-token
// localStorage key ("hub_bearer_token" here as AUTH_STORAGE_KEY, same string
// as save-widget.js's AUTH_TOKEN_KEY) and build the same header object.
function getBearerToken() {
  return localStorage.getItem(AUTH_STORAGE_KEY);
}

function authHeaders() {
  const token = getBearerToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const accountSignedOut = document.getElementById("account-signed-out");
const accountSignedIn = document.getElementById("account-signed-in");
const accountUsernameInput = document.getElementById("account-username-input");
const accountPasswordInput = document.getElementById("account-password-input");
const accountLoginButton = document.getElementById("account-login-button");
const accountSignupButton = document.getElementById("account-signup-button");
const accountStatus = document.getElementById("account-status");
const accountUsernameDisplay = document.getElementById("account-username-display");
const accountSignoutButton = document.getElementById("account-signout-button");
const accountMySaves = document.getElementById("account-my-saves");

function showSignedOut() {
  accountSignedOut.hidden = false;
  accountSignedIn.hidden = true;
}

function showSignedIn(username) {
  accountSignedOut.hidden = true;
  accountSignedIn.hidden = false;
  accountUsernameDisplay.textContent = `Signed in as ${username}`;
  loadMySaves();
}

async function loadMySaves() {
  accountMySaves.textContent = "Loading your saves…";
  try {
    const res = await fetch(`${RATINGS_API_BASE}/users/me/saves`, { headers: authHeaders() });
    if (!res.ok) throw new Error(`status ${res.status}`);
    const saves = await res.json();
    accountMySaves.innerHTML = "";
    if (!saves.length) {
      accountMySaves.textContent =
        'No claimed saves yet — save progress in a game, then use "Claim this save" there once signed in.';
      return;
    }
    const list = document.createElement("ul");
    list.className = "account-saves-list";
    saves.forEach((save) => {
      const item = document.createElement("li");
      const label = document.createElement("span");
      label.textContent = `${save.game_id}: ${save.save_code}`;
      const copyButton = document.createElement("button");
      copyButton.type = "button";
      copyButton.className = "account-link-button";
      copyButton.textContent = "Copy code";
      copyButton.addEventListener("click", () => {
        navigator.clipboard.writeText(save.save_code);
        copyButton.textContent = "Copied!";
        setTimeout(() => (copyButton.textContent = "Copy code"), 1500);
      });
      item.appendChild(label);
      item.appendChild(copyButton);
      list.appendChild(item);
    });
    accountMySaves.appendChild(list);
  // REVIEW(patterns): discards the response body and shows a generic
  // hardcoded string, unlike submitAuth() below which reads body.detail from
  // the backend's HTTPException — the only call site in this file that
  // surfaces the real reason a request failed. Every other catch here and in
  // save-widget.js follows this same generic-message pattern instead.
  } catch (err) {
    accountMySaves.textContent = "Couldn't load your saves right now.";
  }
}

async function submitAuth(endpoint, triggerButton, busyText, idleText) {
  const username = accountUsernameInput.value.trim();
  const password = accountPasswordInput.value;
  if (!username || !password) {
    accountStatus.textContent = "Enter a username and password first.";
    return;
  }
  accountLoginButton.disabled = true;
  accountSignupButton.disabled = true;
  triggerButton.textContent = busyText;
  try {
    const res = await fetch(`${RATINGS_API_BASE}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const body = await res.json();
    if (!res.ok) {
      accountStatus.textContent = body.detail || "Something went wrong — try again.";
      return;
    }
    localStorage.setItem(AUTH_STORAGE_KEY, body.bearer_token);
    localStorage.setItem(AUTH_USERNAME_KEY, body.username);
    accountUsernameInput.value = "";
    accountPasswordInput.value = "";
    accountStatus.textContent = "";
    showSignedIn(body.username);
  } catch (err) {
    accountStatus.textContent = "Couldn't reach the server — try again.";
  } finally {
    accountLoginButton.disabled = false;
    accountSignupButton.disabled = false;
    triggerButton.textContent = idleText;
  }
}

accountLoginButton.addEventListener("click", () =>
  submitAuth("/auth/login", accountLoginButton, "Signing in...", "Sign In")
);
accountSignupButton.addEventListener("click", () =>
  submitAuth("/auth/signup", accountSignupButton, "Creating...", "Create Account")
);

accountSignoutButton.addEventListener("click", () => {
  localStorage.removeItem(AUTH_STORAGE_KEY);
  localStorage.removeItem(AUTH_USERNAME_KEY);
  showSignedOut();
});

const savedUsername = localStorage.getItem(AUTH_USERNAME_KEY);
if (getBearerToken() && savedUsername) {
  showSignedIn(savedUsername);
} else {
  showSignedOut();
}

// --- Site-wide feedback (ACCOUNTS-AND-FEEDBACK-DESIGN.md) ---

const siteFeedbackStars = document.getElementById("site-feedback-stars");
const siteFeedbackComment = document.getElementById("site-feedback-comment");
const siteFeedbackSubmit = document.getElementById("site-feedback-submit");
const siteFeedbackStatus = document.getElementById("site-feedback-status");
const siteFeedbackList = document.getElementById("site-feedback-list");

bindStarRating(siteFeedbackStars);

async function loadSiteFeedback() {
  try {
    const res = await fetch(`${RATINGS_API_BASE}/feedback`);
    if (!res.ok) throw new Error(`status ${res.status}`);
    const items = await res.json();
    siteFeedbackList.innerHTML = "";
    if (!items.length) {
      const li = document.createElement("li");
      li.textContent = "No general feedback yet — be the first.";
      siteFeedbackList.appendChild(li);
      return;
    }
    items.forEach((item) => {
      const li = document.createElement("li");
      const parts = [];
      if (item.rating) parts.push(`${item.rating}★`);
      if (item.comment) parts.push(item.comment);
      li.textContent = parts.join(" — ");
      siteFeedbackList.appendChild(li);
    });
  } catch (err) {
    siteFeedbackList.innerHTML = "";
    const li = document.createElement("li");
    li.textContent = "Feedback unavailable right now.";
    siteFeedbackList.appendChild(li);
  }
}

siteFeedbackSubmit.addEventListener("click", async () => {
  const rating = Number(siteFeedbackStars.dataset.rating) || null;
  const comment = siteFeedbackComment.value.trim() || null;
  if (!rating && !comment) {
    siteFeedbackStatus.textContent = "Add a rating or a comment first.";
    return;
  }
  siteFeedbackSubmit.disabled = true;
  siteFeedbackSubmit.textContent = "Submitting...";
  try {
    const res = await fetch(`${RATINGS_API_BASE}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ rating, comment }),
    });
    if (!res.ok) throw new Error(`status ${res.status}`);
    siteFeedbackComment.value = "";
    resetStarRating(siteFeedbackStars);
    siteFeedbackStatus.textContent = "Thanks for the feedback!";
    await loadSiteFeedback();
  } catch (err) {
    siteFeedbackStatus.textContent = "Submit failed — try again.";
  } finally {
    siteFeedbackSubmit.disabled = false;
    siteFeedbackSubmit.textContent = "Submit";
  }
});

loadSiteFeedback();
