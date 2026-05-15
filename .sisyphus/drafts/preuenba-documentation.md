# Preuenba — LinkedIn Intelligence Hub

**Documentación completa del sistema**

> Plataforma autónoma para gestionar múltiples cuentas de LinkedIn, ejecutar misiones de interacción (comentarios, reacciones), automatizar flujos con piloto automático y asignar proxies residenciales por geolocalización — todo sin pagar servicios externos de proxy.

---

## Tabla de Contenidos

1. [Arquitectura del Sistema](#1-arquitectura-del-sistema)
2. [Requisitos](#2-requisitos)
3. [Instalación y Despliegue](#3-instalación-y-despliegue)
4. [Estructura del Proyecto](#4-estructura-del-proyecto)
5. [Autenticación y Cuentas](#5-autenticación-y-cuentas)
   - 5.1 Login Manual (credenciales + 2FA)
   - 5.2 Importar Cookies desde Extensión Chrome
   - 5.3 Wizard Unificado
6. [Sistema de Proxies](#6-sistema-de-proxies)
   - 6.1 Proxy Pool con Geolocalización
   - 6.2 Instalación de Proxies en VPS (Oracle Free Tier)
   - 6.3 Health Check Automático
   - 6.4 Auto-Asignación por País
7. [Misiones](#7-misiones)
   - 7.1 Tipos de Tareas
   - 7.2 Bulk Missions con AI Rephrase
   - 7.3 Rate Limiting y Execution Locks
8. [Piloto Automático (AutoPilot)](#8-piloto-automático-autopilot)
9. [BrowserPool y Sesiones en Vivo](#9-browserpool-y-sesiones-en-vivo)
10. [API REST Completa](#10-api-rest-completa)
11. [Frontend — Interfaz de Usuario](#11-frontend--interfaz-de-usuario)
12. [Pruebas](#12-pruebas)
13. [Solución de Problemas](#13-solución-de-problemas)
14. [Roadmap / Próximos Pasos](#14-roadmap--próximos-pasos)

---

## 1. Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                   LinkedIn Intelligence Hub                  │
├──────────────────┬──────────────────┬───────────────────────┤
│   Frontend       │   Backend        │   Infraestructura     │
│   (Next.js 16)   │   (FastAPI)      │   Externa             │
├──────────────────┼──────────────────┼───────────────────────┤
│  Dashboard       │  main.py         │  VPS Oracle Cloud     │
│  Account         │  (API REST)      │  (microsocks SOCKS5)  │
│  Registry        │                  │                       │
│  Missions        │  orchestrator.py │  LinkedIn (target)    │
│  AutoPilot       │  (Playwright)    │                       │
│  Live View       │                  │                       │
│  Proxies         │  cookie_importer │  Chrome Extension     │
│  Command Center  │  .py             │  (cookies export)     │
└──────────────────┴──────────────────┴───────────────────────┘
                   │                  │
                   └──────────────────┘
                          SQLite DB
                    (orchestrator.db)
                   - accounts
                   - proxies          ← NUEVO
                   - missions
                   - logs
                   - autopilot targets
                   - warmup configs
```

### Flujo de Datos

```
Usuario → UI (React) → API (FastAPI) → DB (SQLite)
                                     → Playwright (LinkedIn)
                                     → Proxy Pool (SOCKS5)
```

### Stack Tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Backend | Python + FastAPI | 3.14+ / FastAPI |
| Frontend | Next.js + React + Tailwind | 16.2.4 / 19.2 / 4 |
| Base de datos | SQLite vía SQLAlchemy | SQLAlchemy 2.0 |
| Browser automation | Playwright (Chromium) | 1.52+ |
| HTTP client | httpx | para validación directa |
| UI icons | lucide-react | 1.11+ |
| Proxy SOCKS5 | microsocks (VPS Linux) | Open source |

---

## 2. Requisitos

### Mínimos

| Herramienta | Versión mínima | Para qué |
|-------------|---------------|----------|
| **Python** | 3.9+ | Backend (FastAPI) |
| **Node.js** | 18+ | Frontend (Next.js) |
| **npm** | cualquier | Instalar dependencias frontend |
| **Git** | cualquier | Control de versiones |
| **Playwright browsers** | Chromium | Automatización LinkedIn |

### Opcionales (para proxies)

| Herramienta | Para qué |
|-------------|----------|
| **Cuenta Oracle Cloud Free Tier** | VPS gratis en múltiples regiones |
| **SSH client** | Conectar a VPS para instalar proxy |
| **Paramiko** (pip) | Instalación automatizada vía Python |

---

## 3. Instalación y Despliegue

### 3.1 Instalación Local (Desarrollo)

#### Backend

```bash
# 1. Clonar o ubicarse en el proyecto
cd preuenba

# 2. Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\activate  # Windows

# 3. Instalar dependencias
cd orchestrator-center/backend
pip install -r requirements.txt

# 4. Instalar navegador Playwright
playwright install chromium

# 5. Iniciar servidor
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd orchestrator-center/frontend
npm install
npm run dev  # http://localhost:3000
```

#### Variables de Entorno

El frontend usa `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3.2 Despliegue con Docker

```bash
docker compose up --build -d
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

### 3.3 Despliegue en Producción (recomendado)

```
VPS 1 (Backend + Frontend)
  ├── Backend: systemd + uvicorn
  ├── Frontend: nginx + next start
  ├── SQLite: orchestrator.db
  └── Playwright: chromium-headless-shell

VPS 2..N (Proxies SOCKS5)
  └── microsocks (ver sección 6.2)
```

---

## 4. Estructura del Proyecto

```
preuenba/
├── .sisyphus/                    # Planes y drafts
├── orchestrator-center/
│   ├── backend/
│   │   ├── main.py               # ★ API FastAPI (todos los endpoints)
│   │   ├── models.py             # ★ Modelos SQLAlchemy
│   │   ├── database.py           # Conexión SQLite
│   │   ├── orchestrator.py       # ★ Playwright: BrowserPool, MissionRunner, GuidedLogin, etc.
│   │   ├── cookie_importer.py    # ★ Conversión + validación de cookies + detección país
│   │   ├── proxy_pool.py         # ★ Sistema de proxies con geolocalización
│   │   ├── autopilot.py          # Piloto automático scheduler
│   │   ├── scripts/
│   │   │   ├── install_proxy.sh  # Script bash para VPS Linux
│   │   │   └── install_proxy.py  # Instalación vía SSH con Paramiko
│   │   └── tests/                # 119 tests
│   └── frontend/
│       └── src/
│           ├── app/page.tsx      # ★ Hub principal con wizard integrado
│           ├── components/
│           │   ├── views/
│           │   │   ├── AccountsView.tsx
│           │   │   ├── ProxiesView.tsx    # ★ Panel de proxies (NUEVO)
│           │   │   ├── MissionsView.tsx
│           │   │   └── ...
│           │   ├── AccountWizard.tsx
│           │   └── CookieImporter.tsx
│           └── hooks/useOrchestrator.ts
└── README.md
```

---

## 5. Autenticación y Cuentas

### 5.1 Login Manual (Credenciales + 2FA)

**Flujo completo:**

```
1. Usuario ingresa email + contraseña en el wizard
2. POST /accounts/login/start → inicia GuidedLogin en Playwright
3. GuidedLogin:
   a. Abre linkedin.com/login
   b. Detecta versión del formulario (clásico #username o React autocomplete)
   c. Llena credenciales
   d. Hace clic en "Sign in" vía JavaScript
   e. Espera redirección
4. Si hay 2FA:
   a. Detecta tipo: email, app autenticadora, SMS
   b. Guarda sesión en active_logins (TTL: 10 min)
   c. Usuario ingresa código → POST /accounts/login/verify
   d. submit_code() envía el PIN
5. Si login exitoso:
   a. Guarda storage_state en la Account
   b. Account.status = "active"
```

**Manejo de errores:**
- Hasta 5 intentos de 2FA (seguridad anti-fuerza bruta)
- TTL de 10 min para sesiones de login
- Captcha detectado → "needs_captcha"
- Contraseña incorrecta → "failed"

### 5.2 Importar Cookies desde Extensión Chrome

**Cuándo usarlo:** Cuando tenés cookies ya autenticadas desde un navegador real (Chrome con extensión exportadora de cookies como "Get cookies.txt" o "EditThisCookie").

**Flujo completo:**

```
1. Usuario pega JSON de cookies en el wizard
2. POST /accounts/cookies/validate
3. convert_to_storage_state():
   a. Convierte formato extensión → Playwright storage_state
   b. Mapea sameSite ("no_restriction" → "None")
   c. Normaliza dominios (.linkedin.com)
   d. Maneja cookies de sesión (expires = -1)
4. validate_storage_state():
   a. Construye cliente httpx con las cookies
   b. GET a linkedin.com/feed/ (sin abrir navegador, ~2s)
   c. Si HTTP 200 → cookies válidas
   d. Si redirección a /login → cookies expiradas
   e. Si 403/429 → bloqueo temporal
5. detect_country_from_cookies():  ← NUEVO
   a. Lee cookie "timezone" (ej: "America/Buenos_Aires")
   b. Mapea a código ISO (AR, BR, US, etc.)
   c. Fallback: cookie "lang" (es → ES, pt → PT)
6. POST /accounts/cookies → crea Account con storage_state
7. Auto-asignación de proxy: si hay proxy del país detectado, lo asigna
```

**Formato de cookies esperado (desde extensión Chrome):**
```json
[
  {
    "domain": ".www.linkedin.com",
    "expirationDate": 1810392523,
    "httpOnly": true,
    "name": "li_at",
    "path": "/",
    "sameSite": "no_restriction",
    "secure": true,
    "value": "AQED..."
  },
  {
    "domain": ".linkedin.com",
    "name": "timezone",
    "value": "America/Buenos_Aires"
  }
]
```

**Cookies requeridas:**
- `li_at`: cookie de autenticación principal (obligatoria)
- `JSESSIONID`: usada como csrf-token para validación
- `timezone`: usada para detectar país (opcional, mejora auto-asignación)

### 5.3 Wizard Unificado

El wizard de vinculación unifica ambos métodos en un solo flujo:

```
Vincular Nueva
├── Inicio de Sesión Manual
│   ├── Email
│   ├── Contraseña
│   ├── Proxy (opcional)
│   └── → Login + 2FA si requiere
│
└── Importar Cookies
    ├── Pegar JSON de cookies
    ├── Validar (contra LinkedIn)
    ├── País detectado (mostrado en UI)
    ├── Nombre de cuenta
    └── → Guardar cuenta + auto-asignar proxy
```

---

## 6. Sistema de Proxies

### 6.1 Proxy Pool con Geolocalización

**¿Por qué?** LinkedIn detecta cuando una cuenta accede desde IPs de distintos países y puede bloquearla. Cada cuenta necesita una IP que coincida con su ubicación geográfica.

**Modelo en DB (`proxies` tabla):**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer | Primary key |
| name | String | Etiqueta: "Oracle BR", "VPS US" |
| host | String | IP del VPS |
| port | Integer | Puerto SOCKS5 (default: 1080) |
| username | String | Auth opcional |
| password | String | Auth opcional |
| protocol | String | socks5 (default) o http |
| country | String | Código ISO: "BR", "AR", "US" |
| city | String | Ciudad: "São Paulo" |
| is_active | Boolean | Habilitado? |
| is_online | Boolean | Último health check |
| last_health_check | DateTime | Último ping |
| assigned_account_id | Integer | FK → accounts.id |

**Propiedades calculadas:**
- `url`: `socks5://user:pass@host:port` (con auth si aplica)
- `short_url`: `socks5://host:port` (sin credenciales)

**Arquitectura del Pool:**

```python
# proxy_pool.py

class ProxyPool:
    # Obtener todos los proxies
    get_all(db, active_only=True) → [Proxy]
    
    # Obtener disponibles (no asignados)
    get_available(db, country=None) → [Proxy]
    
    # Obtener proxy de una cuenta
    get_for_account(db, account_id) → Proxy | None
    
    # Asignar proxy a cuenta
    assign_to_account(db, proxy_id, account_id) → Proxy
      → actualiza account.proxy_url
    
    # Desasignar
    unassign(db, account_id)
    
    # Auto-asignar (elige el mejor proxy disponible)
    auto_assign(db, account_id, country) → Proxy | None
    
    # Health check
    check_proxy_health(proxy) → bool
    
    # Health check masivo
    run_health_checks(db) → {total, online, offline}
    
    # Estadísticas
    get_stats(db) → {total, active, online, assigned, by_country}
```

### 6.2 Instalación de Proxies en VPS

#### Opción A: Script bash manual

```bash
# Conectarse al VPS y ejecutar:
ssh root@1.2.3.4 'bash -s' < scripts/install_proxy.sh --port 1080 --user proxy --pass MiPassSegura

# Sin autenticación (solo firewall por IP):
ssh root@1.2.3.4 'bash -s' < scripts/install_proxy.sh --no-auth
```

**Qué hace el script:**
1. Instala build-essential, git, ufw
2. Clona y compila microsocks (SOCKS5 server en C, ~200 líneas)
3. Si usa auth: compila plugin de autenticación
4. Configura systemd service (auto-inicio, restart automático)
5. Abre puerto en firewall
6. Muestra URL del proxy

#### Opción B: Script Python vía SSH

```bash
pip install paramiko
python scripts/install_proxy.py --host 1.2.3.4 --user root --port 1080
```

#### Opción C: Manual

```bash
# En el VPS:
apt update && apt install build-essential git ufw -y
git clone https://github.com/rofl0r/microsocks.git
cd microsocks && make
cp microsocks /usr/local/bin/

# Ejecutar:
microsocks -i 0.0.0.0 -p 1080 -A /etc/microsocks_passwd

# O sin auth (solo firewall):
microsocks -i 0.0.0.0 -p 1080
```

#### Obteniendo VPS Gratis (Oracle Cloud)

1. Crear cuenta en **Oracle Cloud Free Tier** (https://www.oracle.com/cloud/free/)
2. Crear una instancia ARM (4 OCPU, 24 GB RAM — siempre gratis)
3. Elegir región según necesidad: São Paulo (BR), US East, Germany, etc.
4. Anotar IP pública
5. Ejecutar script de instalación
6. **Repetir con distintas cuentas Oracle para tener IPs en varios países**

Cada cuenta Oracle da: 2 instancias AMD + hasta 4 ARM = ~6 IPs.

### 6.3 Health Check Automático

Sin dependencia de curl — usa handshake SOCKS5 nativo en Python.

**Cómo funciona:**
1. Para SOCKS5: conexión TCP + handshake SOCKS5 (RFC 1928)
   - Negocia método de autenticación
   - Si aplica: autenticación usuario/contraseña (RFC 1929)
   - UDP ASSOCIATE para verificar conectividad
2. Para HTTP: httpx con proxy configurado
3. Tiempo máximo: 10 segundos por proxy

**Endpoint:**
```bash
POST /proxies/health-check
# Respuesta: {"total": 3, "online": 2, "offline": 1, "details": [...]}
```

**Frecuencia recomendada:** cada 5 minutos (la UI tiene botón manual, se puede automatizar con cron/task).

### 6.4 Auto-Asignación por País

Cuando se importan cookies (POST /accounts/cookies), el sistema automáticamente:

1. **Detecta el país** desde las cookies (timezone → código ISO)
2. **Busca un proxy disponible** de ese país
3. **Asigna** el proxy a la cuenta recién creada
4. **Actualiza** `account.proxy_url`

**Mapa de timezone → país soportado (>30 países):**

| Timezone | País | Código |
|----------|------|--------|
| America/Buenos_Aires | Argentina | AR |
| America/Sao_Paulo | Brasil | BR |
| America/Santiago | Chile | CL |
| America/Mexico_City | México | MX |
| America/Bogota | Colombia | CO |
| America/Lima | Perú | PE |
| America/New_York | Estados Unidos | US |
| Europe/Madrid | España | ES |
| Europe/Lisbon | Portugal | PT |
| +20 más... | | |

**Si no hay proxy del país detectado:** la cuenta se crea igual sin proxy (se puede asignar manualmente después desde la UI).

---

## 7. Misiones

### 7.1 Tipos de Tareas

| Tipo | Descripción | Payload |
|------|-------------|---------|
| `comment` | Publica comentario en post | `{url, text}` |
| `reaction` | Reacciona (Like) a post | `{url, reaction_type}` |
| `check_notifications` | Scrapea notificaciones | `{}` |
| `smart_comment` | Detecta CTA o comenta | `{url, target_profile_id}` |

### 7.2 Bulk Missions con AI Rephrase

```bash
POST /missions/bulk
{
  "account_ids": [1, 2, 3],
  "tasks": [{"type": "comment", "payload": {"url": "...", "text": "Excelente contenido!"}}],
  "comment_mode": "ai",
  "delay_min": 30,
  "delay_max": 120
}
```

El modo `ai` reformula el comentario para cada cuenta usando:
- Mapa de sinónimos en español/inglés/portugués
- Variación de opening y closing
- Seed determinista por account_id (mismo texto ≠ mismo resultado)

### 7.3 Rate Limiting y Execution Locks

**Rate limiting:** por cuenta y tipo de acción
- Cuentas en warmup: 10 acciones/hora
- Cuentas normales: 50 acciones/hora

**Execution locks:** previene ejecución simultánea en misma cuenta
- Lock automático al iniciar misión
- TTL: 10 minutos
- Se libera al completar o fallar

---

## 8. Piloto Automático (AutoPilot)

El AutoPilot monitorea perfiles objetivo y ejecuta misiones automáticamente.

### Perfiles Objetivo

```json
{
  "linkedin_url": "https://www.linkedin.com/in/perfil/",
  "schedule_start": "09:00",
  "schedule_end": "18:00",
  "cta_keywords": "comenta,escribe,opina",
  "comment_base": "Excelente aporte!"
}
```

### Ciclo del Scheduler

```
1. Cada 5 minutos: revisa perfiles activos
2. Para cada perfil en ventana horaria:
   a. Visita linkedin.com/in/perfil/
   b. Busca nuevas publicaciones
   c. Analiza texto para detectar CTA keywords
   d. Si hay CTA: comenta con la keyword exacta
   e. Si no: genera comentario con AI rephrase
3. Cada 15 minutos: revisa notificaciones (comentarios nuevos)
4. Si detecta interacción en comentario propio: responde
```

### Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/autopilot/status` | Estado actual del scheduler |
| GET | `/autopilot/targets` | Lista perfiles objetivo |
| POST | `/autopilot/targets` | Crear perfil |
| PUT | `/autopilot/targets/{id}/toggle` | Activar/pausar |
| DELETE | `/autopilot/targets/{id}` | Eliminar |

---

## 9. BrowserPool y Sesiones en Vivo

### BrowserPool

Gestiona instancias persistentes de Chromium:
- **Máximo:** 5 instancias simultáneas
- **TTL:** 10 minutos sin uso
- **Timeout de adquisición:** 30 segundos
- **Proxy por instancia:** se pasa automáticamente desde Account.proxy_url

### Sesiones en Vivo (Command Center)

- Transmisión en vivo de la pantalla del navegador vía WebSocket
- Control remoto: clicks, tecleo, navegación
- Usa Page.startScreencast para captura JPEG a 60% calidad
- CDP (Chrome DevTools Protocol) para control en tiempo real

### BrowserManager

Cachea páginas abiertas por account_id para acceso rápido desde Live View.

---

## 10. API REST Completa

### Cuentas y Autenticación

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/accounts/` | Listar cuentas |
| DELETE | `/accounts/{id}` | Eliminar cuenta |
| PUT | `/accounts/{id}/warmup/toggle` | Activar/desactivar warmup |
| POST | `/accounts/login/start` | Iniciar login (credenciales) |
| POST | `/accounts/login/verify` | Verificar código 2FA |
| POST | `/accounts/cookies/validate` | Validar cookies (sin guardar) |
| POST | `/accounts/cookies` | Importar cookies + crear cuenta |
| GET | `/accounts/{id}/notifications` | Obtener notificaciones |
| POST | `/accounts/{id}/live` | Activar sesión en vivo |
| GET | `/accounts/{id}/proxy` | Obtener proxy asignado |

### Proxies (NUEVO)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/proxies/` | Listar proxies |
| POST | `/proxies/` | Añadir proxy |
| PUT | `/proxies/{id}` | Actualizar proxy |
| DELETE | `/proxies/{id}` | Eliminar proxy |
| POST | `/proxies/{id}/assign` | Asignar a cuenta |
| POST | `/proxies/{id}/unassign` | Desasignar de cuenta |
| POST | `/proxies/auto-assign` | Auto-asignar por país |
| POST | `/proxies/health-check` | Health check masivo |
| GET | `/proxies/stats` | Estadísticas del pool |

### Misiones

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/missions/` | Listar misiones |
| POST | `/missions/` | Crear misión |
| POST | `/missions/bulk` | Misiones en lote |
| POST | `/test/concurrent` | Test de concurrencia |

### Sistema

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/stats` | Estadísticas globales |
| GET | `/logs/` | Últimos logs |
| GET | `/` | Health check del servidor |
| WS | `/ws/logs/{mission_id}` | Logs en tiempo real |
| WS | `/ws/live/{account_id}` | Sesión en vivo |

### Wizard

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/wizard/start` | Iniciar wizard login |
| GET | `/wizard/status/{id}` | Estado del wizard |
| POST | `/wizard/verify` | Verificar 2FA en wizard |

---

## 11. Frontend — Interfaz de Usuario

### Páginas / Tabs

| Tab | Función |
|-----|---------|
| **Dashboard** | Estadísticas: cuentas, misiones activas, tasa de éxito, logs recientes |
| **Command Center** | Control remoto en vivo de cuentas |
| **Account Registry** | Lista de cuentas + botón "Vincular Nueva" |
| **Warmup Lab** | Estado de calentamiento de cuentas |
| **Missions** | Crear y monitorear misiones |
| **Piloto Automático** | Gestionar perfiles objetivo y scheduler |
| **Interacciones** | Notificaciones detectadas |
| **Live View** | Transmisión en vivo de navegadores |
| **Proxies** | Gestionar pool de proxies (NUEVO) |
| **Security** | Logs de seguridad |

### Componentes Clave

| Componente | Ubicación | Función |
|------------|-----------|---------|
| `ProxiesView` | `components/views/ProxiesView.tsx` | Panel de proxies con stats, lista, asignación |
| `AccountWizard` | `components/AccountWizard.tsx` | Wizard de login por credenciales |
| `CookieImporter` | `components/CookieImporter.tsx` | Importador de cookies standalone |
| `LiveLogViewer` | `components/LiveLogViewer.tsx` | Visualizador de logs WebSocket |
| `CommandHub` | `app/page.tsx` | Hub principal con sidebar y vistas |

### Hook `useOrchestrator`

Hook central que maneja:
- Polling de datos cada 5 segundos
- Fetch de accounts, missions, logs, stats, targets, autopilot status
- CRUD de cuentas y perfiles objetivo

---

## 12. Pruebas

119 tests — 100% passing.

### Cobertura

| Archivo de test | Tests | Cubre |
|----------------|-------|-------|
| `test_autopilot.py` | 28 | Scheduler, CTA detection, comment rephrase |
| `test_browser_pool.py` | 3 | Browser pool lifecycle |
| `test_concurrency_result.py` | 1 | Modelo de resultados concurrentes |
| `test_concurrent_endpoint.py` | 2 | Endpoint de test concurrente |
| `test_cookie_endpoints.py` | 12 | Validate e import endpoints |
| `test_cookie_importer.py` | 31 | Conversión, validación, extracción |
| `test_db_safeguards.py` | 3 | Execution locks, rate limits |
| `test_execution_lock.py` | 3 | Lock/unlock tests |
| `test_integration.py` | 5 | Integración de safegards |
| `test_log_streamer.py` | 4 | WebSocket log streaming |
| `test_pending_login.py` | 4 | Pending login model |
| **`test_proxy_pool.py`** | **19** | **Proxy CRUD, asignación, auto-assign, health check (NUEVO)** |
| `test_rate_limit.py` | 2 | Rate limit model |
| `test_wizard_endpoints.py` | 2 | Wizard flow |

### Ejecutar tests

```bash
cd orchestrator-center/backend
pytest                    # Suite completa
pytest -v                 # Modo verboso
pytest tests/test_proxy_pool.py  # Solo proxy tests
```

---

## 13. Solución de Problemas

### Problema: "No se puede conectar al backend"
```
Causa: El servidor FastAPI no está corriendo
Solución: uvicorn main:app --host 0.0.0.0 --port 8000
```

### Problema: "Playwright error — browser closed"
```
Causa: Playwright browsers no instalados
Solución: playwright install chromium
```

### Problema: "Proxy health check fails"
```
Causa: VPS apagado, firewall bloqueando, microsocks no corriendo
Verificar:
  ssh user@vps systemctl status microsocks
  ssh user@vps ufw status
  Telnet: telnet vps-ip 1080  # debería conectar
```

### Problema: "Cookies inválidas"
```
Causa: li_at cookie expirada (LinkedIn expires session cookies)
Solución: Exportar cookies frescas desde Chrome
```

### Problema: "WS log: No supported WebSocket library detected"
```
Causa: Falta websockets package
Solución: pip install websockets
```

### Problema: "LinkedIn login falla — selector no encontrado"
```
Causa: LinkedIn cambió el HTML del login (A/B testing)
Solución: El código ya maneja #username y autocomplete="username"
          Si falla, capturar screenshot: screenshots/login_failed_{email}.png
```

### Problema: "No hay proxies disponibles"
```
Causa: Pool de proxies vacío
Solución: 
  1. Crear VPS en Oracle Cloud o cualquier servidor
  2. Ejecutar scripts/install_proxy.sh
  3. Añadir proxy en UI → Proxies → Añadir Proxy
```

---

## 14. Roadmap / Próximos Pasos

### ✅ Completado
- [x] Login manual con detección 2FA (email, app, SMS)
- [x] Importación de cookies desde extensión Chrome
- [x] Wizard unificado (ambos métodos en un solo flujo)
- [x] Proxy pool con geolocalización
- [x] Auto-asignación de proxy por país
- [x] Health check de proxies sin curl
- [x] Panel UI de proxies en frontend
- [x] Detección de país desde timezone cookie
- [x] 119 tests (100% passing)

### 🔜 Próximas mejoras posibles
- [ ] Soporte para HTTP/HTTPS además de SOCKS5
- [ ] Rotación automática de proxies
- [ ] Más modos de detección de país (GeoIP)
- [ ] Panel de monitoreo de proxies (uptime, latencia)
- [ ] Notificaciones cuando un proxy se cae
- [ ] Exportación de configuración de proxies

---

*Documentación generada el 15 de mayo de 2026*
*Proyecto: Preuenba — LinkedIn Intelligence Hub*
