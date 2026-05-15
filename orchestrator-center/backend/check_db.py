from database import SessionLocal
import models
db = SessionLocal()
accounts = db.query(models.Account).all()
for a in accounts:
    print(f"ID: {a.id}, Email: {a.email}, Has State: {a.storage_state is not None}")
db.close()
