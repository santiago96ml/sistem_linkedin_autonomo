import urllib.request
import json
import time
import sqlite3

# Launch mission for Morena (account id=3)
data = json.dumps({
    'account_id': 3,
    'tasks': [
        {
            'type': 'reaction',
            'payload': {
                'url': 'https://www.linkedin.com/posts/santiagocosme_he-metido-los-3-libros-de-hormozi-dentro-share-7454787574675570689-qzkd',
                'reaction_type': 'LIKE'
            }
        },
        {
            'type': 'comment',
            'payload': {
                'url': 'https://www.linkedin.com/posts/santiagocosme_he-metido-los-3-libros-de-hormozi-dentro-share-7454787574675570689-qzkd',
                'text': 'Muy interesante enfoque, justo lo que necesitaba leer hoy!'
            }
        }
    ]
}).encode('utf-8')

req = urllib.request.Request(
    'http://localhost:8000/missions/',
    data=data,
    headers={'Content-Type': 'application/json'}
)
resp = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
mission_id = resp['id']
print(f"Mision #{mission_id} creada para Morena — esperando 30s de ejecucion...")

time.sleep(30)

conn = sqlite3.connect('orchestrator-center/backend/orchestrator.db')
c = conn.cursor()

c.execute(f"SELECT id, account_id, status FROM missions WHERE id = {mission_id}")
mission = c.fetchone()
print(f"\nEstado final: {mission}")

c.execute("SELECT message, level FROM logs ORDER BY id DESC LIMIT 8")
logs = c.fetchall()
print("\nUltimos logs:")
for l in logs:
    safe = l[0].encode('ascii', 'ignore').decode()
    print(f"  [{l[1].upper()}] {safe}")

conn.close()
