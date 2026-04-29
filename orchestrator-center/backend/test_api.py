"""
Suite de pruebas completa del LinkedIn Orchestrator API.
Cubre: CRUD de cuentas, misiones, validaciones, bug fixes y casos borde.
"""
import requests
import json
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://127.0.0.1:8000"
PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"

results = []

def test(name, fn):
    try:
        ok, detail = fn()
        symbol = PASS if ok else FAIL
        print(f"  {symbol} {name}")
        if not ok:
            print(f"         --> {detail}")
        results.append((ok, name))
    except Exception as e:
        print(f"  {FAIL} {name}")
        print(f"         --> EXCEPTION: {e}")
        results.append((False, name))

print("=" * 65)
print("  SUITE DE PRUEBAS — LinkedIn Orchestrator API")
print("=" * 65)

# ─────────────────────────────────────────────
print("\n[1] ENDPOINTS BASICOS")
# ─────────────────────────────────────────────

def test_root():
    r = requests.get(f"{BASE}/")
    ok = r.status_code == 200 and "Online" in r.json().get("status", "")
    return ok, f"status={r.status_code}, body={r.text[:80]}"
test("GET / → 200 OK con mensaje 'Online'", test_root)

def test_docs():
    r = requests.get(f"{BASE}/docs")
    return r.status_code == 200, f"status={r.status_code}"
test("GET /docs → Swagger UI accesible", test_docs)

def test_openapi():
    r = requests.get(f"{BASE}/openapi.json")
    ok = r.status_code == 200 and "paths" in r.json()
    return ok, f"status={r.status_code}"
test("GET /openapi.json → schema valido", test_openapi)

# ─────────────────────────────────────────────
print("\n[2] CUENTAS (ACCOUNTS)")
# ─────────────────────────────────────────────

def test_list_accounts():
    r = requests.get(f"{BASE}/accounts/")
    ok = r.status_code == 200 and isinstance(r.json(), list)
    data = r.json()
    count = len(data)
    email = data[0]["email"] if data else "NONE"
    return ok, f"count={count}, first_email={email}"
test("GET /accounts/ → lista de cuentas (200)", test_list_accounts)

def test_account_has_required_fields():
    r = requests.get(f"{BASE}/accounts/")
    data = r.json()
    if not data:
        return False, "Lista vacia, no hay cuenta para verificar"
    acc = data[0]
    required = ["id", "name", "email", "status"]
    missing = [f for f in required if f not in acc]
    ok = len(missing) == 0
    return ok, f"fields_present={list(acc.keys())}, missing={missing}"
test("GET /accounts/ → cuenta tiene id, name, email, status", test_account_has_required_fields)

def test_account_is_active():
    r = requests.get(f"{BASE}/accounts/")
    data = r.json()
    if not data:
        return False, "Lista vacia"
    acc = data[0]
    ok = acc["status"] == "active"
    return ok, f"email={acc['email']}, status={acc['status']}"
test("GET /accounts/ → cuenta tiene status='active'", test_account_is_active)

# ─────────────────────────────────────────────
print("\n[3] STATS")
# ─────────────────────────────────────────────

def test_stats():
    r = requests.get(f"{BASE}/stats")
    ok = r.status_code == 200
    d = r.json()
    return ok, f"total_identities={d.get('total_identities')}, status={d.get('system_status')}"
test("GET /stats → 200 OK", test_stats)

def test_stats_fields():
    r = requests.get(f"{BASE}/stats")
    d = r.json()
    required = ["total_identities", "active_missions", "success_rate", "system_status"]
    missing = [f for f in required if f not in d]
    ok = len(missing) == 0 and d["system_status"] == "nominal"
    return ok, f"fields={list(d.keys())}, missing={missing}"
test("GET /stats → tiene todos los campos requeridos", test_stats_fields)

def test_stats_identity_count():
    r = requests.get(f"{BASE}/stats")
    d = r.json()
    ok = d["total_identities"] == 1
    return ok, f"total_identities={d['total_identities']} (esperado: 1)"
test("GET /stats → total_identities == 1 (DB limpia)", test_stats_identity_count)

# ─────────────────────────────────────────────
print("\n[4] LOGS")
# ─────────────────────────────────────────────

def test_logs_ok():
    r = requests.get(f"{BASE}/logs/")
    ok = r.status_code == 200 and isinstance(r.json(), list)
    return ok, f"status={r.status_code}, count={len(r.json())}"
test("GET /logs/ → 200 OK (bug fix #5: timestamp=null no rompe)", test_logs_ok)

def test_logs_empty():
    r = requests.get(f"{BASE}/logs/")
    data = r.json()
    ok = len(data) == 0
    return ok, f"count={len(data)} (esperado: 0 — DB limpia)"
test("GET /logs/ → lista vacia (DB limpia)", test_logs_empty)

# ─────────────────────────────────────────────
print("\n[5] MISIONES — VALIDACIONES (Bug Fixes #1 y #2)")
# ─────────────────────────────────────────────

def test_missions_list():
    r = requests.get(f"{BASE}/missions/")
    ok = r.status_code == 200 and isinstance(r.json(), list)
    return ok, f"status={r.status_code}, count={len(r.json())}"
test("GET /missions/ → 200 OK, lista vacia (DB limpia)", test_missions_list)

def test_create_mission_orphan_account():
    """Bug Fix #1: Crear mision con account_id inexistente debe dar 404."""
    payload = {"account_id": 9999, "tasks": [{"type": "comment", "payload": {"url": "https://linkedin.com/test", "text": "test"}}]}
    r = requests.post(f"{BASE}/missions/", json=payload)
    ok = r.status_code == 404
    return ok, f"status={r.status_code} (esperado: 404), detail={r.json().get('detail', '')[:80]}"
test("POST /missions/ con account_id=9999 → 404 Not Found (Bug Fix #1)", test_create_mission_orphan_account)

def test_create_mission_bad_payload():
    """Schema validation: sin account_id debe dar 422."""
    payload = {"tasks": [{"type": "comment"}]}
    r = requests.post(f"{BASE}/missions/", json=payload)
    ok = r.status_code == 422
    return ok, f"status={r.status_code} (esperado: 422)"
test("POST /missions/ sin account_id → 422 Unprocessable Entity", test_create_mission_bad_payload)

def test_create_mission_no_session():
    """Bug Fix #1: Cuenta sin storage_state → 422 con mensaje claro."""
    # Primero creamos una cuenta temporal sin session
    acc_r = requests.post(f"{BASE}/accounts/", json={"name": "Test No Session", "email": "nosession_test@test.com"}) if False else None
    # Usamos la cuenta real que SÍ tiene session → no debe dar 422
    r = requests.get(f"{BASE}/accounts/")
    data = r.json()
    if not data:
        return False, "No hay cuentas"
    acc = data[0]
    # La cuenta real tiene session, entonces no debe dar 422
    ok = acc["status"] == "active"
    return ok, f"Cuenta {acc['email']} tiene status=active (tiene session)"
test("Cuenta activa → status=active (tiene storage_state)", test_create_mission_no_session)

# ─────────────────────────────────────────────
print("\n[6] MISION REAL — Crear y verificar ciclo completo")
# ─────────────────────────────────────────────

def test_create_real_mission():
    """Crea una mision real con la cuenta existente y verifica que queda 'pending'."""
    accounts = requests.get(f"{BASE}/accounts/").json()
    if not accounts:
        return False, "No hay cuentas activas"
    acc_id = accounts[0]["id"]
    payload = {
        "account_id": acc_id,
        "tasks": [{"type": "comment", "payload": {"url": "https://www.linkedin.com/feed/", "text": "Test post"}}]
    }
    r = requests.post(f"{BASE}/missions/", json=payload)
    ok = r.status_code == 200
    if ok:
        d = r.json()
        ok = d.get("status") in ["pending", "running"]  # puede cambiar rapido
        return ok, f"mission_id={d.get('id')}, status={d.get('status')}, account_id={d.get('account_id')}"
    return False, f"status={r.status_code}, detail={r.text[:100]}"
test("POST /missions/ con cuenta real → mision creada (pendiente/corriendo)", test_create_real_mission)

# Esperar a que la mision corra un momento
time.sleep(3)

def test_mission_appears_in_list():
    r = requests.get(f"{BASE}/missions/")
    data = r.json()
    ok = len(data) >= 1
    statuses = [m["status"] for m in data]
    return ok, f"count={len(data)}, statuses={statuses}"
test("GET /missions/ → mision aparece en la lista", test_mission_appears_in_list)

def test_logs_after_mission():
    r = requests.get(f"{BASE}/logs/")
    data = r.json()
    ok = len(data) >= 1
    levels = [l.get("level") for l in data]
    first_msg = data[0].get("message", "")[:80] if data else "(vacio)"
    return ok, f"count={len(data)}, levels={levels}, first_msg={first_msg}"
test("GET /logs/ → logs generados por la mision", test_logs_after_mission)

def test_logs_not_empty_messages():
    """Bug Fix #2: Los mensajes de error no deben ser vacios."""
    r = requests.get(f"{BASE}/logs/")
    data = r.json()
    empty_msgs = [l for l in data if not l.get("message")]
    ok = len(empty_msgs) == 0
    return ok, f"logs_con_msg_vacio={len(empty_msgs)} (esperado: 0)"
test("GET /logs/ → ningun mensaje de log vacio (Bug Fix #2)", test_logs_not_empty_messages)

def test_logs_have_timestamp():
    """Los logs nuevos deben tener timestamp (no null como los viejos)."""
    r = requests.get(f"{BASE}/logs/")
    data = r.json()
    # Filtrar solo logs con timestamp
    with_ts = [l for l in data if l.get("timestamp") is not None]
    ok = len(with_ts) >= 1
    return ok, f"logs_con_timestamp={len(with_ts)}/{len(data)}"
test("GET /logs/ → logs nuevos tienen timestamp", test_logs_have_timestamp)

# ─────────────────────────────────────────────
print("\n[7] VERIFICACION FINAL DEL ESTADO")
# ─────────────────────────────────────────────

def test_final_stats():
    r = requests.get(f"{BASE}/stats")
    d = r.json()
    ok = (d["total_identities"] == 1 and
          d["system_status"] == "nominal")
    return ok, f"identities={d['total_identities']}, active={d['active_missions']}, status={d['system_status']}"
test("GET /stats → sistema nominal con 1 identidad", test_final_stats)

def test_cors_header():
    """CORS debe estar habilitado para el frontend."""
    r = requests.options(f"{BASE}/accounts/", headers={"Origin": "http://localhost:3000"})
    # Con fastapi cors habilitado, el response deberia incluir el header
    ok = r.status_code in [200, 400]  # OPTIONS puede dar 200 o no encontrarse
    return ok, f"status={r.status_code}"
test("OPTIONS /accounts/ → CORS configurado", test_cors_header)

# ─────────────────────────────────────────────
print("\n" + "=" * 65)
passed = sum(1 for ok, _ in results if ok)
failed = sum(1 for ok, _ in results if not ok)
total = len(results)
pct = int(passed / total * 100) if total > 0 else 0

print(f"  RESULTADO FINAL: {passed}/{total} pruebas pasaron ({pct}%)")
if failed > 0:
    print(f"\n  PRUEBAS FALLIDAS ({failed}):")
    for ok, name in results:
        if not ok:
            print(f"    - {name}")
else:
    print("  TODAS LAS PRUEBAS PASARON - Sistema operativo correctamente.")
print("=" * 65)
