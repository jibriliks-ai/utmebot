"""
Run this ONCE on your local machine to migrate user_data.json → PostgreSQL.
Usage:
    export DATABASE_URL="<your External Database URL>"
    python migrate_to_postgres.py
"""
import os, json, sys, hashlib
from pathlib import Path

import psycopg2

JSON_FILE = Path("user_data.json")
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ Set DATABASE_URL environment variable first.")
    sys.exit(1)

if not JSON_FILE.exists():
    print("❌ user_data.json not found in current directory.")
    sys.exit(1)

data = json.loads(JSON_FILE.read_text(encoding="utf-8"))
print(f"📦 Found {len(data)} users in JSON")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

# Ensure table exists (in case you haven't deployed the new main.py yet)
cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        uid TEXT PRIMARY KEY,
        username TEXT DEFAULT 'Student',
        phone TEXT,
        invite_code TEXT UNIQUE,
        invited_by TEXT,
        invites INTEGER DEFAULT 0,
        invited_users JSONB DEFAULT '[]'::jsonb,
        referral_rewards_claimed INTEGER DEFAULT 0,
        is_premium BOOLEAN DEFAULT FALSE,
        premium_until TEXT,
        premium_plan TEXT,
        jamb_plan JSONB DEFAULT '["english"]'::jsonb,
        plan_set BOOLEAN DEFAULT FALSE,
        free_english_used BOOLEAN DEFAULT FALSE,
        tutor_counts JSONB DEFAULT '{}'::jsonb,
        ai_why_counts JSONB DEFAULT '{}'::jsonb,
        history JSONB DEFAULT '[]'::jsonb,
        last_mock_failed JSONB DEFAULT '[]'::jsonb,
        last_mock_subject TEXT,
        last_mock_total INTEGER DEFAULT 40,
        used_ids JSONB DEFAULT '[]'::jsonb,
        linked_widget_uid TEXT,
        linked_tg_uid TEXT,
        linked_device_id TEXT,
        joined TEXT DEFAULT CURRENT_DATE::text
    );
""")

migrated = 0
for uid, u in data.items():
    invite_code = u.get("invite_code") or hashlib.md5(str(uid).encode()).hexdigest()[:6].upper()
    cur.execute("""
        INSERT INTO users (
            uid, username, phone, invite_code, invited_by,
            invites, invited_users, referral_rewards_claimed,
            is_premium, premium_until, premium_plan,
            jamb_plan, plan_set, free_english_used,
            tutor_counts, ai_why_counts, history,
            last_mock_failed, last_mock_subject, last_mock_total,
            used_ids, linked_widget_uid, linked_tg_uid, linked_device_id
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (uid) DO NOTHING
    """, (
        str(uid),
        u.get("username", "Student"),
        u.get("phone"),
        invite_code,
        u.get("invited_by"),
        u.get("invites", 0),
        json.dumps(u.get("invited_users", [])),
        u.get("referral_rewards_claimed", 0),
        u.get("is_premium", False),
        u.get("premium_until"),
        u.get("premium_plan"),
        json.dumps(u.get("jamb_plan", ["english"])),
        u.get("plan_set", False),
        u.get("free_english_used", False),
        json.dumps(u.get("tutor_counts", {})),
        json.dumps(u.get("ai_why_counts", {})),
        json.dumps(u.get("history", [])),
        json.dumps(u.get("last_mock_failed", [])),
        u.get("last_mock_subject"),
        u.get("last_mock_total", 40),
        json.dumps(u.get("used_ids", [])),
        u.get("linked_widget_uid"),
        u.get("linked_tg_uid"),
        u.get("linked_device_id"),
    ))
    migrated += 1

conn.commit()
cur.close()
conn.close()
print(f"✅ Migrated {migrated} users to PostgreSQL")