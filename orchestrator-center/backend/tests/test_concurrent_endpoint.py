import pytest
from fastapi.testclient import TestClient
from main import app
from database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime
import asyncio

# Need an async TestClient or httpx.AsyncClient for full async tests, 
# but FastAPI's TestClient uses anyio and sync syntax for testing.
# We will just test the basic logic.

from sqlalchemy.pool import StaticPool

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

import models

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    old_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    yield
    if old_override is not None:
        app.dependency_overrides[get_db] = old_override
    else:
        app.dependency_overrides.pop(get_db, None)

def test_invalid_accounts():
    response = client.post("/test/concurrent", json={
        "account_ids": [999], 
        "task_template": {"type": "reaction"}, 
        "concurrency_level": 1
    })
    assert response.status_code == 404

def test_concurrent_launch():
    # Insert dummy accounts
    db = TestingSessionLocal()
    from models import Account
    acc1 = Account(name="Acc1", email="acc1@test.com", status="active", storage_state={})
    acc2 = Account(name="Acc2", email="acc2@test.com", status="active", storage_state={})
    db.add(acc1)
    db.add(acc2)
    db.commit()
    db.refresh(acc1)
    db.refresh(acc2)
    
    response = client.post("/test/concurrent", json={
        "account_ids": [acc1.id, acc2.id],
        "task_template": {"type": "reaction", "payload": {"url": "http://linkedin.com/post", "reaction_type": "LIKE"}},
        "concurrency_level": 2
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "test_run_id" in data
    assert len(data["results"]) == 2
    
    # check ConcurrencyTestResult
    from models import ConcurrencyTestResult
    results = db.query(ConcurrencyTestResult).filter(ConcurrencyTestResult.test_run_id == data["test_run_id"]).all()
    assert len(results) == 2
    db.close()
