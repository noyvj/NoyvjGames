/*
 * Owner gate: keeps the unlisted owner pages (admin.html, ideas.html,
 * warframe_build_tracker/) to one account, "noyvj".
 *
 * Include as the FIRST script in <head> of a page that should be gated:
 *   <script src="shared/owner-gate.js"></script>
 * It hides the whole page, then shows a small sign-in / "not your account"
 * card until GET /users/me (the backend looks the bearer token up) names the
 * owner. Same account system and storage keys as the hub's own sign-in, so
 * being signed in on the hub is enough.
 *
 * Honest limit: this is a client-side gate on a static site. It hides the
 * page for everyone else and the data behind them stays protected where the
 * backend protects it (saves per account, admin endpoints by token), but the
 * HTML/JS files themselves are still public files that anyone who knows the
 * URL can download. Nothing secret should ever live in those files.
 */
(function () {
  "use strict";
  const OWNER = "noyvj";
  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  const TOKEN_KEY = "hub_bearer_token";
  const USERNAME_KEY = "hub_account_username";
  const OK_KEY = "owner-gate-ok";
  const OK_TTL_MS = 12 * 60 * 60 * 1000; // trust a recent success so the page opens instantly

  const root = document.documentElement;
  root.classList.add("owner-locked");
  const style = document.createElement("style");
  style.textContent =
    "html.owner-locked body > :not(#owner-gate) { display: none !important; }" +
    "#owner-gate { position: fixed; inset: 0; display: flex; align-items: center; justify-content: center; padding: 1rem;" +
    " background: #0e1020; color: #eaeaf0; font: 16px/1.5 system-ui, -apple-system, sans-serif; z-index: 2147483647; }" +
    "#owner-gate .card { width: min(24rem, 100%); background: #171a2e; border: 1px solid rgba(140,160,255,0.3);" +
    " border-radius: 14px; padding: 1.2rem; display: grid; gap: 0.7rem; }" +
    "#owner-gate h1 { margin: 0; font-size: 1.1rem; font-weight: 600; }" +
    "#owner-gate p { margin: 0; color: #aab0d0; font-size: 0.9rem; }" +
    "#owner-gate input, #owner-gate button { font: inherit; padding: 0.55rem 0.7rem; border-radius: 8px; color: inherit;" +
    " border: 1px solid rgba(140,160,255,0.3); background: #1e2240; }" +
    "#owner-gate button { cursor: pointer; }" +
    "#owner-gate button.primary { background: #8fa6ff; color: #0b0d1c; font-weight: 600; border-color: transparent; }" +
    "#owner-gate [hidden] { display: none !important; }" +
    "#owner-gate .status { min-height: 1.2em; font-size: 0.85rem; }";
  document.head.appendChild(style);

  const lsGet = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const lsSet = (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* convenience only */ } };
  const lsDel = (k) => { try { localStorage.removeItem(k); } catch (e) { /* convenience only */ } };

  let gate = null;
  let unlocked = false;

  function tokenTag(token) { return token ? token.slice(-10) : ""; }

  function unlock() {
    unlocked = true;
    root.classList.remove("owner-locked");
    if (gate) { gate.remove(); gate = null; }
  }
  function lock() {
    unlocked = false;
    root.classList.add("owner-locked");
  }

  function build() {
    if (gate) return gate;
    gate = document.createElement("div");
    gate.id = "owner-gate";
    gate.innerHTML =
      '<div class="card" role="dialog" aria-labelledby="owner-gate-title">' +
      '<h1 id="owner-gate-title">Private page</h1>' +
      '<p class="msg">Checking your account…</p>' +
      '<form class="signin" hidden>' +
      '<div style="display:grid;gap:0.5rem">' +
      '<input class="u" type="text" placeholder="username" autocomplete="username" aria-label="Username">' +
      '<input class="p" type="password" placeholder="password" autocomplete="current-password" aria-label="Password">' +
      '<button class="primary" type="submit">Sign in</button></div></form>' +
      '<button class="signout" type="button" hidden>Sign out</button>' +
      '<p class="status" role="status"></p>' +
      '<p><a href="' + hubUrl() + '" style="color:#8fa6ff">Back to the hub</a></p>' +
      "</div>";
    document.body.appendChild(gate);
    gate.querySelector(".signin").addEventListener("submit", onSignIn);
    gate.querySelector(".signout").addEventListener("click", () => {
      lsDel(TOKEN_KEY); lsDel(USERNAME_KEY); lsDel(OK_KEY);
      show("signin", "Signed out. Sign in as the owner account to continue.");
    });
    return gate;
  }
  function hubUrl() {
    // Pages sit at the site root (admin.html, ideas.html) or one folder down (the Warframe tracker).
    return /\/(warframe_build_tracker|games\/[^/]+)\//.test(location.pathname) ? "../index.html" : "index.html";
  }
  function show(mode, message, status) {
    build();
    gate.querySelector(".msg").textContent = message || "";
    gate.querySelector(".signin").hidden = mode !== "signin";
    gate.querySelector(".signout").hidden = mode !== "wrong";
    gate.querySelector(".status").textContent = status || "";
    if (mode === "signin") gate.querySelector(".u").focus();
  }

  async function whoAmI(token) {
    const res = await fetch(API_BASE + "/users/me", { headers: { Authorization: "Bearer " + token }, cache: "no-store" });
    if (res.status === 401) return { kind: "invalid" };
    if (res.status === 404) return { kind: "unsupported" };
    if (!res.ok) return { kind: "error" };
    const body = await res.json();
    return { kind: "ok", username: String(body.username || "") };
  }

  async function check(opts) {
    const background = Boolean(opts && opts.background);
    const token = lsGet(TOKEN_KEY);
    if (!token) { lock(); show("signin", "This page is only for the site owner. Sign in to continue."); return; }
    if (!background) show("none", "Checking your account…");
    let result;
    try { result = await whoAmI(token); } catch (e) { result = { kind: "network" }; }
    if (result.kind === "ok") {
      if (result.username.toLowerCase() === OWNER) {
        lsSet(OK_KEY, JSON.stringify({ tag: tokenTag(token), at: Date.now() }));
        unlock();
      } else {
        lsDel(OK_KEY); lock();
        show("wrong", "You are signed in as “" + result.username + "”. This page is only for the owner account.");
      }
    } else if (result.kind === "invalid") {
      lsDel(TOKEN_KEY); lsDel(USERNAME_KEY); lsDel(OK_KEY); lock();
      show("signin", "Your session has ended. Sign in again.");
    } else if (background && unlocked) {
      // Offline or the server is waking up: keep the page open on the strength of the recent success.
    } else if (result.kind === "unsupported") {
      lock(); show("none", "The server cannot check accounts yet. It needs the latest backend deploy (GET /users/me).");
    } else {
      lock(); show("none", "Couldn't reach the server to check your account. Reload to try again.");
    }
  }

  async function onSignIn(e) {
    e.preventDefault();
    const u = gate.querySelector(".u").value.trim();
    const p = gate.querySelector(".p").value;
    const status = gate.querySelector(".status");
    if (!u || !p) { status.textContent = "Enter a username and password."; return; }
    status.textContent = "Signing in…";
    try {
      const res = await fetch(API_BASE + "/auth/login", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: u, password: p }),
      });
      const body = await res.json();
      if (!res.ok) { status.textContent = body.detail || "Sign-in failed."; return; }
      lsSet(TOKEN_KEY, body.bearer_token);
      lsSet(USERNAME_KEY, body.username);
      gate.querySelector(".p").value = "";
      await check();
    } catch (err) {
      status.textContent = "Couldn't reach the server. Try again.";
    }
  }

  function start() {
    const token = lsGet(TOKEN_KEY);
    let cached = null;
    try { cached = JSON.parse(lsGet(OK_KEY) || "null"); } catch (e) { cached = null; }
    if (token && cached && cached.tag === tokenTag(token) && Date.now() - cached.at < OK_TTL_MS) {
      unlock();                 // recently verified: open at once, re-verify quietly
      check({ background: true });
    } else {
      check();
    }
  }

  window.OwnerGate = { check, owner: OWNER };
  if (document.body) start(); else document.addEventListener("DOMContentLoaded", start);
})();
