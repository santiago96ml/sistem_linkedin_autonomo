import sqlite3
import os

db_path = "orchestrator-center/backend/orchestrator.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("--- MISSION STATUS ---")
    cursor.execute("SELECT id, status, executed_at FROM missions ORDER BY id DESC LIMIT 5;")
    for m in cursor.fetchall():
        print(m)

    print("\n--- LOGS FOR LAST MISSION ---")
    cursor.execute("SELECT mission_id, message, level, timestamp FROM logs ORDER BY id DESC LIMIT 10;")
    for log in cursor.fetchall():
        print(log)
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
