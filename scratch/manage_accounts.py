import sqlite3
import os

db_path = os.path.join(os.getcwd(), "orchestrator-center", "backend", "orchestrator.db")

def manage_accounts():
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List all accounts
    cursor.execute("SELECT id, email, status FROM accounts")
    accounts = cursor.fetchall()
    print("--- Current Accounts ---")
    for acc in accounts:
        print(f"ID: {acc[0]}, Email: {acc[1]}, Status: {acc[2]}")
        
    # Delete test account
    cursor.execute("DELETE FROM accounts WHERE email LIKE '%test%' OR email = 'test@example.com'")
    deleted = cursor.rowcount
    if deleted > 0:
        print(f"\nDeleted {deleted} test account(s).")
        conn.commit()
    else:
        print("\nNo test accounts found to delete.")
        
    # List again
    cursor.execute("SELECT id, email, status FROM accounts")
    remaining = cursor.fetchall()
    print("\n--- Remaining Accounts ---")
    for acc in remaining:
        print(f"ID: {acc[0]}, Email: {acc[1]}, Status: {acc[2]}")
        
    conn.close()

if __name__ == "__main__":
    manage_accounts()
