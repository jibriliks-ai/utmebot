"""
user_manager.py — users, daily limits, premium, mock history, top scorer.
"""
import sqlite3
from datetime import datetime, timedelta

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
            first_name TEXT,
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
    c.execute("""
        CREATE TABLE IF NOT EXISTS mock_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            score INTEGER,
            total INTEGER,
            mock_type TEXT DEFAULT 'free',
            taken_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS top_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            display_name TEXT,
            score INTEGER,
            total INTEGER,
            taken_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_or_create_user(user_id, username=None, first_name=None):
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row is None:
        c.execute(
            "INSERT INTO users (user_id, username, first_name, created_at) "
            "VALUES (?, ?, ?, ?)",
            (user_id, username or "", first_name or "", datetime.now().isoformat()),
        )
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
    else:
        # Keep name fresh
        c.execute(
            "UPDATE users SET username = COALESCE(NULLIF(?, ''), username), "
            "first_name = COALESCE(NULLIF(?, ''), first_name) WHERE user_id = ?",
            (username or "", first_name or "", user_id),
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


def record_mock_taken(user_id, score=None, total=None, mock_type="free"):
    conn = _conn()
    conn.execute(
        "UPDATE users SET last_mock_time = ? WHERE user_id = ?",
        (datetime.now().isoformat(), user_id),
    )
    if score is not None and total is not None:
        conn.execute(
            "INSERT INTO mock_history (user_id, score, total, mock_type, taken_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, score, total, mock_type, datetime.now().isoformat()),
        )
    conn.commit()
    conn.close()


def record_top_score(user_id, display_name, score, total):
    """Store a paid-mock score. Keeps only the highest per user."""
    conn = _conn()
    c = conn.cursor()
    c.execute(
        "SELECT id, score FROM top_scores WHERE user_id = ? ORDER BY score DESC LIMIT 1",
        (user_id,),
    )
    existing = c.fetchone()
    if existing and existing["score"] >= score:
        conn.close()
        return False
    if existing:
        c.execute("DELETE FROM top_scores WHERE user_id = ?", (user_id,))
    c.execute(
        "INSERT INTO top_scores (user_id, display_name, score, total, taken_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, display_name, score, total, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return True


def get_top_scorer():
    """Return the single highest score across all paid mocks, or None."""
    conn = _conn()
    c = conn.cursor()
    c.execute(
        "SELECT display_name, score, total, taken_at FROM top_scores "
        "ORDER BY (CAST(score AS FLOAT) / total) DESC, score DESC LIMIT 1"
    )
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def get_top_scorers(limit=5):
    conn = _conn()
    c = conn.cursor()
    c.execute(
        "SELECT display_name, score, total FROM top_scores "
        "ORDER BY (CAST(score AS FLOAT) / total) DESC, score DESC LIMIT ?",
        (limit,),
    )
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_mock_stats(user_id):
    """Return (total_mocks, best_score, best_total, avg_percent)."""
    conn = _conn()
    c = conn.cursor()
    c.execute(
        "SELECT score, total FROM mock_history WHERE user_id = ? ORDER BY taken_at DESC",
        (user_id,),
    )
    rows = c.fetchall()
    conn.close()
    if not rows:
        return 0, 0, 0, 0
    total_mocks = len(rows)
    best = max(rows, key=lambda r: (r["score"] / r["total"]) if r["total"] else 0)
    best_score = best["score"]
    best_total = best["total"]
    avg = sum((r["score"] / r["total"] * 100) for r in rows if r["total"]) / total_mocks
    return total_mocks, best_score, best_total, round(avg, 1)


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
