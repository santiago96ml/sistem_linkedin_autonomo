import time
import sqlite3

print("Esperando 25s que el backend ejecute la mision #15...")
time.sleep(25)

conn = sqlite3.connect('orchestrator-center/backend/orchestrator.db')
c = conn.cursor()

c.execute("SELECT id, account_id, status FROM missions WHERE id = 15")
mission = c.fetchone()
print(f"\nEstado mision 15: {mission}")

c.execute("SELECT message, level FROM logs ORDER BY id DESC LIMIT 10")
logs = c.fetchall()
print("\nUltimos 10 logs:")
for l in logs:
    safe = l[0].encode('ascii', 'ignore').decode()
    print(f"  [{l[1].upper()}] {safe}")

conn.close()
