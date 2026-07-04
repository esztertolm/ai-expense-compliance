import sqlite3
import pandas as pd

DB_FILE = "audit_logs.db"

def init_db():
    """Initializes the SQLite database and creates the audit table if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            vendor TEXT,
            amount INTEGER,
            status TEXT,
            manager_notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_audit_log(vendor: str, amount: int, status: str, manager_notes: str):
    """Saves a finalized audit record into the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audit_history (vendor, amount, status, manager_notes)
        VALUES (?, ?, ?, ?)
    ''', (vendor, amount, status, manager_notes))
    conn.commit()
    conn.close()

def get_audit_history() -> pd.DataFrame:
    """Retrieves the audit history as a Pandas DataFrame for Streamlit."""
    conn = sqlite3.connect(DB_FILE)
    # Pandas makes it incredibly easy to load SQL directly into a table
    df = pd.read_sql_query("SELECT timestamp, vendor, amount, status, manager_notes FROM audit_history ORDER BY timestamp DESC", conn)
    conn.close()
    return df