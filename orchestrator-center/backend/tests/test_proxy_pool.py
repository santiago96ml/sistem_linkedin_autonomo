"""Tests for ProxyPool — proxy creation, assignment, auto-assign, health check."""
import pytest
from database import SessionLocal, engine, Base
from models import Proxy
from proxy_pool import ProxyPool


@pytest.fixture(autouse=True)
def setup_db():
    """Create fresh tables for each test."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        # Clean up proxy table
        db.query(Proxy).delete()
        db.commit()
        db.close()


class TestProxy:
    def test_create_proxy(self, setup_db):
        db = setup_db
        p = Proxy(host="10.0.0.1", port=1080, protocol="socks5", country="BR", name="Test BR")
        db.add(p)
        db.commit()

        assert p.id is not None
        assert p.url == "socks5://10.0.0.1:1080"
        assert p.short_url == "socks5://10.0.0.1:1080"
        assert p.is_active is True
        assert p.is_online is False

    def test_proxy_with_auth_url(self, setup_db):
        db = setup_db
        p = Proxy(host="1.2.3.4", port=3128, username="proxyuser", password="secret123", protocol="http")
        db.add(p)
        db.commit()

        assert p.url == "http://proxyuser:secret123@1.2.3.4:3128"
        assert p.short_url == "http://1.2.3.4:3128"

    def test_proxy_without_auth_url(self, setup_db):
        db = setup_db
        p = Proxy(host="5.6.7.8", port=1080, protocol="socks5")
        db.add(p)
        db.commit()

        assert p.url == "socks5://5.6.7.8:1080"
        assert p.short_url == "socks5://5.6.7.8:1080"


class TestProxyPoolGetAll:
    def test_get_all_empty(self, setup_db):
        db = setup_db
        proxies = ProxyPool.get_all(db)
        assert proxies == []

    def test_get_all_with_data(self, setup_db):
        db = setup_db
        p1 = Proxy(host="10.0.0.1", port=1080, country="BR")
        p2 = Proxy(host="10.0.0.2", port=1080, country="AR")
        db.add_all([p1, p2])
        db.commit()

        proxies = ProxyPool.get_all(db)
        assert len(proxies) == 2

    def test_get_all_inactive_filtered(self, setup_db):
        db = setup_db
        p1 = Proxy(host="10.0.0.1", port=1080, country="BR", is_active=True)
        p2 = Proxy(host="10.0.0.2", port=1080, country="AR", is_active=False)
        db.add_all([p1, p2])
        db.commit()

        proxies = ProxyPool.get_all(db, active_only=True)
        assert len(proxies) == 1
        assert proxies[0].host == "10.0.0.1"


class TestProxyPoolAssign:
    def test_assign_to_account(self, setup_db):
        db = setup_db
        p = Proxy(host="10.0.0.1", port=1080, country="BR")
        db.add(p)
        db.commit()

        assigned = ProxyPool.assign_to_account(db, p.id, 42)
        assert assigned.assigned_account_id == 42

        # Verify get_for_account works
        found = ProxyPool.get_for_account(db, 42)
        assert found is not None
        assert found.id == p.id

    def test_unassign(self, setup_db):
        db = setup_db
        p = Proxy(host="10.0.0.1", port=1080, country="BR")
        db.add(p)
        db.commit()

        ProxyPool.assign_to_account(db, p.id, 42)
        ProxyPool.unassign(db, 42)

        found = ProxyPool.get_for_account(db, 42)
        assert found is None

    def test_reassign_switches_proxy(self, setup_db):
        db = setup_db
        p1 = Proxy(host="10.0.0.1", port=1080, country="BR")
        p2 = Proxy(host="10.0.0.2", port=1080, country="AR")
        db.add_all([p1, p2])
        db.commit()

        ProxyPool.assign_to_account(db, p1.id, 1)
        ProxyPool.assign_to_account(db, p2.id, 1)  # same account, different proxy

        found = ProxyPool.get_for_account(db, 1)
        assert found.id == p2.id  # should be the new one
        # p1 should be unassigned
        assert p1.assigned_account_id is None

    def test_get_available_no_country(self, setup_db):
        db = setup_db
        p1 = Proxy(host="10.0.0.1", port=1080, country="BR", is_active=True)
        p2 = Proxy(host="10.0.0.2", port=1080, country="AR", is_active=True)
        db.add_all([p1, p2])
        db.commit()

        available = ProxyPool.get_available(db)
        assert len(available) == 2

    def test_get_available_assigned_excluded(self, setup_db):
        db = setup_db
        p1 = Proxy(host="10.0.0.1", port=1080, country="BR", is_active=True, assigned_account_id=1)
        p2 = Proxy(host="10.0.0.2", port=1080, country="AR", is_active=True)
        db.add_all([p1, p2])
        db.commit()

        available = ProxyPool.get_available(db)
        assert len(available) == 1
        assert available[0].id == p2.id

    def test_get_available_by_country(self, setup_db):
        db = setup_db
        p1 = Proxy(host="10.0.0.1", port=1080, country="BR")
        p2 = Proxy(host="10.0.0.2", port=1080, country="AR")
        p3 = Proxy(host="10.0.0.3", port=1080, country="US")
        db.add_all([p1, p2, p3])
        db.commit()

        available_br = ProxyPool.get_available(db, country="BR")
        assert len(available_br) == 1
        assert available_br[0].country == "BR"

        available_ar = ProxyPool.get_available(db, country="AR")
        assert len(available_ar) == 1

        available_xx = ProxyPool.get_available(db, country="XX")
        assert len(available_xx) == 0


class TestProxyPoolAutoAssign:
    def test_auto_assign_matching_country(self, setup_db):
        db = setup_db
        p1 = Proxy(host="10.0.0.1", port=1080, country="BR")
        p2 = Proxy(host="10.0.0.2", port=1080, country="AR")
        db.add_all([p1, p2])
        db.commit()

        result = ProxyPool.auto_assign(db, 1, country="BR")
        assert result is not None
        assert result.country == "BR"
        assert result.assigned_account_id == 1

    def test_auto_assign_no_matching_country_fallback_to_any(self, setup_db):
        db = setup_db
        p1 = Proxy(host="10.0.0.1", port=1080, country="BR")
        db.add_all([p1])
        db.commit()

        # No AR proxy available → should return None since only BR exists
        result = ProxyPool.auto_assign(db, 1, country="AR")
        assert result is None

    def test_auto_assign_no_proxies(self, setup_db):
        db = setup_db
        result = ProxyPool.auto_assign(db, 1, country="BR")
        assert result is None


class TestProxyPoolStats:
    def test_stats_empty(self, setup_db):
        db = setup_db
        stats = ProxyPool.get_stats(db)
        assert stats["total"] == 0
        assert stats["active"] == 0
        assert stats["online"] == 0
        assert stats["assigned"] == 0

    def test_stats_with_data(self, setup_db):
        db = setup_db
        p1 = Proxy(host="10.0.0.1", port=1080, country="BR", is_active=True, is_online=True)
        p2 = Proxy(host="10.0.0.2", port=1080, country="AR", is_active=True, is_online=False)
        p3 = Proxy(host="10.0.0.3", port=1080, country="BR", is_active=False, assigned_account_id=5)
        db.add_all([p1, p2, p3])
        db.commit()

        stats = ProxyPool.get_stats(db)
        assert stats["total"] == 3
        assert stats["active"] == 2
        assert stats["online"] == 1
        assert stats["assigned"] == 1
        assert stats["by_country"] == {"BR": 2, "AR": 1}


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check_unreachable(self, setup_db):
        """Should return False for a non-existent proxy server."""
        p = Proxy(host="10.255.255.1", port=12345, protocol="socks5")
        result = await ProxyPool.check_proxy_health(p)
        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_http_unreachable(self, setup_db):
        """Should return False for unreachable HTTP proxy."""
        p = Proxy(host="10.255.255.1", port=8080, protocol="http")
        result = await ProxyPool.check_proxy_health(p)
        assert result is False
