import sqlite3
import os

DB_PATH = "database/nonprofit_intelligence.db"
SCHEMA_PATH = "database/schema.sql"

def get_connection():
    os.makedirs("database", exist_ok=True)
    return sqlite3.connect(DB_PATH)

def setup_database():
    conn = get_connection()
    cursor = conn.cursor()
    
    with open(SCHEMA_PATH, 'r') as f:
        schema = f.read()
    
    cursor.executescript(schema)
    conn.commit()
    conn.close()
    
    print(f"Database setup complete: {DB_PATH}")

def get_db_path():
    return DB_PATH

if __name__ == "__main__":
    setup_database()
