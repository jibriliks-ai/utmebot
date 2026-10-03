"""
user_manager.py
Handles user data, daily free-mock limits, and premium status.
Uses SQLite so no external database is needed.
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = "users.db"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_premium INTEGER DEFAULT 0,
            premium_expires TEXT,
            last_mock_time TEXT,
            referral_count INTEGER DEFAULT 0,
            referred_by INTEGER,
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER UNIQUE,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_or_create_user(user_id, username=None):
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row is None:
        c.execute(
            "INSERT INTO users (user_id, username, created_at) VALUES (?, ?, ?)",
            (user_id, username or "", datetime.now().isoformat()),
        )
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
    conn.close()
    return dict(row)


def is_premium(user_id):
    user = get_or_create_user(user_id)
    if not user["is_premium"]:
        return False
    expires = user.get("premium_expires")
    if expires:
        try:
            if datetime.fromisoformat(expires) < datetime.now():
                conn = _conn()
                conn.execute("UPDATE users SET is_premium = 0 WHERE user_id = ?", (user_id,))
                conn.commit()
                conn.close()
                return False
        except Exception:
            pass
    return True


def set_premium(user_id, days=30):
    expires = (datetime.now() + timedelta(days=days)).isoformat()
    conn = _conn()
    conn.execute(
        "UPDATE users SET is_premium = 1, premium_expires = ? WHERE user_id = ?",
        (expires, user_id),
    )
    conn.commit()
    conn.close()


def can_take_mock(user_id):
    if is_premium(user_id):
        return True, None

    user = get_or_create_user(user_id)
    last = user.get("last_mock_time")
    if not last:
        return True, None

    try:
        last_dt = datetime.fromisoformat(last)
    except Exception:
        return True, None

    next_allowed = last_dt + timedelta(hours=24)
    now = datetime.now()
    if now >= next_allowed:
        return True, None

    remaining = next_allowed - now
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)
    return False, f"{hours}h {minutes}m"


def record_mock_taken(user_id):
    conn = _conn()
    conn.execute(
        "UPDATE users SET last_mock_time = ? WHERE user_id = ?",
        (datetime.now().isoformat(), user_id),
    )
    conn.commit()
    conn.close()


def record_referral(referrer_id, referred_id):
    if referrer_id == referred_id:
        return False
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO referrals (referrer_id, referred_id, created_at) VALUES (?, ?, ?)",
            (referrer_id, referred_id, datetime.now().isoformat()),
        )
        conn.execute(
            "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?",
            (referrer_id,),
        )
        conn.execute(
            "UPDATE users SET referred_by = ? WHERE user_id = ?",
            (referrer_id, referred_id),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def get_referral_count(user_id):
    user = get_or_create_user(user_id)
    return user.get("referral_count", 0)


init_db()