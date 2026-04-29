import asyncio
import sys
import os
import json

# Add orchestrator-center/backend to sys.path
sys.path.append(os.path.join(os.getcwd(), "orchestrator-center", "backend"))

import orchestrator
import models
import database

async def debug_mission():
    # Use absolute path for DB
    db_path = os.path.join(os.getcwd(), "orchestrator-center", "backend", "orchestrator.db")
    engine = database.create_engine(f"sqlite:///{db_path}")
    database.SessionLocal.configure(bind=engine)
    db = database.SessionLocal()
    account = db.query(models.Account).filter(models.Account.id == 2).first()
    if not account:
        print("Account not found")
        return
    
    print(f"--- Debugging Mission for {account.email} ---")
    tasks = [
        {
            "type": "comment",
            "payload": {
                "url": "https://www.linkedin.com/posts/romerofabio_%C3%BA%F0%9D%97%9F%F0%9D%97%A7%F0%9D%97%9C%F0%9D%97%A0%F0%9D%97%94-%F0%9D%97%9B%F0%9D%97%A2%F0%9D%97%A5%F0%9D%97%94-%F0%9D%97%9F%F0%9D%97%AE-%F0%9D%97%BF%F0%9D%97%B2%F0%9D%97%AE%F0%9D%97%B9%F0%9D%97%B6%F0%9D%97%B1%F0%9D%97%AE%F0%9D%97%B1-ugcPost-7452166043847843840-I8Tf",
                "text": "Prueba de autonomía exitosa. ¡Excelente contenido!"
            }
        }
    ]
    
    runner = orchestrator.MissionRunner(account.storage_state, account.proxy_url)
    try:
        results = await runner.execute_mission(tasks)
        print(f"Results: {results}")
    except Exception as e:
        print(f"EXCEPTION: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(debug_mission())
