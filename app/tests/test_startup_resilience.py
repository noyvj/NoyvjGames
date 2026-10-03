"""The API must boot even when the database is unreachable (as when the
FastAPI Cloud container could not resolve the Neon hostname), instead of
crashing at import and failing the deployment's health check."""

import pytest
from sqlalchemy.exc import OperationalError, ProgrammingError

import database


def _unreachable(*args, **kwargs):
    raise OperationalError("SELECT 1", {}, Exception("could not translate host name"))


def test_init_schema_succeeds_when_database_is_reachable():
    assert database.init_schema() is True


def test_init_schema_returns_false_instead_of_raising_when_unreachable(monkeypatch):
    monkeypatch.setattr(database.Base.metadata, "create_all", _unreachable)
    assert database.init_schema() is False


def test_init_schema_still_raises_on_non_connection_errors(monkeypatch):
    def broken(*args, **kwargs):
        raise ProgrammingError("ALTER TABLE x", {}, Exception("permission denied"))

    monkeypatch.setattr(database.Base.metadata, "create_all", broken)
    with pytest.raises(ProgrammingError):
        database.init_schema()


def test_retry_loop_backs_off_then_stops_once_ready(monkeypatch):
    results = iter([False, False, False, True])
    monkeypatch.setattr(database, "init_schema", lambda: next(results))
    sleeps = []
    database.retry_schema_until_ready(first_delay=5.0, max_delay=12.0, sleep=sleeps.append)
    assert sleeps == [5.0, 10.0, 12.0]
