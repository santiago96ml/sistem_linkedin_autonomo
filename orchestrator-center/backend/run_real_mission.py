"""Launch real mission: Like + Comment on Fabio Romero's post."""
import requests
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://127.0.0.1:8000"
POST_URL = "https://www.linkedin.com/posts/romerofabio_comenta-aprendo-y-te-lo-paso-por-privado-ugcPost-7454701416536842240--h4v"
COMMENT = "Excelente iniciativa! Me encanta la propuesta de aprender y compartir conocimiento. Muy necesario hoy en dia!"

payload = {
    "account_id": 2,
    "tasks": [
        {"type": "reaction", "payload": {"url": POST_URL, "reaction_type": "LIKE"}},
        {"type": "comment", "payload": {"url": POST_URL, "text": COMMENT}}
    ]
}

print("=" * 60)
print("LANZANDO MISION: Like + Comment")
print("=" * 60)
print(f"Post URL: {POST_URL[:60]}...")
print(f"Comment: {COMMENT[:60]}...")
print()

r = requests.post(f"{BASE}/missions/", json=payload)
print(f"Response Status: {r.status_code}")
d = r.json()
mission_id = d.get("id")
print(f"Mission ID: {mission_id}, Initial Status: {d.get('status')}")
print()

# Poll for completion
print("Esperando ejecucion...")
prev_logs = set()
for i in range(40):  # max 120 seconds
    time.sleep(3)
    
    # Check mission status
    mr = requests.get(f"{BASE}/missions/").json()
    m = next((x for x in mr if x["id"] == mission_id), None)
    status = m["status"] if m else "unknown"
    
    # Check new logs
    lr = requests.get(f"{BASE}/logs/").json()
    for log in lr:
        log_key = f"{log['id']}"
        if log_key not in prev_logs:
            level = log["level"].upper()
            symbol = {"INFO": "[*]", "SUCCESS": "[+]", "WARNING": "[!]", "ERROR": "[-]"}.get(level, "[?]")
            print(f"  {symbol} {log['message']}")
            prev_logs.add(log_key)
    
    if status in ["completed", "failed"]:
        print(f"\n{'='*60}")
        if status == "completed":
            print("  MISION COMPLETADA EXITOSAMENTE")
        else:
            print("  MISION FALLIDA")
        print(f"{'='*60}")
        break
    
    elapsed = (i + 1) * 3
    if elapsed % 15 == 0:
        print(f"  ... {elapsed}s transcurridos, status: {status}")

# Final state
print("\n--- ESTADO FINAL ---")
mr = requests.get(f"{BASE}/missions/").json()
for m in mr:
    if m["id"] == mission_id:
        print(f"Mission #{m['id']}: {m['status']}")

lr = requests.get(f"{BASE}/logs/").json()
print(f"\nTotal logs: {len(lr)}")
for log in lr:
    print(f"  [{log['level']}] {log['message']}")

sr = requests.get(f"{BASE}/stats").json()
print(f"\nStats: identities={sr['total_identities']}, active={sr['active_missions']}, success_rate={sr['success_rate']}%, status={sr['system_status']}")
