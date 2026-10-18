"""App assembly for the CodingIsANoyvj ratings API (FastAPI Cloud entry point: `app` in this file).

This file creates the app, adds the middleware, includes one router per feature file (the order below is
the original route registration order, which decides path matching) and re-exports the names the old
single-file main.py exposed (see app/CLAUDE.md, "Compatibility names"). Routes do not live here.
"""

import logging
import os
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import get_current_user, get_current_user_optional, require_admin
from database import get_db, init_schema, retry_schema_until_ready
import ghosts
from rate_limits import _client_key
from routes_core import router as routes_core_router
from routes_answer_reports import router as routes_answer_reports_router
from routes_accounts import router as routes_accounts_router
from routes_account_saves import router as routes_account_saves_router
from routes_owner import router as routes_owner_router
from routes_me import router as routes_me_router
from routes_feedback import router as routes_feedback_router
from routes_email import router as routes_email_router
from routes_admin_users import router as routes_admin_users_router
from routes_stats import router as routes_stats_router
from routes_leaderboards import router as routes_leaderboards_router
from routes_scores import router as routes_scores_router
from routes_market_pools import router as routes_market_pools_router
from routes_account_data import router as routes_account_data_router
from routes_admin_timeseries import router as routes_admin_timeseries_router
from routes_votes import router as routes_votes_router
from routes_bug_reports import router as routes_bug_reports_router
from routes_profiles import router as routes_profiles_router


logger = logging.getLogger(__name__)

if not init_schema():
    threading.Thread(target=retry_schema_until_ready, daemon=True).start()

app = FastAPI(title="CodingIsANoyvj ratings API")

DEFAULT_ORIGINS = "https://noyvj.github.io,http://localhost:8073"

allowed_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",") if o.strip()]

# Largest request body any route accepts (the biggest legitimate payload is a
# game save; the owner-note cap is 1 MB). Checked from Content-Length before
# the body is read, so an oversized POST/PUT is refused without being parsed.
# Added BEFORE the CORS middleware so CORS wraps it and the 413 is readable
# from the browser.
MAX_BODY_BYTES = 5_000_000


class BodySizeLimitMiddleware:
    def __init__(self, app, max_bytes: int = MAX_BODY_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            for name, value in scope["headers"]:
                if name == b"content-length":
                    try:
                        too_big = int(value) > self.max_bytes
                    except ValueError:
                        too_big = True
                    if too_big:
                        body = b'{"detail":"Request body too large"}'
                        await send({"type": "http.response.start", "status": 413,
                                    "headers": [(b"content-type", b"application/json"),
                                                (b"content-length", str(len(body)).encode())]})
                        await send({"type": "http.response.body", "body": body})
                        return
                    break
        await self.app(scope, receive, send)


app.add_middleware(BodySizeLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)


app.include_router(routes_core_router)
app.include_router(routes_answer_reports_router)
app.include_router(routes_accounts_router)
app.include_router(routes_account_saves_router)
app.include_router(routes_owner_router)
app.include_router(routes_me_router)
app.include_router(routes_feedback_router)
app.include_router(routes_email_router)
app.include_router(routes_admin_users_router)
app.include_router(routes_stats_router)
app.include_router(routes_leaderboards_router)
app.include_router(routes_scores_router)
app.include_router(routes_market_pools_router)
app.include_router(routes_account_data_router)
app.include_router(routes_admin_timeseries_router)
app.include_router(routes_votes_router)
app.include_router(routes_bug_reports_router)


# --- R-33: anonymous ghost settlements (opt-in publish, one random peer; see ghosts.py) ---
app.include_router(ghosts.make_router(
    get_db=get_db, get_current_user=get_current_user, get_current_user_optional=get_current_user_optional,
    require_admin=require_admin, client_key=_client_key,
))


app.include_router(routes_profiles_router)


# --- Compatibility names. The old single-file main.py exposed all of these, and tests and scripts use
# `import main` / `from main import ...`. Where a test replaces a name (monkeypatch) it must patch it in the
# module that uses it (see app/CLAUDE.md), not here. Do not add new code below this line.
import hashlib  # noqa: F401
import json  # noqa: F401
import re  # noqa: F401
import secrets  # noqa: F401
import time  # noqa: F401
from datetime import datetime  # noqa: F401
from typing import List, Optional, Union  # noqa: F401
from fastapi import Depends, Header, HTTPException, Request, Response  # noqa: F401
from pydantic import BaseModel, ConfigDict, Field, model_validator, StrictBool, StrictFloat, StrictInt  # noqa: F401
from sqlalchemy import func, or_, text  # noqa: F401
from sqlalchemy.exc import IntegrityError  # noqa: F401
from sqlalchemy.orm import Session  # noqa: F401
import account_data  # noqa: F401
import boards  # noqa: F401
import bug_reports  # noqa: F401
import leaderboards  # noqa: F401
import market  # noqa: F401
import pools  # noqa: F401
import profiles  # noqa: F401
import snapshots  # noqa: F401
import stats  # noqa: F401
from auth import (  # noqa: F401
    _normalize_username, _test_user_ids, ADMIN_TOKEN_ENV_VARS, owner_signup_allowed, OWNER_SIGNUP_ENV_VAR,
    OWNER_USERNAME,
)
from constants import ID_MAX_LENGTH, TEXT_MAX_LENGTH  # noqa: F401
from database import engine  # noqa: F401
from models import (  # noqa: F401
    AnswerReport, AuthSession, BugReport, Feedback, LeaderboardEntry, OwnerNote, PageView, PoolDay, Rating,
    Save, SaveSnapshot, ScoreEntry, ScoreProfile, User, UserProfile,
)
from passwords import (  # noqa: F401
    _hash_password, _verify_password, PASSWORD_SALT_BYTES, PBKDF2_ALGORITHM, PBKDF2_ITERATIONS,
)
from rate_limits import (  # noqa: F401
    _throttle, ANSWER_REPORT_LIMITER, BUG_REPORT_LIMITER, LOGIN_FAILURE_LIMITER, LOGIN_IP_FAILURE_LIMITER,
    PAGEVIEW_LIMITER, PROFILE_LOOKUP_LIMITER, PROFILE_UPDATE_LIMITER, RATING_LIMITER, reset_write_limiters,
    SAVE_CODE_MISS_LIMITER, SAVE_CREATE_LIMITER, SIGNUP_LIMITER, SNAPSHOT_LIMITER, WRITE_LIMITERS,
)
from routes_account_data import delete_my_account, DeleteAccountIn, export_my_data  # noqa: F401
from routes_account_saves import (  # noqa: F401
    _ensure_slots, _own_snapshot, _snapshot_out, _taken_slots, claim_save, create_snapshot, delete_snapshot,
    get_snapshot, list_my_saves, list_snapshots, put_slot_save, SlotSaveIn, SnapshotIn,
)
from routes_accounts import (  # noqa: F401
    _start_session, _username_exists, AI_TEST_USERNAME_PREFIX, AuthIn, AuthOut, login, SESSION_TOKEN_BYTES,
    signup, USERNAME_MAX_LENGTH, USERNAME_PATTERN,
)
from routes_admin_timeseries import admin_timeseries  # noqa: F401
from routes_admin_users import admin_flag_user, admin_list_users, AdminUserOut, UserTestFlagIn  # noqa: F401
from routes_answer_reports import (  # noqa: F401
    AnswerReportIn, AnswerReportOut, create_answer_report, DEFAULT_ANSWER_REPORT_GAME_ID, list_answer_reports,
    mark_answer_report_fixed, ReportFixedIn, ReportResolveIn, resolve_answer_report,
)
from routes_bug_reports import admin_list_bug_reports, admin_patch_bug_report, create_bug_report  # noqa: F401
from routes_core import (  # noqa: F401
    create_rating, create_save, get_save, health, list_ratings, RatingIn, RatingOut, ratings_summary,
    RATINGS_SUMMARY_CACHE_CONTROL, update_save,
)
from routes_email import _EMAIL_PATTERN, EMAIL_MAX_LENGTH, EmailIn, get_my_email, put_my_email  # noqa: F401
from routes_feedback import (  # noqa: F401
    _admin_feedback_out, _admin_rating_out, _check_feedback_rate_limit, _feedback_submission_lock,
    _feedback_submission_log, admin_hide_feedback, admin_hide_rating, admin_list_feedback, admin_list_ratings,
    admin_stats, AdminFeedbackOut, AdminRatingOut, AdminStatsOut, create_feedback,
    FEEDBACK_RATE_LIMIT_PER_HOUR, FeedbackIn, FeedbackOut, FeedbackPublicOut, list_feedback,
)
from routes_leaderboards import (  # noqa: F401
    _board_or_404, _board_order, _rank_of, get_leaderboard, LeaderboardSubmit, remove_leaderboard_entry,
    submit_leaderboard_score,
)
from routes_market_pools import (  # noqa: F401
    _pool_or_404, _pool_summary, add_to_pool, get_pool, market_prices, PoolContribution, stats_pageview,
)
from routes_me import (  # noqa: F401
    _stored_settings, _validate_settings, get_me, get_my_settings, put_my_settings, SETTINGS_TEXT_SCALE_MAX,
    SETTINGS_TEXT_SCALE_MIN,
)
from routes_owner import (  # noqa: F401
    _owner_note_key, get_owner_note, OWNER_NOTE_KEY, OWNER_NOTE_MAX_BYTES, put_owner_note, require_owner,
)
from routes_profiles import (  # noqa: F401
    backfill_my_profile, get_my_profile, get_public_profile, PROFILE_NOT_PUBLIC, put_my_profile,
)
from routes_scores import (  # noqa: F401
    _admin_score_out, _default_window, _score_board_or_404, _score_rank, _show_username, _visible_scores,
    _write_scores, admin_hide_score, admin_list_scores, AdminScoreOut, get_leaderboard_privacy,
    get_score_board, LeaderboardPrivacyIn, list_my_scores, list_score_boards, put_leaderboard_privacy,
    remove_all_my_scores, remove_my_scores, ScoreSubmit, submit_score,
)
from routes_stats import (  # noqa: F401
    _game_saves, _require_known_game, stats_achievements, STATS_CACHE_CONTROL, stats_game,
    stats_game_percentile, stats_games,
)
from routes_votes import (  # noqa: F401
    _vote_voter, admin_whats_new_votes, delete_whats_new_vote, HelpfulVoteIn, put_whats_new_vote,
    VOTE_LIMITER,
)
from schemas_admin import HiddenFlagIn  # noqa: F401
from schemas_saves import (  # noqa: F401
    _generate_save_code, SAVE_CODE_ALPHABET, SAVE_CODE_GENERATION_ATTEMPTS, SAVE_CODE_GROUP_LEN,
    SAVE_CODE_GROUPS, SAVE_SLOTS_PER_GAME, SaveIn, SaveOut, SaveUpdate, SLOT_NAME_MAX_LENGTH,
)
from throttle import FailureLimiter  # noqa: F401
