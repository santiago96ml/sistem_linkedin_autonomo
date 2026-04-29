"""
Limpieza final de la DB del Orchestrator.
Elimina misiones con account_id=1 (cuenta inexistente) y todos sus logs.
"""
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('orchestrator.db')
c = conn.cursor()

print("=" * 60)
print("ESTADO ANTES DE LIMPIAR")
print("=" * 60)

# Mostrar cuentas
c.execute('SELECT id, name, email, status FROM accounts')
accounts = c.fetchall()
print(f"\nCUENTAS ({len(accounts)}):")
for a in accounts:
    print(f"  ID={a[0]} | {a[1]} | {a[2]} | status={a[3]}")

# Mostrar misiones
c.execute('SELECT id, account_id, status FROM missions')
missions = c.fetchall()
print(f"\nMISIONES ({len(missions)}):")
for m in missions:
    print(f"  ID={m[0]} | account_id={m[1]} | status={m[2]}")

# Mostrar logs
c.execute('SELECT id, mission_id, level, message FROM logs ORDER BY id')
logs = c.fetchall()
print(f"\nLOGS ({len(logs)}):")
for l in logs:
    print(f"  ID={l[0]} | mission_id={l[1]} | level={l[2]} | msg={l[3][:60]}")

print("\n" + "=" * 60)
print("EJECUTANDO LIMPIEZA...")
print("=" * 60)

# Encontrar misiones huerfanas (account_id que no existe en accounts)
c.execute('''
    SELECT m.id FROM missions m 
    LEFT JOIN accounts a ON m.account_id = a.id 
    WHERE a.id IS NULL
''')
orphaned_mission_ids = [row[0] for row in c.fetchall()]
print(f"\nMisiones huerfanas encontradas: {orphaned_mission_ids}")

if orphaned_mission_ids:
    # Eliminar logs de misiones huerfanas
    placeholders = ','.join('?' * len(orphaned_mission_ids))
    c.execute(f'DELETE FROM logs WHERE mission_id IN ({placeholders})', orphaned_mission_ids)
    logs_deleted = c.rowcount
    print(f"  -> Logs eliminados: {logs_deleted}")

    # Eliminar misiones huerfanas
    c.execute(f'DELETE FROM missions WHERE id IN ({placeholders})', orphaned_mission_ids)
    missions_deleted = c.rowcount
    print(f"  -> Misiones eliminadas: {missions_deleted}")
else:
    print("  -> No hay misiones huerfanas. DB ya limpia.")

conn.commit()

# Limpiar logs de misiones que no tienen mission_id valido
c.execute('DELETE FROM logs WHERE mission_id IS NULL')
null_logs_deleted = c.rowcount
if null_logs_deleted > 0:
    print(f"  -> Logs sin mission_id eliminados: {null_logs_deleted}")

conn.commit()

print("\n" + "=" * 60)
print("ESTADO FINAL (LIMPIO)")
print("=" * 60)

c.execute('SELECT id, name, email, status FROM accounts')
accounts_after = c.fetchall()
print(f"\nCUENTAS ({len(accounts_after)}):")
for a in accounts_after:
    print(f"  ID={a[0]} | {a[1]} | {a[2]} | status={a[3]}")

c.execute('SELECT id, account_id, status FROM missions')
missions_after = c.fetchall()
print(f"\nMISIONES ({len(missions_after)}):")
if missions_after:
    for m in missions_after:
        print(f"  ID={m[0]} | account_id={m[1]} | status={m[2]}")
else:
    print("  (ninguna - DB limpia)")

c.execute('SELECT id, mission_id, level, message FROM logs ORDER BY id')
logs_after = c.fetchall()
print(f"\nLOGS ({len(logs_after)}):")
if logs_after:
    for l in logs_after:
        print(f"  ID={l[0]} | mission_id={l[1]} | level={l[2]} | msg={l[3][:60]}")
else:
    print("  (ninguno - DB limpia)")

conn.close()
print("\n[OK] Limpieza completada exitosamente.")
