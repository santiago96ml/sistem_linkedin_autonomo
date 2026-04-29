"""Script de limpieza de DB: corrige misiones huerfanas y reporta estado del sistema."""
import sqlite3
import datetime
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('orchestrator.db')
c = conn.cursor()

print("=" * 50)
print("ESTADO ANTES DE LIMPIAR")
print("=" * 50)
accounts = c.execute("SELECT id, name, email, status, storage_state IS NOT NULL as has_session FROM accounts").fetchall()
missions = c.execute("SELECT id, account_id, status FROM missions").fetchall()
logs = c.execute("SELECT id, mission_id, message, level FROM logs ORDER BY id").fetchall()

print(f"CUENTAS ({len(accounts)} total):")
for a in accounts:
    print(f"  id={a[0]} name={a[1]} email={a[2]} status={a[3]} has_session={bool(a[4])}")

print(f"\nMISIONES ({len(missions)} total):")
for m in missions:
    print(f"  id={m[0]} account_id={m[1]} status={m[2]}")

print(f"\nLOGS ({len(logs)} total):")
for l in logs:
    msg = l[2][:80] if l[2] else "(empty)"
    print(f"  id={l[0]} mission_id={l[1]} level={l[3]} msg={msg}")

# Corregir misiones huerfanas (account_id no existe en accounts)
c.execute("""
    UPDATE missions 
    SET status='failed' 
    WHERE status='pending' 
    AND account_id NOT IN (SELECT id FROM accounts)
""")
orphans_fixed = c.rowcount
print(f"\n[OK] Misiones huerfanas corregidas a 'failed': {orphans_fixed}")

# Insertar log explicativo para la mission huerfana
c.execute(
    "INSERT INTO logs (mission_id, message, level) VALUES (?, ?, ?)",
    (1, "Error: Account ID 1 not found in database. Mission was orphaned. Fixed by cleanup script.", "error")
)

conn.commit()

print("\n" + "=" * 50)
print("ESTADO FINAL")
print("=" * 50)
accounts_final = c.execute("SELECT id, name, email, status, storage_state IS NOT NULL as has_session FROM accounts").fetchall()
missions_final = c.execute("SELECT id, account_id, status FROM missions").fetchall()

active_count = len([a for a in accounts_final if a[3] == 'active'])
print(f"CUENTAS ACTIVAS: {active_count}/{len(accounts_final)}")
for a in accounts_final:
    session_str = "HAS_SESSION" if a[4] else "NO_SESSION"
    print(f"  [{a[3].upper()}] id={a[0]} | {a[1]} | {a[2]} | {session_str}")

print(f"\nRESUMEN DE MISIONES ({len(missions_final)} total):")
for m in missions_final:
    print(f"  Mission id={m[0]} -> account_id={m[1]} -> status={m[2]}")

pending = sum(1 for m in missions_final if m[2] == 'pending')
failed = sum(1 for m in missions_final if m[2] == 'failed')
completed = sum(1 for m in missions_final if m[2] == 'completed')
print(f"\n  Pending={pending} | Failed={failed} | Completed={completed}")
print(f"\nCONTEO FINAL: {len(accounts_final)} cuenta(s) en el sistema")

conn.close()
print("\nDB cleanup completado exitosamente.")
