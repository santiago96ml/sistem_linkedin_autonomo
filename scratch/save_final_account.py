import sqlite3
import os
import json
import datetime
import sys

# Add orchestrator-center/backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "orchestrator-center", "backend"))

import models
import database

def save_final_account(email, name, li_at, jsessionid):
    # Use absolute path for DB
    db_path = os.path.join(os.getcwd(), "orchestrator-center", "backend", "orchestrator.db")
    engine = database.create_engine(f"sqlite:///{db_path}")
    database.SessionLocal.configure(bind=engine)
    db = database.SessionLocal()
    
    # Construct storageState
    storage_state = {
        "cookies": [
            {
                "name": "li_at",
                "value": li_at,
                "domain": ".www.linkedin.com",
                "path": "/",
                "expires": -1,
                "httpOnly": True,
                "secure": True,
                "sameSite": "None"
            },
            {
                "name": "JSESSIONID",
                "value": f'"{jsessionid}"',
                "domain": ".www.linkedin.com",
                "path": "/",
                "expires": -1,
                "httpOnly": False,
                "secure": True,
                "sameSite": "None"
            }
        ],
        "origins": []
    }
    
    try:
        # Check if account already exists
        acc = db.query(models.Account).filter(models.Account.email == email).first()
        if acc:
            acc.storage_state = storage_state
            acc.status = "active"
            acc.name = name
            print(f"Updated account: {email}")
        else:
            acc = models.Account(
                name=name,
                email=email,
                storage_state=storage_state,
                status="active",
                created_at=datetime.datetime.utcnow()
            )
            db.add(acc)
            print(f"Created new account: {email}")
        db.commit()
        print("SUCCESS: Account linked and configured.")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    email = "mmorenadiaz.lk@gmail.com"
    name = "Morena Diaz"
    li_at = "AQEDAWd4IKgBNTUBAAABndXEUkEAAAGd-dDWQU0AEmQP7QOpH5WuuEgF__Wym7hbn6MmLbjXKH9Bjfyiljv7IB_H61gHXQzOWPOf6TjwGFNx7jwq2DktLrtkX9q2-yyJbQM-dF4yZZO0jRXtitNR0elw"
    jsessionid = "ajax:8986916462430717318"
    
    save_final_account(email, name, li_at, jsessionid)
