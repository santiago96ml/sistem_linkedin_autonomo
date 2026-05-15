# Plan de Trabajo — Preuenba v2

>**Account Creation Wizard + Concurrent Mission Execution + WebSocket Log Streaming**

---

## 🚦 Estado Actual (post-auditoría de código)

> El código fue auditado el 14/05/2026. **Gran parte del backend ya está implementado.** 
> Este plan refleja SOLO lo que falta por hacer.

### ✅ Ya Implementado (no tocar)
| Componente | Archivo | Status |
|-----------|---------|--------|
| `LogStreamer` class | `orchestrator.py:5-35` | Completo (subscribe/push/unsubscribe) |
| `PendingLogin` model | `models.py:98-112` | Completo (todos los campos) |
| `ConcurrencyTestResult` model | `models.py:114-127` | Completo |
| `ExecutionLock` model | `models.py:129-137` | Completo |
| `RateLimit` model | `models.py:139-146` | Completo |
| `GuidedLogin` 2FA detection | `orchestrator.py:474-530` | Completo (detecta captcha, email con extracción destino, app, SMS) |
| `POST /test/concurrent` | `main.py` | Completo (asyncio.gather + guarda resultados) |
| Wizard API endpoints | `main.py` | Completo (`/wizard/start`, `/wizard/status/{id}`, `/wizard/verify`) |
| `ConcurrentTestRequest` model | `main.py` | Completo |

### ❌ Pendiente de Implementar
| Componente | Prioridad | Depende de |
|-----------|-----------|-----------|
| `AccountWizard.tsx` (Frontend) | 🔴 Alta | Nada |
| `LiveLogViewer.tsx` + `useMissionLogs` hook | 🟡 Media | LogStreamer (ya existe) |
| Modal test concurrencia (Frontend) | 🟡 Media | `/test/concurrent` (ya existe) |
| `BrowserPool` class | 🟡 Media | Nada |
| DB Safeguards (with_for_update + ExecutionLock) | 🟡 Media | Nada |
| WS `/ws/logs/{mission_id}` | 🟡 Media | LogStreamer (ya existe) |
| Integrar LogStreamer en `run_mission_task` | 🟡 Media | LogStreamer (ya existe) |
| Tests (pytest TDD) | 🟢 Baja | Todas las anteriores |
| Migrar `active_logins` dict → PendingLogin | 🟢 Baja | Nada |

---

## TL;DR

> **Resumen**: Implementar 3 features mayores en el sistema de automatización LinkedIn preuenba: (1) un asistente visual para registrar cuentas con detección automática de 2FA, (2) un sistema para ejecutar misiones concurrentes con botón en dashboard y safeguards posteriores, (3) streaming de logs en tiempo real vía WebSocket.

> **Entregables**:
> - Wizard de creación de cuentas (API FastAPI + UI Next.js)
> - Botón de test de concurrencia + safeguards (DB locks, BrowserPool, rate limiting)
> - Canal WebSocket de logs + visor en vivo en frontend
> - Suite completa de tests (pytest, strict TDD)

> **Esfuerzo estimado**: Grande (3 features, multi-capas)
> **Ejecución paralela**: SÍ — 3 tracks paralelos divididos entre Frontend y Backend
> **Ruta crítica**: Modelo PendingLogin → GuidedLogin mejorado → API Wizard → UI Wizard

---

## Contexto

### Solicitud original
El usuario solicitó implementar 3 features en el sistema preuenba (LinkedIn Intelligence Hub):

1. **Account Creation Wizard**: Flujo guiado paso a paso para registrar cuentas LinkedIn. El usuario provee email+contraseña, el sistema intenta login automático vía Playwright. Si LinkedIn pide verificación 2FA, el sistema detecta si es código por email o authenticator app, muestra al usuario DÓNDE se envió el código, y le permite ingresarlo.
2. **Concurrent Mission Execution**: Botón en el dashboard para lanzar N misiones en paralelo a través de múltiples cuentas y observar resultados. Primero TEST para ver comportamiento, LUEGO implementar safeguards (DB locks, BrowserPool, rate limiting).
3. **Real-time WebSocket Log Streaming**: Stream de logs de misión desde el orquestador (FastAPI) al dashboard (Next.js) en vivo mediante WebSocket dedicado.

### Resumen de decisiones

| Decisión | Opción | Razón |
|----------|--------|-------|
| **Alcance** | 3 features en UNA iteración | Entregables independientes |
| **2FA** | Email + Authenticator App | LinkedIn usa ambos |
| **TDD** | Strict TDD (pytest) | Ya configurado en el proyecto |
| **Escala** | 20+ cuentas | Diseño desde el inicio |
| **Concurrencia** | Test primero → Safeguards después | Entender comportamiento real antes de optimizar |
| **Logs WS** | Canal dedicado /ws/logs/{mission_id} | Separado del screencast existente |

---

## Objetivos del Trabajo

### Objetivo Central
Implementar 3 features que lleven el sistema preuenba de un MVP funcional a una plataforma robusta lista para 20+ cuentas con experiencia de usuario guiada, ejecución concurrente segura, y visibilidad en tiempo real.

### Deliverables Concretos
- [ ] Account Creation Wizard funcional (API + Frontend)
- [ ] Test de concurrencia con botón en dashboard
- [ ] Safeguards: DB locks, BrowserPool, rate limiting
- [ ] WebSocket de logs + visor en vivo en frontend
- [ ] Suite completa de tests (pytest, TDD)

### Definición de Done
- [ ] `pytest` pasa todos los tests (nuevos + existentes)
- [ ] Se puede registrar una cuenta desde el frontend en < 2 minutos
- [ ] El botón de test concurrente lanza N misiones y muestra resultados
- [ ] Los logs aparecen en vivo en el dashboard sin recargar página
- [ ] Sistema funciona con 20+ cuentas registradas
- [ ] BrowserPool limita a N instancias concurrentes sin crash

### Must Have
- Detección automática de tipo 2FA (email vs authenticator app)
- Mostrar al usuario qué email recibió el código de verificación
- Botón funcional en dashboard para test de concurrencia
- WebSocket de logs que no interfiere con el screencast existente
- Tests para toda funcionalidad nueva (TDD estricto)
- Manejo de errores: credenciales inválidas, código 2FA incorrecto, expiración

### Must NOT Have (Guardrails)
- NO cambiar la infraestructura de autenticación del dashboard
- NO modificar el sistema de screencast existente `/ws/live/{id}`
- NO agregar AI/LLM más allá del rephrase existente
- NO tocar la configuración de Docker/deployment
- NO cambiar el modelo Account existente (solo extender con nuevos modelos)
- NO agregar billing/suscripciones

---

## Estrategia de Verificación

> **CERO intervención humana** — toda verificación es ejecutada por el agente. Criterios de aceptación que requieran "el usuario verifica manualmente" están PROHIBIDOS.

### Decisión de Tests
- **Infraestructura existe**: SÍ (pytest, pytest.ini en root)
- **Tests automatizados**: TDD estricto (RED → GREEN → REFACTOR)
- **Framework**: pytest + pytest-asyncio
- **Estrategia**: Cada tarea incluye test primero (RED), luego implementación (GREEN), luego refactor

### Política QA
Cada tarea INCLUYE escenarios QA ejecutados por agente:
- **API/Backend**: Bash (curl) — enviar requests, afirmar status + response body
- **Frontend**: Playwright — navegar, interactuar, afirmar DOM, screenshot
- **WebSocket**: Bash + herramientas WS — conectar, recibir mensajes, afirmar contenido
- **Browser**: Playwright — lanzar browser, verificar comportamiento

Evidencia guardada en `.sisyphus/evidence/task-{N}-{scenario}.{ext}`

---

## Estrategia de Ejecución

### Olas de Ejecución Paralela

```
Wave 1 (Fundación — Modelos + Tests):
├── T1: Modelo PendingLogin + test [quick]
├── T2: Modelo ConcurrencyTestResult + test [quick]
├── T3: Modelo ExecutionLock + test [quick]
├── T4: Modelo RateLimit + test [quick]
├── T5: LogStreamer class + test [unspecified-high]
└── T6: Test concurrent endpoint + test [quick]

Wave 2 (Core Backend — APIs + Lógica):
├── T7: GuidedLogin 2FA detection mejorada [deep]
├── T8: API Wizard endpoints (start/verify/status/cancel) [unspecified-high]
├── T9: BrowserPool class [unspecified-high]
├── T10: DB Safeguards (with_for_update, retry) [quick]
├── T11: Rate limiting middleware [quick]
└── T12: WebSocket /ws/logs/{mission_id} [unspecified-high]

Wave 3 (Frontend — UI Components):
├── T13: AccountWizard.tsx (stepper 3 pasos) [visual-engineering]
├── T14: Ruta /wizard + botón "Nueva Cuenta" [visual-engineering]
├── T15: LiveLogViewer.tsx [visual-engineering]
├── T16: useMissionLogs hook [unspecified-high]
├── T17: Modal test de concurrencia [visual-engineering]
└── T18: Integrar log viewer en wizard + missions [visual-engineering]

Wave 4 (Integración + Safeguards):
├── T19: Safeguard wrapping (integrar BrowserPool + Locks + RateLimit en run_mission_task) [deep]
├── T20: Integrar LogStreamer en run_mission_task + MissionRunner [unspecified-high]
├── T21: Test de integración: wizard flow completo [unspecified-high]
└── T22: Cleanup: migrar active_logins dict a PendingLogin DB [quick]

Wave FINAL (Verificación):
├── F1: Plan Compliance Audit (oracle)
├── F2: Code Quality Review (unspecified-high)
├── F3: Real Manual QA (unspecified-high)
└── F4: Scope Fidelity Check (deep)
```

### Matriz de Dependencias

```
T1-T6: Independientes (Wave 1, paralelo total)
T7: Depende de T1 (PendingLogin)
T8: Depende de T7 (GuidedLogin mejorado)
T9: Independiente de T1-T6 (puede correr en Wave 1 o 2)
T10: Independiente
T11: Depende de T4 (RateLimit model)
T12: Depende de T5 (LogStreamer)
T13: Depende de T8 (API Wizard)
T14: Depende de T13
T15: Depende de T12 (WS Logs)
T16: Depende de T12
T17: Depende de T6 (concurrent test endpoint)
T18: Depende de T15+T16
T19: Depende de T9+T10+T11
T20: Depende de T12+T5
T21: Depende de T8+T14+T13 (wizard completo)
T22: Depende de T1+T8
```

---

## TODOs

---

### Wave 1 — Fundación (Modelos + Tests)

---

- [ ] **T1. Modelo `PendingLogin` + Tests (TDD)**

  **Qué hacer**:
  1. **RED**: Escribir test `test_pending_login.py`:
     - `test_create_pending_login()` — crear registro, verificar campos
     - `test_expire_after_ttl()` — crear con TTL, verificar que expira
     - `test_failed_attempts_limit()` — llegar a 5 intentos, verificar locked
     - `test_status_transitions()` — pending → 2fa_email → success, pending → expired
  2. **GREEN**: Crear modelo SQLAlchemy `PendingLogin` en `models.py`:
     - `id` (Integer, PK)
     - `email` (String)
     - `password_encrypted` (String — cifrado básico, no plain text)
     - `proxy_url` (String, nullable)
     - `status` (String: pending/2fa_email/2fa_app/success/expired)
     - `code_sent_to` (String, nullable — email donde LinkedIn envió el código)
     - `storage_state` (JSON, nullable)
     - `failed_attempts` (Integer, default=0)
     - `created_at` (DateTime)
     - `expires_at` (DateTime — TTL de 10 min)
  3. **REFACTOR**: Limpiar, asegurar type hints

  **Perfil de agente recomendado**:
  - **Categoría**: `quick`
  - **Skills**: `fastapi-standard`, `pytest-tdd`
  - **Razón**: Creación de modelo SQLAlchemy simple + tests unitarios. Baja complejidad.

  **Paralelización**:
  - **Puede correr en paralelo**: SÍ (con T2-T6)
  - **Ola**: Wave 1
  - **Bloquea**: T7, T8, T22
  - **Bloqueado por**: Nada (puede empezar inmediatamente)

  **Criterios de Aceptación**:
  - `test_pending_login.py` pasa (tests RED → GREEN)
  - Modelo `PendingLogin` existe en `models.py` con todos los campos
  - Expiración automática: registros con `expires_at < now()` son tratados como expirados
  - Límite de 5 intentos: al llegar a 5 failed_attempts, status → "locked"

  **Escenarios QA**:
  ```
  Escenario: Crear PendingLogin exitosamente
    Tool: Bash (python -c "from models import PendingLogin; ...")
    Preconditions: Base de datos vacía
    Steps:
      1. Importar modelo y SessionLocal
      2. Crear PendingLogin(email="test@test.com", status="pending", ...)
      3. Commit y refrescar
      4. Assert: id no es None, created_at no es None
    Expected Result: Registro creado con todos los campos correctos
    Evidence: .sisyphus/evidence/task-1-create-pending-login.txt

  Escenario: Expiración por TTL
    Tool: Bash
    Preconditions: PendingLogin con expires_at en el pasado
    Steps:
      1. Crear PendingLogin con expires_at = (now - 1 minuto)
      2. Consultar: select * where status != 'expired' and expires_at < now
      3. Marcar como expired
      4. Assert: status ahora es 'expired'
    Expected Result: Registro expirado correctamente
    Evidence: .sisyphus/evidence/task-1-expire-ttl.txt
  ```

  **Commit**: SÍ (agrupado con T2-T6)
  - Mensaje: `feat(models): add PendingLogin, ConcurrencyTestResult, ExecutionLock, RateLimit models`
  - Archivos: `orchestrator-center/backend/models.py`, `tests/test_pending_login.py`, `tests/test_concurrency_result.py`, `tests/test_execution_lock.py`, `tests/test_rate_limit.py`

---

- [ ] **T2. Modelo `ConcurrencyTestResult` + Tests (TDD)**

  **Qué hacer**:
  1. **RED**: Escribir tests para modelo de resultados de test de concurrencia
  2. **GREEN**: Modelo SQLAlchemy:
     - `id` (Integer, PK)
     - `test_run_id` (String, UUID para agrupar resultados de un mismo test)
     - `account_id` (Integer, FK → accounts.id)
     - `account_email` (String)
     - `mission_id` (Integer, nullable)
     - `task_type` (String: comment/reaction/follow)
     - `result` (String: 200/error/ALREADY_LIKED/etc)
     - `duration_ms` (Integer — tiempo de ejecución)
     - `error_message` (Text, nullable)
     - `timestamp` (DateTime)
  3. **REFACTOR**

  **Perfil**: `quick`
  **Skills**: `fastapi-standard`, `pytest-tdd`

---

- [ ] **T3. Modelo `ExecutionLock` + Tests (TDD)**

  **Qué hacer**:
  1. **RED**: Tests para lock de ejecución por cuenta
     - `test_lock_account()` — crear lock para account_id, verificar que existe
     - `test_release_lock()` — liberar lock, verificar que se eliminó
     - `test_double_lock_fails()` — intentar lockear cuenta ya lockeada debe fallar
  2. **GREEN**: Modelo SQLAlchemy:
     - `id` (Integer, PK)
     - `account_id` (Integer, unique — una cuenta = un lock)
     - `mission_id` (Integer)
     - `acquired_at` (DateTime)
     - `ttl_seconds` (Integer, default=600 — 10 min timeout)
  3. **REFACTOR**

  **Perfil**: `quick`
  **Skills**: `fastapi-standard`, `pytest-tdd`

---

- [ ] **T4. Modelo `RateLimit` + Tests (TDD)**

  **Qué hacer**:
  1. **RED**: Tests para rate limiting
     - `test_within_limit()` — 5 acciones en 1h, límite 10 → ok
     - `test_exceeds_limit()` — 11 acciones en 1h, límite 10 → bloqueado
     - `test_window_expires()` — acciones viejas (>1h) no cuentan
  2. **GREEN**: Modelo SQLAlchemy:
     - `id` (Integer, PK)
     - `account_id` (Integer, FK)
     - `action_type` (String: comment/reaction/connect)
     - `action_count` (Integer)
     - `window_start` (DateTime)
  3. **REFACTOR**

  **Perfil**: `quick`
  **Skills**: `fastapi-standard`, `pytest-tdd`

---

- [ ] **T5. `LogStreamer` class + Tests (TDD)**

  **Qué hacer**:
  1. **RED**: Tests para LogStreamer
     - `test_push_and_consume()` — pushear log, consumir del stream, verificar contenido
     - `test_multiple_consumers()` — dos consumidores reciben los mismos logs
     - `test_cleanup_on_complete()` — al completar misión, queue se limpia
     - `test_queue_overflow()` — más de 1000 logs no rompen nada
  2. **GREEN**: Clase `LogStreamer` en `orchestrator.py`:
     - `_queues: dict[int, asyncio.Queue]` — una queue por mission_id
     - `subscribe(mission_id) → asyncio.Queue` — crear o reusar queue
     - `push(mission_id, log_entry: dict)` — pushear a queue
     - `unsubscribe(mission_id)` — limpiar queue al completar
     - Auto-limpieza de queues huérfanas (más de 30 min sin actividad)
  3. **REFACTOR**

  **Perfil**: `unspecified-high`
  **Skills**: `fastapi-standard`, `pytest-asyncio`
  **Razón**: Lógica asyncio con queues concurrentes, gestión de ciclo de vida

  **Paralelización**:
  - **Ola**: Wave 1
  - **Bloquea**: T12, T20
  - **Bloqueado por**: Nada

---

- [ ] **T6. Endpoint test de concurrencia + Tests (TDD)**

  **Qué hacer**:
  1. **RED**: Tests para `POST /test/concurrent`
     - `test_concurrent_launch()` — lanzar 3 misiones, verificar que se crearon
     - `test_concurrent_results()` — verificar que los resultados se guardan en ConcurrencyTestResult
     - `test_invalid_accounts()` — cuenta inexistente → 404
  2. **GREEN**: Endpoint en `main.py`:
     - `POST /test/concurrent` con body: `{account_ids: List[int], task_template: dict, concurrency_level: int}`
     - Validar cuentas existen y tienen sesión activa
     - Crear N misiones en DB (una por cuenta)
     - Lanzarlas con `asyncio.gather()` (sin delays, a propósito)
     - Guardar resultados en `ConcurrencyTestResult`
     - Retornar `{test_run_id, results: [{account_id, mission_id, result, duration_ms}]}`
  3. **REFACTOR**

  **Perfil**: `quick`
  **Skills**: `fastapi-standard`, `pytest-tdd`

  **Escenarios QA**:
  ```
  Escenario: Lanzar test concurrente con 2 cuentas
    Tool: Bash (curl)
    Preconditions: 2 cuentas activas en DB con storage_state
    Steps:
      1. curl -X POST /test/concurrent -H "Content-Type: application/json" -d '{"account_ids": [1,2], "task_template": {"type": "reaction", "payload": {"url": "...", "reaction_type": "LIKE"}}, "concurrency_level": 2}'
      2. Assert: status 200
      3. Assert: response.test_run_id no es None
      4. Assert: response.results tiene 2 entries
      5. Assert: cada entry tiene account_id, mission_id, result, duration_ms
    Expected Result: Test lanzado, resultados guardados en ConcurrencyTestResult
    Evidence: .sisyphus/evidence/task-6-concurrent-test.txt
  ```

---

### Wave 2 — Core Backend (APIs + Lógica)

---

- [ ] **T7. GuidedLogin: detección de tipo 2FA (TDD)**

  **Qué hacer**:
  1. **RED**: Tests para detección de 2FA
     - `test_detect_2fa_email()` — mockear página con `input[name='pin']`, verificar que detecta email
     - `test_detect_2fa_app()` — mockear página con `input[autocomplete='one-time-code']`, verificar que detecta app
     - `test_extract_sent_to_email()` — mockear texto del challenge "We sent a code to j***@gmail.com", extraer destino
     - `test_no_2fa_direct_success()` — mockear redirección a /feed → success directo
  2. **GREEN**: Modificar `GuidedLogin.start()` en `orchestrator.py`:
     - Después de submit, esperar 5s
     - Detectar si hay campo de PIN (2FA)
       - `input[name='pin']` → código por email
       - `input[autocomplete='one-time-code']` → authenticator app
     - Si es email: scrapear texto del challenge para extraer "código enviado a: X"
       - Buscar texto como `"We sent a code to"`, `"Enviamos un código a"`, `"código a"`
       - Extraer el email/phone usando regex
     - Retornar: `{"status": "2fa_email", "sent_to": "j***@gmail.com"}` o `{"status": "2fa_app"}` o `{"status": "success"}`
  3. **REFACTOR**

  **Perfil**: `deep`
  **Skills**: `fastapi-standard`, `pytest-tdd`, `playwright`
  **Razón**: Requiere análisis de selectores reales de LinkedIn, múltiples variantes de texto del challenge, lógica de scraping condicional

  **Escenarios QA**:
  ```
  Escenario: Detectar 2FA por email en página de LinkedIn
    Tool: Playwright
    Preconditions: Página de challenge de LinkedIn mockeada con input[name='pin']
    Steps:
      1. Navegar a página mock de 2FA email
      2. Ejecutar GuidedLogin.start()
      3. Assert: retorna {"status": "2fa_email", "sent_to": "...@..."}
    Expected Result: Sistema detecta correctamente que es 2FA email
    Evidence: .sisyphus/evidence/task-7-detect-2fa-email.png
  ```

---

- [ ] **T8. API Wizard endpoints + Tests (TDD)**

  **Qué hacer**:
  1. **RED**: Tests para endpoints wizard
     - `test_wizard_start_success()` — mockear GuidedLogin que retorna success → cuenta creada
     - `test_wizard_start_2fa_email()` — mockear GuidedLogin que retorna 2fa_email → PendingLogin creado
     - `test_wizard_verify_success()` — mockear submit_code() que retorna storage_state → cuenta activa
     - `test_wizard_verify_wrong_code()` — código incorrecto → failed_attempts++ → retry
     - `test_wizard_verify_max_attempts()` — 5 intentos fallidos → locked
     - `test_wizard_status()` — GET /wizard/status/{id} → estado actual
     - `test_wizard_cancel()` — POST /wizard/cancel/{id} → marca expired + cleanup
  2. **GREEN**: Endpoints en `main.py`:
     - `POST /wizard/start`:
       - Recibe `{email, password, proxy_url?, name?}`
       - Cifra password (cifrado básico, no plain text)
       - Crea `PendingLogin` en DB
       - Ejecuta `GuidedLogin` mejorado
       - Si success: guarda Account directo, limpia PendingLogin
       - Si 2FA: actualiza PendingLogin.status + code_sent_to, retorna pending_login_id
       - Retorna: `{status, pending_login_id?, account_id?, code_sent_to?}`
     - `POST /wizard/verify`:
       - Recibe `{pending_login_id, code}`
       - Busca PendingLogin, verifica no expirado ni locked
       - Ejecuta `GuidedLogin.submit_code(code)`
       - Si éxito: crea/actualiza Account, limpia PendingLogin, retorna account_id
       - Si falla: incrementa failed_attempts, si llega a 5 → locked
     - `GET /wizard/status/{pending_login_id}`:
       - Retorna estado actual del PendingLogin
     - `POST /wizard/cancel/{pending_login_id}`:
       - Marca como expired, libera recursos
  3. **REFACTOR**

  **Perfil**: `unspecified-high`
  **Skills**: `fastapi-standard`, `pytest-tdd`

  **Escenarios QA**:
  ```
  Escenario: Wizard completo con 2FA email (simulado)
    Tool: Bash (curl)
    Preconditions: Mock de GuidedLogin que retorna 2fa_email
    Steps:
      1. curl -X POST /wizard/start -d '{"email":"test@test.com","password":"pass123"}'
      2. Assert: status = "2fa_email", pending_login_id no es None, code_sent_to contiene "@"
      3. curl -X POST /wizard/verify -d '{"pending_login_id": "...", "code": "123456"}'
      4. Assert: status = "success", account_id no es None
      5. curl -X GET /accounts/ | grep test@test.com
      6. Assert: cuenta existe con status = "active"
    Expected Result: Cuenta creada exitosamente a través del wizard
    Evidence: .sisyphus/evidence/task-8-wizard-flow.txt
  ```

---

- [ ] **T9. `BrowserPool` class + Tests (TDD)**

  **Qué hacer**:
  1. **RED**: Tests para BrowserPool
     - `test_acquire_release()` — adquirir browser del pool, liberarlo, verificar contador
     - `test_max_instances()` — intentar adquirir más del límite → wait en cola
     - `test_timeout_release()` — browser que excede timeout se libera automáticamente
     - `test_concurrent_acquire()` — N tareas adquieren y liberan concurrentemente
  2. **GREEN**: Clase `BrowserPool` en `orchestrator.py`:
     - `__init__(max_instances=5, instance_ttl=600)`
     - `acquire(account_id, storage_state, proxy_url) → BrowserInstance`
     - `release(account_id)` — libera al pool
     - `_cleanup_stale()` — limpia instancias que excedieron TTL
     - `get_metrics()` — instancias activas, en espera, adquiridas hoy
     - Reemplazar `BrowserManager._instances` dict global con `BrowserPool`
  3. **REFACTOR**

  **Perfil**: `unspecified-high`
  **Skills**: `fastapi-standard`, `pytest-asyncio`

  **Escenarios QA**:
  ```
  Escenario: Pool limita a 2 instancias concurrentes
    Tool: Bash (python -c "...")
    Preconditions: BrowserPool(max_instances=2)
    Steps:
      1. Adquirir instancia A (account_id=1)
      2. Adquirir instancia B (account_id=2)
      3. Intentar adquirir instancia C (account_id=3) con timeout=0.1
      4. Assert: C lanza TimeoutError (cola llena)
      5. Liberar A
      6. Adquirir C (debería funcionar ahora)
      7. Assert: acquire exitoso
    Expected Result: Pool respeta límite de instancias
    Evidence: .sisyphus/evidence/task-9-browser-pool.txt
  ```

---

- [ ] **T10. DB Safeguards — with_for_update + retry (TDD)**

  **Qué hacer**:
  1. **RED**: Tests para safeguards
     - `test_increment_action_count_concurrent()` — 2 hilos incrementan a la vez, sin race condition
     - `test_execution_lock_prevents_duplicate()` — misma cuenta no puede tener 2 misiones
  2. **GREEN**:
     - Función `_safe_increment_action_count(account_id, db)`:
       - Usa `db.query(Account).with_for_update().filter(Account.id == account_id).first()`
       - Incrementa `daily_action_count`
       - Retry lógico si hay SQLite lock (hasta 3 intentos con backoff)
     - Función `_acquire_execution_lock(account_id, mission_id, db)`:
       - Inserta en `ExecutionLock`, si ya existe → la misión espera
       - `_release_execution_lock(account_id, db)` al completar
     - Modificar `run_mission_task()` para usar ambas funciones
  3. **REFACTOR**

  **Perfil**: `quick`
  **Skills**: `fastapi-standard`, `pytest-tdd`

---

- [ ] **T11. Rate Limiting middleware + Tests (TDD)**

  **Qué hacer**:
  1. **RED**: Tests para rate limiting
     - `test_check_rate_limit_ok()` — dentro del límite → permite
     - `test_check_rate_limit_blocked()` — excede límite → bloquea
     - `test_window_rotation()` — nueva ventana después de 1h → resetea contador
  2. **GREEN**:
     - Función `check_rate_limit(account_id, action_type, db) → bool`
     - Consulta `RateLimit` para la ventana actual
     - Si excede → retorna False (misión se pone en "queued")
     - Si ok → incrementa contador
  3. **REFACTOR**

  **Perfil**: `quick`
  **Skills**: `fastapi-standard`, `pytest-tdd`

---

- [ ] **T12. WebSocket `/ws/logs/{mission_id}` + Tests (TDD)**

  **Qué hacer**:
  1. **RED**: Tests para WS logs
     - `test_ws_log_stream()` — conectar a WS, pushear logs, verificar que llegan
     - `test_ws_invalid_mission()` — mission_id inexistente → 404
     - `test_ws_cleanup_on_disconnect()` — al desconectar, queue se limpia
  2. **GREEN**: Endpoint WebSocket en `main.py`:
     - `ws /ws/logs/{mission_id}`
     - Aceptar conexión
     - Suscribirse al `LogStreamer` para esa mission_id
     - Loop: recibir logs de la queue → enviar al websocket
     - Al desconectar: unsubscribe
     - Formato mensaje: `{timestamp, level, message, task_type?}`
  3. **REFACTOR**

  **Perfil**: `unspecified-high`
  **Skills**: `fastapi-standard`, `pytest-asyncio`

  **Escenarios QA**:
  ```
  Escenario: Logs fluyen en tiempo real por WebSocket
    Tool: Bash (websocat o script Python)
    Preconditions: Misión activa con ID conocido
    Steps:
      1. ws = connect("/ws/logs/1")
      2. Pushear log "Iniciando misión" al LogStreamer
      3. Recibir mensaje de ws
      4. Assert: message contiene "Iniciando misión"
    Expected Result: Log aparece en WebSocket en < 1s
    Evidence: .sisyphus/evidence/task-12-ws-logs.txt
  ```

---

### Wave 3 — Frontend (UI Components)

---

- [ ] **T13. `AccountWizard.tsx` — Componente stepper 3 pasos**

  **Qué hacer**:
  1. Crear componente React del wizard:
     - **Paso 1 — Credenciales**: Formulario con:
       - Campo email (validación formato email)
       - Campo password (mostrar/ocultar)
       - Campo proxy (opcional, colapsable)
       - Campo "nombre para identificar" (opcional)
       - Botón "Iniciar Sesión"
     - **Paso 2 — Autenticando**: Pantalla de progreso con:
       - Spinner animado
       - Logs en vivo del GuidedLogin (usa `useMissionLogs`)
       - Texto "Iniciando sesión en LinkedIn..." con ellipsis animado
     - **Paso 3a — Éxito**: Pantalla verde con:
       - Checkmark animado
       - "✅ Cuenta X registrada exitosamente"
       - Botón "Ir a Cuentas"
       - Botón "Registrar Otra"
     - **Paso 3b — 2FA Email**: Pantalla con:
       - "📧 Código de verificación enviado"
       - Texto destacado: `"Te enviamos un código a: usuario@email.com"`
       - Input para código (6 dígitos, auto-focus, auto-submit al completar)
       - Botón "Verificar"
       - Contador de reintentos restantes
       - Link "Reenviar código?" (simulado)
     - **Paso 3c — 2FA App**: Similar pero con:
       - "🔐 Verificación de dos pasos"
       - "Ingresa el código de tu app de autenticación:"
       - Input + botón "Verificar"
  2. Manejo de errores:
     - Credenciales inválidas → mensaje rojo, volver a paso 1
     - Código incorrecto → "Código incorrecto. Te quedan N intentos."
     - Sesión expirada → "El tiempo de verificación expiró. Inicia de nuevo."
     - Error de red → "Error de conexión. Reintentando..."
  3. Integración con API:
     - Llamar a `POST /wizard/start`
     - Hacer polling a `GET /wizard/status/{id}` durante paso 2
     - Llamar a `POST /wizard/verify`

  **Perfil**: `visual-engineering`
  **Skills**: `nextjs-react`, `frontend-ui-ux`
  **Razón**: UI pulida con animaciones, estados de carga, transiciones suaves

  **Escenarios QA**:
  ```
  Escenario: Wizard paso 1 → paso 2 (login exitoso sin 2FA)
    Tool: Playwright
    Preconditions: API mockeada para retornar success directo
    Steps:
      1. Navegar a /wizard
      2. Assert: formulario visible (email input, password input, botón)
      3. Llenar email: "test@test.com"
      4. Llenar password: "password123"
      5. Click "Iniciar Sesión"
      6. Assert: paso 2 visible con spinner
      7. Esperar 3s (mock success)
      8. Assert: paso 3a visible con "Cuenta registrada exitosamente"
    Expected Result: Flujo completo sin 2FA funciona desde UI
    Evidence: .sisyphus/evidence/task-13-wizard-no-2fa.png

  Escenario: Wizard paso 2 → paso 3b (2FA email)
    Tool: Playwright
    Preconditions: API mockeada para retornar 2fa_email
    Steps:
      1. Repetir login como arriba
      2. Assert: paso 3b visible
      3. Assert: texto contiene "código a:" o "envió un código a"
      4. Assert: email enmascarado visible (ej: "t***@test.com")
      5. Llenar input código: "123456"
      6. Click "Verificar"
      7. Assert: paso 3a visible (éxito)
    Expected Result: Usuario ve dónde se envió el código, puede ingresarlo
    Evidence: .sisyphus/evidence/task-13-wizard-2fa.png
  ```

---

- [ ] **T14. Ruta `/wizard` + botón "Nueva Cuenta"**

  **Qué hacer**:
  1. Crear página `/app/wizard/page.tsx` que renderiza `AccountWizard`
  2. Agregar botón "➕ Nueva Cuenta" en página `/accounts`:
     - Botón primario, visible en header o junto a la lista
     - `onClick → router.push('/wizard')`
  3. Layout limpio: centrado, mismo diseño dark/glassmorphism del dashboard

  **Perfil**: `visual-engineering`
  **Skills**: `nextjs-react`

---

- [ ] **T15. `LiveLogViewer.tsx` — Componente de logs en vivo**

  **Qué hacer**:
  1. Componente React:
     - Terminal-like: fondo oscuro (#0a0a0a), fuente monospace
     - Scroll automático al último log
     - Colores por nivel:
       - `info` → blanco/gris claro
       - `success` → verde (#00ff88)
       - `warning` → amarillo (#ffaa00)
       - `error` → rojo (#ff4444)
     - Timestamp en formato `[HH:MM:SS]` al inicio de cada línea
     - Badge con tipo de tarea (opcional)
  2. Props:
     - `missionId: number` — se conecta automáticamente al WebSocket
     - `height?: string` — altura del componente (default: "300px")
     - `filter?: string` — filtrar por nivel (opcional)
     - `maxLines?: number` — máximo de líneas en memoria (default: 500)
  3. Estados:
     - **Conectando**: "Conectando al stream de logs..."
     - **Conectado**: logs fluyendo
     - **Desconectado**: "Conexión perdida. Reintentando..."
     - **Vacío**: "Esperando logs..." cuando no hay actividad

  **Perfil**: `visual-engineering`
  **Skills**: `nextjs-react`, `frontend-ui-ux`

---

- [ ] **T16. `useMissionLogs` hook**

  **Qué hacer**:
  1. Hook React personalizado:
     - `useMissionLogs(missionId: number | null) → { logs: LogEntry[], connected: boolean, error: string | null }`
     - Conecta a WebSocket `ws://localhost:8000/ws/logs/{missionId}`
     - Reconexión automática (exponential backoff: 1s, 2s, 4s, max 30s)
     - Buffer de logs en memoria (max 1000 líneas)
     - Cleanup al desmontar el componente
     - Tipo `LogEntry: { timestamp: string, level: string, message: string }`
  2. Funcionalidad extra:
     - `sendCommand(type: string, data: any)` — opcional, para control del stream

  **Perfil**: `unspecified-high`
  **Skills**: `nextjs-react`

---

- [ ] **T17. Modal test de concurrencia**

  **Qué hacer**:
  1. Modal con:
     - **Selectbox "Cuentas"**: multi-select con todas las cuentas activas
     - **Selectbox "Tipo de Misión"**: comment / reaction / follow
     - **Input URL**: URL del post de LinkedIn para la misión
     - **Slider "Nivel de Concurrencia"**: 1-10, con valor actual mostrado
     - **Botón "🚀 Lanzar Test"**: primary, grande
     - **Sección Resultados** (después del test):
       - Tabla con columnas: Cuenta, Misión, Resultado, Duración, Estado
       - Resultado coloreado: verde (200), amarillo (ALREADY_LIKED), rojo (error)
       - Resumen: "N/N misiones completadas en X segundos"
  2. UX:
     - Loading state mientras las misiones corren
     - Logs en vivo integrados (LiveLogViewer) para cada misión
     - Botón "Descargar Reporte" que exporta resultados como JSON

  **Perfil**: `visual-engineering`
  **Skills**: `nextjs-react`, `frontend-ui-ux`

  **Escenarios QA**:
  ```
  Escenario: Abrir modal, configurar y lanzar test
    Tool: Playwright
    Preconditions: 2 cuentas activas en DB
    Steps:
      1. Navegar a /missions
      2. Click botón "🧪 Test de Concurrencia"
      3. Assert: modal visible
      4. Seleccionar 2 cuentas en el multi-select
      5. Seleccionar "reaction" como tipo
      6. Ingresar URL de post
      7. Set slider a 2
      8. Click "🚀 Lanzar Test"
      9. Assert: tabla de resultados aparece
      10. Assert: cada cuenta tiene resultado
    Expected Result: Test lanzado y resultados visibles
    Evidence: .sisyphus/evidence/task-17-concurrent-modal.png
  ```

---

- [ ] **T18. Integrar LogViewer en wizard + missions**

  **Qué hacer**:
  1. Integrar `LiveLogViewer` en el wizard (Paso 2):
     - Mostrar logs del GuidedLogin en vivo
     - Que el usuario vea "Navegando a LinkedIn...", "Ingresando credenciales...", etc.
  2. Integrar en página de detalle de misión `/missions/[id]`:
     - Agregar `LiveLogViewer` que se conecta automáticamente al missionId
     - Debajo de la info de la misión
  3. Integrar múltiples `LiveLogViewer` en el modal de concurrencia:
     - Un panel por misión (o un panel consolidado)

  **Perfil**: `visual-engineering`
  **Skills**: `nextjs-react`

---

### Wave 4 — Integración + Safeguards

---

- [ ] **T19. Safeguard wrapping — Integrar BrowserPool + Locks + RateLimit**

  **Qué hacer**:
  1. Modificar `run_mission_task()` en `main.py`:
     - **Rate Limit**: antes de ejecutar, verificar `check_rate_limit()`. Si excede → poner misión en "queued"
     - **Execution Lock**: `_acquire_execution_lock()` antes de ejecutar, `_release_execution_lock()` al finalizar
     - **BrowserPool**: en lugar de lanzar browser nuevo cada vez, usar `BrowserPool.acquire()`
     - **Action Count**: `_safe_increment_action_count()` en lugar de incremento directo
  2. Manejo de errores:
     - Si lock acquisition falla → retry con backoff (3 intentos)
     - Si rate limit bloquea → log claro + misión en "queued"
     - Si BrowserPool timeout → error claro

  **Perfil**: `deep`
  **Skills**: `fastapi-standard`, `pytest-tdd`
  **Razón**: Integración compleja de múltiples sistemas, edge cases de concurrencia real

  **Escenarios QA**:
  ```
  Escenario: Rate limit bloquea misión
    Tool: Bash (curl)
    Preconditions: Cuenta con rate limit excedido
    Steps:
      1. curl -X POST /missions/ -d '{"account_id": 1, "tasks": [{"type": "reaction", ...}]}'
      2. Assert: status 200 (misión creada)
      3. curl -X GET /missions/ | grep "queued"
      4. Assert: misión en estado "queued"
      5. Assert: log contiene "rate limit exceeded"
    Expected Result: Misión encolada, no bloquea el sistema
    Evidence: .sisyphus/evidence/task-19-rate-limit.txt
  ```

---

- [ ] **T20. Integrar LogStreamer en run_mission_task + MissionRunner**

  **Qué hacer**:
  1. Modificar `run_mission_task()`:
     - Al iniciar: `LogStreamer.subscribe(mission_id)`
     - En cada paso: `LogStreamer.push(mission_id, {timestamp, level, message})`
     - Al completar: `LogStreamer.push(mission_id, {level: "success", message: "Misión completada"})`
     - Al fallar: `LogStreamer.push(mission_id, {level: "error", message: error})`
     - Al final: `LogStreamer.unsubscribe(mission_id)`
  2. Modificar `MissionRunner._run_on_page()`:
     - Aceptar `log_streamer` opcional
     - Pushear logs por cada tarea: "Iniciando tarea comment...", "Navegando a URL...", etc.
  3. Integrar con el endpoint WS existente

  **Perfil**: `unspecified-high`
  **Skills**: `fastapi-standard`

---

- [ ] **T21. Tests de integración — Wizard flow completo**

  **Qué hacer**: Tests de integración que cubran:
  1. Wizard flow: start → detect 2FA email → verify code → account created
  2. Wizard flow: start → direct success → account created
  3. Wizard flow: start → 2FA app → verify code → account created
  4. Wizard error: invalid credentials → error message
  5. Wizard error: max 2FA attempts → locked
  6. Concurrent test: launch N → all complete → results saved
  7. WebSocket logs: subscribe → logs arrive → unsubscribe → cleanup

  **Perfil**: `unspecified-high`
  **Skills**: `pytest-tdd`, `pytest-asyncio`

---

- [ ] **T22. Cleanup: Migrar `active_logins` dict a `PendingLogin` DB**

  **Qué hacer**:
  1. Eliminar `active_logins` dict global y `active_logins_lock` de `main.py`
  2. Eliminar `_cleanup_expired_logins()` función
  3. Refactorizar `start_login()` y `verify_login()` endpoints existentes para usar `PendingLogin`
  4. Mantener retrocompatibilidad: los endpoints viejos siguen funcionando pero usan la nueva tabla
  5. **Importante**: No romper el login directo/sin 2FA actual

  **Perfil**: `quick`
  **Skills**: `fastapi-standard`

---

## Wave Final — Verificación

---

- [ ] **F1. Plan Compliance Audit** — `oracle`

  Leer el plan completo. Para cada "Must Have": verificar que existe implementación (leer archivos, correr endpoints). Para cada "Must NOT Have": buscar en código patrones prohibidos. Verificar archivos de evidencia existen en `.sisyphus/evidence/`.

  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

---

- [ ] **F2. Code Quality Review** — `unspecified-high`

  - Correr `pytest` — todos los tests pasan
  - Revisar: `as any`/`@ts-ignore`, `console.log` en prod, código comentado, imports sin usar
  - Verificar convenciones del proyecto (type hints, docstrings, etc.)

  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | VERDICT`

---

- [ ] **F3. Real Manual QA** — `unspecified-high` (+ `playwright`)

  Ejecutar CADA escenario QA de CADA tarea (T1-T22) siguiendo pasos exactos:
  - Wizard flow sin 2FA
  - Wizard flow con 2FA email
  - Wizard flow con 2FA app
  - Concurrent test con 3 cuentas
  - Logs en vivo en dashboard
  - Rate limiting (exceder límite)
  - BrowserPool (exceder instancias)
  - DB locks (2 misiones simultáneas misma cuenta)

  Output: `Scenarios [N/N pass] | Integration [N/N] | VERDICT`

---

- [ ] **F4. Scope Fidelity Check** — `deep`

  Verificar 1:1 — todo lo especificado fue construido, nada extra fue añadido. Verificar "Must NOT do" compliance. Detectar contaminación cross-task.

  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | VERDICT`

---

## Estrategia de Commits

| Grupo | Mensaje | Archivos |
|-------|---------|----------|
| T1-T6 | `feat(models): add PendingLogin, ConcurrencyTestResult, ExecutionLock, RateLimit, LogStreamer` | models.py, tests/ |
| T7 | `feat(orchestrator): detect 2FA type (email vs authenticator app) in GuidedLogin` | orchestrator.py, tests/ |
| T8 | `feat(api): add wizard endpoints (start/verify/status/cancel)` | main.py, tests/ |
| T9 | `feat(orchestrator): add BrowserPool with max instances limit` | orchestrator.py, tests/ |
| T10+T11 | `feat(db): add execution locks and rate limiting safeguards` | main.py, models.py, tests/ |
| T12 | `feat(api): add /ws/logs/{mission_id} WebSocket endpoint` | main.py, tests/ |
| T13+T14 | `feat(ui): add AccountWizard component with 3-step flow` | frontend/src/ |
| T15+T16 | `feat(ui): add LiveLogViewer and useMissionLogs hook` | frontend/src/ |
| T17 | `feat(ui): add concurrent test modal to dashboard` | frontend/src/ |
| T18 | `feat(ui): integrate log viewer in wizard and mission pages` | frontend/src/ |
| T19+T20 | `feat(core): integrate safeguards and LogStreamer into mission execution` | main.py, orchestrator.py |
| T21 | `test: add integration tests for wizard, concurrent, and logs` | tests/ |
| T22 | `refactor: migrate active_logins dict to PendingLogin DB model` | main.py |

---

## Criterios de Éxito

### Comandos de Verificación
```bash
# Tests
cd orchestrator-center/backend
pytest -v  # Todos los tests pasan

# API Wizard
curl -X POST http://localhost:8000/wizard/start -H "Content-Type: application/json" -d '{"email":"test@test.com","password":"pass123"}'
# → {"status": "2fa_email" | "success", "pending_login_id": ..., "code_sent_to": "..."}

curl -X POST http://localhost:8000/wizard/verify -H "Content-Type: application/json" -d '{"pending_login_id": 1, "code": "123456"}'
# → {"status": "success", "account_id": 1}

# Concurrent test
curl -X POST http://localhost:8000/test/concurrent -H "Content-Type: application/json" -d '{"account_ids": [1,2], "task_template": {"type": "reaction", "payload": {"url": "...", "reaction_type": "LIKE"}}, "concurrency_level": 2}'
# → {"test_run_id": "...", "results": [...]} (en < 30s)

# Stats
curl http://localhost:8000/stats
# → {"total_identities": 20+, "active_missions": 0, "success_rate": 95}
```

### Checklist Final
- [ ] **Wizard**: Registrar cuenta completa desde frontend en < 2 min
- [ ] **Wizard 2FA Email**: Detecta, muestra destino, acepta código
- [ ] **Wizard 2FA App**: Detecta, pide código, acepta código
- [ ] **Wizard Errores**: Credenciales inválidas, expiración, límite intentos
- [ ] **Concurrent Test**: Botón funcional, resultados en tabla
- [ ] **Safeguards**: DB locks, BrowserPool, rate limit funcionan
- [ ] **Logs WS**: Logs aparecen en vivo sin recargar
- [ ] **Tests**: `pytest` pasa todo (nuevos + existentes)
- [ ] **Escala**: Sistema funcional con 20+ cuentas registradas
