import pytest
from models import ConcurrencyTestResult, Account

def test_concurrency_result_create(db):
    account = Account(name="Test", email="test@test.com")
    db.add(account)
    db.commit()

    result = ConcurrencyTestResult(
        test_run_id="run_123",
        account_id=account.id,
        account_email=account.email,
        mission_id=1,
        task_type="reaction",
        result="200",
        duration_ms=1500
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    
    assert result.id is not None
    assert result.test_run_id == "run_123"
    assert result.result == "200"
    assert result.duration_ms == 1500
