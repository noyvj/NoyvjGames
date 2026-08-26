import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

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
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def patch_schema():
    """One-off, idempotent schema patch for the pre-existing `ratings` table
    (there's no Alembic/migration tooling in this project). Safe to call on
    every startup: `ADD COLUMN IF NOT EXISTS` and `DROP NOT NULL` are both
    no-ops once already applied. Postgres-only — Base.metadata.create_all
    already builds a fresh sqlite table (used by tests) with the current,
    correct column definitions, so no patching is needed there.
    """
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE ratings ADD COLUMN IF NOT EXISTS response VARCHAR"))
        conn.execute(text("ALTER TABLE ratings ALTER COLUMN stars DROP NOT NULL"))
        # ACCOUNTS-AND-FEEDBACK-DESIGN.md: saves predates users, so the
        # link between them is a patched-in column, not a fresh table.
        conn.execute(text("ALTER TABLE saves ADD COLUMN IF NOT EXISTS user_id VARCHAR REFERENCES users(id)"))
