import sys
import asyncio
import logging
import base64

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- WINDOWS ASYNCIO FIX (CRITICAL FOR PLAYWRIGHT SUBPROCESSES) ---
if sys.platform == 'win32':
    try:
        from asyncio import WindowsProactorEventLoopPolicy
        # Set the policy globally
        asyncio.set_event_loop_policy(WindowsProactorEventLoopPolicy())
        logger.info("Enforced WindowsProactorEventLoopPolicy at module level")
    except ImportError:
        logger.error("Could not import WindowsProactorEventLoopPolicy")
# ------------------------------------------------

def _simple_encrypt(text: str) -> str:
    key = 0x5A
    encoded = ''.join(chr(ord(c) ^ key) for c in text)
    return base64.b64encode(encoded.encode()).decode()

def _simple_decrypt(encrypted: str) -> str:
    key = 0x5A
    decoded = base64.b64decode(encrypted.encode()).decode()
    return ''.join(chr(ord(c) ^ key) for c in decoded)

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import models, database, orchestrator, cookie_importer, proxy_pool
import os
import uuid
from database import engine, get_db, SessionLocal
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
import datetime
import traceback
import json

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="LinkedIn Orchestrator API")

@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_event_loop()
    logger.info(f"Running with event loop: {type(loop).__name__}")
    if sys.platform == 'win32' and type(loop).__name__ != 'ProactorEventLoop':
        logger.warning("WARNING: Not using ProactorEventLoop! Subprocesses (Playwright) will fail.")

    # Start the autopilot scheduler loop in the background
    import autopilot
    asyncio.create_task(autopilot.start_autopilot_scheduler())
    logger.info("AutoPilot scheduler task created.")

# Enable CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global dictionary to store active login sessions {email: {manager, created_at}}
import threading
active_logins = {}
active_logins_lock = threading.Lock()
ACTIVE_LOGIN_TTL_MINUTES = 10  # Bug Fix #5: TTL para evitar sessions huérfanas

def _cleanup_expired_logins():
    """Elimina active_logins que superaron el TTL."""
    now = datetime.datetime.utcnow()
    expired = [
        email for email, data in active_logins.items()
        if (now - data["created_at"]).total_seconds() > ACTIVE_LOGIN_TTL_MINUTES * 60
    ]
    for email in expired:
        del active_logins[email]

class AccountBase(BaseModel):
    name: str
    email: str
    proxy_url: Optional[str] = None

class AccountCreate(AccountBase):
    pass

class Account(AccountBase):
    id: int
    status: str
    model_config = ConfigDict(from_attributes=True)

class MissionBase(BaseModel):
    account_id: Optional[int] = None
    tasks: List[dict]

class Mission(MissionBase):
    id: int
    status: str
    source: str = "manual"
    target_profile_id: Optional[int] = None
    created_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

class LogEntry(BaseModel):
    id: int
    message: str
    level: str
    timestamp: Optional[datetime.datetime] = None  # Bug Fix #6: optional para logs sin timestamp
    model_config = ConfigDict(from_attributes=True)

class LoginStart(BaseModel):
    email: str
    password: str
    proxy_url: Optional[str] = None

class LoginVerify(BaseModel):
    email: str
    code: str

class WarmupConfigBase(BaseModel):
    niche: Optional[str] = None
    personality: Optional[str] = None
    languages: Optional[str] = "Spanish, English"
    forbidden_topics: Optional[str] = None
    tone_modifiers: Optional[str] = "Professional, Helpful"
    vip_profiles: Optional[List[str]] = None
    total_days: Optional[int] = 120

class WarmupConfigUpdate(WarmupConfigBase):
    account_id: int

class WarmupStatus(BaseModel):
    account_id: int
    name: str
    profile_pic_url: Optional[str]
    current_day: int
    total_days: int = 120
    current_level: int
    daily_actions: int
    max_actions: int = 150
    health_percentage: int
    is_warming_up: int = 1

class ConcurrentTestRequest(BaseModel):
    account_ids: List[int]
    task_template: dict
    concurrency_level: int


def _safe_increment_action_count(account_id: int, db) -> bool:
    """Atomically increment action count using with_for_update."""
    from models import Account
    try:
        account = db.query(Account).with_for_update().filter(Account.id == account_id).first()
        if not account:
            return False

        today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        if account.last_action_date != today:
            account.daily_action_count = 0
            account.last_action_date = today

        MAX_WARMUP_ACTIONS = 10
        if account.is_warming_up and account.daily_action_count >= MAX_WARMUP_ACTIONS:
            return False

        account.daily_action_count += 1
        db.commit()
        return True
    except Exception as e:
        logger.error(f"_safe_increment_action_count error: {e}")
        db.rollback()
        return False


def _acquire_execution_lock(account_id: int, mission_id: int, db) -> bool:
    """Acquire a lock for an account. Returns False if already locked."""
    from models import ExecutionLock
    try:
        existing = db.query(ExecutionLock).filter(
            ExecutionLock.account_id == account_id
        ).with_for_update().first()
        if existing:
            if existing.acquired_at:
                elapsed = (datetime.datetime.utcnow() - existing.acquired_at).total_seconds()
                if elapsed > existing.ttl_seconds:
                    db.delete(existing)
                    db.commit()
                else:
                    return False
            else:
                return False

        lock = ExecutionLock(
            account_id=account_id,
            mission_id=mission_id,
            acquired_at=datetime.datetime.utcnow(),
            ttl_seconds=600
        )
        db.add(lock)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"_acquire_execution_lock error: {e}")
        db.rollback()
        return False


def _release_execution_lock(account_id: int, db):
    """Release the lock for an account."""
    from models import ExecutionLock
    try:
        lock = db.query(ExecutionLock).filter(
            ExecutionLock.account_id == account_id
        ).first()
        if lock:
            db.delete(lock)
            db.commit()
    except Exception as e:
        logger.error(f"_release_execution_lock error: {e}")
        db.rollback()


def check_rate_limit(account_id: int, action_type: str, db) -> bool:
    """Check if account is within rate limit. Returns True if OK, False if blocked."""
    from models import RateLimit, Account
    try:
        now = datetime.datetime.utcnow()
        window_start = now - datetime.timedelta(hours=1)

        record = db.query(RateLimit).filter(
            RateLimit.account_id == account_id,
            RateLimit.action_type == action_type
        ).with_for_update().first()

        if not record:
            record = RateLimit(account_id=account_id, action_type=action_type, action_count=1, window_start=now)
            db.add(record)
            db.commit()
            return True

        if record.window_start < window_start:
            record.action_count = 1
            record.window_start = now
            db.commit()
            return True

        account = db.query(Account).filter(Account.id == account_id).first()
        limit = 10 if (account and account.is_warming_up) else 50

        if record.action_count >= limit:
            return False

        record.action_count += 1
        db.commit()
        return True
    except Exception as e:
        logger.error(f"check_rate_limit error: {e}")
        db.rollback()
        return True


# --- BACKGROUND TASKS ---
async def run_mission_task(mission_id: int):
    """Bug Fix #3: Usa SessionLocal directamente en lugar de un generator corrupto."""
    db = SessionLocal()
    queue = log_streamer.subscribe(mission_id)
    
    def push_log(level: str, message: str):
        entry = {"timestamp": datetime.datetime.utcnow().isoformat(), "level": level, "message": message}
        log_streamer.push(mission_id, entry)
        db.add(models.Log(mission_id=mission_id, message=message, level=level))
    
    try:
        # Debug: Verificar el tipo de loop
        loop = asyncio.get_running_loop()
        logger.info(f"Running mission {mission_id} on loop: {type(loop)}")
        if sys.platform == 'win32' and 'ProactorEventLoop' not in str(type(loop)):
            logger.error("CRITICAL: Subprocesses will fail! ProactorEventLoop not found.")

        mission = db.get(models.Mission, mission_id)
        if not mission:
            return

        mission.status = "running"
        db.commit()

        account = mission.account
        # Bug Fix #1: Validar que la cuenta existe y tiene sesión activa
        if not account:
            mission.status = "failed"
            push_log("error", f"Error: Account ID {mission.account_id} not found in database. Mission is orphaned.")
            db.commit()
            return

        if not account.storage_state:
            mission.status = "failed"
            push_log("error", f"Error: Account '{account.email}' has no active session. Please log in first.")
            db.commit()
            return

        # --- WARM-UP LOGIC: Daily Limits ---
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        if account.last_action_date != today:
            account.daily_action_count = 0
            account.last_action_date = today
            db.commit()

        # Si está en calentamiento, límite estricto de 10 acciones
        MAX_WARMUP_ACTIONS = 10
        if account.is_warming_up and account.daily_action_count >= MAX_WARMUP_ACTIONS:
            mission.status = "failed"
            push_log("warning", f"BLOQUEO DE SEGURIDAD: La cuenta '{account.email}' está en modo CALENTAMIENTO y ha superado el límite de {MAX_WARMUP_ACTIONS} acciones diarias.")
            db.commit()
            return

        # --- ACQUIRE EXECUTION LOCK ---
        if not _acquire_execution_lock(account.id, mission_id, db):
            push_log("warning", f"Account '{account.email}' is busy with another mission. Queuing.")
            mission.status = "queued"
            db.commit()
            return

        # --- CHECK RATE LIMIT ---
        first_task_type = mission.tasks[0].get("type", "unknown") if mission.tasks else "unknown"
        if not check_rate_limit(account.id, first_task_type, db):
            push_log("warning", f"Rate limit exceeded for account '{account.email}'. Queuing.")
            mission.status = "queued"
            db.commit()
            _release_execution_lock(account.id, db)
            return

        runner = orchestrator.MissionRunner(account.storage_state, account.proxy_url, account_id=account.id)

        try:
            push_log("info", f"Starting mission with {len(mission.tasks)} tasks for account '{account.email}'.")
            db.commit()

            results = await runner.execute_mission(mission.tasks)

            mission.status = "completed"
            mission.executed_at = datetime.datetime.utcnow()

            for res in results:
                result_val = res['result']
                is_success = result_val == 200
                
                if is_success:
                    account.daily_action_count += 1
                
                log_msg = f"Task '{res['task']['type']}' → result: {result_val}"
                push_log("success" if is_success else "warning", log_msg)

        except Exception as e:
            # Bug Fix #2: Captura traceback completo, no solo str(e)
            tb = traceback.format_exc()
            mission.status = "failed"
            push_log("error", f"Mission error: {type(e).__name__}: {str(e) or 'no message'}\n{tb[:1000]}")

        db.commit()
    finally:
        _release_execution_lock(account.id, db)
        log_streamer.unsubscribe(mission_id, queue)
        db.close()

# --- ENDPOINTS ---

@app.get("/accounts/", response_model=List[Account])
def read_accounts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Account).offset(skip).limit(limit).all()

@app.delete("/accounts/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.get(models.Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Delete related missions and logs first (though SQLite handles cascade if configured, but let's be safe or just delete the account if no foreign keys block it)
    db.delete(account)
    db.commit()
    return {"status": "success", "message": f"Account {account_id} deleted"}

@app.put("/accounts/{account_id}/warmup/toggle")
def toggle_account_warmup(account_id: int, db: Session = Depends(get_db)):
    account = db.get(models.Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account.is_warming_up = 0 if account.is_warming_up == 1 else 1
    db.commit()
    return {"status": "success", "is_warming_up": account.is_warming_up}

@app.get("/accounts/{account_id}/notifications")
async def get_notifications(account_id: int, db: Session = Depends(get_db)):
    account = db.get(models.Account, account_id)
    if not account or not account.storage_state:
        raise HTTPException(status_code=404, detail="Account or session not found")
    
    runner = orchestrator.MissionRunner(account.storage_state, account.proxy_url, account_id=account.id)
    # We run it as a one-off mission task
    results = await runner.execute_mission([{"type": "check_notifications", "payload": {}}])
    
    # The result will be in the first item's 'result' field
    if results and len(results) > 0:
        return {"account_id": account_id, "notifications": results[0].get("result", [])}
    return {"account_id": account_id, "notifications": []}


@app.post("/accounts/{account_id}/live")
async def activate_live_session(account_id: int, db: Session = Depends(get_db)):
    """Warms up and keeps a browser instance alive for an account."""
    account = db.get(models.Account, account_id)
    if not account or not account.storage_state:
        raise HTTPException(status_code=404, detail="Account or session not found")
    
    try:
        # Trigger get_page to ensure it's running
        await orchestrator.BrowserManager.get_page(account_id, account.storage_state, account.proxy_url)
        return {"status": "alive", "account_id": account_id}
    except Exception as e:
        logger.error(f"Failed to start live session for account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Browser activation failed: {str(e)}")

@app.websocket("/ws/live/{account_id}")
async def live_stream(websocket: WebSocket, account_id: int):
    logger.info(f"WS Attempt: Account {account_id} from {websocket.client}")
    try:
        await websocket.accept()
        logger.info(f"WS Accepted: Account {account_id}")
    except Exception as e:
        logger.error(f"WS Accept Failed for account {account_id}: {e}")
        return
    
    # 1. Get browser instance (with retry to handle slow startup)
    instance = None
    for _ in range(10): # Try for 5 seconds
        instance = orchestrator.BrowserManager._instances.get(account_id)
        if instance and instance.get("page"):
            break
        await asyncio.sleep(0.5)
        
    if not instance:
        logger.error(f"WS FAIL: No instance found in BrowserManager._instances for account {account_id} after timeout")
        await websocket.close(code=1008)
        return
        
    page = instance.get("page")
    if not page or page.is_closed():
        logger.error(f"WS FAIL: Page is closed or missing for account {account_id}")
        await websocket.close(code=1008)
        return

    try:
        # Create CDP session
        logger.info(f"WS: Creating CDP session for account {account_id}")
        # Ensure page is ready for CDP
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except:
            pass
        cdp = await page.context.new_cdp_session(page)
        
        async def on_frame(event):
            try:
                await websocket.send_json({
                    "type": "stream",
                    "image": event["data"]
                })
                await cdp.send("Page.screencastFrameAck", {"sessionId": event["sessionId"]})
            except Exception as e:
                logger.debug(f"Screencast send error: {e}")

        cdp.on("Page.screencastFrame", lambda event: asyncio.create_task(on_frame(event)))
        
        await cdp.send("Page.startScreencast", {
            "format": "jpeg",
            "quality": 60,
            "maxWidth": 1280,
            "maxHeight": 720,
            "everyNthFrame": 1
        })
        logger.info(f"WS: Screencast STARTED for account {account_id}")

        while True:
            try:
                data = await websocket.receive_text()
                cmd = json.loads(data)
                
                if cmd["type"] == "click":
                    await page.mouse.click(cmd["x"], cmd["y"])
                elif cmd["type"] == "type":
                    await page.keyboard.type(cmd["text"])
                elif cmd["type"] == "press":
                    await page.keyboard.press(cmd["key"])
            except asyncio.TimeoutError:
                continue
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.debug(f"Input relay error: {e}")
                
    except WebSocketDisconnect:
        logger.info(f"WS: Disconnected for account {account_id}")
    except Exception as e:
        logger.error(f"WS CRITICAL Error for account {account_id}: {e}")
    finally:
        logger.info(f"WS CLEANUP for account {account_id}")
        try:
            await cdp.send("Page.stopScreencast")
        except:
            pass
        if websocket.client_state.name != "DISCONNECTED":
            try:
                await websocket.close()
            except:
                pass

@app.get("/notifications/")
def list_all_notifications(account_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(models.Notification)
    if account_id:
        query = query.filter(models.Notification.account_id == account_id)
    return query.order_by(models.Notification.id.desc()).all()

@app.post("/accounts/login/start")
async def start_login(data: LoginStart, db: Session = Depends(get_db)):
    _cleanup_expired_logins()  # Bug Fix #5: limpiar sessions expiradas
    login_id = data.email
    manager = orchestrator.GuidedLogin(data.email, data.password, data.proxy_url)
    # Thread‑safe insertion using lock and initialise attempt counter
    with active_logins_lock:
        active_logins[login_id] = {"manager": manager, "created_at": datetime.datetime.utcnow(), "failed_attempts": 0}

    try:
        status = await manager.start()
    except Exception as e:
        tb = traceback.format_exc()
        del active_logins[login_id]
        raise HTTPException(status_code=500, detail=f"Error iniciando browser: {type(e).__name__}: {str(e) or 'no message'}")

    # Si el login fue directo (sin 2FA), guardamos inmediatamente en DB
    if status == "success" and manager.storage_state:
        existing = db.query(models.Account).filter(models.Account.email == data.email).first()
        if existing:
            existing.storage_state = manager.storage_state
            existing.status = "active"
        else:
            new_acc = models.Account(
                name=data.email.split('@')[0],
                email=data.email,
                storage_state=manager.storage_state,
                proxy_url=data.proxy_url,
                status="active"
            )
            db.add(new_acc)
        db.commit()
        del active_logins[login_id]

    return {"status": status, "email": data.email}

@app.post("/accounts/login/verify")
async def verify_login(data: LoginVerify, db: Session = Depends(get_db)):
    # Clean up any expired sessions before proceeding
    _cleanup_expired_logins()
    with active_logins_lock:
        login_data = active_logins.get(data.email)
        if not login_data:
            raise HTTPException(status_code=404, detail="Login session not found or expired (>10 min)")
        # Enforce a maximum number of 2FA attempts (e.g., 5)
        if login_data.get("failed_attempts", 0) >= 5:
            # Invalidate the session to prevent further brute‑force attempts
            del active_logins[data.email]
            raise HTTPException(status_code=429, detail="Too many 2FA attempts. Session locked.")
        manager = login_data["manager"]

    storage_state = await manager.submit_code(data.code)
    if storage_state:
        existing = db.query(models.Account).filter(models.Account.email == data.email).first()
        if existing:
            existing.storage_state = storage_state
            existing.status = "active"
            db.commit()
            db.refresh(existing)
            account_id = existing.id
        else:
            new_acc = models.Account(
                name=data.email.split('@')[0],
                email=data.email,
                storage_state=storage_state,
                status="active"
            )
            db.add(new_acc)
            db.commit()
            db.refresh(new_acc)
            account_id = new_acc.id
        # Successful verification – remove the login session
        with active_logins_lock:
            active_logins.pop(data.email, None)
        return {"status": "success", "account_id": account_id}
    else:
        # Increment failed attempts counter safely
        with active_logins_lock:
            if data.email in active_logins:
                active_logins[data.email]["failed_attempts"] = active_logins[data.email].get("failed_attempts", 0) + 1
        return {"status": "failed", "detail": "2FA code incorrect or expired"}


# ══════════════════════════════════════════════════════════════════════
# PROXY POOL
# ══════════════════════════════════════════════════════════════════════

class ProxyCreate(BaseModel):
    name: Optional[str] = None
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "socks5"
    country: Optional[str] = None
    city: Optional[str] = None

class ProxyUpdate(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    is_active: Optional[bool] = None

class ProxyResponse(BaseModel):
    id: int
    name: Optional[str] = None
    host: str
    port: int
    protocol: str
    country: Optional[str] = None
    city: Optional[str] = None
    is_active: bool
    is_online: bool
    last_health_check: Optional[datetime.datetime] = None
    assigned_account_id: Optional[int] = None
    created_at: Optional[datetime.datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ProxyAssignRequest(BaseModel):
    account_id: int

class ProxyAutoAssignRequest(BaseModel):
    account_id: int
    country: Optional[str] = None


@app.get("/proxies/", response_model=List[ProxyResponse])
def list_proxies(active_only: bool = True, db: Session = Depends(get_db)):
    return proxy_pool.ProxyPool.get_all(db, active_only)

@app.post("/proxies/", response_model=ProxyResponse)
def create_proxy(payload: ProxyCreate, db: Session = Depends(get_db)):
    p = proxy_pool.Proxy(
        name=payload.name,
        host=payload.host,
        port=payload.port,
        username=payload.username,
        password=payload.password,
        protocol=payload.protocol,
        country=payload.country.upper() if payload.country else None,
        city=payload.city,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    logger.info(f"Proxy creado: {p.short_url} ({p.country})")
    return p

@app.put("/proxies/{proxy_id}", response_model=ProxyResponse)
def update_proxy(proxy_id: int, payload: ProxyUpdate, db: Session = Depends(get_db)):
    p = db.get(proxy_pool.Proxy, proxy_id)
    if not p:
        raise HTTPException(status_code=404, detail="Proxy not found")
    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        if k == "country" and v:
            v = v.upper()
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p

@app.delete("/proxies/{proxy_id}")
def delete_proxy(proxy_id: int, db: Session = Depends(get_db)):
    p = db.get(proxy_pool.Proxy, proxy_id)
    if not p:
        raise HTTPException(status_code=404, detail="Proxy not found")
    # Liberar cuenta si estaba asignada
    if p.assigned_account_id:
        acc = db.get(models.Account, p.assigned_account_id)
        if acc:
            acc.proxy_url = None
    db.delete(p)
    db.commit()
    return {"status": "success", "message": f"Proxy {proxy_id} eliminado"}

@app.post("/proxies/{proxy_id}/assign")
def assign_proxy(proxy_id: int, payload: ProxyAssignRequest, db: Session = Depends(get_db)):
    try:
        p = proxy_pool.ProxyPool.assign_to_account(db, proxy_id, payload.account_id)
        return {"status": "success", "proxy_id": p.id, "account_id": payload.account_id,
                "proxy_url": p.short_url}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/proxies/auto-assign")
def auto_assign_proxy(payload: ProxyAutoAssignRequest, db: Session = Depends(get_db)):
    p = proxy_pool.ProxyPool.auto_assign(db, payload.account_id, payload.country)
    if not p:
        available = proxy_pool.ProxyPool.get_available(db)
        if available:
            # Asignar cualquiera disponible
            p = proxy_pool.ProxyPool.assign_to_account(db, available[0].id, payload.account_id)
        else:
            raise HTTPException(status_code=404, detail="No hay proxies disponibles")
    return {"status": "success", "proxy_id": p.id, "proxy_url": p.short_url,
            "country": p.country}

@app.post("/proxies/{proxy_id}/unassign")
def unassign_proxy(proxy_id: int, db: Session = Depends(get_db)):
    p = db.get(proxy_pool.Proxy, proxy_id)
    if not p:
        raise HTTPException(status_code=404, detail="Proxy not found")
    if p.assigned_account_id:
        acc = db.get(models.Account, p.assigned_account_id)
        if acc:
            acc.proxy_url = None
        p.assigned_account_id = None
        db.commit()
    return {"status": "success", "message": f"Proxy {proxy_id} desasignado"}

@app.post("/proxies/health-check")
async def run_proxy_health_check(db: Session = Depends(get_db)):
    results = await proxy_pool.ProxyPool.run_health_checks(db)
    return results

@app.get("/proxies/stats")
def proxy_stats(db: Session = Depends(get_db)):
    return proxy_pool.ProxyPool.get_stats(db)

@app.get("/accounts/{account_id}/proxy")
def get_account_proxy(account_id: int, db: Session = Depends(get_db)):
    proxy = proxy_pool.ProxyPool.get_for_account(db, account_id)
    if not proxy:
        return {"assigned": False, "proxy": None}
    return {"assigned": True, "proxy": {
        "id": proxy.id,
        "url": proxy.short_url,
        "country": proxy.country,
        "city": proxy.city,
        "protocol": proxy.protocol,
        "is_online": proxy.is_online,
    }}


# ══════════════════════════════════════════════════════════════════════
# COOKIE IMPORT (desde extensión Chrome)
# ══════════════════════════════════════════════════════════════════════

class CookieImportRequest(BaseModel):
    """Formato: JSON con el array de cookies que exporta la extensión Chrome."""
    cookies: list[dict] = Field(..., description="Array de cookies en formato extensión Chrome")
    name: Optional[str] = Field(None, description="Nombre amigable para la cuenta")
    proxy_url: Optional[str] = Field(None, description="Proxy opcional (http://user:pass@host:port)")

class CookieImportResponse(BaseModel):
    status: str
    account_id: Optional[int] = None
    name: Optional[str] = None
    detail: Optional[str] = None

class CookieValidateRequest(BaseModel):
    cookies: list[dict] = Field(..., description="Array de cookies en formato extensión Chrome")

class CookieValidateResponse(BaseModel):
    valid: bool
    name: Optional[str] = None
    profile_pic: Optional[str] = None
    error: Optional[str] = None
    detected_country: Optional[str] = None


@app.post("/accounts/cookies/validate", response_model=CookieValidateResponse)
async def validate_cookies(payload: CookieValidateRequest):
    """Valida cookies sin guardar nada. Responde si la sesión es válida y opcionalmente el nombre."""
    try:
        storage_state = cookie_importer.convert_to_storage_state(payload.cookies)
        result = cookie_importer.validate_storage_state(storage_state)
        result["detected_country"] = cookie_importer.detect_country_from_cookies(payload.cookies)
        return CookieValidateResponse(**result)
    except Exception as e:
        logger.error(f"Error validating cookies: {e}")
        return CookieValidateResponse(valid=False, error=f"Error interno: {str(e)[:100]}")


@app.post("/accounts/cookies", response_model=CookieImportResponse)
async def import_cookies(payload: CookieImportRequest, db: Session = Depends(get_db)):
    """Importa cookies desde extensión Chrome, las valida y crea la cuenta."""
    # 1. Convertir formato extensión → Playwright storage_state
    storage_state = cookie_importer.convert_to_storage_state(payload.cookies)

    if not storage_state.get("cookies"):
        raise HTTPException(status_code=400, detail="No se encontraron cookies válidas en el JSON")

    # 2. Validar contra LinkedIn
    validation = cookie_importer.validate_storage_state(storage_state)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation.get("error", "Cookies inválidas o expiradas"))

    # 3. Extraer email de las cookies (o usar un placeholder)
    # Buscar en el storage_state la cookie li_at para identificar la cuenta
    name = payload.name or validation.get("name") or "Cuenta desde Cookie"

    # 4. Verificar si ya existe una cuenta con ese nombre
    existing = db.query(models.Account).filter(models.Account.name == name).first()
    if existing:
        # Actualizar storage_state de la cuenta existente
        existing.storage_state = storage_state
        existing.status = "active"
        db.commit()
        return CookieImportResponse(status="success", account_id=existing.id, name=name,
                                    detail="Cookies actualizadas para cuenta existente")

    # 5. Crear nueva cuenta (email único para evitar conflictos)
    email_slug = name.lower().replace(" ", ".").replace("@", "_")[:30]
    unique_email = f"{email_slug}.{uuid.uuid4().hex[:8]}@cookie.import"
    new_account = models.Account(
        name=name,
        email=unique_email,
        storage_state=storage_state,
        proxy_url=payload.proxy_url,
        status="active",
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)

    # 6. Auto-asignar proxy del país detectado (si hay disponible)
    detected_country = cookie_importer.detect_country_from_cookies(payload.cookies)
    if detected_country and not payload.proxy_url:
        assigned = proxy_pool.ProxyPool.auto_assign(db, new_account.id, detected_country)
        if assigned:
            logger.info(f"Proxy auto-asignado: {assigned.short_url} ({detected_country}) → Account {new_account.id}")

    logger.info(f"Cuenta creada desde cookie: ID={new_account.id}, name={name}")
    return CookieImportResponse(status="success", account_id=new_account.id, name=name,
                                detail="Cuenta creada exitosamente desde cookies")


@app.get("/missions/", response_model=List[Mission])
def read_missions(db: Session = Depends(get_db)):
    return db.query(models.Mission).order_by(models.Mission.created_at.desc()).limit(10).all()

@app.post("/missions/", response_model=Mission)
async def create_mission(mission: MissionBase, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Bug Fix #1: Validar que la cuenta existe antes de crear la misión
    account = db.get(models.Account, mission.account_id)
    if not account:
        raise HTTPException(
            status_code=404,
            detail=f"Account ID {mission.account_id} not found. Cannot create mission for a non-existent account."
        )
    if not account.storage_state:
        raise HTTPException(
            status_code=422,
            detail=f"Account '{account.email}' has no active session. Please log in first before creating missions."
        )

    db_mission = models.Mission(**mission.dict())
    db.add(db_mission)
    db.commit()
    db.refresh(db_mission)

    # Bug Fix #3: Pasar solo el ID, run_mission_task crea su propia sesión de DB
    background_tasks.add_task(run_mission_task, db_mission.id)
    return db_mission

@app.get("/logs/", response_model=List[LogEntry])
def read_logs(db: Session = Depends(get_db)):
    return db.query(models.Log).order_by(models.Log.timestamp.desc()).limit(20).all()

@app.get("/stats")
def read_stats(db: Session = Depends(get_db)):
    total_accounts = db.query(models.Account).count()
    active_missions = db.query(models.Mission).filter(models.Mission.status == "running").count()
    completed_missions = db.query(models.Mission).filter(models.Mission.status == "completed").count()
    failed_missions = db.query(models.Mission).filter(models.Mission.status == "failed").count()
    
    total_m = completed_missions + failed_missions
    success_rate = int((completed_missions / total_m * 100)) if total_m > 0 else 100

    return {
        "total_identities": total_accounts,
        "active_missions": active_missions,
        "success_rate": success_rate,
        "system_status": "nominal"
    }

@app.get("/")
def read_root():
    return {"status": "LinkedIn Orchestrator Online"}


# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2501
# BULK MISSION  (multi-account + human delays + AI rephrase)
# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2501

import random
import re as _re

def _rephrase_comment(original: str, account_index: int) -> str:
    """
    Lightweight AI-style rephraser that produces a unique variant of `original`
    for each account without needing an external API.
    Strategy: sentence-level shuffling + synonym map + emoji rotation.
    """
    synonyms = {
        r"\bde acuerdo\b": ["totalmente de acuerdo", "de acuerdo contigo", "en la misma l\u00ednea"],
        r"\bgenial\b": ["excelente", "fant\u00e1stico", "muy bueno"],
        r"\binteresante\b": ["fascinante", "muy valioso", "relevante"],
        r"\bclave\b": ["fundamental", "esencial", "determinante"],
        r"\bimportante\b": ["crucial", "significativo", "relevante"],
        r"\bgracias\b": ["muchas gracias", "muy agradecido", "agradezco"],
        r"\bcompartir\b": ["difundir", "publicar", "mostrar"],
        r"\benfoque\b": ["perspectiva", "visi\u00f3n", "punto de vista"],
        r"\bincre\u00edble\b": ["sorprendente", "notable", "impresionante"],
        r"\bfant\u00e1stico\b": ["maravilloso", "excelente", "estupendo"],
        r"\bseguro\b": ["sin duda", "definitivamente", "con certeza"],
        r"\btrabajo\b": ["esfuerzo", "contenido", "aporte"],
    }
    openers = [
        "", "Completamente de acuerdo. ", "Muy buen punto. ", "Excelente reflexi\u00f3n. ",
        "Gran aporte. ", "100% de acuerdo. ", "Interesante perspectiva. "
    ]
    closers = [
        "", " \ud83d\udc4f", " \ud83d\ude4c", " \ud83d\udca1", " \ud83d\udd25", " \u2705", "!", " \ud83d\udcaf"
    ]

    rng = random.Random(account_index * 7919 + len(original))  # deterministic per account+text

    result = original
    for pattern, variants in synonyms.items():
        if _re.search(pattern, result, flags=_re.IGNORECASE):
            replacement = rng.choice(variants)
            result = _re.sub(pattern, replacement, result, count=1, flags=_re.IGNORECASE)

    opener = rng.choice(openers)
    closer = rng.choice(closers)
    
    # If the random generator picked empty strings for both AND no synonyms matched, force a change
    if opener == "" and closer == "" and result == original:
        closer = rng.choice([" \ud83d\udc4f", " \ud83d\ude4c", " \ud83d\udca1", " \u2705"])
        
    result = opener + result.strip() + closer

    return result


class BulkMissionBase(BaseModel):
    account_ids: List[int]         # IDs de las cuentas, vac\u00edo = todas las activas
    tasks: List[dict]              # mismas tareas para todos
    comment_mode: str = "literal"  # "literal" | "ai"
    delay_min: int = 30            # segundos m\u00ednimos entre cuentas
    delay_max: int = 120           # segundos m\u00e1ximos entre cuentas


async def _run_bulk_with_delays(
    account_ids: List[int],
    tasks: List[dict],
    comment_mode: str,
    delay_min: int,
    delay_max: int,
    mission_ids: List[int],
):
    """Background coroutine: ejecuta misiones en orden con delays aleatorios humanos."""
    for idx, (account_id, mission_id) in enumerate(zip(account_ids, mission_ids)):
        # Human-like delay between accounts (skip for the very first)
        if idx > 0:
            delay = random.randint(delay_min, delay_max)
            await asyncio.sleep(delay)

        # If AI mode, rephrase comment tasks per account
        final_tasks = tasks
        if comment_mode == "ai":
            final_tasks = []
            for task in tasks:
                if task.get("type") == "comment" and task.get("payload", {}).get("text"):
                    rephrased = _rephrase_comment(task["payload"]["text"], account_id)
                    final_tasks.append({
                        **task,
                        "payload": {**task["payload"], "text": rephrased}
                    })
                else:
                    final_tasks.append(task)

        # Update the mission's tasks in DB before running
        db = SessionLocal()
        try:
            mission = db.get(models.Mission, mission_id)
            if mission:
                mission.tasks = final_tasks
                db.commit()
        finally:
            db.close()

        await run_mission_task(mission_id)


@app.post("/missions/bulk")
async def create_bulk_missions(
    payload: BulkMissionBase,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Resolve accounts: if empty list \u2192 all active accounts
    if not payload.account_ids:
        accounts = db.query(models.Account).filter(
            models.Account.status == "active",
            models.Account.storage_state.isnot(None)
        ).all()
        account_ids = [a.id for a in accounts]
    else:
        account_ids = payload.account_ids

    if not account_ids:
        raise HTTPException(status_code=400, detail="No active accounts found.")

    # Validate all accounts exist and have sessions
    for aid in account_ids:
        acc = db.get(models.Account, aid)
        if not acc:
            raise HTTPException(status_code=404, detail=f"Account {aid} not found.")
        if not acc.storage_state:
            raise HTTPException(status_code=422, detail=f"Account '{acc.email}' has no active session.")

    # Create mission records upfront (all as pending)
    mission_ids = []
    for aid in account_ids:
        db_mission = models.Mission(account_id=aid, tasks=payload.tasks)
        db.add(db_mission)
        db.commit()
        db.refresh(db_mission)
        mission_ids.append(db_mission.id)

    # Fire the sequential background runner
    background_tasks.add_task(
        _run_bulk_with_delays,
        account_ids,
        payload.tasks,
        payload.comment_mode,
        payload.delay_min,
        payload.delay_max,
        mission_ids,
    )

    return {
        "queued": len(mission_ids),
        "mission_ids": mission_ids,
        "comment_mode": payload.comment_mode,
        "delay_range": f"{payload.delay_min}-{payload.delay_max}s",
    }

# \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2501
# AUTOPILOT (Target Profiles & Scheduling)
# ─────────────────────────────────────────────────────────────────────

@app.get("/autopilot/status")
def get_autopilot_status(db: Session = Depends(get_db)):
    """Returns the real-time state of the autopilot scheduler."""
    import autopilot as _ap
    return _ap.get_scheduler_status(db_session=db)


class TargetProfileCreate(BaseModel):
    linkedin_url: str
    schedule_start: str = "09:00"
    schedule_end: str = "18:00"
    cta_keywords: Optional[str] = None
    comment_base: Optional[str] = None

class TargetProfileResponse(TargetProfileCreate):
    id: int
    status: str
    created_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

@app.get("/autopilot/targets", response_model=List[TargetProfileResponse])
def get_target_profiles(db: Session = Depends(get_db)):
    return db.query(models.TargetProfile).all()

@app.post("/autopilot/targets", response_model=TargetProfileResponse)
def create_target_profile(profile: TargetProfileCreate, db: Session = Depends(get_db)):
    # Check if exists
    existing = db.query(models.TargetProfile).filter(models.TargetProfile.linkedin_url == profile.linkedin_url).first()
    if existing:
        raise HTTPException(status_code=400, detail="Target profile already exists")
    
    new_prof = models.TargetProfile(**profile.dict())
    db.add(new_prof)
    db.commit()
    db.refresh(new_prof)
    return new_prof

@app.put("/autopilot/targets/{target_id}/toggle")
def toggle_target_profile(target_id: int, db: Session = Depends(get_db)):
    target = db.get(models.TargetProfile, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target profile not found")
    
    target.status = "paused" if target.status == "active" else "active"
    db.commit()
    return {"status": "success", "new_status": target.status}

@app.delete("/autopilot/targets/{target_id}")
def delete_target_profile(target_id: int, db: Session = Depends(get_db)):
    target = db.get(models.TargetProfile, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target profile not found")
    
    # Delete associated processed posts
    db.query(models.ProcessedPost).filter(models.ProcessedPost.target_profile_id == target_id).delete()
    db.delete(target)
    db.commit()
    return {"status": "success"}

# --- WARMUP LAB ENDPOINTS ---

@app.get("/warmup/status", response_model=List[WarmupStatus])
def get_warmup_status(db: Session = Depends(get_db)):
    try:
        # 1. Get accounts that are warming up
        accounts = db.query(models.Account).filter(models.Account.is_warming_up == 1).all()
        results = []
        now = datetime.datetime.utcnow()
        
        # 2. Collect accounts that need a config
        needs_config = []
        
        for acc in accounts:
            try:
                # Day calculation (handle None)
                start_date = acc.created_at if acc.created_at else now
                days_diff = (now - start_date).days + 1
                
                config = acc.warmup_config
                if not config:
                    # Create default config but don't commit yet to avoid locks
                    config = models.WarmupConfig(account_id=acc.id)
                    db.add(config)
                    needs_config.append(config)
                
                daily_actions = acc.daily_action_count if acc.daily_action_count is not None else 0
                health = int((daily_actions / 150) * 100)
                
                # Use a default trust level if config is new/missing
                trust_level = int(config.current_trust_level) if (config and config.current_trust_level is not None) else 1
                
                results.append({
                    "account_id": int(acc.id),
                    "name": str(acc.name) if acc.name else f"Account {acc.id}",
                    "profile_pic_url": acc.profile_pic_url,
                    "current_day": int(days_diff),
                    "total_days": int(config.total_days) if config.total_days else 120,
                    "current_level": trust_level,
                    "daily_actions": int(daily_actions),
                    "max_actions": 150,
                    "health_percentage": int(min(health, 100)),
                    "is_warming_up": int(acc.is_warming_up)
                })
            except Exception as inner_e:
                print(f"Error processing account {acc.id}: {inner_e}")
                continue
        
        # 3. Single commit at the end if needed
        if needs_config:
            db.commit()
            
        return results
    except Exception as e:
        import traceback
        print("CRITICAL Error in /warmup/status:")
        traceback.print_exc()
        return []

@app.get("/warmup/config/{account_id}", response_model=WarmupConfigBase)
def get_warmup_config(account_id: int, db: Session = Depends(get_db)):
    config = db.query(models.WarmupConfig).filter(models.WarmupConfig.account_id == account_id).first()
    if not config:
        # Create default
        config = models.WarmupConfig(account_id=account_id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

@app.post("/warmup/config")
def update_warmup_config(payload: WarmupConfigUpdate, db: Session = Depends(get_db)):
    config = db.query(models.WarmupConfig).filter(models.WarmupConfig.account_id == payload.account_id).first()
    if not config:
        config = models.WarmupConfig(account_id=payload.account_id)
        db.add(config)
    
    for key, value in payload.dict(exclude={'account_id'}).items():
        if value is not None:
            setattr(config, key, value)
            
    db.commit()
    return {"status": "success"}

@app.post("/test/concurrent")
async def test_concurrent(req: ConcurrentTestRequest, db: Session = Depends(get_db)):
    accounts = db.query(models.Account).filter(models.Account.id.in_(req.account_ids)).all()
    if len(accounts) != len(req.account_ids):
        raise HTTPException(status_code=404, detail="One or more accounts not found")
        
    account_map = {acc.id: acc for acc in accounts}
    test_run_id = str(uuid.uuid4())
    
    async def run_single_test(account_id):
        import time
        start_time = time.time()
        try:
            acc = account_map[account_id]
            db_mission = models.Mission(account_id=account_id, tasks=[req.task_template], status="running", source="concurrent_test")
            db.add(db_mission)
            db.commit()
            db.refresh(db_mission)
            
            if not acc.storage_state:
                res_str = "failed: no session"
            else:
                runner = orchestrator.MissionRunner(acc.storage_state, acc.proxy_url, account_id=acc.id)
                try:
                    task_res = await runner.execute_mission([req.task_template])
                    if task_res and len(task_res) > 0:
                        res_str = str(task_res[0].get("result", "error"))
                    else:
                        res_str = "error: no result"
                except Exception as e:
                    res_str = f"error: {str(e)}"
                    
            duration = int((time.time() - start_time) * 1000)
            
            return {
                "account_id": account_id,
                "mission_id": db_mission.id,
                "result": res_str,
                "duration_ms": duration
            }
        except Exception as e:
            return {
                "account_id": account_id,
                "mission_id": None,
                "result": f"error: {str(e)}",
                "duration_ms": int((time.time() - start_time) * 1000)
            }
            
    import asyncio
    coros = [run_single_test(aid) for aid in req.account_ids]
    gathered_results = await asyncio.gather(*coros)
    
    for item in gathered_results:
        ctr = models.ConcurrencyTestResult(
            test_run_id=test_run_id,
            account_id=item["account_id"],
            account_email=account_map[item["account_id"]].email,
            mission_id=item["mission_id"],
            task_type=req.task_template.get("type", "unknown"),
            result=item["result"],
            duration_ms=item["duration_ms"]
        )
        db.add(ctr)
    db.commit()
    
    return {
        "test_run_id": test_run_id,
        "results": gathered_results
    }


log_streamer = orchestrator.log_streamer

@app.websocket("/ws/logs/{mission_id}")
async def mission_log_stream(websocket: WebSocket, mission_id: int):
    await websocket.accept()
    queue = log_streamer.subscribe(mission_id)
    try:
        while True:
            try:
                log_entry = await asyncio.wait_for(queue.get(), timeout=30.0)
                await websocket.send_json(log_entry)
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS /ws/logs/{mission_id} error: {e}")
    finally:
        log_streamer.unsubscribe(mission_id, queue)

# --- WIZARD ENDPOINTS ---

class WizardStart(BaseModel):
    email: str
    password: str
    proxy_url: Optional[str] = None

class WizardVerify(BaseModel):
    session_id: int
    code: str

active_wizard_sessions = {}
wizard_lock = threading.Lock()

async def run_wizard_login(session_id: int):
    # This runs in background
    db = SessionLocal()
    try:
        pending = db.get(models.PendingLogin, session_id)
        if not pending:
            return

        manager = orchestrator.GuidedLogin(pending.email, _simple_decrypt(pending.password_encrypted), pending.proxy_url)
        with wizard_lock:
            active_wizard_sessions[session_id] = {
                "manager": manager,
                "created_at": datetime.datetime.utcnow(),
                "failed_attempts": 0
            }
            
        status = await manager.start()
        
        # Parse status
        if status == "success":
            pending.status = "success"
            # create account immediately
            existing = db.query(models.Account).filter(models.Account.email == pending.email).first()
            if existing:
                existing.storage_state = manager.storage_state
                existing.status = "active"
            else:
                new_acc = models.Account(
                    name=pending.email.split('@')[0],
                    email=pending.email,
                    storage_state=manager.storage_state,
                    proxy_url=pending.proxy_url,
                    status="active"
                )
                db.add(new_acc)
            with wizard_lock:
                if session_id in active_wizard_sessions:
                    del active_wizard_sessions[session_id]
        elif status == "needs_captcha":
            pending.status = "failed"
            with wizard_lock:
                if session_id in active_wizard_sessions:
                    del active_wizard_sessions[session_id]
        elif status.startswith("needs_2fa_email"):
            pending.status = "2fa_email"
            parts = status.split(":", 1)
            if len(parts) > 1:
                pending.code_sent_to = parts[1]
        elif status == "needs_2fa_app":
            pending.status = "2fa_app"
        elif status == "needs_2fa_sms":
            pending.status = "2fa_sms"
        elif status == "2fa_required":
            pending.status = "2fa_unknown"
        else:
            pending.status = "failed"
            with wizard_lock:
                if session_id in active_wizard_sessions:
                    del active_wizard_sessions[session_id]
                    
        db.commit()
    except Exception as e:
        logger.error(f"Wizard error: {e}")
        try:
            pending = db.get(models.PendingLogin, session_id)
            if pending:
                pending.status = "failed"
                db.commit()
        except:
            pass
        with wizard_lock:
            if session_id in active_wizard_sessions:
                del active_wizard_sessions[session_id]
    finally:
        db.close()


@app.post("/wizard/start")
async def wizard_start(data: WizardStart, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    pending = models.PendingLogin(
        email=data.email,
        password_encrypted=_simple_encrypt(data.password),
        proxy_url=data.proxy_url,
        status="processing"
    )
    db.add(pending)
    db.commit()
    db.refresh(pending)
    
    background_tasks.add_task(run_wizard_login, pending.id)
    return {"session_id": pending.id, "status": "processing"}

@app.get("/wizard/status/{session_id}")
def wizard_status(session_id: int, db: Session = Depends(get_db)):
    pending = db.get(models.PendingLogin, session_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Session not found")
        
    return {
        "session_id": pending.id,
        "status": pending.status,
        "two_fa_destination": pending.code_sent_to
    }

@app.post("/wizard/verify")
async def wizard_verify(data: WizardVerify, db: Session = Depends(get_db)):
    pending = db.get(models.PendingLogin, data.session_id)
    if not pending:
        raise HTTPException(status_code=404, detail="Session not found")
        
    with wizard_lock:
        if data.session_id not in active_wizard_sessions:
            raise HTTPException(status_code=400, detail="Wizard session expired or invalid")
        sess_data = active_wizard_sessions[data.session_id]
        if sess_data["failed_attempts"] >= 5:
            del active_wizard_sessions[data.session_id]
            pending.status = "failed"
            db.commit()
            raise HTTPException(status_code=429, detail="Too many attempts")
            
        manager = sess_data["manager"]
        
    storage_state = await manager.submit_code(data.code)
    
    if storage_state:
        existing = db.query(models.Account).filter(models.Account.email == pending.email).first()
        if existing:
            existing.storage_state = storage_state
            existing.status = "active"
            db.commit()
            db.refresh(existing)
            account_id = existing.id
        else:
            new_acc = models.Account(
                name=pending.email.split('@')[0],
                email=pending.email,
                storage_state=storage_state,
                proxy_url=pending.proxy_url,
                status="active"
            )
            db.add(new_acc)
            db.commit()
            db.refresh(new_acc)
            account_id = new_acc.id
            
        pending.status = "success"
        db.commit()
        
        with wizard_lock:
            if data.session_id in active_wizard_sessions:
                del active_wizard_sessions[data.session_id]
                
        return {"status": "success", "account_id": account_id}
    else:
        with wizard_lock:
            if data.session_id in active_wizard_sessions:
                active_wizard_sessions[data.session_id]["failed_attempts"] += 1
        return {"status": "failed", "detail": "Invalid code"}


# ── WebSocket: Live Mission Logs ──────────────────────────────────────
@app.websocket("/ws/logs/{mission_id}")
async def ws_mission_logs(websocket: WebSocket, mission_id: int):
    await websocket.accept()
    last_log_id = 0
    try:
        while True:
            db = SessionLocal()
            try:
                mission = db.query(models.Mission).filter(models.Mission.id == mission_id).first()
                if not mission:
                    await websocket.send_json({"type": "error", "level": "error", "message": f"Mission #{mission_id} not found"})
                    break

                # Fetch new logs since last check
                new_logs = db.query(models.Log).filter(
                    models.Log.mission_id == mission_id,
                    models.Log.id > last_log_id
                ).order_by(models.Log.id.asc()).all()

                for log in new_logs:
                    await websocket.send_json({
                        "type": "log",
                        "level": log.level or "info",
                        "message": log.message,
                        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    })
                    last_log_id = log.id

                # If mission is done, send final status and close
                if mission.status in ("completed", "failed"):
                    await websocket.send_json({
                        "type": "status",
                        "level": "success" if mission.status == "completed" else "error",
                        "message": f"Mission #{mission_id} {mission.status}.",
                    })
                    break

                # Heartbeat
                await websocket.send_json({"type": "heartbeat"})
            finally:
                db.close()

            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
