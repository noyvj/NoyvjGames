"""The in-process per-address / per-account brakes (FailureLimiter instances) and the helpers that use them. Layer 1."""

from fastapi import HTTPException, Request

from throttle import FailureLimiter


# Online-guessing brakes. A wrong password counts against BOTH the username
# (so a distributed guesser is stopped) and the client address (so one machine
# cannot try many usernames); a wrong save code counts against the address.
# Successes clear the counters. See throttle.py.
LOGIN_FAILURE_LIMITER = FailureLimiter(max_failures=8, window_seconds=15 * 60)
LOGIN_IP_FAILURE_LIMITER = FailureLimiter(max_failures=40, window_seconds=15 * 60)
SAVE_CODE_MISS_LIMITER = FailureLimiter(max_failures=40, window_seconds=15 * 60)


# Per-address brakes on the unauthenticated write routes, so a script cannot
# fill the database. Every call counts (not just failures). Generous: a real
# player is nowhere near these. In-process like the others (see throttle.py).
SIGNUP_LIMITER = FailureLimiter(max_failures=20, window_seconds=3600)
RATING_LIMITER = FailureLimiter(max_failures=60, window_seconds=3600)
SAVE_CREATE_LIMITER = FailureLimiter(max_failures=60, window_seconds=3600)
ANSWER_REPORT_LIMITER = FailureLimiter(max_failures=120, window_seconds=3600)
PAGEVIEW_LIMITER = FailureLimiter(max_failures=120, window_seconds=3600)


# Z-10: save snapshots, per ACCOUNT (the key is the user id). The widget takes one before a Load, a
# New Game or a restore and one per 10 minutes of autosave, so 40 an hour is far above real play.
SNAPSHOT_LIMITER = FailureLimiter(max_failures=40, window_seconds=3600)


# Z-17: "Report a problem" reports, per address (a real player sends a handful at most).
BUG_REPORT_LIMITER = FailureLimiter(max_failures=15, window_seconds=3600)


# Z-7: profile progress posts, per ACCOUNT (the key is the user id). shared/profile.js posts at most
# about once every five minutes per game, so 90 an hour is far above real play.
PROFILE_UPDATE_LIMITER = FailureLimiter(max_failures=90, window_seconds=3600)


# Y-1: public profile lookups, per address, so usernames cannot be walked quickly.
PROFILE_LOOKUP_LIMITER = FailureLimiter(max_failures=300, window_seconds=3600)
WRITE_LIMITERS = (
    SIGNUP_LIMITER, RATING_LIMITER, SAVE_CREATE_LIMITER, ANSWER_REPORT_LIMITER, PAGEVIEW_LIMITER, SNAPSHOT_LIMITER,
    BUG_REPORT_LIMITER, PROFILE_UPDATE_LIMITER, PROFILE_LOOKUP_LIMITER,
)


def _client_key(request: Request) -> str:
    """The caller's address: the first X-Forwarded-For entry when behind the
    host's proxy, else the socket peer."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded.strip():
        return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else "unknown"


def _throttle(limiter: FailureLimiter, request: Request, detail: str = "Too many requests, try again later") -> None:
    key = _client_key(request)
    if limiter.blocked(key):
        raise HTTPException(status_code=429, detail=detail)
    limiter.record_failure(key)


def reset_write_limiters() -> None:
    for limiter in WRITE_LIMITERS:
        limiter.reset()
