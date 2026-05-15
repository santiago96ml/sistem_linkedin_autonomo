"""Tests for cookie_importer.py — conversion and validation of Chrome cookies to Playwright storage_state."""

import pytest
import json
from unittest.mock import patch, MagicMock, ANY
import httpx

from cookie_importer import (
    convert_to_storage_state,
    validate_storage_state,
    _extract_name_from_nav,
    _extract_profile_pic,
    SAMESITE_MAP,
)


# ==============================================================================
# Tests: convert_to_storage_state
# ==============================================================================


class TestConvertToStorageState:
    """Unit tests for convert_to_storage_state()."""

    def test_basic_linkedin_cookies(self):
        """Normal LinkedIn cookies with all fields."""
        raw = [
            {
                "domain": "www.linkedin.com",
                "expirationDate": 1805544294.0,
                "hostOnly": False,
                "httpOnly": True,
                "name": "li_at",
                "path": "/",
                "sameSite": "no_restriction",
                "secure": True,
                "session": False,
                "value": "AQED...mock_value...",
            },
            {
                "domain": ".www.linkedin.com",
                "expirationDate": 1805544294.0,
                "hostOnly": False,
                "httpOnly": False,
                "name": "JSESSIONID",
                "path": "/",
                "sameSite": "none",
                "secure": True,
                "session": False,
                "value": '"ajax:123456789"',
            },
        ]
        result = convert_to_storage_state(raw)

        assert "cookies" in result
        assert len(result["cookies"]) == 2

        # Check li_at conversion
        li_at = result["cookies"][0]
        assert li_at["name"] == "li_at"
        assert li_at["value"] == "AQED...mock_value..."
        assert li_at["domain"] == ".www.linkedin.com"  # dot prefix added
        assert li_at["httpOnly"] is True
        assert li_at["secure"] is True
        assert li_at["expires"] == 1805544294.0
        assert li_at["sameSite"] == "None"  # mapped from no_restriction

        # Check JSESSIONID
        jsess = result["cookies"][1]
        assert jsess["name"] == "JSESSIONID"
        assert jsess["domain"] == ".www.linkedin.com"  # already starts with dot

    def test_empty_array(self):
        """Empty array returns empty cookies."""
        result = convert_to_storage_state([])
        assert result == {"cookies": []}

    def test_skip_invalid_items(self):
        """Skips items that are not dicts or missing name/value."""
        raw = [
            None,
            "string",
            {"name": "no_value"},
            {"value": "no_name"},
            {"name": "", "value": "empty_name"},
            {"name": "valid", "value": "ok", "domain": "linkedin.com"},
        ]
        result = convert_to_storage_state(raw)
        assert len(result["cookies"]) == 1
        assert result["cookies"][0]["name"] == "valid"

    def test_session_cookie_no_expiration(self):
        """Session cookie without expirationDate gets expires=-1."""
        raw = [
            {
                "domain": "www.linkedin.com",
                "name": "li_at",
                "value": "session_value",
                "session": True,
                "httpOnly": True,
                "secure": True,
            }
        ]
        result = convert_to_storage_state(raw)
        assert result["cookies"][0]["expires"] == -1

    def test_no_session_no_expiration_skipped(self):
        """Non-session cookie without expirationDate is skipped."""
        raw = [
            {
                "domain": "www.linkedin.com",
                "name": "li_at",
                "value": "val",
                "session": False,
                "httpOnly": True,
                "secure": True,
            }
        ]
        result = convert_to_storage_state(raw)
        assert len(result["cookies"]) == 0

    def test_samesite_mapping_all_variants(self):
        """All sameSite values are correctly mapped."""
        for chrome_value, expected in SAMESITE_MAP.items():
            raw = [
                {
                    "domain": "linkedin.com",
                    "expirationDate": 1900000000.0,
                    "name": "test",
                    "value": "val",
                    "sameSite": chrome_value,
                    "httpOnly": False,
                    "secure": True,
                }
            ]
            result = convert_to_storage_state(raw)
            assert result["cookies"][0].get("sameSite") == expected, (
                f"Failed for sameSite={chrome_value}"
            )

    def test_samesite_null_omitted(self):
        """null sameSite is omitted from output."""
        raw = [
            {
                "domain": "linkedin.com",
                "expirationDate": 1900000000.0,
                "name": "test",
                "value": "val",
                "sameSite": None,
                "httpOnly": False,
                "secure": True,
            }
        ]
        result = convert_to_storage_state(raw)
        assert "sameSite" not in result["cookies"][0]

    def test_domain_normalization_hostonly(self):
        """hostOnly cookies do NOT get a dot prefix."""
        raw = [
            {
                "domain": "www.linkedin.com",
                "expirationDate": 1900000000.0,
                "name": "li_at",
                "value": "val",
                "hostOnly": True,
                "httpOnly": True,
                "secure": True,
            }
        ]
        result = convert_to_storage_state(raw)
        assert result["cookies"][0]["domain"] == "www.linkedin.com"

    def test_non_linkedin_domain_not_normalized(self):
        """Non-linkedin domain keeps original domain."""
        raw = [
            {
                "domain": "example.com",
                "expirationDate": 1900000000.0,
                "name": "test",
                "value": "val",
                "httpOnly": False,
                "secure": False,
            }
        ]
        result = convert_to_storage_state(raw)
        assert result["cookies"][0]["domain"] == "example.com"

    def test_default_path_and_secure(self):
        """Defaults: path='/', secure=True."""
        raw = [
            {
                "domain": "linkedin.com",
                "expirationDate": 1900000000.0,
                "name": "li_at",
                "value": "val",
                "httpOnly": True,
            }
        ]
        result = convert_to_storage_state(raw)
        cookie = result["cookies"][0]
        assert cookie["path"] == "/"
        assert cookie["secure"] is True


# ==============================================================================
# Tests: validate_storage_state
# ==============================================================================


class TestValidateStorageState:
    """Tests for validate_storage_state(). Uses mocked httpx."""

    VALID_STORAGE_STATE = {
        "cookies": [
            {
                "name": "li_at",
                "value": "AQED_valid_mock",
                "domain": ".www.linkedin.com",
                "path": "/",
                "expires": 1900000000.0,
                "httpOnly": True,
                "secure": True,
                "sameSite": "None",
            }
        ]
    }

    def _mock_response(self, status=200, text="", headers=None):
        """Helper to create a mock httpx response."""
        mock = MagicMock(spec=httpx.Response)
        mock.status_code = status
        mock.text = text
        mock.headers = headers or {}
        return mock

    @patch("cookie_importer.httpx.Client")
    def test_valid_cookies(self, mock_client_class):
        """Valid cookies return valid=True with name."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        html_with_name = """
        <script>window.__INITIAL_STATE__={"miniProfile":{"firstName":"Juan","lastName":"Pérez"}}</script>
        """
        mock_client.get.return_value = self._mock_response(
            status=200, text=html_with_name
        )

        result = validate_storage_state(self.VALID_STORAGE_STATE)

        assert result["valid"] is True
        assert result["name"] == "Juan Pérez"
        assert result["error"] is None
        mock_client.get.assert_called_once_with("https://www.linkedin.com/feed/")

    @patch("cookie_importer.httpx.Client")
    def test_valid_cookies_no_name(self, mock_client_class):
        """Valid cookies but HTML has no name -> valid=True, name=None."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        mock_client.get.return_value = self._mock_response(
            status=200, text="<html>no profile data</html>"
        )

        result = validate_storage_state(self.VALID_STORAGE_STATE)

        assert result["valid"] is True
        assert result["name"] is None

    def test_missing_li_at(self):
        """No li_at cookie -> invalid."""
        storage_state = {"cookies": [{"name": "JSESSIONID", "value": "xxx", "domain": ".www.linkedin.com"}]}
        result = validate_storage_state(storage_state)
        assert result["valid"] is False
        assert "li_at" in result["error"]

    def test_empty_cookies(self):
        """Empty cookies array -> invalid (no li_at)."""
        result = validate_storage_state({"cookies": []})
        assert result["valid"] is False

    def test_no_cookies_key(self):
        """Missing 'cookies' key -> invalid."""
        result = validate_storage_state({})
        assert result["valid"] is False

    @patch("cookie_importer.httpx.Client")
    def test_redirect_to_login(self, mock_client_class):
        """Redirect to /login -> expired cookies."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        mock_client.get.return_value = self._mock_response(
            status=302,
            headers={"location": "https://www.linkedin.com/login?from=feed"},
        )

        result = validate_storage_state(self.VALID_STORAGE_STATE)
        assert result["valid"] is False
        assert "expirada" in result["error"].lower() or "login" in result["error"]

    @patch("cookie_importer.httpx.Client")
    def test_redirect_to_authwall(self, mock_client_class):
        """Redirect to /authwall -> expired cookies."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        mock_client.get.return_value = self._mock_response(
            status=302,
            headers={"location": "https://www.linkedin.com/authwall"},
        )

        result = validate_storage_state(self.VALID_STORAGE_STATE)
        assert result["valid"] is False

    @patch("cookie_importer.httpx.Client")
    def test_redirect_to_feed(self, mock_client_class):
        """Redirect to /feed/ (canonical) -> valid."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        mock_client.get.return_value = self._mock_response(
            status=302,
            headers={"location": "https://www.linkedin.com/feed/?trk=homepage"},
        )

        result = validate_storage_state(self.VALID_STORAGE_STATE)
        assert result["valid"] is True

    @patch("cookie_importer.httpx.Client")
    def test_http_403_challenge(self, mock_client_class):
        """HTTP 403 -> security challenge."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        mock_client.get.return_value = self._mock_response(status=403)

        result = validate_storage_state(self.VALID_STORAGE_STATE)
        assert result["valid"] is False
        assert "403" in result["error"]

    @patch("cookie_importer.httpx.Client")
    def test_http_429_rate_limit(self, mock_client_class):
        """HTTP 429 -> rate limited."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        mock_client.get.return_value = self._mock_response(status=429)

        result = validate_storage_state(self.VALID_STORAGE_STATE)
        assert result["valid"] is False
        assert "429" in result["error"] or "requests" in result["error"].lower()

    @patch("cookie_importer.httpx.Client")
    def test_timeout_exception(self, mock_client_class):
        """Timeout -> invalid."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        mock_client.get.side_effect = httpx.TimeoutException("timed out")

        result = validate_storage_state(self.VALID_STORAGE_STATE)
        assert result["valid"] is False
        assert "tiempo" in result["error"].lower()

    @patch("cookie_importer.httpx.Client")
    def test_connect_error(self, mock_client_class):
        """Connection error -> invalid."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        mock_client.get.side_effect = httpx.ConnectError("connection refused")

        result = validate_storage_state(self.VALID_STORAGE_STATE)
        assert result["valid"] is False
        assert "conectar" in result["error"].lower()

    @patch("cookie_importer.httpx.Client")
    def test_unexpected_exception(self, mock_client_class):
        """Unexpected exception -> caught and returned as error."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        mock_client.get.side_effect = ValueError("something weird")

        result = validate_storage_state(self.VALID_STORAGE_STATE)
        assert result["valid"] is False
        assert "inesperado" in result["error"].lower() or "error" in result["error"].lower()

    @patch("cookie_importer.httpx.Client")
    def test_jsessionid_sent_as_csrf_token(self, mock_client_class):
        """JSESSIONID is sent as csrf-token header."""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client_class.return_value = mock_client

        mock_client.get.return_value = self._mock_response(status=200, text="ok")

        storage_state_with_jsess = {
            "cookies": [
                {
                    "name": "li_at",
                    "value": "AQED_valid",
                    "domain": ".www.linkedin.com",
                    "path": "/",
                    "expires": 1900000000.0,
                    "httpOnly": True,
                    "secure": True,
                },
                {
                    "name": "JSESSIONID",
                    "value": '"ajax:98765"',
                    "domain": ".www.linkedin.com",
                    "path": "/",
                    "expires": 1900000000.0,
                    "httpOnly": False,
                    "secure": True,
                },
            ]
        }

        result = validate_storage_state(storage_state_with_jsess)

        assert result["valid"] is True
        # Verify csrf-token was set (we can check headers passed to Client)
        call_args = mock_client_class.call_args
        headers = call_args[1].get("headers", {})
        # Actually httpx.Client is called with headers=... so let's verify differently
        # The headers dict should contain csrf-token
        # The mock_client_class call is: httpx.Client(headers=..., cookies=..., ...)
        _, kwargs = mock_client_class.call_args
        assert "csrf-token" in kwargs.get("headers", {})
        assert kwargs["headers"]["csrf-token"] == "ajax:98765"


# ==============================================================================
# Tests: helper extraction functions
# ==============================================================================


class TestExtractNameFromNav:
    """Tests for _extract_name_from_nav()."""

    def test_miniprofile_pattern(self):
        """Extracts full name from miniProfile JSON."""
        html = """
        <script>
        window.__INITIAL_STATE__={"miniProfile":{"firstName":"María","lastName":"García","headline":"Developer"}}
        </script>
        """
        assert _extract_name_from_nav(html) == "María García"

    def test_fallback_firstname_pattern(self):
        """Fallback: extracts just firstName when miniProfile not found."""
        html = """
        <script>{"firstName":"Carlos","lastName":"López","headline":"Engineer"}</script>
        """
        name = _extract_name_from_nav(html)
        assert name is not None
        assert "Carlos" in name

    def test_no_match(self):
        """Returns None when no name pattern matches."""
        html = "<html><body>No profile data here</body></html>"
        assert _extract_name_from_nav(html) is None

    def test_empty_html(self):
        """Empty string returns None."""
        assert _extract_name_from_nav("") is None


class TestExtractProfilePic:
    """Tests for _extract_profile_pic()."""

    def test_picture_found(self):
        """Extracts rootUrl from picture JSON."""
        html = """
        <script>{"picture":{"rootUrl":"https://media.licdn.com/media/abc123","artifact":"123"}}</script>
        """
        assert _extract_profile_pic(html) == "https://media.licdn.com/media/abc123"

    def test_no_picture(self):
        """Returns None when no picture found."""
        html = "<html><body>No picture</body></html>"
        assert _extract_profile_pic(html) is None

    def test_empty_html(self):
        """Empty string returns None."""
        assert _extract_profile_pic("") is None
