import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models, database, orchestrator
from database import engine, get_db, SessionLocal
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import datetime
import traceback

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="LinkedIn Orchestrator API")

# Enable CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
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

# --- BACKGROUND TASKS ---
async def run_mission_task(mission_id: int):
    """Bug Fix #3: Usa SessionLocal directamente en lugar de un generator corrupto."""
    db = SessionLocal()
    try:
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

        runner = orchestrator.MissionRunner(account.storage_state, account.proxy_url)

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
    # Fix for Windows asyncio loop policy
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
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

