"""
cookie_importer.py — Conversor de cookies formato extensión Chrome
a Playwright storage_state + validador HTTP directo.

Flujo:
  1. Recibe JSON de cookies desde extensión Chrome
  2. Convierte al formato que Playwright espera (storage_state)
  3. Valida contra LinkedIn usando httpx (SIN navegador, ~2s)
  4. Si es válido, se guarda en DB como Account
"""

import re
import logging
import httpx

logger = logging.getLogger(__name__)

# ==============================================================================
# CONVERSIÓN: Formato Extensión Chrome → Playwright storage_state
# ==============================================================================

SAMESITE_MAP = {
    "no_restriction": "None",
    "lax": "Lax",
    "strict": "Strict",
    "None": "None",
    "Lax": "Lax",
    "Strict": "Strict",
}

def convert_to_storage_state(raw_cookies: list[dict]) -> dict:
    """
    Convierte cookies desde formato extensión Chrome a storage_state de Playwright.

    Formato entrada (extensión):
    [{
        "domain": "www.linkedin.com",
        "expirationDate": 1805544294.0,
        "hostOnly": true|false,
        "httpOnly": true|false,
        "name": "li_at",
        "path": "/",
        "sameSite": "no_restriction" | "lax" | "strict" | null,
        "secure": true|false,
        "session": true|false,
        "value": "AQED..."
    }]

    Formato salida (Playwright):
    {"cookies": [{
        "name": "li_at", "value": "...",
        "domain": ".www.linkedin.com", "path": "/",
        "expires": 1805544294.0,
        "httpOnly": true, "secure": true,
        "sameSite": "None"
    }]}
    """
    playwright_cookies = []

    for c in raw_cookies:
        if not isinstance(c, dict) or "name" not in c or "value" not in c:
            continue

        # Saltar cookies sin nombre/valor
        if not c.get("name") or c["value"] is None:
            continue

        pc = {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", True),
        }

        # expirationDate → expires (formato Playwright)
        if "expirationDate" in c and c["expirationDate"] is not None:
            pc["expires"] = float(c["expirationDate"])
        elif c.get("session", True):
            # Session cookie sin expiración: Playwright usa -1
            pc["expires"] = -1
        else:
            # Cookie no-session sin expiración — la omitimos
            continue

        # sameSite: "no_restriction" → "None", null → omitir
        ss = c.get("sameSite")
        if ss and ss in SAMESITE_MAP:
            pc["sameSite"] = SAMESITE_MAP[ss]
        # Si ss es None o está vacío, no incluimos sameSite

        # Normalizar dominio: Playwright espera que empiece con "."
        # para cookies de linkedin.com
        domain = pc["domain"]
        if domain and not domain.startswith(".") and "linkedin" in domain:
            # Si es hostOnly, no agregamos el punto
            if not c.get("hostOnly", False):
                pc["domain"] = "." + domain

        playwright_cookies.append(pc)

    return {"cookies": playwright_cookies}


# ==============================================================================
# VALIDACIÓN: Verificar que las cookies dan acceso a LinkedIn
# ==============================================================================

def validate_storage_state(storage_state: dict) -> dict:
    """
    Valida un storage_state contra LinkedIn usando HTTP directo (sin Playwright).

    Construye un cliente httpx con las cookies y trata de acceder a /feed/.
    Si LinkedIn redirige a /login o /authwall, la cookie expiró o es inválida.

    Returns:
        {"valid": bool, "name": str|None, "profile_pic": str|None, "error": str|None}
    """
    cookies = storage_state.get("cookies", [])

    # Extraer li_at y JSESSIONID para validación
    li_at = None
    jsessionid = None
    cookie_dict = {}
    for c in cookies:
        name = c.get("name", "")
        domain = c.get("domain", "")
        if "linkedin" not in domain:
            continue
        cookie_dict[name] = c.get("value", "")
        if name == "li_at":
            li_at = c["value"]
        elif name == "JSESSIONID":
            jsessionid = c["value"]

    if not li_at:
        return {"valid": False, "name": None, "profile_pic": None,
                "error": "No se encontró la cookie li_at. Asegurate de incluir las cookies de linkedin.com"}

    # Headers que imitan un navegador real
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
    }

    # Si tenemos JSESSIONID, lo usamos como csrf-token para detectar mejor
    if jsessionid:
        headers["csrf-token"] = jsessionid.strip('"')

    try:
        with httpx.Client(
            headers=headers,
            cookies=cookie_dict,
            follow_redirects=False,
            timeout=15.0,
            verify=True,
        ) as client:
            # Estrategia: probar /feed/ primero (más confiable)
            feed_resp = client.get("https://www.linkedin.com/feed/")

            # Manejar redirecciones
            if feed_resp.status_code in (301, 302, 303, 307, 308):
                location = feed_resp.headers.get("location", "")
                if "login" in location or "authwall" in location:
                    return {"valid": False, "name": None, "profile_pic": None,
                            "error": "Cookie expirada o inválida. LinkedIn redirige a login."}
                # Redirige a /feed/ u otra URL → cookie válida (puede ser canonical)
                return {"valid": True, "name": None, "profile_pic": None, "error": None}

            if feed_resp.status_code == 200:
                name = _extract_name_from_nav(feed_resp.text)
                pic = _extract_profile_pic(feed_resp.text)
                return {"valid": True, "name": name, "profile_pic": pic, "error": None}

            # Otro código (403 = challenge, 429 = rate limit, etc.)
            if feed_resp.status_code == 403:
                return {"valid": False, "name": None, "profile_pic": None,
                        "error": "LinkedIN devolvió 403. Posible challenge de seguridad."}
            if feed_resp.status_code == 429:
                return {"valid": False, "name": None, "profile_pic": None,
                        "error": "Demasiadas requests. Esperá un momento y reintentá."}

            return {"valid": True, "name": None, "profile_pic": None,
                    "error": f"HTTP {feed_resp.status_code}"}

    except httpx.TimeoutException:
        return {"valid": False, "name": None, "profile_pic": None,
                "error": "Tiempo de espera agotado conectando con LinkedIn"}
    except httpx.ConnectError:
        return {"valid": False, "name": None, "profile_pic": None,
                "error": "No se pudo conectar con LinkedIn. Verifica tu conexión a internet."}
    except Exception as e:
        logger.error(f"Error validando cookies: {e}")
        return {"valid": False, "name": None, "profile_pic": None,
                "error": f"Error inesperado: {str(e)[:100]}"}


# ==============================================================================
# DETECCIÓN DE PAÍS desde cookies
# ==============================================================================

TIMEZONE_TO_COUNTRY = {
    # Sudamérica
    "America/Buenos_Aires": "AR",
    "America/Argentina/": "AR",
    "America/Sao_Paulo": "BR",
    "America/Santiago": "CL",
    "America/Bogota": "CO",
    "America/Lima": "PE",
    "America/Mexico_City": "MX",
    "America/Montevideo": "UY",
    "America/Caracas": "VE",
    "America/La_Paz": "BO",
    "America/Guayaquil": "EC",
    "America/Asuncion": "PY",
    # Norteamérica
    "America/New_York": "US",
    "America/Chicago": "US",
    "America/Los_Angeles": "US",
    "America/Toronto": "CA",
    "America/Vancouver": "CA",
    # Europa
    "Europe/Madrid": "ES",
    "Europe/Lisbon": "PT",
    "Europe/London": "GB",
    "Europe/Paris": "FR",
    "Europe/Berlin": "DE",
    "Europe/Rome": "IT",
    "Europe/Amsterdam": "NL",
    "Europe/Brussels": "BE",
    "Europe/Stockholm": "SE",
    "Europe/Oslo": "NO",
    "Europe/Copenhagen": "DK",
    "Europe/Zurich": "CH",
    "Europe/Vienna": "AT",
    "Europe/Dublin": "IE",
    "Europe/Moscow": "RU",
    # Asia-Pacífico
    "Asia/Tokyo": "JP",
    "Asia/Shanghai": "CN",
    "Asia/Hong_Kong": "HK",
    "Asia/Singapore": "SG",
    "Asia/Seoul": "KR",
    "Asia/Dubai": "AE",
    "Asia/Kolkata": "IN",
    "Australia/Sydney": "AU",
    "Pacific/Auckland": "NZ",
}


def detect_country_from_cookies(raw_cookies: list[dict]) -> str | None:
    """
    Detecta el país de origen de las cookies basado en la cookie 'timezone'
    o en otras señales como 'lang'.
    """
    timezone = None

    for c in raw_cookies:
        name = c.get("name", "")
        value = c.get("value", "")

        if name == "timezone":
            timezone = value
        elif name == "lang":
            # lang: "v=2&lang=es-es" → "es"
            if "lang=" in value:
                lang_code = value.split("lang=")[-1].split("&")[0].split("-")[0]
                LANG_TO_COUNTRY = {
                    "es": "ES", "pt": "PT", "en": "US", "fr": "FR",
                    "de": "DE", "it": "IT", "ja": "JP", "zh": "CN",
                    "ko": "KR", "ar": "AE", "hi": "IN",
                }
                if lang_code in LANG_TO_COUNTRY:
                    return LANG_TO_COUNTRY[lang_code]

    if timezone:
        # Match exact or prefix
        if timezone in TIMEZONE_TO_COUNTRY:
            return TIMEZONE_TO_COUNTRY[timezone]
        for prefix, country in TIMEZONE_TO_COUNTRY.items():
            if timezone.startswith(prefix):
                return country

    return None


# ==============================================================================
# HELPERS DE EXTRACCIÓN
# ==============================================================================

def _extract_name_from_nav(html: str) -> str | None:
    """Extrae el nombre del perfil desde la respuesta de LinkedIn."""
    # Buscar en el miniProfile JSON (más confiable)
    patterns = [
        r'"miniProfile"\s*:\s*{[^}]*"firstName"\s*:\s*"([^"]+)"[^}]*"lastName"\s*:\s*"([^"]+)"',
        r'"firstName"\s*:\s*"([^"]+)"[^}]*"lastName"\s*:\s*"([^"]+)"[^}]*"headline"',
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            first = match.group(1)
            last = match.group(2)
            return f"{first} {last}".strip()

    # Fallback: buscar solo firstName
    match = re.search(r'"firstName"\s*:\s*"([^"]+)"', html)
    if match:
        return match.group(1)

    return None


def _extract_profile_pic(html: str) -> str | None:
    """Extrae URL de foto de perfil si está disponible."""
    match = re.search(
        r'"picture"\s*:\s*{[^}]*"rootUrl"\s*:\s*"([^"]+)"',
        html, re.DOTALL
    )
    if match:
        return match.group(1)
    return None
