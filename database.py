# database.py — handles all chat history storage using SQLite

import sqlite3
from datetime import datetime

DB_PATH = "tutor.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        )
    """)
    conn.commit()
    conn.close()

def create_session():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO sessions (created_at) VALUES (?)",
        (datetime.now().isoformat(),)
    )
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    return session_id

def save_message(session_id: int, role: str, content: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, role, content, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def load_session(session_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id",
        (session_id,)
    )
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows]

def list_sessions():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT s.id, s.created_at, COUNT(m.id) as msg_count
        FROM sessions s
        LEFT JOIN messages m ON m.session_id = s.id
        GROUP BY s.id
        ORDER BY s.id DESC
    """)
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "created_at": r[1], "msg_count": r[2]} for r in rows]

def delete_session(session_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()