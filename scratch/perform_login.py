import asyncio
import sys
import os
import json

# Add orchestrator-center/backend to sys.path to import orchestrator and models
sys.path.append(os.path.join(os.getcwd(), "orchestrator-center", "backend"))

import orchestrator
import models
import database
from sqlalchemy.orm import Session

async def run_login(email, password):
    print(f"[DEBUG] Starting Login process for {email}")
    manager = orchestrator.GuidedLogin(email, password)
    status = await manager.start()
    print(f"[DEBUG] Initial login status: {status}")
    
    if status == "success":
        print("[DEBUG] Login successful immediately.")
        storage_state = await manager.context.storage_state()
        save_account(email, storage_state)
        await manager.browser.close()
        await manager.p.stop()
        return "SUCCESS"
    
    elif status == "2fa_required":
        print("[DEBUG] 2FA required. Waiting for code in scratch/2fa_code.txt")
        code = None
        for i in range(60): # 5 minutes
            if os.path.exists("scratch/2fa_code.txt"):
                with open("scratch/2fa_code.txt", "r") as f:
                    code = f.read().strip()
                print(f"[DEBUG] Found code in file: {code}")
                if code:
                    os.remove("scratch/2fa_code.txt")
                    break
            if i % 6 == 0: # Print every 30 seconds
                print(f"[DEBUG] Still waiting... ({i*5}s)")
            await asyncio.sleep(5)
        
        if code:
            print(f"[DEBUG] Submitting 2FA code...")
            state = await manager.submit_code(code)
            if state:
                print(f"[DEBUG] 2FA submission SUCCESS.")
                save_account(email, state)
                return "SUCCESS"
            else:
                print(f"[DEBUG] 2FA submission FAILED.")
                return "FAILED"
        else:
            print("[DEBUG] Timeout waiting for code.")
            await manager.browser.close()
            await manager.p.stop()
            return "TIMEOUT"
    
    else:
        print(f"[DEBUG] Login failed with status: {status}")
        await manager.browser.close()
        await manager.p.stop()
        return "FAILED"

def save_account(email, storage_state):
    print(f"[DEBUG] Saving account {email} to database...")
    db = database.SessionLocal()
    try:
        acc = db.query(models.Account).filter(models.Account.email == email).first()
        if acc:
            acc.storage_state = storage_state
            acc.status = "active"
            print(f"[DEBUG] Updated existing account: {email}")
        else:
            acc = models.Account(
                name=email.split('@')[0],
                email=email,
                storage_state=storage_state,
                status="active"
            )
            db.add(acc)
            print(f"[DEBUG] Created new account: {email}")
        db.commit()
    except Exception as e:
        print(f"[DEBUG] Error saving to DB: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    email = "mmorenadiaz.lk@gmail.com"
    password = "Leadlinked.ai2026#"
    asyncio.run(run_login(email, password))
