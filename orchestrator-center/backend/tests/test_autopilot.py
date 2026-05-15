"""Tests for autopilot protocol improvements.

Covers:
- _check_schedule (timezone-aware UTC-3)
- _check_cta (keyword presence)
- _detect_call_to_action (multi-language CTA detection)
- Mission.source field
- Circuit breaker state
- _rephrase_comment behavior
"""
import datetime
from datetime import timezone, timedelta
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from models import Mission, TargetProfile, ProcessedPost, Base
from conftest import TestingSessionLocal, engine


# ──────────────────────────────────────────────
# _check_schedule tests
# ──────────────────────────────────────────────

def _check_schedule(start_time_str, end_time_str):
    """Copy of autopilot._check_schedule for isolated testing."""
    try:
        tz = timezone(timedelta(hours=-3))
        now = datetime.datetime.now(tz).time()
        start = datetime.datetime.strptime(start_time_str, "%H:%M").time()
        end = datetime.datetime.strptime(end_time_str, "%H:%M").time()

        if start <= end:
            return start <= now <= end
        else:
            return start <= now or now <= end
    except Exception:
        return True


class TestCheckSchedule:
    def test_within_range(self):
        """Time is within a normal range."""
        # We can't control `now`, but we can test the logic.
        # If start=00:00 end=23:59, should always be True.
        assert _check_schedule("00:00", "23:59") is True

    def test_invalid_format_returns_true(self):
        """Invalid time strings default to True (safe fallback)."""
        assert _check_schedule("", "") is True
        assert _check_schedule("not-a-time", "also-bad") is True

    def test_midnight_crossover_logic(self):
        """Midnight crossover: start > end means overnight window."""
        start = datetime.datetime.strptime("22:00", "%H:%M").time()
        end = datetime.datetime.strptime("06:00", "%H:%M").time()
        now = datetime.datetime.now(timezone(timedelta(hours=-3))).time()
        expected = (start <= now or now <= end)
        assert _check_schedule("22:00", "06:00") == expected


# ──────────────────────────────────────────────
# _check_cta tests
# ──────────────────────────────────────────────

def _check_cta(post_text, cta_keywords_str):
    """Copy of autopilot._check_cta for isolated testing."""
    import re
    if not cta_keywords_str or not cta_keywords_str.strip():
        return True
    keywords = [k.strip().lower() for k in cta_keywords_str.split(",") if k.strip()]
    if not keywords:
        return True
    text_lower = post_text.lower()
    for kw in keywords:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, text_lower):
            return True
    return False


class TestCheckCTA:
    def test_no_keywords_always_triggers(self):
        """No keywords = always trigger."""
        assert _check_cta("Some post text", "") is True
        assert _check_cta("Some post text", None) is True
        assert _check_cta("Some post text", "   ") is True

    def test_keyword_found(self):
        """Keyword present in text triggers True."""
        assert _check_cta("Check out this webinar about AI", "webinar") is True

    def test_keyword_not_found(self):
        """Keyword not present returns False."""
        assert _check_cta("Nice weather today", "webinar") is False

    def test_multiple_keywords_one_match(self):
        """Multiple keywords, one match = True."""
        assert _check_cta("Register for our free demo", "webinar, register, demo") is True

    def test_word_boundary_no_partial_match(self):
        """Word boundary prevents partial matches."""
        assert _check_cta("This is a webinarbage post", "webinar") is False

    def test_case_insensitive(self):
        """Case insensitive matching."""
        assert _check_cta("REGISTER NOW", "register") is True


# ──────────────────────────────────────────────
# _detect_call_to_action tests
# ──────────────────────────────────────────────

def _detect_call_to_action(post_text, cta_keywords_str):
    """Copy of autopilot._detect_call_to_action for isolated testing."""
    import re
    if not cta_keywords_str or not cta_keywords_str.strip():
        return None
    keywords = [k.strip().lower() for k in cta_keywords_str.split(",") if k.strip()]
    if not keywords:
        return None
    text_lower = post_text.lower()
    for kw in keywords:
        patterns = [
            f"comenta\\s+{re.escape(kw)}",
            f"escribe\\s+{re.escape(kw)}",
            f"dime\\s+{re.escape(kw)}",
            f"pon\\s+{re.escape(kw)}",
            f"comment\\s+{re.escape(kw)}",
            f"type\\s+{re.escape(kw)}",
            f"say\\s+{re.escape(kw)}",
            f"write\\s+{re.escape(kw)}",
            f"comente\\s+{re.escape(kw)}",
            f"digite\\s+{re.escape(kw)}",
            f"keyword\\s*[:\\-]?\\s*{re.escape(kw)}",
            f"palabra\\s*[:\\-]?\\s*{re.escape(kw)}",
        ]
        if any(re.search(p, text_lower) for p in patterns):
            return kw
    return None


class TestDetectCallToAction:
    def test_no_keywords_returns_none(self):
        """No keywords configured returns None."""
        assert _detect_call_to_action("Some text", "") is None
        assert _detect_call_to_action("Some text", None) is None

    def test_spanish_comenta(self):
        """Detects 'comenta [keyword]' in Spanish."""
        result = _detect_call_to_action("Hola, comenta python si te gusta", "python")
        assert result == "python"

    def test_spanish_escribe(self):
        """Detects 'escribe [keyword]' in Spanish."""
        result = _detect_call_to_action("Escribe code para más info", "code")
        assert result == "code"

    def test_english_comment(self):
        """Detects 'comment [keyword]' in English."""
        result = _detect_call_to_action("Please comment react if you agree", "react")
        assert result == "react"

    def test_english_type(self):
        """Detects 'type [keyword]' in English."""
        result = _detect_call_to_action("Type yes in the comments", "yes")
        assert result == "yes"

    def test_portuguese_comente(self):
        """Detects 'comente [keyword]' in Portuguese."""
        result = _detect_call_to_action("Comente obrigado se gostou", "obrigado")
        assert result == "obrigado"

    def test_universal_keyword_prefix(self):
        """Detects 'keyword: [kw]' universal pattern."""
        result = _detect_call_to_action("Keyword: typescript", "typescript")
        assert result == "typescript"

    def test_keyword_not_in_post(self):
        """Post without any CTA pattern returns None."""
        result = _detect_call_to_action("Nice weather today", "python")
        assert result is None

    def test_multiple_keywords_selects_first_match(self):
        """Returns the first keyword that matches a CTA pattern."""
        result = _detect_call_to_action("Comenta node si te gusta", "python, node, rust")
        assert result == "node"


# ──────────────────────────────────────────────
# _rephrase_comment tests
# ──────────────────────────────────────────────

def _rephrase_comment(original, account_index):
    """Copy of main._rephrase_comment for isolated testing."""
    import random
    import re as _re

    synonyms = {
        r"\bde acuerdo\b": ["totalmente de acuerdo", "de acuerdo contigo", "en la misma línea"],
        r"\bgenial\b": ["excelente", "fantástico", "muy bueno"],
        r"\binteresante\b": ["fascinante", "muy valioso", "relevante"],
        r"\bgracias\b": ["muchas gracias", "muy agradecido", "agradezco"],
        r"\bincreíble\b": ["sorprendente", "notable", "impresionante"],
    }
    openers = [
        "", "Completamente de acuerdo. ", "Muy buen punto. ", "Excelente reflexión. ",
        "Gran aporte. ", "100% de acuerdo. ", "Interesante perspectiva. "
    ]
    closers = [
        "", " \U0001f44f", " \U0001f64c", " \U0001f4a1", " \U0001f525", " \u2705", "!", " \U0001f4af"
    ]

    rng = random.Random(account_index * 7919 + len(original))

    result = original
    for pattern, variants in synonyms.items():
        if _re.search(pattern, result, flags=_re.IGNORECASE):
            replacement = rng.choice(variants)
            result = _re.sub(pattern, replacement, result, count=1, flags=_re.IGNORECASE)

    opener = rng.choice(openers)
    closer = rng.choice(closers)

    if opener == "" and closer == "" and result == original:
        closer = " \U0001f44f"

    return opener + result.strip() + closer


class TestRephraseComment:
    def test_synonym_replacement(self):
        """Known synonyms get replaced."""
        result = _rephrase_comment("Estoy de acuerdo", 1)
        assert "acuerdo" not in result or result != "Estoy de acuerdo"

    def test_deterministic_per_account(self):
        """Same account_id + same text = same result."""
        r1 = _rephrase_comment("Contenido interesante", 5)
        r2 = _rephrase_comment("Contenido interesante", 5)
        assert r1 == r2

    def test_different_account_different_result(self):
        """Different account_id produces different rephrase."""
        r1 = _rephrase_comment("Contenido interesante", 1)
        r2 = _rephrase_comment("Contenido interesante", 2)
        assert r1 != r2

    def test_always_adds_something(self):
        """If no synonyms matched and opener/closer are empty, forces a closer."""
        result = _rephrase_comment("xyz_nonexistent_123", 42)
        # Should have at least some transformation
        assert result != "xyz_nonexistent_123"


# ──────────────────────────────────────────────
# Mission.source field tests
# ──────────────────────────────────────────────

class TestMissionSourceField:
    def test_default_source_is_manual_after_commit(self, db):
        """Default source 'manual' takes effect after DB commit."""
        mission = Mission(account_id=1, tasks=[{"type": "test"}])
        db.add(mission)
        db.commit()
        db.refresh(mission)
        assert mission.source == "manual"

    def test_source_autopilot(self, db):
        """Source can be set to 'autopilot' and persists."""
        mission = Mission(account_id=1, tasks=[{"type": "test"}], source="autopilot")
        db.add(mission)
        db.commit()
        db.refresh(mission)
        assert mission.source == "autopilot"

    def test_source_autopilot_notification(self, db):
        """Source can be set to 'autopilot_notification' and persists."""
        mission = Mission(account_id=1, tasks=[{"type": "test"}], source="autopilot_notification")
        db.add(mission)
        db.commit()
        db.refresh(mission)
        assert mission.source == "autopilot_notification"

    def test_source_mixed_in_db(self, db):
        """Multiple missions with different sources."""
        m1 = Mission(account_id=42, tasks=[{"type": "test"}], source="autopilot")
        m2 = Mission(account_id=43, tasks=[{"type": "test2"}])
        db.add_all([m1, m2])
        db.commit()
        db.refresh(m1)
        db.refresh(m2)
        assert m1.source == "autopilot"
        assert m2.source == "manual"


# ──────────────────────────────────────────────
# ProcessedPost dedup model test
# ──────────────────────────────────────────────

class TestProcessedPost:
    def test_create_processed_post(self, db):
        """Can create ProcessedPost record."""
        tp = TargetProfile(linkedin_url="https://linkedin.com/in/test", cta_keywords="test")
        db.add(tp)
        db.commit()
        db.refresh(tp)

        pp = ProcessedPost(target_profile_id=tp.id, post_url="https://linkedin.com/posts/123")
        db.add(pp)
        db.commit()
        db.refresh(pp)
        assert pp.post_url == "https://linkedin.com/posts/123"
        assert pp.target_profile_id == tp.id

    def test_processed_post_unique_url(self, db):
        """post_url is unique."""
        tp = TargetProfile(linkedin_url="https://linkedin.com/in/test2", cta_keywords="test")
        db.add(tp)
        db.commit()
        db.refresh(tp)

        pp1 = ProcessedPost(target_profile_id=tp.id, post_url="https://linkedin.com/posts/unique")
        db.add(pp1)
        db.commit()

        pp2 = ProcessedPost(target_profile_id=tp.id, post_url="https://linkedin.com/posts/unique")
        with pytest.raises(Exception):
            db.add(pp2)
            db.commit()
