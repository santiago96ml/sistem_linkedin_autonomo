import pytest
import datetime
from models import ExecutionLock, RateLimit, Account

def test_acquire_execution_lock(db):
    from main import _acquire_execution_lock, _release_execution_lock
    r1 = _acquire_execution_lock(999, 1, db)
    assert r1 is True
    r2 = _acquire_execution_lock(999, 2, db)
    assert r2 is False
    _release_execution_lock(999, db)
    r3 = _acquire_execution_lock(999, 3, db)
    assert r3 is True
    _release_execution_lock(999, db)

def test_check_rate_limit(db):
    from main import check_rate_limit
    result = check_rate_limit(997, "comment", db)
    assert result is True

def test_safe_increment(db):
    from main import _safe_increment_action_count
    acc = Account(name="Test", email="safe_inc_test@test.com", status="active")
    db.add(acc)
    db.commit()
    result = _safe_increment_action_count(acc.id, db)
    assert result is True
