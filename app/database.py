import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]
if DATABASE_URL.startswith("postgres://"):
    # Neon/Heroku-style URLs use the "postgres://" scheme; SQLAlchemy needs "postgresql://".
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    # Test-only path (see tests/conftest.py): a plain sqlite engine hands
    # out a fresh, separate in-memory DB per connection, which would make
    # the table `create_all()` just built disappear before the first
    # request. StaticPool keeps every checkout on the one connection.
    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
else:
    # pool_pre_ping is the actual fix for "save errors, then works a few
    # clicks later": Neon's serverless Postgres suspends its compute after
    # a few minutes of inactivity, which silently kills any connection
    # SQLAlchemy's pool was holding onto. Without pre_ping, the *first*
    # request after that idle window hands out the now-dead connection,
    # the query on it raises immediately (psycopg2.OperationalError —
    # "server closed the connection unexpectedly"), and that surfaces to
    # the caller as a bare 500 with no retry anywhere. pool_pre_ping=True
    # makes SQLAlchemy issue a cheap `SELECT 1` before handing out a pooled
    # connection on every checkout, so a dead one gets silently replaced
    # instead of used — the request that would have failed instead pays a
    # small one-time reconnect cost and just succeeds. Confirmed this
    # failure shape live against production: the first request after idle
    # returned a 500 in under a second, then every next request succeeded
    # (each slower than steady-state, consistent with Neon's own compute
    # waking back up) — exactly what a user clicking Save repeatedly and
    # having it "eventually work" would experience.
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def patch_schema():
    """One-off, idempotent schema patch for two pre-existing tables that
    predate columns added by later features (there's no Alembic/migration
    tooling in this project): `ratings` (the `response`/nullable-`stars`
    columns added for per-game feedback prompts) and `saves` (the `user_id`
    column added for the accounts/save-claim feature). Safe to call on every
    startup: `ADD COLUMN IF NOT EXISTS` and `DROP NOT NULL` are both no-ops
    once already applied. Postgres-only — Base.metadata.create_all already
    builds fresh sqlite tables (used by tests) with the current, correct
    column definitions, so no patching is needed there.
    """
    if engine.dialect.name != "postgresql":
        return
    # Each statement is logged individually (not just wrapped in one
    # try/except around the whole block) so that if one fails partway
    # through — e.g. a permissions issue — the startup crash's log carries
    # which specific statement failed rather than leaving that to be
    # reconstructed from a bare stack trace during triage. The exception
    # still propagates after logging: a failed schema patch should still
    # crash startup loudly, not be swallowed.
    statements = [
        "ALTER TABLE ratings ADD COLUMN IF NOT EXISTS response VARCHAR",
        "ALTER TABLE ratings ALTER COLUMN stars DROP NOT NULL",
        # ACCOUNTS-AND-FEEDBACK-DESIGN.md: saves predates users, so the
        # link between them is a patched-in column, not a fresh table.
        "ALTER TABLE saves ADD COLUMN IF NOT EXISTS user_id VARCHAR REFERENCES users(id)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            try:
                conn.execute(text(statement))
            except Exception:
                logger.exception("patch_schema() failed on statement: %s", statement)
                raise
