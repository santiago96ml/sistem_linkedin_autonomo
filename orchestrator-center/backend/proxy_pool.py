"""
proxy_pool.py — Pool de proxies SOCKS5 con geolocalización.

Cada proxy se asocia a una Account y se usa automáticamente
cuando BrowserPool/MissionRunner crean un contexto de navegador.

Flujo:
  1. Admin carga proxies en DB (desde UI o API)
  2. Al vincular cuenta, se asigna proxy del mismo país
  3. BrowserPool usa el proxy asignado para abrir contextos
  4. Health check periódico para detectar proxies caídos
"""
import asyncio
import logging
import socket
import httpx
from database import Base
import datetime

logger = logging.getLogger(__name__)

# El modelo Proxy está definido en models.py
from models import Proxy


# ==============================================================================
# POOL MANAGER
# ==============================================================================

class ProxyPool:
    """
    Gestiona la asignación de proxies a cuentas y health checks.

    Uso:
        pool = ProxyPool()
        proxy = pool.assign_to_account(db, account_id, preferred_country="BR")
        proxy = pool.get_for_account(db, account_id)
        pool.run_health_check(db)  # en background
    """

    HEALTH_CHECK_TIMEOUT = 10  # segundos
    HEALTH_CHECK_INTERVAL = 300  # 5 min entre checks

    @staticmethod
    def get_all(db, active_only=True):
        """Lista todos los proxies."""
        q = db.query(Proxy)
        if active_only:
            q = q.filter(Proxy.is_active == True)
        return q.order_by(Proxy.created_at.desc()).all()

    @staticmethod
    def get_available(db, country=None):
        """Proxies disponibles (no asignados) opcionalmente filtrados por país."""
        q = db.query(Proxy).filter(
            Proxy.is_active == True,
            Proxy.assigned_account_id.is_(None)
        )
        if country:
            q = q.filter(Proxy.country == country.upper())
        return q.all()

    @staticmethod
    def get_for_account(db, account_id) -> Proxy | None:
        """Devuelve el proxy asignado a una cuenta."""
        return db.query(Proxy).filter(
            Proxy.assigned_account_id == account_id,
            Proxy.is_active == True
        ).first()

    @staticmethod
    def assign_to_account(db, proxy_id: int, account_id: int) -> Proxy:
        """Asigna un proxy a una cuenta. Desasigna el anterior si existía."""
        # Liberar proxy anterior de esta cuenta
        old = db.query(Proxy).filter(
            Proxy.assigned_account_id == account_id
        ).first()
        if old:
            old.assigned_account_id = None

        proxy = db.get(Proxy, proxy_id)
        if not proxy:
            raise ValueError(f"Proxy {proxy_id} no encontrado")
        proxy.assigned_account_id = account_id

        # Actualizar también proxy_url en Account
        from models import Account
        account = db.get(Account, account_id)
        if account:
            account.proxy_url = proxy.url

        db.commit()
        return proxy

    @staticmethod
    def unassign(db, account_id: int):
        """Desasigna el proxy de una cuenta."""
        proxy = db.query(Proxy).filter(
            Proxy.assigned_account_id == account_id
        ).first()
        if proxy:
            proxy.assigned_account_id = None
            from models import Account
            account = db.get(Account, account_id)
            if account:
                account.proxy_url = None
            db.commit()

    @staticmethod
    def auto_assign(db, account_id: int, country: str = None) -> Proxy | None:
        """
        Asigna automáticamente el mejor proxy disponible para una cuenta.
        Si se especifica country, busca proxy de ese país.
        """
        proxies = ProxyPool.get_available(db, country)
        if not proxies:
            logger.warning(f"No hay proxies disponibles para país={country}")
            return None

        # Elegir el más reciente (último agregado)
        proxy = proxies[0]
        return ProxyPool.assign_to_account(db, proxy.id, account_id)

    @staticmethod
    async def check_proxy_health(proxy: Proxy) -> bool:
        """Testea un proxy conectándose a un servicio externo.
        
        Para SOCKS5: conecta TCP + handshake SOCKS5.
        Para HTTP: usa httpx con proxy.
        Sin dependencias externas (no requiere curl).
        """
        try:
            if proxy.protocol == "socks5":
                return await ProxyPool._check_socks5(proxy)
            else:
                return await ProxyPool._check_http_proxy(proxy)
        except Exception as e:
            logger.warning(f"Health check fail for {proxy.short_url}: {e}")
            return False

    @staticmethod
    async def _check_socks5(proxy: Proxy) -> bool:
        """Test SOCKS5 via raw socket handshake. No requiere curl."""
        loop = asyncio.get_event_loop()
        
        def _do_handshake():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(ProxyPool.HEALTH_CHECK_TIMEOUT)
                s.connect((proxy.host, proxy.port))

                # SOCKS5 handshake: https://tools.ietf.org/html/rfc1928
                # Client: VER=5, NMETHODS=1, METHODS=[0=no-auth, 2=user/pass]
                if proxy.username:
                    # With auth (method 2)
                    s.sendall(bytes([5, 2, 0, 2]))  # VER, NMETHODS, [no-auth, userpass]
                    data = s.recv(2)
                    if data != bytes([5, 2]):  # Server chose userpass
                        s.close()
                        return False
                    # User/pass auth sub-negotiation
                    uname = proxy.username.encode()
                    passwd = proxy.password.encode() if proxy.password else b""
                    s.sendall(bytes([1, len(uname)]) + uname + bytes([len(passwd)]) + passwd)
                    data = s.recv(2)
                    if data != bytes([1, 0]):  # Auth failed
                        s.close()
                        return False
                else:
                    # No auth
                    s.sendall(bytes([5, 1, 0]))  # VER, NMETHODS, [no-auth]
                    data = s.recv(2)
                    if data != bytes([5, 0]):  # Server rejected
                        s.close()
                        return False

                # Final: UDP ASSOCIATE to test connectivity
                # VER=5, CMD=3(UDP ASSOCIATE), RSV=0, ATYP=1(IPv4), DST.ADDR=0, DST.PORT=0
                s.sendall(bytes([5, 3, 0, 1, 0, 0, 0, 0, 0, 0]))
                data = s.recv(10)
                s.close()
                return len(data) >= 2 and data[0] == 5 and data[1] == 0
            except Exception:
                return False

        return await loop.run_in_executor(None, _do_handshake)

    @staticmethod
    async def _check_http_proxy(proxy: Proxy) -> bool:
        """Test HTTP/HTTPS proxy via httpx."""
        url = proxy.url
        test_url = "http://ifconfig.me"
        try:
            async with httpx.AsyncClient(
                proxies=url,
                timeout=ProxyPool.HEALTH_CHECK_TIMEOUT
            ) as client:
                r = await client.get(test_url)
                return r.status_code == 200 and len(r.text.strip()) > 0
        except Exception:
            return False

    @staticmethod
    async def run_health_checks(db) -> dict:
        """
        Corre health check en todos los proxies activos.
        Devuelve stats: {total, online, offline}
        """
        proxies = db.query(Proxy).filter(Proxy.is_active == True).all()
        now = datetime.datetime.utcnow()
        results = {"total": len(proxies), "online": 0, "offline": 0, "details": []}

        for proxy in proxies:
            is_online = await ProxyPool.check_proxy_health(proxy)
            proxy.is_online = is_online
            proxy.last_health_check = now

            if is_online:
                results["online"] += 1
            else:
                results["offline"] += 1
                logger.warning(f"Proxy offline: {proxy.short_url} ({proxy.country})")

            results["details"].append({
                "id": proxy.id,
                "name": proxy.name,
                "url": proxy.short_url,
                "country": proxy.country,
                "online": is_online,
            })

        db.commit()
        return results

    @staticmethod
    def get_stats(db) -> dict:
        """Estadísticas del pool."""
        total = db.query(Proxy).count()
        active = db.query(Proxy).filter(Proxy.is_active == True).count()
        online = db.query(Proxy).filter(Proxy.is_active == True, Proxy.is_online == True).count()
        assigned = db.query(Proxy).filter(Proxy.assigned_account_id.isnot(None)).count()
        by_country = {}
        for p in db.query(Proxy).filter(Proxy.country.isnot(None)).all():
            c = p.country.upper()
            by_country[c] = by_country.get(c, 0) + 1

        return {
            "total": total,
            "active": active,
            "online": online,
            "assigned": assigned,
            "by_country": by_country,
        }
