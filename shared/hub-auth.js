/*
 * Shared bearer-token helpers.
 *
 * Single source of truth for the localStorage key and header-building
 * logic that both the hub's sign-in UI (script.js) and every game's save
 * widget (shared/save-widget.js) need to talk to the same account system —
 * previously each defined its own copy of both, hardcoding the same
 * "hub_bearer_token" string independently, so a future key rename in one
 * file without the other would have silently broken auth-gated requests.
 *
 * Loaded as a plain global script (not a module, no build step) — same
 * "one shared file, dropped in unchanged" pattern as save-widget.js itself.
 * Must be included before script.js (hub's index.html) or save-widget.js
 * (every game's index.html) so these globals already exist when either
 * runs.
 */

// `var` (not `const`) so including this file twice is harmless instead of a SyntaxError that
// would stop the second copy and, in some browsers, everything that follows it.
var HUB_AUTH_TOKEN_KEY = "hub_bearer_token";

// A browser with storage blocked throws from localStorage.getItem; treat that as signed out.
function hubGetBearerToken() {
  try { return localStorage.getItem(HUB_AUTH_TOKEN_KEY); } catch (err) { return null; }
}

function hubAuthHeaders() {
  const token = hubGetBearerToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
