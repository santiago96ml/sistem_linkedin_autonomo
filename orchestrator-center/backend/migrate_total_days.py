import sqlite3

conn = sqlite3.connect("orchestrator.db")
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE warmup_configs ADD COLUMN total_days INTEGER DEFAULT 120;")
    print("Column total_days added to warmup_configs")
except Exception as e:
    print(f"Error: {e}")

conn.commit()
conn.close()
