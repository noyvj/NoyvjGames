"""Points the ratings API at an in-memory sqlite DB instead of the real
Neon/Postgres deployment, so this suite never touches production data.
Must set DATABASE_URL before `database`/`main` are imported anywhere.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

APP_DIR = Path(__file__).resolve().parent.parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))
