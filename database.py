import sqlite3
from datetime import datetime

DB_NAME = "/app/data/leads.db"

def init_db():
    """Создает таблицу для заявок, если её еще нет"""
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
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_lead(user_id, username, service, name, phone, comment):
    """Сохраняет новую заявку в базу данных"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO leads (user_id, username, service, name, phone, comment, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, username, service, name, phone, comment, now))
    conn.commit()
    lead_id = cursor.lastrowid
    conn.close()
    return lead_id

def get_recent_leads(limit=10):
    """Возвращает последние заявки для админ-панели"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, created_at, service, name, phone FROM leads ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows