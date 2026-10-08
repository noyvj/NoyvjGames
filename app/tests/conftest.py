"""Points the ratings API at an in-memory sqlite DB instead of the real
Neon/Postgres deployment, so this suite never touches production data.
Must set DATABASE_URL before `database`/`main` are imported anywhere.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
# U8: admin endpoints need a token; tests use these two fixed values.
os.environ["ADMIN_TOKEN"] = "test-admin-token"
os.environ["AI_ADMIN_TOKEN"] = "test-ai-token"
# FY-16: the name "noyvj" is reserved at signup unless this is set. Most of the suite makes the owner
# account by signing it up, so it is on for the suite; test_owner_signup_reserved.py switches it off
# per test to prove the default.
os.environ["OWNER_SIGNUP_ALLOWED"] = "1"

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


ADMIN_HEADERS = {"X-Admin-Token": "test-admin-token"}


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_write_limiters():
    """The per-address write brakes are module-global; every test starts with them empty."""
    import main

    main.reset_write_limiters()
    yield
