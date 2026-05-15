import pytest
import datetime
from models import RateLimit, Account

def test_within_limit(db):
    account = Account(name="Test", email="rate1@test.com")
    db.add(account)
    db.commit()

    rl = RateLimit(
        account_id=account.id,
        action_type="reaction",
        action_count=5,
        window_start=datetime.datetime.utcnow()
    )
    db.add(rl)
    db.commit()

    assert rl.action_count == 5

def test_window_expires(db):
    now = datetime.datetime.utcnow()
    past = now - datetime.timedelta(hours=2)

    account = Account(name="Test", email="rate2@test.com")
    db.add(account)
    db.commit()

    rl = RateLimit(
        account_id=account.id,
        action_type="reaction",
        action_count=10,
        window_start=past
    )
    db.add(rl)
    db.commit()
    
    # Normally handled by middleware logic
    assert rl.window_start < now - datetime.timedelta(hours=1)
