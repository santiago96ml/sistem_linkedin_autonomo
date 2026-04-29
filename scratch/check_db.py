import sqlite3
import os

db_path = "orchestrator-center/backend/orchestrator.db"
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, name, email, status FROM accounts;")
        accounts = cursor.fetchall()
        print(f"Found {len(accounts)} accounts:")
        for acc in accounts:
            print(acc)
        
        cursor.execute("SELECT id, status, created_at FROM missions;")
        missions = cursor.fetchall()
        print(f"\nFound {len(missions)} missions:")
        for m in missions:
            print(m)
    except Exception as e:
        print(f"Error: {e}")
    conn.close()
