import sqlite3

def migrate():
    conn = sqlite3.connect('orchestrator.db')
    cursor = conn.cursor()
    
    # Columns for accounts table
    accounts_columns = [
        ('profile_pic_url', 'TEXT'),
        ('created_at', 'DATETIME')
    ]
    
    for col_name, col_type in accounts_columns:
        try:
            cursor.execute(f"ALTER TABLE accounts ADD COLUMN {col_name} {col_type}")
            print(f"Added column to accounts: {col_name}")
        except sqlite3.OperationalError:
            print(f"Column {col_name} already exists in accounts")

    # Columns for warmup_configs table
    warmup_columns = [
        ('current_trust_level', 'INTEGER DEFAULT 1'),
        ('vip_profiles', 'JSON'),
        ('start_date', 'DATETIME'),
        ('languages', 'TEXT DEFAULT "Spanish, English"'),
        ('tone_modifiers', 'TEXT DEFAULT "Professional, Helpful"')
    ]
    
    for col_name, col_type in warmup_columns:
        try:
            cursor.execute(f"ALTER TABLE warmup_configs ADD COLUMN {col_name} {col_type}")
            print(f"Added column to warmup_configs: {col_name}")
        except sqlite3.OperationalError:
            print(f"Column {col_name} already exists in warmup_configs")
            
    # Set default created_at for old accounts
    cursor.execute("UPDATE accounts SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    
    conn.commit()
    conn.close()
    print("Migration finished successfully")

if __name__ == "__main__":
    migrate()
