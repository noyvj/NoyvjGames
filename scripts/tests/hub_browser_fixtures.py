"""Not a conftest (shared/tests has one, and two modules of that name collide when both folders run
together): test files here import the fixtures from this module.

Browser fixtures for the hub page tests: reuses the Playwright harness that shared/tests already
has (a fake origin served from disk, the live backend answered by the test, every other host
refused), so no test here can reach the network."""

import importlib.util
from pathlib import Path

_path = Path(__file__).resolve().parents[2] / "shared" / "tests" / "conftest.py"
_spec = importlib.util.spec_from_file_location("shared_tests_conftest", _path)
_shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)

chromium = _shared.chromium
harness = _shared.harness
