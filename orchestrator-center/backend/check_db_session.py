import sqlite3
import json

conn = sqlite3.connect("orchestrator.db")
c = conn.cursor()
c.execute("SELECT storage_state FROM accounts WHERE id = 2")
row = c.fetchone()
conn.close()

if row and row[0]:
    state = json.loads(row[0])
    cookies = state.get("cookies", [])
    print(f"Session Size: {len(row[0])} bytes")
    print(f"Cookies Count: {len(cookies)}")
    print("Top Cookies:")
    for ck in cookies[:5]:
        print(f"  {ck['name']}: {ck['value'][:15]}...")
else:
    print("No session found in DB for account 2")
