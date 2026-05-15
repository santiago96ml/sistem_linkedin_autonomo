"""Tests for the cookie import/validate API endpoints."""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import models
import json

# --- In-memory SQLite for tests ---
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
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
    """Ensure clean DB + correct dependency override before each test.

    This must be autouse because other test files also override
    app.dependency_overrides[get_db] at module level, and the last
    import wins. By resetting it before every test we stay isolated.
    """
    # Clean DB
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    # Ensure our override is active
    app.dependency_overrides[get_db] = override_get_db
    yield


# ==============================================================================
# Sample cookies (mimicking Chrome extension export format)
# ==============================================================================

SAMPLE_COOKIES = [
    {
        "domain": ".www.linkedin.com",
        "expirationDate": 1810306995.875365,
        "hostOnly": False,
        "httpOnly": True,
        "name": "li_at",
        "path": "/",
        "sameSite": "no_restriction",
        "secure": True,
        "session": False,
        "value": "AQED_mock_value_for_testing",
    },
    {
        "domain": ".www.linkedin.com",
        "expirationDate": 1810306995.875519,
        "hostOnly": False,
        "httpOnly": False,
        "name": "JSESSIONID",
        "path": "/",
        "sameSite": "no_restriction",
        "secure": True,
        "session": False,
        "value": '"ajax:mock_12345"',
    },
    {
        "domain": ".linkedin.com",
        "expirationDate": 1810392523.431173,
        "hostOnly": False,
        "httpOnly": False,
        "name": "bcookie",
        "path": "/",
        "sameSite": "no_restriction",
        "secure": True,
        "session": False,
        "value": '"v=2&mock_value"',
    },
]


# ==============================================================================
# Tests: POST /accounts/cookies/validate
# ==============================================================================


class TestValidateEndpoint:
    """Tests for POST /accounts/cookies/validate."""

    @patch("cookie_importer.httpx.Client")
    def test_validate_valid_cookies(self, mock_client_class):
        """Valid cookies return valid=True."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        # Mock a successful LinkedIn response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = (
            '<script>{"miniProfile":{"firstName":"Test","lastName":"User"}}</script>'
        )
        mock_client.get.return_value = mock_response

        response = client.post(
            "/accounts/cookies/validate",
            json={"cookies": SAMPLE_COOKIES},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["name"] == "Test User"

    @patch("cookie_importer.httpx.Client")
    def test_validate_expired_cookies(self, mock_client_class):
        """Expired cookies return valid=False."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        # Mock a redirect to login
        mock_response = MagicMock()
        mock_response.status_code = 302
        mock_response.headers = {"location": "https://www.linkedin.com/login"}
        mock_client.get.return_value = mock_response

        response = client.post(
            "/accounts/cookies/validate",
            json={"cookies": SAMPLE_COOKIES},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["error"] is not None

    def test_validate_empty_cookies(self):
        """Empty cookies array returns invalid."""
        response = client.post(
            "/accounts/cookies/validate",
            json={"cookies": []},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    def test_validate_missing_li_at(self):
        """Cookies without li_at return invalid."""
        response = client.post(
            "/accounts/cookies/validate",
            json={"cookies": [{"name": "bcookie", "value": "test", "domain": ".linkedin.com"}]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "li_at" in data["error"]

    def test_validate_malformed_json(self):
        """Invalid JSON body returns 422."""
        response = client.post(
            "/accounts/cookies/validate",
            json={"cookies": "not_an_array"},
        )
        assert response.status_code == 422

    def test_validate_missing_field(self):
        """Missing required 'cookies' field returns 422."""
        response = client.post(
            "/accounts/cookies/validate",
            json={},
        )
        assert response.status_code == 422


# ==============================================================================
# Tests: POST /accounts/cookies (import)
# ==============================================================================


class TestImportEndpoint:
    """Tests for POST /accounts/cookies."""

    @patch("cookie_importer.httpx.Client")
    def test_import_creates_account(self, mock_client_class):
        """Valid cookies create a new account in DB."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = (
            '<script>{"miniProfile":{"firstName":"Juan","lastName":"Pérez"}}</script>'
        )
        mock_client.get.return_value = mock_response

        response = client.post(
            "/accounts/cookies",
            json={
                "cookies": SAMPLE_COOKIES,
                "name": "Mi Cuenta LinkedIn",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["account_id"] is not None
        assert data["name"] == "Mi Cuenta LinkedIn"
        assert "exitosa" in data["detail"]

        # Verify account was actually created in DB
        db = TestingSessionLocal()
        try:
            account = db.query(models.Account).filter(models.Account.id == data["account_id"]).first()
            assert account is not None
            assert account.name == "Mi Cuenta LinkedIn"
            assert account.status == "active"
            assert account.storage_state is not None
        finally:
            db.close()

    @patch("cookie_importer.httpx.Client")
    def test_import_updates_existing(self, mock_client_class):
        """Importing same name updates existing account's storage_state."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<script>{"miniProfile":{"firstName":"Test","lastName":"User"}}</script>'
        mock_client.get.return_value = mock_response

        # First import
        res1 = client.post(
            "/accounts/cookies",
            json={"cookies": SAMPLE_COOKIES, "name": "Duplicate Test"},
        )
        assert res1.status_code == 200
        account_id = res1.json()["account_id"]

        # Second import with same name
        res2 = client.post(
            "/accounts/cookies",
            json={"cookies": SAMPLE_COOKIES, "name": "Duplicate Test"},
        )
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["account_id"] == account_id
        assert "actualizadas" in data2["detail"] or "existente" in data2["detail"]

    @patch("cookie_importer.httpx.Client")
    def test_import_with_proxy(self, mock_client_class):
        """Import with proxy_url stores it on the account."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '<script>{"miniProfile":{"firstName":"Proxy","lastName":"User"}}</script>'
        mock_client.get.return_value = mock_response

        response = client.post(
            "/accounts/cookies",
            json={
                "cookies": SAMPLE_COOKIES,
                "name": "Proxy Account",
                "proxy_url": "http://user:pass@proxy:8080",
            },
        )
        assert response.status_code == 200
        data = response.json()

        db = TestingSessionLocal()
        try:
            account = db.query(models.Account).filter(models.Account.id == data["account_id"]).first()
            assert account.proxy_url == "http://user:pass@proxy:8080"
        finally:
            db.close()

    @patch("cookie_importer.httpx.Client")
    def test_import_no_name_uses_detected_name(self, mock_client_class):
        """Import without name uses the name detected from LinkedIn."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = (
            '<script>{"miniProfile":{"firstName":"Auto","lastName":"Detected"}}</script>'
        )
        mock_client.get.return_value = mock_response

        response = client.post(
            "/accounts/cookies",
            json={"cookies": SAMPLE_COOKIES},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Auto Detected"

    def test_import_empty_cookies(self):
        """Empty cookies returns 400."""
        response = client.post(
            "/accounts/cookies",
            json={"cookies": []},
        )
        assert response.status_code == 400
        assert "cookies" in response.json()["detail"].lower()

    @patch("cookie_importer.httpx.Client")
    def test_import_invalid_storage_state_rejected(self, mock_client_class):
        """Cookies that fail validation are rejected with 400."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        # Simulate expired cookies
        mock_response = MagicMock()
        mock_response.status_code = 302
        mock_response.headers = {"location": "https://www.linkedin.com/login"}
        mock_client.get.return_value = mock_response

        response = client.post(
            "/accounts/cookies",
            json={"cookies": SAMPLE_COOKIES},
        )
        assert response.status_code == 400
        assert "inválidas" in response.json()["detail"].lower() or "expirada" in response.json()["detail"].lower()
