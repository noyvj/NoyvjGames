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

const HUB_AUTH_TOKEN_KEY = "hub_bearer_token";

function hubGetBearerToken() {
  return localStorage.getItem(HUB_AUTH_TOKEN_KEY);
}

function hubAuthHeaders() {
  const token = hubGetBearerToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
