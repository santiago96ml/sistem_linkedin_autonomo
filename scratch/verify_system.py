import sqlite3
import os
import json
import datetime

DB_PATH = "orchestrator-center/backend/orchestrator.db"

def setup_mock_account():
    print("--- Setting up mock account ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Mock storage state
    storage_state = {
        "cookies": [{"name": "li_at", "value": "mock_session_token", "domain": ".linkedin.com", "path": "/"}],
        "origins": []
    }
    
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO accounts (id, name, email, proxy_url, storage_state, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (1, "Test User", "test@example.com", None, json.dumps(storage_state), "active", datetime.datetime.utcnow().isoformat()))
        conn.commit()
        print("Mock account 'test@example.com' created/updated.")
    except Exception as e:
        print(f"Error creating mock account: {e}")
    finally:
        conn.close()

def verify_data():
    print("\n--- Verifying database state ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, email, status FROM accounts;")
    accounts = cursor.fetchall()
    print(f"Accounts in DB: {len(accounts)}")
    for acc in accounts:
        print(acc)
        
    cursor.execute("SELECT COUNT(*) FROM missions;")
    mission_count = cursor.fetchone()[0]
    print(f"Total missions: {mission_count}")
    
    conn.close()

def create_test_mission():
    print("\n--- Creating test mission ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    tasks = [
        {"type": "reaction", "params": {"url": "https://www.linkedin.com/posts/activity-7290000000000000000", "reaction": "LIKE"}},
        {"type": "comment", "params": {"url": "https://www.linkedin.com/posts/activity-7290000000000000000", "text": "Great post!"}}
    ]
    
    try:
        cursor.execute("""
            INSERT INTO missions (account_id, status, tasks, created_at)
            VALUES (?, ?, ?, ?)
        """, (1, "pending", json.dumps(tasks), datetime.datetime.utcnow().isoformat()))
        mission_id = cursor.lastrowid
        conn.commit()
        print(f"Test mission {mission_id} created in 'pending' state.")
    except Exception as e:
        print(f"Error creating mission: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"Warning: Database not found at {DB_PATH}. It might be created on first run of the app.")
        # Attempt to create tables if they don't exist (simplified)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, proxy_url TEXT, storage_state TEXT, status TEXT, created_at TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS missions (id INTEGER PRIMARY KEY, account_id INTEGER, status TEXT, tasks TEXT, created_at TEXT, executed_at TEXT)")
        cursor.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, mission_id INTEGER, message TEXT, level TEXT, timestamp TEXT)")
        conn.commit()
        conn.close()
        
    setup_mock_account()
    verify_data()
    create_test_mission()
    verify_data()
