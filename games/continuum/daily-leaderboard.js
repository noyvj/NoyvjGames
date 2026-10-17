// K-10: opt-in leaderboard for the daily challenge (shared/leaderboard.js).
// K-10: opt-in "you vs everyone" for the daily challenge (backend board continuum/daily_challenge, UTC day).
if (window.NoyvjLeaderboard) {
  NoyvjLeaderboard.addBoard({ game: "continuum", board: "daily_challenge", title: "Today's challenge: everyone", unit: "points",
                              order: "desc", windows: ["daily"], mount: "#challenge-leaderboard-mount" });
}
