import sqlite3
from datetime import datetime

DB_NAME = "/app/data/leads.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            service TEXT,
            name TEXT,
            phone TEXT,
            comment TEXT,
            status TEXT DEFAULT 'new',
            appointment_at TEXT,  -- НОВОЕ ПОЛЕ: храним время записи
            created_at TEXT
        )
    """)
    # Безопасная миграция для старых баз
    cursor.execute("PRAGMA table_info(leads)")
    columns = [info[1] for info in cursor.fetchall()]
    if "status" not in columns:
        cursor.execute("ALTER TABLE leads ADD COLUMN status TEXT DEFAULT 'new'")
    if "appointment_at" not in columns:
        cursor.execute("ALTER TABLE leads ADD COLUMN appointment_at TEXT")
        
    conn.commit()
    conn.close()

def add_lead(user_id, username, service, name, phone, comment, appointment_at):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO leads (user_id, username, service, name, phone, comment, appointment_at, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?)
    """, (user_id, username, service, name, phone, comment, appointment_at, now))
    conn.commit()
    lead_id = cursor.lastrowid
    conn.close()
    return lead_id

def get_leads_by_status(status, limit=10):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, created_at, service, name, phone, comment, username 
        FROM leads WHERE status = ? ORDER BY id DESC LIMIT ?
    """, (status, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_lead_status(lead_id, new_status):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET status = ? WHERE id = ?", (new_status, lead_id))
    conn.commit()
    conn.close()

def count_leads_by_status():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) FROM leads GROUP BY status")
    rows = cursor.fetchall()
    conn.close()
    return dict(rows)

def get_all_leads():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, created_at, service, name, phone, comment FROM leads ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows

def is_slot_taken(appointment_at):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Ищем заявки на это время, у которых статус не "cancelled" (не отменена)
    cursor.execute("SELECT COUNT(*) FROM leads WHERE appointment_at = ? AND status != 'cancelled'", (appointment_at,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

