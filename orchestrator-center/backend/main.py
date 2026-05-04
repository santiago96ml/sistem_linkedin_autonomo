import sys
import asyncio
import logging

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

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import models, database, orchestrator
import os
from database import engine, get_db, SessionLocal
from pydantic import BaseModel, ConfigDict
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

# Ensure static dir exists
os.makedirs("static/screenshots", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

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

# --- BACKGROUND TASKS ---
async def run_mission_task(mission_id: int):
    """Bug Fix #3: Usa SessionLocal directamente en lugar de un generator corrupto."""
    db = SessionLocal()
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
            db.add(models.Log(
                mission_id=mission_id,
                message=f"Error: Account ID {mission.account_id} not found in database. Mission is orphaned.",
                level="error"
            ))
            db.commit()
            return

        if not account.storage_state:
            mission.status = "failed"
            db.add(models.Log(
                mission_id=mission_id,
                message=f"Error: Account '{account.email}' has no active session. Please log in first.",
                level="error"
            ))
            db.commit()
            return

        # --- WARM-UP LOGIC: Daily Limits ---
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        if account.last_action_date != today:
            account.daily_action_count = 0
            account.last_action_date = today
            db.commit()

        # Si est en calentamiento, lmite estricto de 10 acciones (likes + comentarios)
        MAX_WARMUP_ACTIONS = 10
        if account.is_warming_up and account.daily_action_count >= MAX_WARMUP_ACTIONS:
            mission.status = "failed"
            db.add(models.Log(
                mission_id=mission_id,
                message=f"BLOQUEO DE SEGURIDAD: La cuenta '{account.email}' est en modo CALENTAMIENTO y ha superado el lmite de {MAX_WARMUP_ACTIONS} acciones diarias.",
                level="warning"
            ))
            db.commit()
            return

        runner = orchestrator.MissionRunner(account.storage_state, account.proxy_url, account_id=account.id)

        try:
            db.add(models.Log(
                mission_id=mission_id,
                message=f"Starting mission with {len(mission.tasks)} tasks for account '{account.email}'."
            ))
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
                db.add(models.Log(
                    mission_id=mission_id,
                    message=log_msg,
                    level="success" if is_success else "warning"
                ))

        except Exception as e:
            # Bug Fix #2: Captura traceback completo, no solo str(e)
            tb = traceback.format_exc()
            mission.status = "failed"
            db.add(models.Log(
                mission_id=mission_id,
                message=f"Mission error: {type(e).__name__}: {str(e) or 'no message'}\n{tb[:1000]}",
                level="error"
            ))

        db.commit()
    finally:
        db.close()  # Siempre liberar la sesión

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

from fastapi import WebSocket, WebSocketDisconnect
import json

@app.websocket("/ws/live/{account_id}")
async def live_stream(websocket: WebSocket, account_id: int):
    logger.info(f"WS: Connection attempt for account {account_id}")
    await websocket.accept()
    logger.info(f"WS: Connection accepted for account {account_id}")
    try:
        while True:
            # 1. Listen for input commands from frontend
            try:
                # Use wait_for to avoid blocking indefinitely
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                cmd = json.loads(data)
                
                # Relay command to BrowserManager
                page = orchestrator.BrowserManager._instances.get(account_id, {}).get("page")
                if page:
                    if cmd["type"] == "click":
                        await page.mouse.click(cmd["x"], cmd["y"])
                    elif cmd["type"] == "type":
                        await page.keyboard.type(cmd["text"])
                    elif cmd["type"] == "press":
                        await page.keyboard.press(cmd["key"])
            except asyncio.TimeoutError:
                pass
            
            # 2. Send current screenshot back
            import base64
            screenshot_path = f"static/screenshots/account_{account_id}.png"
            if os.path.exists(screenshot_path):
                with open(screenshot_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode('utf-8')
                    await websocket.send_json({"type": "stream", "image": encoded})
            
            await asyncio.sleep(0.5) # Stream at ~2fps
    except WebSocketDisconnect:
        logger.info(f"Live stream disconnected for account {account_id}")
    except Exception as e:
        logger.error(f"WS Error: {e}")

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


# ─────────────────────────────────────────────────
# BULK MISSION  (multi-account + human delays + AI rephrase)
# ─────────────────────────────────────────────────

import random
import re as _re

def _rephrase_comment(original: str, account_index: int) -> str:
    """
    Lightweight AI-style rephraser that produces a unique variant of `original`
    for each account without needing an external API.
    Strategy: sentence-level shuffling + synonym map + emoji rotation.
    """
    synonyms = {
        r"\bde acuerdo\b": ["totalmente de acuerdo", "de acuerdo contigo", "en la misma línea"],
        r"\bgenial\b": ["excelente", "fantástico", "muy bueno"],
        r"\binteresante\b": ["fascinante", "muy valioso", "relevante"],
        r"\bclave\b": ["fundamental", "esencial", "determinante"],
        r"\bimportante\b": ["crucial", "significativo", "relevante"],
        r"\bgracias\b": ["muchas gracias", "muy agradecido", "agradezco"],
        r"\bcompartir\b": ["difundir", "publicar", "mostrar"],
        r"\benfoque\b": ["perspectiva", "visión", "punto de vista"],
        r"\bincreíble\b": ["sorprendente", "notable", "impresionante"],
        r"\bfantástico\b": ["maravilloso", "excelente", "estupendo"],
        r"\bseguro\b": ["sin duda", "definitivamente", "con certeza"],
        r"\btrabajo\b": ["esfuerzo", "contenido", "aporte"],
    }
    openers = [
        "", "Completamente de acuerdo. ", "Muy buen punto. ", "Excelente reflexión. ",
        "Gran aporte. ", "100% de acuerdo. ", "Interesante perspectiva. "
    ]
    closers = [
        "", " 👏", " 🙌", " 💡", " 🔥", " ✅", "!", " 💯"
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
        closer = rng.choice([" 👏", " 🙌", " 💡", " ✅"])
        
    result = opener + result.strip() + closer

    return result


class BulkMissionBase(BaseModel):
    account_ids: List[int]         # IDs de las cuentas, vacío = todas las activas
    tasks: List[dict]              # mismas tareas para todos
    comment_mode: str = "literal"  # "literal" | "ai"
    delay_min: int = 30            # segundos mínimos entre cuentas
    delay_max: int = 120           # segundos máximos entre cuentas


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
    # Resolve accounts: if empty list → all active accounts
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

# ─────────────────────────────────────────────────
# AUTOPILOT (Target Profiles & Scheduling)
# ─────────────────────────────────────────────────

import autopilot

@app.on_event("startup")
async def startup_event():
    # Start the autopilot scheduler loop in the background
    asyncio.create_task(autopilot.start_autopilot_scheduler())

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

