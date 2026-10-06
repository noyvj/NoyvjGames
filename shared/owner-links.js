/*
 * "Owner only" dropdown in the hub nav: links to the unlisted owner pages (admin, the ideas answer
 * sheet, the Warframe tracker), shown only while signed in as the owner account "noyvj".
 *
 * The links are deliberately NOT in index.html: this script builds the dropdown only after the
 * account checks out, so they are not in the page for anyone else (the pages themselves are also
 * behind shared/owner-gate.js, and the Warframe tracker stays off every public page).
 *
 * Check: GET /users/me names the account. If the backend cannot answer (an older deploy without
 * that route, or offline) the stored username decides, because the links only lead to pages that
 * check the account again themselves.
 *
 * script.js calls NoyvjOwnerLinks.refresh() whenever the sign-in state changes.
 */
(function () {
  "use strict";
  const OWNER = "noyvj";
  const API_BASE = "https://noyvjgames.fastapicloud.dev";
  const TOKEN_KEY = "hub_bearer_token";
  const USERNAME_KEY = "hub_account_username";
  const LINKS = [
    ["Admin", "admin.html"],
    ["Ideas answer sheet", "ideas.html"],
    ["Warframe tracker", "warframe_build_tracker/index.html"],
  ];

  const lsGet = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  let pending = null;

  async function isOwner() {
    const token = lsGet(TOKEN_KEY);
    if (!token) return false;
    const stored = (lsGet(USERNAME_KEY) || "").toLowerCase() === OWNER;
    try {
      const res = await fetch(API_BASE + "/users/me", { headers: { Authorization: "Bearer " + token }, cache: "no-store" });
      if (res.ok) return String((await res.json()).username || "").toLowerCase() === OWNER;
      if (res.status === 401) return false;   // the session has ended or belongs to nobody
      return stored;                           // 404 (older backend) or another server error
    } catch (e) {
      return stored;                           // offline
    }
  }

  function render(show) {
    const nav = document.querySelector(".hub-nav");
    if (!nav) return;
    let box = document.getElementById("owner-nav");
    if (!show) { if (box) box.remove(); return; }
    if (box) return;
    box = document.createElement("details");
    box.id = "owner-nav";
    box.className = "hub-nav-owner";
    const summary = document.createElement("summary");
    summary.textContent = "Owner only";
    const menu = document.createElement("div");
    menu.className = "hub-nav-owner-menu";
    for (const [label, href] of LINKS) {
      const a = document.createElement("a");
      a.href = href;
      a.textContent = label;
      menu.appendChild(a);
    }
    box.append(summary, menu);
    nav.appendChild(box);
    // Close on an outside click or Escape, like the other dropdowns on the site.
    document.addEventListener("click", (e) => { if (box.open && !box.contains(e.target)) box.open = false; });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && box.open) { box.open = false; summary.focus(); } });
  }

  function refresh() {
    if (pending) return pending;
    pending = isOwner().then(render).finally(() => { pending = null; });
    return pending;
  }

  window.NoyvjOwnerLinks = { refresh };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", refresh);
  else refresh();
})();
