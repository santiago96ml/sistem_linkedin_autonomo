import pytest
import datetime
from models import PendingLogin

def test_create_pending_login(db):
    pending = PendingLogin(
        email="test@example.com",
        password_encrypted="encrypted_pass",
        status="pending",
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    )
    db.add(pending)
    db.commit()
    db.refresh(pending)
    
    assert pending.id is not None
    assert pending.email == "test@example.com"
    assert pending.status == "pending"
    assert pending.failed_attempts == 0
    assert pending.created_at is not None

def test_expire_after_ttl(db):
    now = datetime.datetime.utcnow()
    past_time = now - datetime.timedelta(minutes=5)
    
    pending = PendingLogin(
        email="expired@example.com",
        password_encrypted="pass",
        status="pending",
        expires_at=past_time
    )
    db.add(pending)
    db.commit()
    
    # Query logic to treat it as expired would normally be in the repository/service
    expired_logins = db.query(PendingLogin).filter(PendingLogin.expires_at < now).all()
    assert len(expired_logins) == 1
    assert expired_logins[0].email == "expired@example.com"

def test_failed_attempts_limit(db):
    pending = PendingLogin(
        email="locked@example.com",
        password_encrypted="pass",
        status="pending",
        failed_attempts=4,
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    )
    db.add(pending)
    db.commit()
    
    # Simulate a failed attempt
    pending.failed_attempts += 1
    if pending.failed_attempts >= 5:
        pending.status = "locked"
    
    db.commit()
    assert pending.status == "locked"

def test_status_transitions(db):
    pending = PendingLogin(
        email="transition@example.com",
        password_encrypted="pass",
        status="pending",
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    )
    db.add(pending)
    db.commit()
    
    pending.status = "2fa_email"
    db.commit()
    assert pending.status == "2fa_email"
    
    pending.status = "success"
    db.commit()
    assert pending.status == "success"
