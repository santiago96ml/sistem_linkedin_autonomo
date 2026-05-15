import pytest
from models import ExecutionLock, Account
from sqlalchemy.exc import IntegrityError

def test_lock_account(db):
    account = Account(name="Test", email="lock1@test.com")
    db.add(account)
    db.commit()

    lock = ExecutionLock(account_id=account.id, mission_id=1)
    db.add(lock)
    db.commit()
    db.refresh(lock)

    assert lock.id is not None
    assert lock.account_id == account.id
    assert lock.ttl_seconds == 600

def test_double_lock_fails(db):
    account = Account(name="Test", email="lock2@test.com")
    db.add(account)
    db.commit()

    lock1 = ExecutionLock(account_id=account.id, mission_id=1)
    db.add(lock1)
    db.commit()

    lock2 = ExecutionLock(account_id=account.id, mission_id=2)
    db.add(lock2)
    with pytest.raises(IntegrityError):
        db.commit()

def test_release_lock(db):
    account = Account(name="Test", email="lock3@test.com")
    db.add(account)
    db.commit()

    lock = ExecutionLock(account_id=account.id, mission_id=1)
    db.add(lock)
    db.commit()

    db.delete(lock)
    db.commit()
    
    assert db.query(ExecutionLock).filter_by(account_id=account.id).first() is None
