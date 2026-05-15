import pytest
import datetime
import time
from models import Account, RateLimit, ExecutionLock
from orchestrator import BrowserPool


def test_browser_pool_get_metrics(db):
    pool = BrowserPool(max_instances=5, instance_ttl=600)
    metrics = pool.get_metrics()
    assert metrics["active_instances"] == 0
    assert metrics["max_instances"] == 5
    assert metrics["available_slots"] == 5
    assert metrics["ttl_seconds"] == 600


def test_check_rate_limit_blocked(db):
    from main import check_rate_limit
    acc = Account(name="Test", email="rate_blocked@test.com", status="active", is_warming_up=0)
    db.add(acc)
    db.commit()
    now = datetime.datetime.utcnow()
    rl = RateLimit(account_id=acc.id, action_type="comment", action_count=50, window_start=now)
    db.add(rl)
    db.commit()
    result = check_rate_limit(acc.id, "comment", db)
    assert result is False


def test_check_rate_limit_warmup_blocked(db):
    from main import check_rate_limit
    acc = Account(name="Test2", email="rate_warmup_blocked@test.com", status="active", is_warming_up=1)
    db.add(acc)
    db.commit()
    now = datetime.datetime.utcnow()
    rl = RateLimit(account_id=acc.id, action_type="comment", action_count=10, window_start=now)
    db.add(rl)
    db.commit()
    result = check_rate_limit(acc.id, "comment", db)
    assert result is False


def test_safe_increment_warmup_blocked(db):
    from main import _safe_increment_action_count
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    acc = Account(
        name="Test3", email="safe_inc_blocked@test.com", status="active",
        is_warming_up=1, daily_action_count=10, last_action_date=today
    )
    db.add(acc)
    db.commit()
    result = _safe_increment_action_count(acc.id, db)
    assert result is False


def test_acquire_execution_lock_ttl_expiry(db):
    from main import _acquire_execution_lock, _release_execution_lock
    past = datetime.datetime.utcnow() - datetime.timedelta(seconds=10)
    lock = ExecutionLock(account_id=999, mission_id=1, acquired_at=past, ttl_seconds=1)
    db.add(lock)
    db.commit()
    time.sleep(1)
    result = _acquire_execution_lock(999, 2, db)
    assert result is True
    _release_execution_lock(999, db)
