# preuenba – LinkedIn Intelligence Hub

> **preuenba** es una plataforma autónoma para gestionar múltiples cuentas de LinkedIn, ejecutar misiones de interacción (comentarios, reacciones, mensajes) y automatizar flujos de trabajo mediante un orquestador basado en **FastAPI** y una interfaz moderna en **Next.js**.

---

## Tabla de contenidos
- [Características principales](#características-principales)
- [Requisitos](#requisitos)
- [Instalación rápida (Docker)](#instalación-rápida-docker)
- [Ejecutar sin Docker (dev local)](#ejecutar-sin-docker-dev-local)
- [Estructura del proyecto](#estructura-del-proyecto)
- [API – Endpoints principales](#api---endpoints-principales)
- [Frontend – Navegación básica](#frontend---navegación-básica)
- [Gestión de cuentas y sesiones](#gestión-de-cuentas-y-sesiones)
- [Misiones y bulk‑missions](#misiones-y-bulk‑missions)
- [Autopilot (programación automática)](#autopilot‑programación-automática)
- [Pruebas](#pruebas)
- [Contribuir](#contribuir)
- [Licencia](#licencia)

---

## Características principales
- **Multi‑cuenta**: administra varias cuentas de LinkedIn con sesiones aisladas.
- **Login guiado con 2FA**: soporte para autenticación en dos pasos.
- **Misiones personalizables**: define listas de tareas (comentario, like, follow, etc.) y ejecútalas de forma concurrente o en lote.
- **Bulk‑missions con AI‑rephrase**: para comentarios masivos, el texto se reformula automáticamente por cuenta.
- **Autopilot**: perfiles objetivo con ventanas horarias y palabras clave de CTA; el motor programa y lanza misiones automáticamente.
- **Dashboard UI**: visualiza cuentas, misiones, logs y métricas en tiempo real.
- **API REST**: FastAPI con documentación automática (OpenAPI).
- **Docker‑Compose**: despliegue de backend y frontend con una sola orden.
- **Test suite**: pruebas unitarias e integradas con `pytest`.

---

## Requisitos
| Herramienta | Versión mínima |
|-------------|----------------|
| **Python** | 3.9+ |
| **Node.js** | 18+ |
| **Docker**  | 20+ (con Docker‑Compose) |
| **Git**     | cualquier versión |

> **Nota:** El proyecto incluye un archivo `.gitignore` que excluye la base de datos SQLite (`orchestrador.db`), dependencias de Python (`venv/`), módulos de Node (`node_modules/`) y archivos temporales.

---

## Instalación rápida (Docker)
1. **Clonar el repositorio** (si aún no lo tienes):
   ```bash
   git clone https://github.com/santiago96ml/sistem_linkedin_autonomo.git
   cd sistem_linkedin_autonomo
   ```
2. **Construir y levantar los contenedores**:
   ```bash
   docker compose up --build -d
   ```
   - El backend escuchará en `http://localhost:8000`.
   - El frontend estará disponible en `http://localhost:3000`.
3. **Abrir la UI** en tu navegador y empezar a registrar cuentas.

---

## Ejecutar sin Docker (dev local)
### Backend
```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r orchestrator-center/backend/requirements.txt

# Ejecutar la API
uvicorn orchestrator-center/backend.main:app --reload --host 0.0.0.0 --port 8000
```
### Frontend
```bash
cd orchestrator-center/frontend
npm install
npm run dev   # por defecto http://localhost:3000
```
---

## Estructura del proyecto
```
preuenba/
│   .gitignore               # reglas de exclusión
│   README.md                # <-- este archivo
│
├─ leadlinked_fusion/        # código de soporte para la API Voyager
├─ linkedin_voice_bot/       # (sub‑repositorio) bot de voz para LinkedIn
├─ orchestrator-center/       # ★ Núcleo de la aplicación
│   ├─ backend/              # FastAPI + lógica de orquestación
│   │   ├─ main.py           # API server
│   │   ├─ models.py         # SQLAlchemy models (Account, Mission, Log…)
│   │   ├─ database.py       # creación del engine y sesión
│   │   ├─ orchestrator.py   # motor de Selenium/Playwright
│   │   └─ autopilot.py      # scheduler de perfiles objetivo
│   ├─ frontend/              # Next.js UI
│   │   └─ src/               # componentes y hooks
│   └─ docker-compose.yml     # definición de servicios
│
└─ scratch/                  # scripts auxiliares de pruebas y depuración
```
---

## API – Endpoints principales
| Método | Ruta | Descripción |
|--------|------|-------------|
| **GET** | `/accounts/` | Lista cuentas (paginado). |
| **POST**| `/accounts/login/start` | Inicia login (2FA opcional). |
| **POST**| `/accounts/login/verify` | Verifica código 2FA y guarda sesión. |
| **POST**| `/missions/` | Crea misión para una cuenta (valida sesión). |
| **POST**| `/missions/bulk` | Crea misiones en lote con delays humanos y opción `ai` para re‑fraseado. |
| **GET** | `/logs/` | Últimos 20 registros del orquestador. |
| **GET** | `/stats` | Métricas resumidas (cuentas totales, misiones activas, tasa de éxito). |
| **GET/POST/PUT/DELETE** | `/autopilot/targets…` | CRUD de perfiles objetivo (URL, horarios, CTA, comentario base). |

La documentación interactiva está disponible en `http://localhost:8000/docs`.
---

## Frontend – Navegación básica
- **/accounts** – Ver lista de cuentas, estado de sesión y botones para iniciar/cerrar sesión.
- **/autopilot** – Gestionar perfiles objetivo y programar su ejecución.
- **/missions** – Ver misiones en curso, crear nuevas y revisar logs.
- **/dashboard** – Estadísticas globales y visualización de métricas.

Los componentes React utilizan el hook `useOrchestrator` (`orchestrator-center/frontend/src/hooks/useOrchestrator.ts`) para consumir la API.
---

## Gestión de cuentas y sesiones
1. **Crear cuenta**: Se registra automáticamente al iniciar sesión con `login/start`.
2. **2FA**: Si LinkedIn solicita código, el frontend mostrará un modal y enviará el código a `/accounts/login/verify`.
3. **TTL de sesión**: Las sesiones inactivas expiran tras **10 min** (configurable en `ACTIVE_LOGIN_TTL_MINUTES`).
4. **Logout**: Eliminando la cuenta o expirando la sesión, el orquestador revoca `storage_state`.
---

## Misiones y bulk‑missions
- Cada misión contiene un **array de tareas** (`type` y `payload`).
- Las tareas soportadas actualmente:
  - `comment` – publicar un comentario.
  - `react` – reaccionar a una publicación.
  - `follow` – enviar solicitud de conexión.
- **Bulk‑missions**: permite lanzar la misma lista de tareas a varias cuentas con:
  - Delays humanos (`delay_min` / `delay_max`).
  - Modo `ai` que re‑frasea el texto del comentario mediante `_rephrase_comment` para evitar detección de contenido duplicado.
---

## Autopilot (programación automática)
1. **Crear perfil objetivo** (`POST /autopilot/targets`).
   - `linkedin_url`: URL del perfil a interactuar.
   - `schedule_start` / `schedule_end`: horario de ejecución (ej. `09:00`‑`18:00`).
   - `cta_keywords`: palabras clave para detectar llamadas a la acción.
   - `comment_base`: texto base usado cuando el modo `ai` está activo.
2. **Activar/pausar**: `PUT /autopilot/targets/{id}/toggle`.
3. **Scheduler**: al iniciar la aplicación (`startup_event`) se lanza `autopilot.start_autopilot_scheduler()` que revisa los perfiles activos y genera misiones automáticamente.
---

## Pruebas
```bash
# Desde la raíz del proyecto
cd orchestrator-center/backend
pytest                # ejecuta la suite completa
```
Los tests están configurados para ejecutarse en **Strict TDD Mode**; cualquier nuevo módulo debe incluir pruebas antes de ser mergeado.
---

## Contribuir
1. **Fork** este repositorio.
2. **Crea una rama** para tu feature o fix (ej. `git checkout -b feature/nueva‑tarea`).
3. **Escribe pruebas** y asegura que `pytest` pasa.
4. **Commitea** siguiendo el formato de *conventional commits*.
5. **Abre un Pull Request** describiendo los cambios y enlazando cualquier issue relacionado.

Para discusiones técnicas y soporte, consulta el canal de *issues* del repositorio.
---

## Licencia
Este proyecto está bajo la licencia **MIT**. Consulta el archivo `LICENSE` para más detalles.
