import pytest
from fastapi.testclient import TestClient
from main import app
from database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import models

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

models.Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

client = TestClient(app)


@pytest.fixture(autouse=True)
def _setup_db():
    """Ensure clean DB + correct dependency override before each test."""
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield


def test_wizard_start_validation():
    response = client.post("/wizard/start", json={})
    assert response.status_code == 422 # missing required fields

def test_wizard_flow_mocked(monkeypatch):
    import main
    monkeypatch.setattr(main, "SessionLocal", TestingSessionLocal)
    
    # Mock GuidedLogin start
    class MockGuidedLogin:
        def __init__(self, email, password, proxy):
            self.email = email
            self.storage_state = {"mock": "state"}
        async def start(self):
            return "needs_2fa_email:m***@gmail.com"
        async def submit_code(self, code):
            if code == "123456":
                return self.storage_state
            return None

    import orchestrator
    monkeypatch.setattr(orchestrator, "GuidedLogin", MockGuidedLogin)
    
    # 1. Start wizard
    res_start = client.post("/wizard/start", json={"email": "test@wizard.com", "password": "pass"})
    assert res_start.status_code == 200
    data = res_start.json()
    assert "session_id" in data
    session_id = data["session_id"]
    
    # Wait a bit since start might run in background, but in tests BackgroundTasks run sync or async after return.
    # We will test the status directly. Wait, if it runs in background, TestClient waits for it?
    # TestClient in FastAPI runs BackgroundTasks after the response is sent, but in testing it actually runs them synchronously after!
    
    # 2. Check status
    res_status = client.get(f"/wizard/status/{session_id}")
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "2fa_email"
    assert res_status.json()["two_fa_destination"] == "m***@gmail.com"
    
    # 3. Verify
    res_verify = client.post("/wizard/verify", json={"session_id": session_id, "code": "123456"})
    assert res_verify.status_code == 200
    assert res_verify.json()["status"] == "success"
    assert "account_id" in res_verify.json()
