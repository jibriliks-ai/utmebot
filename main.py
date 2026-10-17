"""
UTME Success Bot v47 — PostgreSQL + Admin + WhatsApp + Leaderboard
"""
import os, json, random, time, threading, hashlib, asyncio, re, hmac, traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote, parse_qsl

import requests
import psycopg2
import psycopg2.extras
from flask import Flask, render_template_string, jsonify, request, send_file

from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, MenuButtonCommands, BotCommand,
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters,
)

try:
    from gtts import gTTS
    HAS_TTS = True
except Exception:
    HAS_TTS = False

# ============================================================
# CONFIG
# ============================================================
try:
    from config import (
        BOT_TOKEN, BOT_USERNAME, ADMIN_ID, PAYMENT_URL, PORT,
        PREMIUM_PRICE, PREMIUM_PRICE_TEXT,
        PREMIUM_6MONTHS_PRICE, PREMIUM_6MONTHS_TEXT,
        PREMIUM_DAYS, PREMIUM_6MONTHS_DAYS,
        FREE_TUTOR_PER_DAY,
        REFERRAL_REQUIRED, REFERRAL_REWARD_DAYS,
        CHANNEL_ID, USER_DATA_FILE,
        FLW_PUBLIC_KEY, FLW_SECRET_KEY, FLW_SECRET_HASH,
        PAYSTACK_SECRET_KEY, ALL_SUBJECTS,
    )
    print("[config] loaded")
except Exception as _e:
    print(f"[config] using env defaults ({_e})")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    BOT_USERNAME = os.getenv("BOT_USERNAME", "UTMESucessBot")
    ADMIN_ID = os.getenv("ADMIN_ID", "")
    PAYMENT_URL = os.getenv("PAYMENT_URL", "https://utmebot.onrender.com")
    PORT = int(os.getenv("PORT", "5000"))
    PREMIUM_PRICE = int(os.getenv("PREMIUM_PRICE", "2000"))
    PREMIUM_PRICE_TEXT = f"\u20a6{PREMIUM_PRICE}"
    PREMIUM_6MONTHS_PRICE = int(os.getenv("PREMIUM_6MONTHS_PRICE", "6000"))
    PREMIUM_6MONTHS_TEXT = f"\u20a6{PREMIUM_6MONTHS_PRICE}"
    PREMIUM_DAYS = int(os.getenv("PREMIUM_DAYS", "30"))
    PREMIUM_6MONTHS_DAYS = int(os.getenv("PREMIUM_6MONTHS_DAYS", "180"))
    FREE_TUTOR_PER_DAY = int(os.getenv("FREE_TUTOR_PER_DAY", "5"))
    REFERRAL_REQUIRED = int(os.getenv("REFERRAL_REQUIRED", "3"))
    REFERRAL_REWARD_DAYS = int(os.getenv("REFERRAL_REWARD_DAYS", "7"))
    CHANNEL_ID = os.getenv("CHANNEL_ID", "")
    USER_DATA_FILE = os.getenv("USER_DATA_FILE", "user_data.json")
    FLW_PUBLIC_KEY = os.getenv("FLW_PUBLIC_KEY", "")
    FLW_SECRET_KEY = os.getenv("FLW_SECRET_KEY", "")
    FLW_SECRET_HASH = os.getenv("FLW_SECRET_HASH", "")
    PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
    ALL_SUBJECTS = ["english","mathematics","biology","physics","chemistry",
                    "economics","government","commerce","accounting",
                    "literature","crk"]

BOT_USERNAME = "UTMESucessBot"
SUPPORT_HANDLE = "@UTMESUCCESS"
TUTOR_NAME = "Mr. Ellams"
WEBAPP_URL = "https://www.schoolsecure.com.ng/p/bot.html"
CHANNEL_INVITE_LINK = "https://t.me/+Qw3DqGwCSM4wMDk0"
LOGO_URL = os.getenv("LOGO_URL", "https://cdn.jsdelivr.net/gh/jibriliks-ai/utmebot@main/logo.png")

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "utmebot_verify_2026")
WHATSAPP_GRAPH_URL = "https://graph.facebook.com/v22.0"

if CHANNEL_ID:
    CHANNEL_ID = str(CHANNEL_ID).strip()

SUBJECT_DISPLAY = {
    "english": "📖 English", "mathematics": "📐 Maths", "biology": "🧬 Biology",
    "physics": "⚛️ Physics", "chemistry": "🧪 Chemistry", "economics": "💰 Economics",
    "government": "🏛️ Government", "commerce": "🏪 Commerce",
    "accounting": "📊 Accounting", "literature": "📚 Literature", "crk": "✝️ CRK",
}
PLAN_SIZE = 4
FREE_ENGLISH_QS = 40
FREE_AI_WHY_PER_DAY = 3
KNOWN_SOURCES = ["whatsapp","telegram","facebook","twitter","instagram",
                 "tiktok","direct","referral","web_widget"]

NIGERIAN_STATES = ["Delta","Edo","Lagos","Ondo","Anambra","Oyo","Kano","Rivers",
    "Kaduna","Enugu","Imo","Abia","Akwa Ibom","Cross River","Plateau","Benue",
    "Kogi","Kwara","Osun","Ekiti","Ogun","Bayelsa","Ebonyi","Nasarawa","Niger",
    "Sokoto","Kebbi","Zamfara","Yobe","Borno","Adamawa","Taraba","Gombe",
    "Jigawa","Katsina","Bauchi"]
NIGERIAN_CITIES = ["Warri","Lagos","Benin","Enugu","Kano","Ibadan","Port Harcourt",
    "Kaduna","Aba","Jos","Uyo","Owerri","Maiduguri","Abeokuta","Akure","Sokoto",
    "Calabar","Asaba","Makurdi","Bauchi"]
NIGERIAN_NAMES = ["Chinedu O.","Amina B.","Tunde A.","Ngozi E.","Emeka N.",
    "Fatima Y.","Blessing I.","Yusuf M.","Chioma U.","Segun F.","Aisha K.",
    "Kelechi A.","Ifeoma O.","Ibrahim S.","Adaeze M.","Oluwaseun T.","Halima G.",
    "Nkem C.","Bolanle A.","Uche O.","Zainab M.","Obinna E.","Folake B.",
    "Bashir A.","Ebere N.","Yemi O.","Hauwa A.","Chidi N.","Funmi D.","Mustapha K."]

# ============================================================
# ENGINE
# ============================================================
ALL_QS = []
LOCAL_DATABANK = {}
AVAILABLE_SUBJECTS = list(ALL_SUBJECTS)
HAS_ENGINE = False
fetcher = None
format_question = None
search_databank = None
get_random_question = None

try:
    from cbt_engine import (
        fetcher as _fetcher, format_question as _fmt,
        search_databank as _search, get_random_question as _rnd,
        LOCAL_DATABANK as _LDB, ALL_QS as _AQS,
        AVAILABLE_SUBJECTS as _AVS,
    )
    fetcher, format_question = _fetcher, _fmt
    search_databank, get_random_question = _search, _rnd
    LOCAL_DATABANK = dict(_LDB)
    ALL_QS = list(_AQS)
    AVAILABLE_SUBJECTS = list(_AVS) if _AVS else list(ALL_SUBJECTS)
    HAS_ENGINE = True
    print(f"[engine] {len(ALL_QS)} Qs across {len(AVAILABLE_SUBJECTS)} subjects")
except Exception as _e:
    print(f"[engine] failed: {_e}")
    def _fmt(q,i,t):
        lines=[f"Q{i}/{t}", q.get("question","")]
        for L in ("A","B","C","D"):
            v=q.get(f"option_{L.lower()}")
            if v: lines.append(f"{L}) {v}")
        return "\n".join(lines)
    def _search(q,s=None,limit=5): return []
    def _rnd(s=None): return None
    class _F:
        def fetch(self,s,y=None,limit=40): return []
    fetcher=_F(); format_question=_fmt; search_databank=_search
    get_random_question=_rnd; LOCAL_DATABANK={}; ALL_QS=[]

if not AVAILABLE_SUBJECTS:
    AVAILABLE_SUBJECTS = list(ALL_SUBJECTS)

# ============================================================
# AI TUTOR
# ============================================================
HAS_AI_TUTOR = False
try:
    from tutor import (
        ask_tutor as _ask_tutor, analyze_failure as _analyze_failure,
        build_voice_inputfile as _build_voice, build_knowledge_base as _build_kb,
        get_kb_stats as _get_kb_stats, ping as _tutor_ping,
        make_voice_professional as _make_voice_professional,
    )
    HAS_AI_TUTOR = True
    print(f"[tutor] AI Tutor loaded ({TUTOR_NAME})")
except Exception as _e:
    print(f"[tutor] unavailable: {_e}")
    def _ask_tutor(q,s=""): return "AI Tutor not available."
    def _analyze_failure(q,ua,ca,t=""): return "Trap Detector not available."
    def _build_voice(t): return None
    def _build_kb(f=False): return False
    def _get_kb_stats(): return {}
    def _tutor_ping(): return False, "not loaded"
    def _make_voice_professional(t): return None


# ============================================================
# HELPERS
# ============================================================
def md(s):
    if s is None: return ""
    s = str(s)
    return (s.replace("\\","\\\\").replace("_","\\_").replace("*","\\*")
             .replace("`","\\`").replace("[","\\["))


def _normalize_source(raw):
    if not raw: return None
    s = str(raw).strip().lower()[:30]
    if not s: return None
    if "whatsapp" in s or s in ("wa","whats"): return "whatsapp"
    if "telegram" in s or s in ("tg",): return "telegram"
    if "facebook" in s or s in ("fb","meta"): return "facebook"
    if "twitter" in s or s == "x": return "twitter"
    if "instagram" in s or s in ("ig","insta"): return "instagram"
    if "tiktok" in s or s in ("tt",): return "tiktok"
    if "referral" in s or s == "ref": return "referral"
    if "direct" in s: return "direct"
    if s in KNOWN_SOURCES: return s
    return s[:30]


def _normalize_subjects(raw):
    if not raw: return []
    try:
        if isinstance(raw, list):
            arr = raw
        else:
            s = str(raw).strip()
            if s.startswith("["):
                arr = json.loads(s)
            elif "," in s:
                arr = [x.strip() for x in s.split(",") if x.strip()]
            else:
                arr = [s]
        cleaned = []
        for x in arr:
            t = str(x).strip().lower()
            if t and t not in cleaned:
                cleaned.append(t)
        return [s for s in cleaned if s in ALL_SUBJECTS or s in SUBJECT_DISPLAY][:PLAN_SIZE]
    except Exception:
        return []


def _shuffle_options(q):
    if not isinstance(q, dict): return q
    opts=[q.get("option_a","") or "", q.get("option_b","") or "",
          q.get("option_c","") or "", q.get("option_d","") or ""]
    valid_pairs=[(chr(65+i),opts[i]) for i in range(4) if str(opts[i]).strip()]
    if len(valid_pairs)<2: return q
    orig_ans=str(q.get("answer","") or "").upper().strip()[:1]
    answer_text=None
    for letter,text in valid_pairs:
        if letter==orig_ans: answer_text=text; break
    if not answer_text:
        alt=str(q.get("answer_text","") or "").strip()
        if alt:
            for letter,text in valid_pairs:
                if text.strip()==alt: answer_text=text; break
    if not answer_text: return q
    random.shuffle(valid_pairs)
    new_q=dict(q); new_letters=["A","B","C","D"]; new_answer=orig_ans
    for i,(ol,text) in enumerate(valid_pairs):
        new_q[f"option_{new_letters[i].lower()}"]=text
        if text==answer_text: new_answer=new_letters[i]
    for j in range(len(valid_pairs),4):
        new_q[f"option_{new_letters[j].lower()}"]=""
    new_q["answer"]=new_answer
    return new_q


def _prepare_questions(qs):
    return [_shuffle_options(q) for q in qs]


def _make_failure_snapshot(q, user_ans, correct_ans, q_num):
    return {"q_num":int(q_num),
            "question":str(q.get("question","") or "")[:300],
            "option_a":str(q.get("option_a","") or "")[:200],
            "option_b":str(q.get("option_b","") or "")[:200],
            "option_c":str(q.get("option_c","") or "")[:200],
            "option_d":str(q.get("option_d","") or "")[:200],
            "user_ans":str(user_ans or "")[:1],
            "correct_ans":str(correct_ans or "")[:1],
            "topic":str(q.get("topic","General") or "General")[:60]}


def _fetch_rotated(uid, subject, limit):
    u = get_user(uid)
    used = set(str(x) for x in u.get("used_ids",[]))
    pool = LOCAL_DATABANK.get(subject,[])
    if not pool: return []
    unused=[q for q in pool if str(q.get("id","")) not in used]
    used_qs=[q for q in pool if str(q.get("id","")) in used]
    random.shuffle(unused); random.shuffle(used_qs)
    selected=(unused+used_qs)[:limit]
    new_ids=[str(q.get("id","")) for q in selected if q.get("id")]
    if new_ids:
        u["used_ids"]=(u.get("used_ids",[])+new_ids)[-5000:]
        save_data()
    return selected


def _fetch_rotated_multi(uid, subjects, total):
    u = get_user(uid)
    used = set(str(x) for x in u.get("used_ids",[]))
    n=len(subjects)
    if n==0: return []
    per=total//n; rem=total%n
    picked=[]; picked_ids=[]
    for i,subj in enumerate(subjects):
        pool=LOCAL_DATABANK.get(subj,[])
        if not pool: continue
        need=per+(1 if i<rem else 0)
        unused=[q for q in pool if str(q.get("id","")) not in used]
        used_qs=[q for q in pool if str(q.get("id","")) in used]
        random.shuffle(unused); random.shuffle(used_qs)
        selected=(unused+used_qs)[:need]
        picked.extend(selected)
        picked_ids.extend(str(q.get("id","")) for q in selected if q.get("id"))
    random.shuffle(picked)
    picked=picked[:total]
    if picked_ids:
        u["used_ids"]=(u.get("used_ids",[])+picked_ids)[-5000:]
        save_data()
    return picked


def _get_user_state(uid):
    h=int(hashlib.md5(f"{uid}_{date.today().isoformat()}_state".encode()).hexdigest(),16)
    return NIGERIAN_STATES[h%len(NIGERIAN_STATES)]


def _get_user_rank_number(uid, user_score, total):
    h=int(hashlib.md5(f"{uid}_{date.today().isoformat()}_rank".encode()).hexdigest(),16)
    if user_score>=35: return (h%15)+1
    if user_score>=25: return (h%40)+15
    if user_score>=15: return (h%80)+40
    return (h%100)+80


def _generate_rank(uid, subject_display, user_score, total):
    state=_get_user_state(uid)
    seed_int=int(hashlib.md5(f"{uid}_{subject_display}_{date.today().isoformat()}".encode()).hexdigest(),16)%(2**32)
    rng=random.Random(seed_int)
    names=rng.sample(NIGERIAN_NAMES,5)
    min_score=35; max_score=max(min_score,total)
    if total<min_score: min_score=max(1,total-5); max_score=total
    scores=[rng.randint(min_score,max_score) for _ in range(5)]
    scores.sort(reverse=True)
    medals=["🥇","🥈","🥉","4️⃣","5️⃣"]
    lines=[f"🏆 *{state} State Ranking — {subject_display} Mock*\n"]
    for i,(n,s) in enumerate(zip(names,scores)):
        lines.append(f"{medals[i]} {md(n)} — *{s}/{total}*")
    user_rank=_get_user_rank_number(uid,user_score,total)
    lines.append(f"\n📊 *Your Score:* *{user_score}/{total}*")
    lines.append(f"🎯 *Your Rank:* *#{user_rank}* in {state} State")
    lines.append("\n_Simulated based on state benchmarks._")
    return "\n".join(lines)


def _social_proof_line(uid, prev_score, total):
    rng=random.Random(f"{uid}_{date.today().isoformat()}_sp")
    name=rng.choice(NIGERIAN_NAMES).split()[0]
    city=rng.choice(NIGERIAN_CITIES)
    new_score=min(total,prev_score+rng.randint(6,12))
    return f"→ *{name}* from {city}: Now scoring *{new_score}/{total}*"


def _build_completion_message(uid, score, total, failed, subject_label, subj_display):
    n_failed=len(failed)
    header=f"🎉 *Mock Completed!* You scored *{score}/{total}*\n"
    if n_failed==0:
        state=_get_user_state(uid); rank=_get_user_rank_number(uid,score,total)
        return (f"{header}\n🎯 *Perfect score!*\n\n"
                f"🏆 You're ranked *#{rank}* in *{state} State*.\n\n"
                f"Keep the momentum going! 🚀", True)
    topic_losses={}
    for f in failed:
        t=f.get("topic","General") or "General"
        topic_losses[t]=topic_losses.get(t,0)+1
    sorted_t=sorted(topic_losses.items(),key=lambda x:-x[1])
    loss_lines=[f"  • *{md(t)}* — {c} mark{'s' if c>1 else ''} LOST"
                for t,c in sorted_t[:5]]
    marks_line=(f"\n❌ *You lost {n_failed} mark{'s' if n_failed>1 else ''} from:*\n"
                + "\n".join(loss_lines))
    fear_line=(f"\n\n⚠️ *In JAMB, {n_failed} mark{'s' if n_failed>1 else ''} = "
               f"You will lose admission to your dream course.*")
    social_line=(f"\n\n*Your mates who scored {score} yesterday fixed it today:*\n"
                 f"{_social_proof_line(uid,score,total)}")
    return header+marks_line+fear_line+social_line, False


# ============================================================
# POSTGRESQL
# ============================================================
DATABASE_URL = os.getenv("DATABASE_URL", "")


def _get_db_conn():
    if not DATABASE_URL: raise RuntimeError("DATABASE_URL is not set")
    is_ext="render.com" in DATABASE_URL and "dpg-" not in DATABASE_URL.split("@")[-1].split("/")[0]
    return psycopg2.connect(DATABASE_URL, sslmode="require" if is_ext else "prefer")


def init_db():
    conn=_get_db_conn()
    try:
        cur=conn.cursor()
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
                joined TEXT DEFAULT CURRENT_DATE::text,
                source TEXT,
                wa_phone TEXT,
                subject_combination JSONB DEFAULT '[]'::jsonb,
                first_seen_platform TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_users_phone ON users (phone);
            CREATE INDEX IF NOT EXISTS idx_users_invite_code ON users (invite_code);
            CREATE INDEX IF NOT EXISTS idx_users_source ON users (source);
            CREATE INDEX IF NOT EXISTS idx_users_wa_phone ON users (wa_phone);
        """)
        conn.commit(); cur.close()
        print("[db] Table 'users' ready")
    finally:
        conn.close()


USER_DATA = {}
USER_SESSIONS = {}
PROCESSED_TX_FILE = Path("processed_tx.json")
PROCESSED_TX = set()

BOTTOM_KEYBOARD = ReplyKeyboardMarkup(
    [[KeyboardButton("📚 Past Questions"), KeyboardButton("📝 Mock Exam")],
     [KeyboardButton("📊 My Score"), KeyboardButton("💬 Ask Tutor")],
     [KeyboardButton("💎 Premium"), KeyboardButton("👥 Invite Friends")],
     [KeyboardButton("📢 Join Our Channel")]],
    resize_keyboard=True, is_persistent=True)


def load_processed_tx():
    global PROCESSED_TX
    if PROCESSED_TX_FILE.exists():
        try: PROCESSED_TX=set(json.loads(PROCESSED_TX_FILE.read_text()))
        except: PROCESSED_TX=set()


def save_processed_tx():
    try: PROCESSED_TX_FILE.write_text(json.dumps(sorted(PROCESSED_TX),indent=2))
    except: pass


def mark_processed(tx_ref):
    if not tx_ref or tx_ref in PROCESSED_TX: return False
    PROCESSED_TX.add(tx_ref); save_processed_tx(); return True


JSONB_FIELDS = ["invited_users","jamb_plan","tutor_counts","ai_why_counts",
                "history","last_mock_failed","used_ids","subject_combination"]


def _coerce_jsonb(u):
    for field in JSONB_FIELDS:
        if isinstance(u.get(field),str):
            try: u[field]=json.loads(u[field])
            except: u[field]={} if field in ("tutor_counts","ai_why_counts") else []
        if u.get(field) is None:
            u[field]={} if field in ("tutor_counts","ai_why_counts") else []
    return u


def load_data():
    global USER_DATA
    conn=_get_db_conn()
    try:
        cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users")
        USER_DATA={}
        for row in cur.fetchall():
            u=_coerce_jsonb(dict(row))
            USER_DATA[u["uid"]]=u
        cur.close()
        print(f"[db] Loaded {len(USER_DATA)} users")
    finally:
        conn.close()


def save_data():
    if not USER_DATA: return
    conn=_get_db_conn()
    try:
        cur=conn.cursor()
        for uid,u in USER_DATA.items():
            cur.execute("""
                INSERT INTO users (
                    uid, username, phone, invite_code, invited_by,
                    invites, invited_users, referral_rewards_claimed,
                    is_premium, premium_until, premium_plan,
                    jamb_plan, plan_set, free_english_used,
                    tutor_counts, ai_why_counts, history,
                    last_mock_failed, last_mock_subject, last_mock_total,
                    used_ids, linked_widget_uid, linked_tg_uid, linked_device_id,
                    source, wa_phone, subject_combination, first_seen_platform
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (uid) DO UPDATE SET
                    username=EXCLUDED.username, phone=EXCLUDED.phone,
                    invited_by=EXCLUDED.invited_by, invites=EXCLUDED.invites,
                    invited_users=EXCLUDED.invited_users,
                    referral_rewards_claimed=EXCLUDED.referral_rewards_claimed,
                    is_premium=EXCLUDED.is_premium, premium_until=EXCLUDED.premium_until,
                    premium_plan=EXCLUDED.premium_plan, jamb_plan=EXCLUDED.jamb_plan,
                    plan_set=EXCLUDED.plan_set, free_english_used=EXCLUDED.free_english_used,
                    tutor_counts=EXCLUDED.tutor_counts, ai_why_counts=EXCLUDED.ai_why_counts,
                    history=EXCLUDED.history, last_mock_failed=EXCLUDED.last_mock_failed,
                    last_mock_subject=EXCLUDED.last_mock_subject,
                    last_mock_total=EXCLUDED.last_mock_total, used_ids=EXCLUDED.used_ids,
                    linked_widget_uid=EXCLUDED.linked_widget_uid,
                    linked_tg_uid=EXCLUDED.linked_tg_uid,
                    linked_device_id=EXCLUDED.linked_device_id,
                    source=COALESCE(users.source, EXCLUDED.source),
                    wa_phone=COALESCE(users.wa_phone, EXCLUDED.wa_phone),
                    subject_combination=CASE
                        WHEN users.subject_combination IS NULL
                             OR users.subject_combination='[]'::jsonb
                        THEN EXCLUDED.subject_combination
                        ELSE users.subject_combination END,
                    first_seen_platform=COALESCE(users.first_seen_platform, EXCLUDED.first_seen_platform)
            """, (
                uid, u.get("username","Student"), u.get("phone"), u.get("invite_code"),
                u.get("invited_by"), u.get("invites",0),
                json.dumps(u.get("invited_users",[])),
                u.get("referral_rewards_claimed",0), u.get("is_premium",False),
                u.get("premium_until"), u.get("premium_plan"),
                json.dumps(u.get("jamb_plan",["english"])), u.get("plan_set",False),
                u.get("free_english_used",False),
                json.dumps(u.get("tutor_counts",{})),
                json.dumps(u.get("ai_why_counts",{})),
                json.dumps(u.get("history",[])),
                json.dumps(u.get("last_mock_failed",[])),
                u.get("last_mock_subject"), u.get("last_mock_total",40),
                json.dumps(u.get("used_ids",[])), u.get("linked_widget_uid"),
                u.get("linked_tg_uid"), u.get("linked_device_id"),
                u.get("source"), u.get("wa_phone"),
                json.dumps(u.get("subject_combination",[])),
                u.get("first_seen_platform"),
            ))
        conn.commit(); cur.close()
    except Exception as e:
        print(f"[save_data] failed: {e}")
        try: conn.rollback()
        except: pass
    finally:
        conn.close()


def get_user(uid, username=""):
    uid=str(uid)
    if uid in USER_DATA:
        u=USER_DATA[uid]
        if username and (not u.get("username") or str(u.get("username","")).startswith("User")):
            u["username"]=username; save_data()
        if u.get("premium_until"):
            try:
                if datetime.now()>datetime.fromisoformat(u["premium_until"]):
                    u["is_premium"]=False; u["premium_until"]=None
                    u["premium_plan"]=None; save_data()
            except: pass
        return u
    conn=_get_db_conn()
    try:
        cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM users WHERE uid=%s",(uid,))
        row=cur.fetchone()
        if row is None:
            invite_code=hashlib.md5(uid.encode()).hexdigest()[:6].upper()
            cur.execute("INSERT INTO users (uid,username,invite_code) VALUES (%s,%s,%s) RETURNING *",
                        (uid, username or f"User{uid[-4:]}", invite_code))
            row=cur.fetchone(); conn.commit()
            print(f"[db] Created user {uid}")
        u=_coerce_jsonb(dict(row))
        if username and (not u.get("username") or str(u.get("username","")).startswith("User")):
            u["username"]=username
            cur.execute("UPDATE users SET username=%s WHERE uid=%s",(username,uid))
            conn.commit()
        cur.close()
        USER_DATA[uid]=u
        return u
    finally:
        conn.close()


def _merge_widget_user(widget_uid, tg_uid):
    widget_uid=str(widget_uid); tg_uid=str(tg_uid)
    widget_u=USER_DATA.get(widget_uid)
    if not widget_u:
        try:
            conn=_get_db_conn()
            cur=conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT * FROM users WHERE uid=%s",(widget_uid,))
            row=cur.fetchone(); cur.close(); conn.close()
            if row: widget_u=_coerce_jsonb(dict(row))
        except: pass
    if not widget_u: return False, "Web app account not found."
    tg_u=get_user(tg_uid)
    if tg_u.get("linked_widget_uid")==widget_uid: return True, "already"
    seen=set(); merged_hist=[]
    for h in list(tg_u.get("history",[]))+list(widget_u.get("history",[])):
        key=(h.get("date",""),h.get("subject",""),h.get("score",0),h.get("total",0))
        if key not in seen:
            seen.add(key); merged_hist.append(h)
    tg_u["history"]=merged_hist[-50:]
    w_until=widget_u.get("premium_until")
    if w_until:
        try:
            w_dt=datetime.fromisoformat(w_until)
            t_until=tg_u.get("premium_until")
            t_dt=datetime.fromisoformat(t_until) if t_until else None
            if t_dt is None or w_dt>t_dt:
                tg_u["premium_until"]=w_until; tg_u["is_premium"]=True
                tg_u["premium_plan"]=widget_u.get("premium_plan") or "widget_merge"
        except: pass
    if not tg_u.get("plan_set") and widget_u.get("plan_set"):
        tg_u["jamb_plan"]=widget_u.get("jamb_plan",["english"])
        tg_u["plan_set"]=True
    if widget_u.get("free_english_used"): tg_u["free_english_used"]=True
    tg_u["used_ids"]=list(set(tg_u.get("used_ids",[]))|set(widget_u.get("used_ids",[])))[-5000:]
    if not tg_u.get("last_mock_failed") and widget_u.get("last_mock_failed"):
        tg_u["last_mock_failed"]=widget_u["last_mock_failed"]
        tg_u["last_mock_subject"]=widget_u.get("last_mock_subject")
        tg_u["last_mock_total"]=widget_u.get("last_mock_total",40)
    w_name=(widget_u.get("username") or "").strip()
    if w_name and (not tg_u.get("username") or tg_u["username"].startswith("User")):
        tg_u["username"]=w_name
    if widget_u.get("phone"): tg_u["phone"]=widget_u["phone"]
    if widget_u.get("source") and not tg_u.get("source"): tg_u["source"]=widget_u["source"]
    if widget_u.get("wa_phone") and not tg_u.get("wa_phone"): tg_u["wa_phone"]=widget_u["wa_phone"]
    if widget_u.get("subject_combination") and not tg_u.get("subject_combination"):
        tg_u["subject_combination"]=widget_u["subject_combination"]
    if widget_u.get("first_seen_platform") and not tg_u.get("first_seen_platform"):
        tg_u["first_seen_platform"]=widget_u["first_seen_platform"]
    tg_u["linked_widget_uid"]=widget_uid
    widget_u["linked_tg_uid"]=tg_uid
    USER_DATA[widget_uid]=widget_u
    save_data()
    print(f"[link] merged {widget_uid} -> TG {tg_uid}")
    return True, "merged"


def _find_user_by_phone(phone):
    if not phone: return None
    normalized=re.sub(r'\D','',str(phone))
    if not normalized or len(normalized)<10: return None
    candidates={normalized}
    if normalized.startswith("0") and len(normalized)==11:
        candidates.add("234"+normalized[1:]); candidates.add(normalized[1:])
    if normalized.startswith("234") and len(normalized)==13:
        candidates.add("0"+normalized[3:]); candidates.add(normalized[3:])
    conn=_get_db_conn()
    try:
        cur=conn.cursor()
        ph=",".join(["%s"]*len(candidates))
        cur.execute(f"SELECT uid FROM users WHERE phone IN ({ph}) OR wa_phone IN ({ph}) LIMIT 1",
                    tuple(candidates)+tuple(candidates))
        row=cur.fetchone(); cur.close()
        return row[0] if row else None
    finally:
        conn.close()


def _apply_referral_code(new_uid, code):
    if not code or not new_uid: return None
    code=str(code).strip().upper(); new_uid=str(new_uid)
    u=get_user(new_uid)
    if u.get("invited_by"): return None
    for inviter_id,inv_data in USER_DATA.items():
        if inviter_id==new_uid: continue
        if str(inv_data.get("invite_code","")).upper()==code:
            if new_uid not in inv_data.get("invited_users",[]):
                u["invited_by"]=inviter_id
                inv_data["invites"]=inv_data.get("invites",0)+1
                inv_data.setdefault("invited_users",[]).append(new_uid)
                if inv_data["invites"]>=REFERRAL_REQUIRED:
                    add_premium(inviter_id,days=REFERRAL_REWARD_DAYS,plan="referral")
                    inv_data["invites"]=0
                    inv_data["referral_rewards_claimed"]=inv_data.get("referral_rewards_claimed",0)+1
                save_data()
                return inviter_id
    return None


def _get_referral_status(uid):
    u=get_user(uid); code=u.get("invite_code","")
    return {"invite_code":code,
            "invite_link":f"{WEBAPP_URL}?ref={code}",
            "invites":u.get("invites",0), "required":REFERRAL_REQUIRED,
            "reward_days":REFERRAL_REWARD_DAYS,
            "referral_rewards_claimed":u.get("referral_rewards_claimed",0)}


def is_premium(uid):
    u=get_user(uid)
    if ADMIN_ID and str(uid)==str(ADMIN_ID): return True
    return bool(u.get("is_premium",False))


def can_use_ai_why(uid):
    if is_premium(uid): return True, 999
    u=get_user(uid); today=str(date.today())
    used=u.get("ai_why_counts",{}).get(today,0)
    remaining=max(0,FREE_AI_WHY_PER_DAY-used)
    return remaining>0, remaining


def consume_ai_why(uid):
    u=get_user(uid); today=str(date.today())
    u.setdefault("ai_why_counts",{})
    u["ai_why_counts"][today]=u["ai_why_counts"].get(today,0)+1
    save_data()


def can_use_tutor(uid):
    if is_premium(uid): return True
    u=get_user(uid)
    return u["tutor_counts"].get(str(date.today()),0)<FREE_TUTOR_PER_DAY


def consume_tutor(uid):
    u=get_user(uid); today=str(date.today())
    u["tutor_counts"][today]=u["tutor_counts"].get(today,0)+1
    save_data()


def get_leaderboard(limit=10):
    """Return top scorers across all users, ranked by best mock percentage."""
    leaders = []
    for uid, u in USER_DATA.items():
        hist = u.get("history", []) or []
        if not hist:
            continue
        best = None
        best_pct = -1.0
        for entry in hist:
            try:
                total = int(entry.get("total", 0) or 0)
                score = int(entry.get("score", 0) or 0)
            except Exception:
                continue
            if total <= 0:
                continue
            pct = (score * 100.0) / total
            if pct > best_pct:
                best_pct = pct
                best = entry
        if best is None:
            continue
        leaders.append({
            "uid": uid,
            "username": (u.get("username") or f"User{uid[-4:]}")[:24],
            "score": int(best.get("score", 0)),
            "total": int(best.get("total", 0)),
            "percent": int(round(best_pct)),
            "is_premium": bool(u.get("is_premium")),
        })
    leaders.sort(key=lambda x: (-x["percent"], -x["score"], -x["total"]))
    return leaders[:limit]


def get_leading():
    best_name,best_score="No scores yet",0
    for uid_k,d in USER_DATA.items():
        hist=d.get("history",[])
        if not hist: continue
        avg=sum(h.get("percent",0) for h in hist)/len(hist)
        if avg>best_score:
            best_score,best_name=avg,d.get("username",f"User{str(uid_k)[-4:]}")
    return best_name,int(best_score)


def add_premium(uid, days=None, plan="monthly"):
    uid=str(uid); days=days or PREMIUM_DAYS
    u=get_user(uid); now=datetime.now(); base=now
    if u.get("premium_until"):
        try:
            ex=datetime.fromisoformat(u["premium_until"])
            if ex>now: base=ex
        except: pass
    u["is_premium"]=True
    u["premium_until"]=(base+timedelta(days=days)).isoformat()
    u["premium_plan"]=plan
    save_data()
    print(f"[premium] {plan} ({days}d) -> uid={uid}")
    return True


PLANS = {"monthly":{"key":"monthly","label":"Monthly","price":PREMIUM_PRICE,
                    "price_text":PREMIUM_PRICE_TEXT,"days":PREMIUM_DAYS},
         "6months":{"key":"6months","label":"6 Months","price":PREMIUM_6MONTHS_PRICE,
                    "price_text":PREMIUM_6MONTHS_TEXT,"days":PREMIUM_6MONTHS_DAYS}}


def _resolve_plan(key): return PLANS.get(key,PLANS["monthly"])


def _uid_from_tx_ref(tx_ref):
    if not tx_ref or not tx_ref.startswith("UTME-"): return None
    parts=tx_ref.split("-")
    if len(parts)<3: return None
    uid_part=parts[1]
    if uid_part.isdigit() or uid_part.startswith("widget_"): return uid_part
    return None


def _grant_from_verified(tx_ref, plan_key):
    uid=_uid_from_tx_ref(tx_ref)
    if not uid: return None
    if not mark_processed(tx_ref): return None
    plan=_resolve_plan(plan_key)
    add_premium(uid,days=plan["days"],plan=plan["key"])
    return uid


def plan_buttons(uid):
    return [[InlineKeyboardButton(f"💳 Monthly — {PREMIUM_PRICE_TEXT}",
             url=f"{PAYMENT_URL}/upgrade/{uid}?plan=monthly")],
            [InlineKeyboardButton(f"💳 6 Months — {PREMIUM_6MONTHS_TEXT} (BEST VALUE)",
             url=f"{PAYMENT_URL}/upgrade/{uid}?plan=6months")]]


def upgrade_kb(uid):
    msg=(f"🔒 *Upgrade Required*\n\n💎 *Unlock Premium for:*\n"
         f"• ♾️ Unlimited mocks\n• 📚 Subject Mock (40 Qs)\n"
         f"• 🔥 Full JAMB CBT Mock (180 Qs)\n"
         f"• 💬 Unlimited {TUTOR_NAME} + 🎙️ Voice\n"
         f"• 🎯 Unlimited AI Why analysis\n\n"
         f"*Plans:*\n• Monthly — {PREMIUM_PRICE_TEXT} / {PREMIUM_DAYS} days\n"
         f"• 6 Months — {PREMIUM_6MONTHS_TEXT} / {PREMIUM_6MONTHS_DAYS} days")
    kb=plan_buttons(uid)
    kb.append([InlineKeyboardButton(f"👥 Invite {REFERRAL_REQUIRED}=FREE",
                                    callback_data="invite_friends")])
    kb.append([InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)])
    kb.append([InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")])
    return msg, InlineKeyboardMarkup(kb)


def ai_why_limit_kb(uid):
    msg=(f"🔒 *Free AI Why limit reached*\n\n"
         f"You've used your *{FREE_AI_WHY_PER_DAY} free AI Why analyses* today.\n\n"
         f"💎 *Unlock Premium* ({PREMIUM_PRICE_TEXT})")
    kb=plan_buttons(uid)
    kb.append([InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")])
    return msg, InlineKeyboardMarkup(kb)


def main_menu_text_kb(uid):
    u=get_user(uid)
    plan=u.get("jamb_plan",["english"])
    plan_str=" • ".join(SUBJECT_DISPLAY.get(s,s.title()) for s in plan)
    if is_premium(uid):
        status_badge="💎 *PREMIUM MEMBER*"
        status_line="✨ _Unlimited access on all subjects_"
    else:
        status_badge="🆓 *FREE ACCOUNT*"
        status_line="🎁 _1 free English mock available_" if not u.get("free_english_used",False) else "🔒 _Upgrade to unlock more mocks_"
    leader_name,leader_score=get_leading()
    total_users=len(USER_DATA)
    _,ai_remaining=can_use_ai_why(uid) if not is_premium(uid) else (True,999)
    ai_str="♾️ Unlimited" if is_premium(uid) else f"{ai_remaining}/{FREE_AI_WHY_PER_DAY} today"
    text=(f"╔══════════════════════════╗\n"
          f"     🎓  *UTME SUCCESS BOT*  🎓\n"
          f"╚══════════════════════════╝\n\n"
          f"👋 *Welcome back, Champion!*\n_{status_line}_\n\n"
          f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
          f"📋  *YOUR JAMB PLAN*\n"
          f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n🎯 {plan_str}\n\n"
          f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
          f"📊  *YOUR STATS*\n"
          f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
          f"  {status_badge}\n  🤖 AI Tutor:  `{ai_str}`\n"
          f"  👥 Students:  `{total_users:,}`\n  📚 Questions:  `{len(ALL_QS):,}`\n\n"
          f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
          f"🏆  *TOP PERFORMER*\n"
          f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
          f"  🥇  {md(leader_name)}\n  🎯  *{leader_score}/400*\n\n"
          f"💡 _Tap any button below to begin._")
    kb=[[InlineKeyboardButton("🌐  Open Web App (Blogger)",web_app={"url":WEBAPP_URL})],
        [InlineKeyboardButton("🎯  Start Mock from My Plan",callback_data="start_plan_mock")],
        [InlineKeyboardButton("📚  Past Questions",callback_data="past_by_subject"),
         InlineKeyboardButton("📝  Mock Menu",callback_data="mock_menu")],
        [InlineKeyboardButton("📖  Study Plan",callback_data="study_plan"),
         InlineKeyboardButton("📋  Syllabus",callback_data="syllabus")],
        [InlineKeyboardButton("📊  My Score",callback_data="my_score"),
         InlineKeyboardButton("💬  Ask AI Tutor",callback_data="ask_tutor")],
        [InlineKeyboardButton(f"👥  Invite {REFERRAL_REQUIRED} = {REFERRAL_REWARD_DAYS} Days FREE",
                              callback_data="invite_friends")],
        [InlineKeyboardButton("📢  Join Our Channel",url=CHANNEL_INVITE_LINK)],
        [InlineKeyboardButton("💎  Upgrade to Premium",callback_data="premium_info"),
         InlineKeyboardButton("❓  Help",callback_data="help_menu")],
        [InlineKeyboardButton("✏️  Change My Plan",callback_data="plan_builder")]]
    if ADMIN_ID and str(uid)==str(ADMIN_ID):
        kb.append([InlineKeyboardButton("⚙️  Admin Panel",callback_data="admin_panel")])
    return text, InlineKeyboardMarkup(kb)


def subjects_kb(prefix):
    buttons=[]; row=[]
    for subj in AVAILABLE_SUBJECTS[:14]:
        row.append(InlineKeyboardButton(SUBJECT_DISPLAY.get(subj,subj.title()),
                                        callback_data=f"{prefix}_{subj}"))
        if len(row)==2: buttons.append(row); row=[]
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)])
    buttons.append([InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def _answer_keyboard(q):
    a=md((q.get("option_a") or "")[:25]); b=md((q.get("option_b") or "")[:25])
    c=md((q.get("option_c") or "")[:25]); d=md((q.get("option_d") or "")[:25])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"A) {a}",callback_data="ans:A"),
         InlineKeyboardButton(f"B) {b}",callback_data="ans:B")],
        [InlineKeyboardButton(f"C) {c}",callback_data="ans:C"),
         InlineKeyboardButton(f"D) {d}",callback_data="ans:D")],
        [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]])


def _start_mock_session(uid, qs, subject_label, intro_text=""):
    qs=_prepare_questions(qs)
    USER_SESSIONS[uid]={"mode":"mock","qs":qs,"idx":0,"score":0,
                        "subject":subject_label,"failed":[]}
    q=qs[0]
    txt=(intro_text+"\n\n" if intro_text else "")+format_question(q,1,len(qs))
    return txt, _answer_keyboard(q)


PLAN_OPTIONAL_SUBJECTS=["mathematics","biology","physics","chemistry",
                        "economics","government","commerce","accounting",
                        "literature","crk"]


def _plan_builder_text(uid):
    u=get_user(uid); plan=u.get("jamb_plan",["english"])
    others=[s for s in plan if s!="english"]
    filled=len(others)+1
    bar="▰"*filled+"▱"*(PLAN_SIZE-filled)
    text=(f"╔══════════════════════════╗\n"
          f"    🔥  *WELCOME TO UTME*  🔥\n         *SUCCESS BOT*\n"
          f"╚══════════════════════════╝\n\n"
          f"🎓 _Nigeria's smartest JAMB practice bot._\n\n"
          f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n✨  *WHY STUDENTS LOVE US*\n"
          f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
          f"  📚  *{len(ALL_QS):,}+* past questions\n"
          f"  🤖  *AI Tutor* (Mr. Ellams) with voice 🎙️\n"
          f"  🎯  *Real exam mode*\n"
          f"  📊  *State rankings*\n"
          f"  🆓  *1 free English mock*\n\n"
          f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
          f"📋  *BUILD YOUR JAMB PLAN*\n"
          f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
          f"_Pick 3 more subjects. English is compulsory._\n\n"
          f"  `{bar}`  *{filled}/{PLAN_SIZE}*\n\n"
          f"  1️⃣  📖 English  ✅ _(compulsory)_\n\n")
    for i,s in enumerate(PLAN_OPTIONAL_SUBJECTS,2):
        icon="✅" if s in plan else "⬜"
        text+=f"  {i}️⃣  {SUBJECT_DISPLAY.get(s,s.title())}  {icon}\n"
    if plan:
        text+="\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n📌  *YOUR SELECTED PLAN*\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i,s in enumerate(plan,1):
            text+=f"  {i}.  {SUBJECT_DISPLAY.get(s,s.title())}\n"
    if filled==PLAN_SIZE:
        text+=("\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n✅  *READY TO START!*\n"
               "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
               "_Tap 🚀 Start Mock below to begin._\n"
               "💡 _Your first mock is FREE._")
    else:
        rem=PLAN_SIZE-filled
        text+=(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
               f"⬜  Select *{rem}* more subject{'s' if rem>1 else ''} to continue.\n"
               f"━━━━━━━━━━━━━━━━━━━━━━━━━━")
    return text


def _plan_builder_kb(uid):
    u=get_user(uid); plan=u.get("jamb_plan",["english"])
    buttons=[]; row=[]
    for subj in PLAN_OPTIONAL_SUBJECTS:
        icon="✅" if subj in plan else "⬜"
        row.append(InlineKeyboardButton(f"{icon} {SUBJECT_DISPLAY.get(subj,subj.title())}",
                                        callback_data=f"plan_toggle_{subj}"))
        if len(row)==2: buttons.append(row); row=[]
    if row: buttons.append(row)
    if len(plan)==PLAN_SIZE:
        buttons.append([InlineKeyboardButton("🚀 Start Mock",callback_data="plan_start")])
    if len(plan)>1:
        buttons.append([InlineKeyboardButton("🗑️ Reset Plan",callback_data="plan_reset")])
    buttons.append([InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)])
    buttons.append([InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def can_take_subject(uid, subject):
    if is_premium(uid): return True, "premium"
    u=get_user(uid)
    if subject=="english":
        if not u.get("free_english_used",False): return True, "free_english"
        return False, "english_used"
    return False, "premium_only"


def _mock_menu_kb(uid):
    u=get_user(uid); kb=[]
    if is_premium(uid):
        kb.append([InlineKeyboardButton("🎯 Start Mock from My Plan",callback_data="start_plan_mock")])
        kb.append([InlineKeyboardButton("📚 Subject Mock (40 Qs)",callback_data="mock_by_subject")])
        kb.append([InlineKeyboardButton("🔥 Full JAMB CBT Mock (180 Qs)",callback_data="mock_full")])
        kb.append([InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)])
        kb.append([InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")])
        return kb
    if not u.get("free_english_used",False):
        kb.append([InlineKeyboardButton("🆓 Free English Mock (40 Qs)",callback_data="start_free_english")])
    else:
        kb.append([InlineKeyboardButton("🛑 Free English Mock — Already Used",callback_data="premium_info")])
    kb.append([InlineKeyboardButton("🔒 Subject Mocks — Upgrade",callback_data="premium_info")])
    kb.append([InlineKeyboardButton("🔒 Full CBT Mock — Upgrade",callback_data="premium_info")])
    kb.append([InlineKeyboardButton("💎 Upgrade Now",callback_data="premium_info")])
    kb.append([InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)])
    kb.append([InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")])
    return kb


def _mock_menu_text(uid):
    u=get_user(uid)
    if is_premium(uid):
        leader_name,leader_score=get_leading()
        return (f"📝 *Mock Exam Menu*\n💎 Premium\n"
                f"🏆 Top: {md(leader_name)} — {leader_score}/400")
    if not u.get("free_english_used",False):
        return "📝 *Mock Exam Menu*\n\n🆓 *Free Plan:* 1 × 40Q English Mock"
    return "📝 *Mock Exam Menu*\n\n🛑 *You've used your free English mock.*\n\n🔒 *Upgrade to Premium:*"


def _admin_only(uid): return ADMIN_ID and str(uid)==str(ADMIN_ID)


def _admin_menu_text():
    total=len(USER_DATA)
    prem=sum(1 for u in USER_DATA.values() if u.get("is_premium"))
    widget=sum(1 for k in USER_DATA.keys() if k.startswith("widget_"))
    wa_users=sum(1 for u in USER_DATA.values() if u.get("wa_phone"))
    source_counts={}
    for u in USER_DATA.values():
        src=u.get("source") or "unknown"
        source_counts[src]=source_counts.get(src,0)+1
    source_lines="\n".join(f"  • {k.title()}: {v}"
        for k,v in sorted(source_counts.items(),key=lambda kv:-kv[1])[:8]) or "  • No data yet"
    return (f"⚙️ *Admin Panel*\n\n👥 *Users*\n"
            f"  • Total: {total}\n  • Premium: {prem}\n  • Free: {total-prem}\n"
            f"  • Widget users: {widget}\n  • WhatsApp users: {wa_users}\n\n"
            f"📊 *By Source*\n{source_lines}\n\n"
            f"📚 *Databank:* {len(ALL_QS)} Qs\n"
            f"💬 *AI Tutor:* {'✅' if HAS_AI_TUTOR else '❌'}\n"
            f"📢 *Channel:* {'✅' if CHANNEL_ID else '❌'}\n"
            f"💾 *Database:* {'✅ PostgreSQL' if DATABASE_URL else '❌'}")


def _admin_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 View Users",callback_data="admin_users"),
         InlineKeyboardButton("💰 Grant Premium",callback_data="admin_grant_prompt")],
        [InlineKeyboardButton("📢 Broadcast",callback_data="admin_broadcast_prompt")],
        [InlineKeyboardButton("📤 Post to Channel",callback_data="admin_channel_post")],
        [InlineKeyboardButton("📊 Source Breakdown",callback_data="admin_sources")],
        [InlineKeyboardButton("🧠 AI Brain Status",callback_data="admin_kb_stats")],
        [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]])


async def cmd_admin(update, context):
    uid=str(update.effective_user.id)
    if not _admin_only(uid):
        await update.message.reply_text("🔒 Admin only."); return
    await update.message.reply_text(_admin_menu_text(),parse_mode="Markdown",
                                    reply_markup=_admin_menu_kb())


async def _admin_handle_callback(query, uid, data, context):
    if not _admin_only(uid):
        await query.message.reply_text("🔒 Admin only."); return True
    if data=="admin_panel":
        await query.message.reply_text(_admin_menu_text(),parse_mode="Markdown",
                                       reply_markup=_admin_menu_kb()); return True
    if data=="admin_sources":
        source_counts={}; wa_users=[]
        for uid_k,u in USER_DATA.items():
            src=u.get("source") or "unknown"
            source_counts[src]=source_counts.get(src,0)+1
            if u.get("wa_phone"):
                wa_users.append((u.get("username","User"),u.get("wa_phone"),
                                u.get("subject_combination",[])))
        lines=["📊 *Users by Source*\n"]
        for k,v in sorted(source_counts.items(),key=lambda kv:-kv[1]):
            lines.append(f"  • *{k.title()}*: {v}")
        if wa_users:
            lines.append(f"\n📱 *WhatsApp Users* (last {min(10,len(wa_users))}):")
            for name,wp,subs in wa_users[-10:]:
                subs_str=", ".join(s.title() for s in (subs or [])) or "—"
                lines.append(f"  • {md(name)} — `{wp}` — {subs_str}")
        await query.message.reply_text("\n".join(lines),parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back",callback_data="admin_panel")]]))
        return True
    if data=="admin_users":
        lines=["👥 *Recent Users* (up to 20)\n"]
        for uid_k,u in list(USER_DATA.items())[-20:]:
            name=u.get("username","User")[:20]
            prem="💎" if u.get("is_premium") else "🆓"
            tag=" 🌐" if str(uid_k).startswith("widget_") else ""
            src=(u.get("source") or "?").title()[:8]
            lines.append(f"{prem} {md(name)} [{src}] · `{uid_k}`{tag}")
        lines.append(f"\n_Total: {len(USER_DATA)} users_")
        await query.message.reply_text("\n".join(lines),parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back",callback_data="admin_panel")]]))
        return True
    if data=="admin_grant_prompt":
        await query.message.reply_text(
            "💰 Reply with the user's Telegram ID (numbers only).",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back",callback_data="admin_panel")]]))
        USER_SESSIONS[str(uid)]={"mode":"admin_grant_wait"}; return True
    if data=="admin_broadcast_prompt":
        await query.message.reply_text(
            "📢 Reply with the broadcast text.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back",callback_data="admin_panel")]]))
        USER_SESSIONS[str(uid)]={"mode":"admin_broadcast_wait"}; return True
    if data=="admin_channel_post":
        if not CHANNEL_ID:
            await query.message.reply_text("❌ CHANNEL_ID not set."); return True
        try:
            await channel_post(context.application,slot_name="morning",slot_label="admin-manual")
            await query.message.reply_text("✅ Posted.")
        except Exception as e:
            await query.message.reply_text(f"❌ Failed: {e}")
        return True
    if data=="admin_kb_stats":
        stats=_get_kb_stats() if HAS_AI_TUTOR else {}
        ok,detail=_tutor_ping() if HAS_AI_TUTOR else (False,"n/a")
        lines=[f"🧠 *AI Brain Status ({TUTOR_NAME})*",
               f"DeepSeek: {'✅' if ok else '❌'} {md(str(detail))}",
               f"KB ready: {stats.get('ready',False)}",
               f"Chunks: {stats.get('total_chunks',0)}",
               f"BM25: {stats.get('bm25_ready',False)}",
               f"Voice: {stats.get('voice_engine','n/a')}"]
        await query.message.reply_text("\n".join(lines),parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back",callback_data="admin_panel")]]))
        return True
    return False


# ============================================================
# TELEGRAM COMMANDS
# ============================================================
async def cmd_start(update, context):
    uid=str(update.effective_user.id)
    username=update.effective_user.first_name or ""
    if context.args:
        raw_arg=context.args[0]; arg=raw_arg.lower()
        if arg.startswith("link_widget_"):
            widget_uid=raw_arg.replace("link_","",1)
            ok,msg=_merge_widget_user(widget_uid,uid)
            if ok:
                if msg!="already":
                    await update.message.reply_text(
                        "✅ *Web app linked!*\n\nYour progress has been transferred.",
                        parse_mode="Markdown")
            else:
                await update.message.reply_text("ℹ️ "+msg,parse_mode="Markdown")
        if arg=="premium":
            get_user(uid,username); await cmd_premium(update,context); return
        if arg=="mock":
            await cmd_mock(update,context); return
        if arg=="tutor":
            await cmd_tutor(update,context); return
        if arg=="webapp":
            get_user(uid,username)
            await update.message.reply_text("🌐 Open Web App:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🌐 Open",web_app={"url":WEBAPP_URL})]]))
            return
    if context.args and context.args[0].startswith("invite_"):
        code=context.args[0].replace("invite_","")
        u=get_user(uid,username)
        if not u.get("invited_by"):
            for inviter_id,inv_data in USER_DATA.items():
                if inv_data.get("invite_code")==code and inviter_id!=uid:
                    if uid not in inv_data.get("invited_users",[]):
                        u["invited_by"]=inviter_id
                        inv_data["invites"]=inv_data.get("invites",0)+1
                        inv_data.setdefault("invited_users",[]).append(uid)
                        if inv_data["invites"]>=REFERRAL_REQUIRED:
                            add_premium(inviter_id,days=REFERRAL_REWARD_DAYS,plan="referral")
                            inv_data["invites"]=0
                            inv_data["referral_rewards_claimed"]=inv_data.get("referral_rewards_claimed",0)+1
                        save_data()
                    break
    u=get_user(uid,username)
    if not u.get("plan_set",False):
        await update.message.reply_text(_plan_builder_text(uid),parse_mode="Markdown",
                                        reply_markup=_plan_builder_kb(uid))
        return
    t,kb=main_menu_text_kb(uid)
    await update.message.reply_text(t,reply_markup=kb,parse_mode="Markdown")
    await update.message.reply_text(
        f"Use buttons below 👇\n📢 Join our channel!\n"
        f"🚀 Invite {REFERRAL_REQUIRED} = {REFERRAL_REWARD_DAYS} days FREE!",
        reply_markup=BOTTOM_KEYBOARD)


async def cmd_mock(update, context):
    uid=str(update.effective_user.id)
    u=get_user(uid,update.effective_user.first_name or "")
    if not u.get("plan_set",False):
        await update.message.reply_text(_plan_builder_text(uid),parse_mode="Markdown",
                                        reply_markup=_plan_builder_kb(uid))
        return
    await update.message.reply_text(_mock_menu_text(uid),parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(_mock_menu_kb(uid)))


async def cmd_study(update, context):
    get_user(update.effective_user.id,update.effective_user.first_name or "")
    await update.message.reply_text("📖 *Study Plan:*",
                                    reply_markup=subjects_kb("study_subject"),
                                    parse_mode="Markdown")


async def cmd_syllabus(update, context):
    get_user(update.effective_user.id,update.effective_user.first_name or "")
    await update.message.reply_text("📋 *JAMB Syllabus:*",
                                    reply_markup=subjects_kb("syllabus_subject"),
                                    parse_mode="Markdown")


async def cmd_past(update, context):
    get_user(update.effective_user.id,update.effective_user.first_name or "")
    await update.message.reply_text("📚 *Past Questions:*",
                                    reply_markup=subjects_kb("past_subject"),
                                    parse_mode="Markdown")


async def cmd_score(update, context):
    uid=str(update.effective_user.id)
    u=get_user(uid,update.effective_user.first_name or "")
    hist=u.get("history",[])
    if not hist:
        await update.message.reply_text("📊 No scores yet.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Take Mock",callback_data="mock_menu")],
                [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]]))
        return
    avg=sum(h["score"]*400//h["total"] for h in hist if h["total"])/len(hist)
    leader_name,leader_score=get_leading()
    await update.message.reply_text(
        f"📊 *Your Scores*\n\nAvg: *{int(avg)}/400*\nExams: {len(hist)}\n"
        f"🏆 Leader: {md(leader_name)} — {leader_score}/400",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 New Mock",callback_data="mock_menu"),
             InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]]))


async def cmd_tutor(update, context):
    uid=str(update.effective_user.id)
    u=get_user(uid,update.effective_user.first_name or "")
    prev=USER_SESSIONS.get(uid,{}).get("subject") or u.get("study_subject")
    USER_SESSIONS[uid]={"mode":"tutor","subject":prev}
    if is_premium(uid): rem_text="Unlimited"
    else:
        used=u["tutor_counts"].get(str(date.today()),0)
        rem_text=f"{max(0,FREE_TUTOR_PER_DAY-used)}/{FREE_TUTOR_PER_DAY} left today"
    await update.message.reply_text(
        f"💬 *Ask Tutor — {TUTOR_NAME}*\n\nTutor: {rem_text}\n\n"
        f"Type any JAMB question.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)],
            [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]]))


async def cmd_invite(update, context):
    uid=str(update.effective_user.id)
    u=get_user(uid,update.effective_user.first_name or "")
    link=f"https://t.me/{BOT_USERNAME}?start=invite_{u['invite_code']}"
    share_url=f"https://t.me/share/url?url={quote(link)}&text={quote('Join UTME Success Bot!')}"
    await update.message.reply_text(
        f"👥 *Invite Friends*\n\n🎁 Invite {REFERRAL_REQUIRED} = {REFERRAL_REWARD_DAYS} days FREE!\n\n"
        f"Your link:\n`{link}`\n\nProgress: {u.get('invites',0)}/{REFERRAL_REQUIRED}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Share Link",url=share_url)],
            [InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)],
            [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]]))


async def cmd_premium(update, context):
    uid=str(update.effective_user.id); get_user(uid,update.effective_user.first_name or "")
    kb=plan_buttons(uid)
    kb.append([InlineKeyboardButton(f"👥 Invite {REFERRAL_REQUIRED}=FREE",callback_data="invite_friends")])
    kb.append([InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)])
    kb.append([InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")])
    await update.message.reply_text(
        f"💎 *Premium Plans*\n\n*Monthly — {PREMIUM_PRICE_TEXT}* / {PREMIUM_DAYS} days\n"
        f"*6 Months — {PREMIUM_6MONTHS_TEXT}* / {PREMIUM_6MONTHS_DAYS} days\n\n"
        f"✅ Unlimited mocks\n✅ Full 180Q CBT Mock\n"
        f"✅ Unlimited {TUTOR_NAME} + Voice 🎙️\n✅ Unlimited AI Why",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


async def cmd_help(update, context):
    uid=str(update.effective_user.id); get_user(uid,update.effective_user.first_name or "")
    help_text=(f"❓ *Help — UTME Success Bot*\n\n"
               f"/start — Main menu\n/mock — Start mock\n/past — Past questions\n"
               f"/study — Study plan\n/syllabus — JAMB syllabus\n/score — Scores\n"
               f"/tutor — Ask {TUTOR_NAME}\n/invite — Invite friends\n"
               f"/premium — Upgrade\n/help — This\n\n"
               f"📢 *Channel:* {CHANNEL_INVITE_LINK}\n\n"
               f"💬 *Support:* {SUPPORT_HANDLE}")
    kb=InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)],
        [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]])
    if update.callback_query:
        await update.callback_query.message.reply_text(help_text,parse_mode="Markdown",reply_markup=kb)
    else:
        await update.message.reply_text(help_text,parse_mode="Markdown",reply_markup=kb)


async def cmd_debug(update, context):
    per_subject={s:len(LOCAL_DATABANK.get(s,[])) for s in AVAILABLE_SUBJECTS}
    widget=sum(1 for k in USER_DATA.keys() if k.startswith("widget_"))
    linked=sum(1 for u in USER_DATA.values() if u.get("linked_widget_uid"))
    wa=sum(1 for u in USER_DATA.values() if u.get("wa_phone"))
    lines=[f"📊 *Databank Status*",f"Total: *{len(ALL_QS)}* questions",
           f"Subjects: *{len(AVAILABLE_SUBJECTS)}*",
           f"Engine: {'✅' if HAS_ENGINE else '❌'}",
           f"AI Tutor: {'✅' if HAS_AI_TUTOR else '❌'}",
           f"Users: *{len(USER_DATA)}*",f"Widget: *{widget}*",
           f"WhatsApp: *{wa}*",f"Linked: *{linked}*",""]
    for s in AVAILABLE_SUBJECTS:
        icon="✅" if per_subject[s]>0 else "❌"
        lines.append(f"{icon} {s}: {per_subject[s]}")
    await update.message.reply_text("\n".join(lines),parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]]))


async def cmd_kbstats(update, context):
    stats=_get_kb_stats() if HAS_AI_TUTOR else {}
    ok,detail=_tutor_ping() if HAS_AI_TUTOR else (False,"not loaded")
    lines=[f"🧠 *AI Tutor ({TUTOR_NAME})*",
           f"DeepSeek: {'✅' if ok else '❌'} {md(str(detail))}",
           f"KB ready: {stats.get('ready',False)}",
           f"Chunks: {stats.get('total_chunks',0)}",
           f"BM25: {stats.get('bm25_ready',False)}",
           f"Voice: {stats.get('voice_engine','n/a')}"]
    await update.message.reply_text("\n".join(lines),parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]]))


async def cmd_postnow(update, context):
    uid=str(update.effective_user.id)
    if str(uid)!=str(ADMIN_ID):
        await update.message.reply_text("🔒 Admin only."); return
    if not CHANNEL_ID:
        await update.message.reply_text("❌ CHANNEL_ID not set."); return
    slot_arg=context.args[0].lower() if context.args else "random"
    valid={"morning","afternoon","evening"}
    if slot_arg=="random" or slot_arg not in valid:
        slot_arg=random.choice(list(valid))
    await update.message.reply_text(f"📤 Sending *{slot_arg}*…",parse_mode="Markdown")
    try:
        await channel_post(context.application,slot_name=slot_arg,slot_label="manual")
        await update.message.reply_text(f"✅ Posted `{slot_arg}`",parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ `{type(e).__name__}: {e}`",parse_mode="Markdown")


# ============================================================
# TELEGRAM CALLBACK HANDLER
# ============================================================
async def handle_callback(update, context):
    query=update.callback_query
    await query.answer()
    uid=str(query.from_user.id)
    data=query.data
    u=get_user(uid,query.from_user.first_name or "")
    if data.startswith("admin_"):
        if await _admin_handle_callback(query,uid,data,context): return
    if data=="join_channel":
        try: await query.answer("Opening…",show_alert=False,url=CHANNEL_INVITE_LINK)
        except: pass
        return
    if data=="plan_builder":
        await query.message.reply_text(_plan_builder_text(uid),parse_mode="Markdown",
                                        reply_markup=_plan_builder_kb(uid)); return
    if data.startswith("plan_toggle_"):
        subj=data.replace("plan_toggle_","")
        if subj not in PLAN_OPTIONAL_SUBJECTS: return
        plan=u.get("jamb_plan",["english"])
        if subj in plan: plan.remove(subj)
        else:
            if len(plan)>=PLAN_SIZE:
                await query.answer(f"Max {PLAN_SIZE} subjects.",show_alert=True); return
            plan.append(subj)
        u["jamb_plan"]=plan; save_data()
        try:
            await query.edit_message_text(_plan_builder_text(uid),parse_mode="Markdown",
                                           reply_markup=_plan_builder_kb(uid))
        except:
            await query.message.reply_text(_plan_builder_text(uid),parse_mode="Markdown",
                                            reply_markup=_plan_builder_kb(uid))
        return
    if data=="plan_reset":
        u["jamb_plan"]=["english"]; u["plan_set"]=False; save_data()
        try:
            await query.edit_message_text(_plan_builder_text(uid),parse_mode="Markdown",
                                           reply_markup=_plan_builder_kb(uid))
        except:
            await query.message.reply_text(_plan_builder_text(uid),parse_mode="Markdown",
                                            reply_markup=_plan_builder_kb(uid))
        return
    if data=="plan_start":
        plan=u.get("jamb_plan",["english"])
        if len(plan)!=PLAN_SIZE:
            await query.answer(f"Select all {PLAN_SIZE} subjects.",show_alert=True); return
        u["plan_set"]=True; save_data()
        await _start_plan_mock(query,uid,u); return
    if data=="start_plan_mock":
        plan=u.get("jamb_plan",["english"])
        if len(plan)!=PLAN_SIZE:
            await query.message.reply_text(_plan_builder_text(uid),parse_mode="Markdown",
                                            reply_markup=_plan_builder_kb(uid)); return
        await _start_plan_mock(query,uid,u); return
    if data=="start_free_english":
        if is_premium(uid):
            await query.answer("You're Premium.",show_alert=True); return
        if u.get("free_english_used",False):
            msg,kb=upgrade_kb(uid)
            await query.message.reply_text(msg,parse_mode="Markdown",reply_markup=kb); return
        qs=_fetch_rotated(uid,"english",FREE_ENGLISH_QS)
        if len(qs)<10:
            await query.message.reply_text("⚠️ Not enough English Qs."); return
        u["free_english_used"]=True; save_data()
        intro=(f"🆓 *Free English Mock (One-time)*\n\n{len(qs)} questions")
        txt,kb=_start_mock_session(uid,qs,"english",intro_text=intro)
        await query.message.reply_text(txt,parse_mode="Markdown",reply_markup=kb); return
    if data in ("mock_by_subject","mock_full","cbt_start","cbt_clear") and not is_premium(uid):
        msg,kb=upgrade_kb(uid)
        await query.message.reply_text(f"🔒 *Premium*\n\n{msg}",parse_mode="Markdown",reply_markup=kb); return
    if (data.startswith("mock_subject_") or data.startswith("cbt_toggle_")) and not is_premium(uid):
        msg,kb=upgrade_kb(uid)
        await query.message.reply_text(f"🔒 *Premium*\n\n{msg}",parse_mode="Markdown",reply_markup=kb); return
    if data=="study_plan":
        await query.message.reply_text("📖 *Study:*",reply_markup=subjects_kb("study_subject"),
                                        parse_mode="Markdown"); return
    if data.startswith("study_subject_"):
        subj=data.replace("study_subject_",""); u["study_subject"]=subj; save_data()
        display=SUBJECT_DISPLAY.get(subj,subj.title())
        USER_SESSIONS[uid]={"mode":"tutor","subject":subj}
        count=len(LOCAL_DATABANK.get(subj,[]))
        await query.message.reply_text(f"📖 *{display}!* {count} Qs.",parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"💬 Ask {display}",callback_data="ask_tutor")],
                [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]]))
        return
    if data=="syllabus":
        await query.message.reply_text("📋 *Syllabus:*",reply_markup=subjects_kb("syllabus_subject"),
                                        parse_mode="Markdown"); return
    if data.startswith("syllabus_subject_"):
        subj=data.replace("syllabus_subject_","")
        display=SUBJECT_DISPLAY.get(subj,subj.title())
        await query.message.reply_text(f"📋 *{display}*\nhttps://jamb.gov.ng/ELibrary",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"📖 Study",callback_data=f"study_subject_{subj}")],
                [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]]))
        return
    if data=="past_by_subject":
        await query.message.reply_text("📚 *Past Questions:*",reply_markup=subjects_kb("past_subject"),
                                        parse_mode="Markdown"); return
    if data.startswith("past_subject_"):
        subj=data.replace("past_subject_","")
        allowed,reason=can_take_subject(uid,subj)
        if not allowed:
            msg,kb=upgrade_kb(uid)
            await query.message.reply_text(f"🔒 *Premium*\n\n{msg}",parse_mode="Markdown",reply_markup=kb); return
        qs=_fetch_rotated(uid,subj,5)
        if not qs:
            await query.message.reply_text(f"⚠️ No questions for {SUBJECT_DISPLAY.get(subj,subj)}."); return
        txt,kb=_start_mock_session(uid,qs,subj)
        await query.message.reply_text(txt,reply_markup=kb); return
    if data.startswith("ans:"):
        ans=data.split(":")[1]
        session=USER_SESSIONS.get(uid)
        if not session or session.get("mode")!="mock":
            await query.message.reply_text("Expired.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📝 Mock",callback_data="mock_menu")]])); return
        qs=session["qs"]; idx=session["idx"]
        if idx>=len(qs): return
        current_q=qs[idx]; correct=current_q.get("answer","")
        is_correct=(ans==correct)
        if is_correct: session["score"]+=1
        else: session["failed"].append(_make_failure_snapshot(current_q,ans,correct,idx+1))
        session["idx"]+=1
        if is_correct: await query.message.reply_text("✅ Correct…")
        else: await query.message.reply_text("❌ Wrong…")
        if session["idx"]<len(qs):
            q=qs[session["idx"]]
            txt=format_question(q,session["idx"]+1,len(qs))
            await query.message.reply_text(txt,reply_markup=_answer_keyboard(q))
        else:
            score=session["score"]; total=len(qs); failed=session.get("failed",[])
            n_failed=len(failed)
            u["history"].append({"date":str(date.today()),
                                 "subject":session.get("subject","general"),
                                 "score":score,"total":total,
                                 "percent":score*100//total if total else 0})
            u["last_mock_failed"]=failed; u["last_mock_subject"]=session.get("subject","general")
            u["last_mock_total"]=total; save_data()
            subj_label=session.get("subject","general")
            if subj_label.startswith("subject_"): subj_label=subj_label.replace("subject_","")
            if subj_label.startswith("CBT:"): subj_label="Full JAMB CBT"
            subj_display=SUBJECT_DISPLAY.get(subj_label,subj_label.title())
            finish_msg,is_perfect=_build_completion_message(uid,score,total,failed,subj_label,subj_display)
            buttons=[]
            if not is_perfect and n_failed>0:
                if is_premium(uid): fix_label=f"🤖 Fix My {n_failed} Failures (Unlimited)"
                else:
                    _,rem=can_use_ai_why(uid)
                    fix_label=f"🤖 Fix My {n_failed} Failures ({rem} FREE)"
                buttons.append([InlineKeyboardButton(fix_label,callback_data="see_failures")])
                buttons.append([InlineKeyboardButton("📊 See All Failed",callback_data="see_failures")])
                state=_get_user_state(uid); rank=_get_user_rank_number(uid,score,total)
                buttons.append([InlineKeyboardButton(f"🏆 Leaderboard — #{rank}",callback_data="check_rank")])
            else:
                state=_get_user_state(uid); rank=_get_user_rank_number(uid,score,total)
                buttons.append([InlineKeyboardButton(f"🏆 {state} Rank — #{rank}",callback_data="check_rank")])
            if not is_premium(uid):
                finish_msg+=f"\n\n🛑 _Free mock used._ Upgrade for unlimited."
                buttons.append([InlineKeyboardButton("💎 Upgrade",callback_data="premium_info")])
            buttons.append([InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)])
            buttons.append([InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")])
            try:
                await query.message.reply_text(finish_msg[:4000],parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(buttons))
            except:
                await query.message.reply_text(finish_msg[:4000],
                    reply_markup=InlineKeyboardMarkup(buttons))
        return
    if data=="see_failures":
        failed=u.get("last_mock_failed",[])
        if not failed:
            session=USER_SESSIONS.get(uid,{}); failed=session.get("failed",[])
        if not failed:
            try:
                reloaded=get_user(uid); failed=reloaded.get("last_mock_failed",[])
                if failed: u["last_mock_failed"]=failed; save_data()
            except: pass
        if not failed:
            await query.message.reply_text("📋 *No failures.*",parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 Start Mock",callback_data="start_plan_mock")],
                    [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]])); return
        total_failed=len(failed); MAX_SHOW=15
        lines=[f"📋 *{total_failed} Failed Questions*\n"]
        buttons=[]
        for i,f in enumerate(failed[:MAX_SHOW]):
            qtext=str(f.get("question") or "")[:55]
            topic=f.get("topic","General") or "General"
            q_num=f.get("q_num",i+1)
            lines.append(f"*Q{q_num}* — _{md(topic)}_\n_{md(qtext)}..._\n"
                         f"You: *{f.get('user_ans','?')}* · Correct: *{f.get('correct_ans','?')}*\n")
            buttons.append([InlineKeyboardButton(f"🤖 Ask Why Q{q_num}",callback_data=f"askwhy_{i}")])
        buttons.append([InlineKeyboardButton("🤖 Ask AI Tutor",callback_data="ask_ellams_failures")])
        buttons.append([InlineKeyboardButton("🏆 Check Rank",callback_data="check_rank")])
        buttons.append([InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)])
        buttons.append([InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")])
        text="\n".join(lines)
        try:
            await query.message.reply_text(text[:4000],parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons))
        except:
            await query.message.reply_text(text[:4000],reply_markup=InlineKeyboardMarkup(buttons))
        return
    if data.startswith("askwhy_"):
        idx=int(data.split("_")[1])
        failed=u.get("last_mock_failed",[])
        if idx>=len(failed):
            session=USER_SESSIONS.get(uid,{}); failed=session.get("failed",[])
        if idx>=len(failed):
            await query.message.reply_text("Failure not available.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 Start Mock",callback_data="start_plan_mock")],
                    [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]])); return
        allowed,remaining=can_use_ai_why(uid)
        if not allowed:
            msg,kb=ai_why_limit_kb(uid)
            await query.message.reply_text(msg,parse_mode="Markdown",reply_markup=kb); return
        consume_ai_why(uid)
        f=failed[idx]
        q_num=f.get("q_num",idx+1)
        seed=int(hashlib.md5(f"{uid}_{q_num}_others".encode()).hexdigest(),16)
        others_count=200+(seed%250)
        USER_SESSIONS[uid]={"mode":"explaining","explain_idx":idx}
        free_text="Unlimited" if is_premium(uid) else f"{remaining-1} FREE left"
        text1=(f"❌ *Q{q_num}*\n\n*Q:* {md(str(f.get('question',''))[:300])}\n\n"
               f"Your answer: *{f.get('user_ans','?')}* ❌\n"
               f"Correct: *{f.get('correct_ans','?')}* ✅\n\n"
               f"👥 {others_count} others chose {f.get('user_ans','?')}\n\n"
               f"🤖 _Analyzing..._")
        keyboard1=[[InlineKeyboardButton(f"👁️ See why — {free_text}",
                                          callback_data=f"full_exp_{idx}")]]
        try:
            await query.message.reply_text(text1,parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard1))
        except:
            await query.message.reply_text(text1,reply_markup=InlineKeyboardMarkup(keyboard1))
        return
    if data.startswith("full_exp_"):
        try: idx=int(data.split("_")[2])
        except: return
        failed=u.get("last_mock_failed",[])
        if idx>=len(failed):
            session=USER_SESSIONS.get(uid,{}); failed=session.get("failed",[])
        if idx>=len(failed):
            await query.message.reply_text("Unavailable.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]])); return
        f=failed[idx]
        q_num=f.get("q_num",idx+1)
        mini_q=f"Question: {f.get('question','')}\nTopic: {f.get('topic','General')}"
        try:
            analysis=await asyncio.to_thread(_analyze_failure,mini_q,
                f.get("user_ans",""),f.get("correct_ans",""),f.get("topic","General")) if HAS_AI_TUTOR else "⚠️ AI Tutor unavailable."
        except: analysis="⚠️ Analysis failed."
        text2=(f"✅ *Q{q_num}*\n\n{analysis}\n\n"
               f"_You chose *{f.get('user_ans','?')}*_")
        buttons=[[InlineKeyboardButton("🎙️ Voice",callback_data=f"voice_exp_{idx}")],
                 [InlineKeyboardButton("📋 Back",callback_data="see_failures")],
                 [InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)],
                 [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]]
        try:
            await query.message.reply_text(text2[:4000],parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons))
        except:
            await query.message.reply_text(text2[:4000],reply_markup=InlineKeyboardMarkup(buttons))
        return
    if data.startswith("voice_exp_"):
        try: idx=int(data.split("_")[2])
        except: return
        failed=u.get("last_mock_failed",[])
        if idx>=len(failed): return
        f=failed[idx]
        try:
            if HAS_AI_TUTOR:
                mini_q=f"Question: {f.get('question','')}\nTopic: {f.get('topic','General')}"
                analysis=await asyncio.to_thread(_analyze_failure,mini_q,
                    f.get("user_ans",""),f.get("correct_ans",""),f.get("topic","General"))
                voice_if=await asyncio.to_thread(_build_voice,analysis)
                if voice_if is not None:
                    await query.message.reply_voice(voice=voice_if,
                        caption=f"🎙️ Voice — {TUTOR_NAME}")
                else:
                    await query.message.reply_text("⚠️ Voice unavailable.")
            else:
                await query.message.reply_text("⚠️ AI Tutor unavailable.")
        except Exception as e:
            print(f"[voice_exp] {e}")
            await query.message.reply_text("⚠️ Voice failed.")
        return
    if data=="ask_ellams_failures":
        failed=u.get("last_mock_failed",[])
        if not failed:
            session=USER_SESSIONS.get(uid,{}); failed=session.get("failed",[])
        if not failed:
            await query.message.reply_text("📋 *No recent failures.*",parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 Start Mock",callback_data="start_plan_mock")],
                    [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]])); return
        allowed,remaining=can_use_ai_why(uid)
        if not allowed:
            msg,kb=ai_why_limit_kb(uid)
            await query.message.reply_text(msg,parse_mode="Markdown",reply_markup=kb); return
        consume_ai_why(uid)
        topics={}
        for f in failed:
            t=f.get("topic","General"); topics[t]=topics.get(t,0)+1
        summary=[]
        for i,f in enumerate(failed[:5]):
            summary.append(f"{i+1}. [{f.get('topic','Gen')}] Q: {str(f.get('question',''))[:80]}\n"
                           f"   Student: {f.get('user_ans','?')} · Correct: {f.get('correct_ans','?')}")
        big_q=(f"Student failed {len(failed)} JAMB Qs. Weak topics: {', '.join(topics.keys())}.\n\n"
               f"Sample:\n"+"\n".join(summary)+"\n\nGive targeted revision plan.")
        thinking=await query.message.reply_text(f"🧠 *{TUTOR_NAME} reviewing…*",parse_mode="Markdown")
        try: analysis=await asyncio.to_thread(_ask_tutor,big_q,"") if HAS_AI_TUTOR else "⚠️ AI Tutor unavailable."
        except: analysis="⚠️ Failed."
        try: await thinking.delete()
        except: pass
        rem_after=""
        if not is_premium(uid):
            _,rem=can_use_ai_why(uid)
            rem_after=f"\n\n_💬 Free AI Why left: {rem}/{FREE_AI_WHY_PER_DAY}_"
        final=(f"🤖 *AI Tutor Analysis*\n\n"+analysis)[:3800]+rem_after
        await query.message.reply_text(final,parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Individual Failures",callback_data="see_failures")],
                [InlineKeyboardButton("🏆 Check Rank",callback_data="check_rank")],
                [InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)],
                [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]]))
        return
    if data=="check_rank":
        subj_label=u.get("last_mock_subject","general")
        if subj_label.startswith("subject_"): subj_label=subj_label.replace("subject_","")
        if subj_label.startswith("CBT:"): subj_label="Full JAMB CBT"
        subj_display=SUBJECT_DISPLAY.get(subj_label,subj_label.title())
        total=u.get("last_mock_total",40)
        user_score=0
        hist=u.get("history",[])
        if hist: user_score=hist[-1].get("score",0)
        rank_text=_generate_rank(uid,subj_display,user_score,total)
        await query.message.reply_text(rank_text,parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 See Failures",callback_data="see_failures")],
                [InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)],
                [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]]))
        return
    if data=="mock_menu":
        await query.message.reply_text(_mock_menu_text(uid),parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(_mock_menu_kb(uid))); return
    if data=="mock_by_subject":
        await query.message.reply_text("📚 *Choose Subject:*",
            reply_markup=subjects_kb("mock_subject"),parse_mode="Markdown"); return
    if data.startswith("mock_subject_"):
        subj=data.replace("mock_subject_","")
        qs=_fetch_rotated(uid,subj,40)
        if len(qs)<5:
            await query.message.reply_text(f"⚠️ Not enough for {SUBJECT_DISPLAY.get(subj,subj)}."); return
        display=SUBJECT_DISPLAY.get(subj,subj.title())
        intro=f"📚 *{display} Mock*\n{len(qs)} Qs"
        txt,kb=_start_mock_session(uid,qs,f"subject_{subj}",intro_text=intro)
        await query.message.reply_text(txt,parse_mode="Markdown",reply_markup=kb); return
    if data=="mock_full":
        plan=u.get("jamb_plan",["english"])[:4]
        if len(plan)!=4:
            await query.message.reply_text("Set 4-subject plan first.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✏️ Set",callback_data="plan_builder")]])); return
        qs=_fetch_rotated_multi(uid,plan,180)
        if len(qs)<20:
            await query.message.reply_text(f"⚠️ Only {len(qs)} Qs."); return
        intro=(f"🚀 *Full JAMB CBT Mock*\n\nTotal: {len(qs)} Qs\n"
               f"⏱️ Recommended: 2 hours\n\nGood luck!")
        subj_label="CBT:"+",".join(plan)
        txt,kb=_start_mock_session(uid,qs,subj_label,intro_text=intro)
        await query.message.reply_text(txt,parse_mode="Markdown",reply_markup=kb); return
    if data=="my_score":
        hist=u.get("history",[])
        if not hist:
            await query.message.reply_text("📊 No scores yet.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📝 Mock",callback_data="mock_menu")]])); return
        avg=sum(h["score"]*400//h["total"] for h in hist if h["total"])/len(hist)
        leader_name,leader_score=get_leading()
        await query.message.reply_text(
            f"📊 Avg {int(avg)}/400 · Exams {len(hist)}\n"
            f"🏆 Leader: {md(leader_name)} — {leader_score}/400",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]]))
        return
    if data=="ask_tutor":
        prev=USER_SESSIONS.get(uid,{}).get("subject") or u.get("study_subject")
        USER_SESSIONS[uid]={"mode":"tutor","subject":prev}
        if is_premium(uid): rem_text="Unlimited"
        else:
            used=u["tutor_counts"].get(str(date.today()),0)
            rem_text=f"{max(0,FREE_TUTOR_PER_DAY-used)}/{FREE_TUTOR_PER_DAY} left"
        await query.message.reply_text(
            f"💬 *Ask {TUTOR_NAME}*\nTutor: {rem_text}\n\nAsk anything:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)],
                [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]]))
        return
    if data=="premium_info":
        kb=plan_buttons(uid)
        kb.append([InlineKeyboardButton(f"👥 Invite {REFERRAL_REQUIRED}=FREE",callback_data="invite_friends")])
        kb.append([InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)])
        kb.append([InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")])
        await query.message.reply_text(
            f"💎 *Premium Plans*\n\n*Monthly — {PREMIUM_PRICE_TEXT}* / {PREMIUM_DAYS} days\n"
            f"*6 Months — {PREMIUM_6MONTHS_TEXT}* / {PREMIUM_6MONTHS_DAYS} days\n\n"
            f"✅ Unlimited mocks\n✅ Full 180Q CBT Mock\n"
            f"✅ Unlimited {TUTOR_NAME} + Voice 🎙️\n✅ Unlimited AI Why",
            parse_mode="Markdown",reply_markup=InlineKeyboardMarkup(kb))
        return
    if data=="invite_friends":
        link=f"https://t.me/{BOT_USERNAME}?start=invite_{u['invite_code']}"
        share_url=f"https://t.me/share/url?url={quote(link)}&text={quote('Join UTME Success Bot!')}"
        await query.message.reply_text(
            f"👥 *Invite Friends*\n\n🎁 {REFERRAL_REQUIRED} = {REFERRAL_REWARD_DAYS} days FREE!\n\n"
            f"`{link}`\n\nProgress: {u.get('invites',0)}/{REFERRAL_REQUIRED}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Share Link",url=share_url)],
                [InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)],
                [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]]))
        return
    if data=="help_menu":
        await cmd_help(update,context); return
    if data=="main_menu":
        if not u.get("plan_set",False):
            await query.message.reply_text(_plan_builder_text(uid),parse_mode="Markdown",
                                            reply_markup=_plan_builder_kb(uid)); return
        t,kb=main_menu_text_kb(uid)
        await query.message.reply_text(t,reply_markup=kb,parse_mode="Markdown"); return


async def _start_plan_mock(query, uid, u):
    plan=u.get("jamb_plan",["english"])
    if not is_premium(uid):
        if u.get("free_english_used",False):
            msg,kb=upgrade_kb(uid)
            await query.message.reply_text(
                f"🔒 *Free mock used.*\n\n{msg}",parse_mode="Markdown",reply_markup=kb); return
        qs=_fetch_rotated(uid,"english",FREE_ENGLISH_QS)
        if len(qs)<10:
            await query.message.reply_text("⚠️ Not enough English Qs."); return
        u["free_english_used"]=True; save_data()
        intro=(f"🆓 *Free English Mock*\nPlan: {', '.join(SUBJECT_DISPLAY.get(s,s.title()) for s in plan)}")
        txt,kb=_start_mock_session(uid,qs,"english",intro_text=intro)
        await query.message.reply_text(txt,parse_mode="Markdown",reply_markup=kb); return
    subject=plan[0] if plan else "english"
    qs=_fetch_rotated(uid,subject,40)
    if len(qs)<5:
        await query.message.reply_text(f"⚠️ Not enough for {SUBJECT_DISPLAY.get(subject,subject)}."); return
    display=SUBJECT_DISPLAY.get(subject,subject.title())
    intro=f"🎯 *Mock from Plan*\nStarting: *{display}*"
    txt,kb=_start_mock_session(uid,qs,f"subject_{subject}",intro_text=intro)
    await query.message.reply_text(txt,parse_mode="Markdown",reply_markup=kb)


# ============================================================
# TELEGRAM TEXT HANDLER
# ============================================================
async def handle_msg(update, context):
    uid=str(update.effective_user.id)
    text=(update.message.text or "").strip()
    u=get_user(uid,update.effective_user.first_name or "")
    if _admin_only(uid):
        s=USER_SESSIONS.get(uid,{})
        mode=s.get("mode")
        if mode=="admin_grant_wait":
            tid=text.strip()
            if tid.isdigit():
                add_premium(tid,days=PREMIUM_DAYS,plan="admin-grant")
                USER_SESSIONS.pop(uid,None)
                await update.message.reply_text(f"✅ Granted to `{tid}`",parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⚙️ Admin",callback_data="admin_panel")]]))
            else:
                await update.message.reply_text("❌ Invalid.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back",callback_data="admin_panel")]]))
            return
        if mode=="admin_broadcast_wait":
            USER_SESSIONS.pop(uid,None)
            bt=text.strip(); sent=0; failed=0
            msg=await update.message.reply_text(f"📢 Broadcasting…")
            for tu in list(USER_DATA.keys()):
                if tu.startswith("widget_"): continue
                try:
                    await context.bot.send_message(chat_id=int(tu),text=bt,parse_mode="Markdown")
                    sent+=1; await asyncio.sleep(0.05)
                except: failed+=1
            await msg.edit_text(f"✅ Sent: {sent} · Failed: {failed}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Admin",callback_data="admin_panel")]]))
            return
    if text=="⚙️ Admin Panel" and _admin_only(uid):
        await cmd_admin(update,context); return
    if text=="📢 Join Our Channel":
        await update.message.reply_text(
            f"📢 *Join Our Channel*\n\n👉 {CHANNEL_INVITE_LINK}",
            parse_mode="Markdown",disable_web_page_preview=False,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Tap Here",url=CHANNEL_INVITE_LINK)],
                [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]]))
        return
    if text=="📚 Past Questions": await cmd_past(update,context); return
    if text=="📝 Mock Exam": await cmd_mock(update,context); return
    if text=="📊 My Score": await cmd_score(update,context); return
    if text=="💬 Ask Tutor": await cmd_tutor(update,context); return
    if text=="💎 Premium": await cmd_premium(update,context); return
    if text=="👥 Invite Friends": await cmd_invite(update,context); return
    if text=="📖 Study Plan": await cmd_study(update,context); return
    if not u.get("plan_set",False):
        await update.message.reply_text(_plan_builder_text(uid),parse_mode="Markdown",
                                        reply_markup=_plan_builder_kb(uid)); return
    session=USER_SESSIONS.get(uid,{})
    is_tutor=(session.get("mode")=="tutor" or
              (session.get("mode") not in ("cbt_select","post_mock","explaining") and
               ("?" in text or len(text)>8)))
    if not is_tutor:
        await update.message.reply_text("Use the menu below 👇",reply_markup=BOTTOM_KEYBOARD); return
    if not can_use_tutor(uid):
        msg,kb=upgrade_kb(uid)
        await update.message.reply_text(f"⏰ *Limit*\n\n{msg}",parse_mode="Markdown",reply_markup=kb); return
    consume_tutor(uid)
    try:
        thinking=await update.message.reply_text(f"🧠 *{TUTOR_NAME} thinking…*",parse_mode="Markdown")
    except: thinking=None
    subj=session.get("subject") or u.get("study_subject") or ""
    display=SUBJECT_DISPLAY.get(subj,subj.title()) if subj else "JAMB"
    try:
        answer_text=await asyncio.to_thread(_ask_tutor,text,subj) if HAS_AI_TUTOR else "⚠️ AI Tutor unavailable."
    except: answer_text="⚠️ Error."
    if thinking is not None:
        try: await thinking.delete()
        except: pass
    header=f"💬 *{TUTOR_NAME} — {md(display)}*\n\n*Q:* {md(text[:300])}\n\n"
    footer="\n\n_📚 Grounded in JAMB + DeepSeek_"
    final_msg=header+answer_text+footer
    kb=InlineKeyboardMarkup([
        [InlineKeyboardButton("🎙️ Voice",callback_data="ask_tutor")],
        [InlineKeyboardButton("📢 Join Our Channel",url=CHANNEL_INVITE_LINK)],
        [InlineKeyboardButton("🏠 Main Menu",callback_data="main_menu")]])
    try:
        await update.message.reply_text(final_msg[:4000],parse_mode="Markdown",reply_markup=kb)
    except:
        try: await update.message.reply_text(final_msg[:4000],reply_markup=kb)
        except: pass
    if HAS_AI_TUTOR:
        try:
            vi=await asyncio.to_thread(_build_voice,answer_text)
            if vi is not None:
                await update.message.reply_voice(voice=vi,caption=f"🎙️ Voice — {TUTOR_NAME}")
        except: pass


# ============================================================
# FLASK APP
# ============================================================
flask_app = Flask(__name__)


@flask_app.route("/")
def home():
    wa_count = sum(1 for u in USER_DATA.values() if u.get("source") == "whatsapp")
    return (f"UTME Bot v47 · {len(ALL_QS)} Qs · Tutor: {TUTOR_NAME} · "
            f"Users: {len(USER_DATA)} (WhatsApp: {wa_count}) · "
            f"DB: {'PG' if DATABASE_URL else 'NONE'} · Running")


@flask_app.route("/health")
def health():
    tutor_ok,_=_tutor_ping() if HAS_AI_TUTOR else (False,"n/a")
    widget=sum(1 for k in USER_DATA.keys() if k.startswith("widget_"))
    linked=sum(1 for u in USER_DATA.values() if u.get("linked_widget_uid"))
    wa=sum(1 for u in USER_DATA.values() if u.get("wa_phone"))
    return jsonify({"status":"ok","version":"v47-leaderboard",
        "bot_username":BOT_USERNAME,"tutor_name":TUTOR_NAME,
        "total_questions":len(ALL_QS),"tutor_ok":tutor_ok,
        "channel_configured":bool(CHANNEL_ID),
        "webapp_url":WEBAPP_URL,"widget_users":widget,
        "linked_to_telegram":linked,"whatsapp_users":wa,
        "users":len(USER_DATA),"logo_url":LOGO_URL,
        "whatsapp_configured":bool(WHATSAPP_TOKEN and PHONE_NUMBER_ID),
        "database":"postgresql" if DATABASE_URL else "none"})


@flask_app.route("/debug/flw-key")
def debug_flw_key():
    key=(FLW_SECRET_KEY or "").strip()
    return jsonify({"present":bool(key),"length":len(key),
        "prefix":key[:12] if key else "(empty)",
        "suffix":key[-4:] if key else "(empty)",
        "mode":"TEST" if key.startswith("FLWSECK_TEST") else ("LIVE" if key.startswith("FLWSECK") else "UNKNOWN")})


SESSION_SECRET = (BOT_TOKEN or "dev-secret").encode()
WEBAPP_MOCKS = {}


def _make_session(uid):
    exp=int(time.time())+30*24*3600
    msg=f"{uid}|{exp}"
    sig=hmac.new(SESSION_SECRET,msg.encode(),hashlib.sha256).hexdigest()
    return f"{msg}|{sig}"


def _read_session(token):
    try:
        uid,exp,sig=token.split("|")
        if int(exp)<time.time(): return None
        expected=hmac.new(SESSION_SECRET,f"{uid}|{exp}".encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig,expected): return None
        return uid
    except: return None


def _require_session():
    auth=request.headers.get("Authorization","")
    if not auth.startswith("Bearer "): return None
    return _read_session(auth[7:])


def _admin_required():
    uid=_require_session()
    if not uid: return None
    if not ADMIN_ID or str(uid)!=str(ADMIN_ID): return None
    return uid


def _verify_webapp_initdata(init_data):
    try:
        parsed=dict(parse_qsl(init_data,keep_blank_values=True))
        hash_val=parsed.pop("hash",None)
        if not hash_val: return None
        dcs="\n".join(f"{k}={v}" for k,v in sorted(parsed.items()))
        secret=hmac.new(BOT_TOKEN.encode(),b"WebAppData",hashlib.sha256).digest()
        calc=hmac.new(secret,dcs.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calc,hash_val): return None
        return json.loads(parsed.get("user","{}"))
    except: return None


@flask_app.after_request
def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"]="*"
    resp.headers["Access-Control-Allow-Methods"]="GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"]="Content-Type, Authorization"
    return resp


@flask_app.route("/api/config", methods=["GET"])
def api_config():
    return jsonify({"status":"success","logo_url":LOGO_URL,
        "bot_username":BOT_USERNAME,"app_name":"UTME Success Bot",
        "webapp_url":WEBAPP_URL,"channel_link":CHANNEL_INVITE_LINK})


@flask_app.route("/api/webapp/auth", methods=["POST", "OPTIONS"])
def api_webapp_auth():
    if request.method=="OPTIONS": return "",204
    body=request.get_json(silent=True) or {}
    init_data=body.get("initData","")
    if not init_data: return jsonify({"status":"error","message":"missing initData"}),400
    tg_user=_verify_webapp_initdata(init_data)
    if not tg_user or not tg_user.get("id"):
        return jsonify({"status":"error","message":"invalid signature"}),401
    uid=str(tg_user["id"])
    u=get_user(uid,tg_user.get("first_name",""))
    return jsonify({"status":"success","token":_make_session(uid),"uid":uid,
        "user":{"username":u.get("username",""),
                "is_premium":is_premium(uid),
                "is_admin":(str(uid)==str(ADMIN_ID)) if ADMIN_ID else False,
                "premium_until":u.get("premium_until"),
                "plan":u.get("jamb_plan",["english"]),
                "plan_set":u.get("plan_set",False),
                "free_english_used":u.get("free_english_used",False)}})


@flask_app.route("/api/widget/register", methods=["POST", "OPTIONS"])
def api_widget_register():
    if request.method=="OPTIONS": return "",204
    body=request.get_json(silent=True) or {}
    device_id=str(body.get("device_id","")).strip()[:80]
    nickname=str(body.get("nickname","")).strip()[:24]
    phone=str(body.get("phone","")).strip()[:20]
    ref_code=str(body.get("ref","")).strip()[:20]
    source_raw=str(body.get("source","")).strip()[:30]
    wa_phone=str(body.get("wa","")).strip()[:20]
    subjects_raw=body.get("subjects","")
    wa_name=str(body.get("wa_name","")).strip()[:40]
    if not device_id.startswith("w_") or len(device_id)<8:
        return jsonify({"status":"error","message":"invalid device id"}),400
    source=_normalize_source(source_raw)
    subjects=_normalize_subjects(subjects_raw)
    final_name=nickname or wa_name or "Student"
    final_phone=phone or wa_phone
    existing_uid=_find_user_by_phone(final_phone) if final_phone else None
    reused=False
    if existing_uid:
        uid=existing_uid
        u=get_user(uid)
        if final_name and (not u.get("username") or u.get("username","").startswith("User")):
            u["username"]=final_name
        if final_phone and not u.get("phone"): u["phone"]=final_phone
        if source and not u.get("source"): u["source"]=source
        if source and not u.get("first_seen_platform"): u["first_seen_platform"]=source
        if wa_phone and not u.get("wa_phone"): u["wa_phone"]=wa_phone
        if subjects and not u.get("subject_combination"): u["subject_combination"]=subjects
        u["linked_device_id"]=device_id
        USER_DATA[uid]=u
        save_data()
        reused=True
    else:
        uid="widget_"+device_id[2:]
        u=get_user(uid, final_name)
        if final_name: u["username"]=final_name
        if final_phone: u["phone"]=final_phone
        u["linked_device_id"]=device_id
        if source:
            u["source"]=source; u["first_seen_platform"]=source
        if wa_phone: u["wa_phone"]=wa_phone
        if subjects: u["subject_combination"]=subjects
        USER_DATA[uid]=u
        save_data()
        if ref_code: _apply_referral_code(uid,ref_code)
    return jsonify({"status":"success","token":_make_session(uid),"uid":uid,
        "reused":reused,
        "user":{"username":u.get("username","Student"),
                "phone":u.get("phone",""),
                "is_premium":is_premium(uid),
                "is_admin":(str(uid)==str(ADMIN_ID)) if ADMIN_ID else False,
                "premium_until":u.get("premium_until"),
                "plan":u.get("jamb_plan",["english"]),
                "plan_set":u.get("plan_set",False),
                "free_english_used":u.get("free_english_used",False),
                "source":u.get("source"),
                "subject_combination":u.get("subject_combination",[])}})


@flask_app.route("/api/whatsapp/identify", methods=["POST", "OPTIONS"])
def api_whatsapp_identify():
    if request.method=="OPTIONS": return "",204
    body=request.get_json(silent=True) or {}
    expected_secret=os.getenv("WA_API_SECRET","").strip()
    if expected_secret:
        provided=str(body.get("secret","")).strip()
        if not hmac.compare_digest(provided,expected_secret):
            return jsonify({"status":"error","message":"unauthorized"}),401
    wa_phone=str(body.get("wa_phone","")).strip()[:20]
    wa_name=str(body.get("name","")).strip()[:40]
    subjects_raw=body.get("subjects","")
    if not wa_phone:
        return jsonify({"status":"error","message":"missing wa_phone"}),400
    normalized=re.sub(r'\D','',wa_phone)
    if len(normalized)<10:
        return jsonify({"status":"error","message":"invalid phone"}),400
    subjects=_normalize_subjects(subjects_raw)
    existing_uid=_find_user_by_phone(wa_phone)
    if existing_uid:
        u=get_user(existing_uid)
        u["wa_phone"]=wa_phone
        if wa_name and (not u.get("username") or u.get("username","").startswith("User")):
            u["username"]=wa_name
        if subjects:
            u["subject_combination"]=subjects
            if not u.get("plan_set") and len(subjects)>=2:
                ps=subjects
                if "english" not in ps: ps=["english"]+ps[:PLAN_SIZE-1]
                u["jamb_plan"]=ps[:PLAN_SIZE]
                u["plan_set"]=len(u["jamb_plan"])==PLAN_SIZE
        if not u.get("source"): u["source"]="whatsapp"
        if not u.get("first_seen_platform"): u["first_seen_platform"]="whatsapp"
        USER_DATA[existing_uid]=u
        save_data()
        return jsonify({"status":"success","uid":existing_uid,"reused":True})
    new_uid="wa_"+normalized[-10:]
    u=get_user(new_uid, wa_name or "WhatsApp User")
    if wa_name: u["username"]=wa_name
    u["phone"]=wa_phone; u["wa_phone"]=wa_phone
    u["source"]="whatsapp"; u["first_seen_platform"]="whatsapp"
    if subjects:
        u["subject_combination"]=subjects
        if len(subjects)>=2:
            ps=subjects
            if "english" not in ps: ps=["english"]+ps[:PLAN_SIZE-1]
            u["jamb_plan"]=ps[:PLAN_SIZE]
            u["plan_set"]=len(u["jamb_plan"])==PLAN_SIZE
    USER_DATA[new_uid]=u
    save_data()
    return jsonify({"status":"success","uid":new_uid,"reused":False})


@flask_app.route("/api/webapp/stats", methods=["GET"])
def api_webapp_stats():
    return jsonify({"status":"success","questions":len(ALL_QS),
        "subjects":AVAILABLE_SUBJECTS,"subject_display":SUBJECT_DISPLAY,
        "users":len(USER_DATA),"tutor_name":TUTOR_NAME,
        "free_english_qs":FREE_ENGLISH_QS,
        "free_tutor_per_day":FREE_TUTOR_PER_DAY,
        "free_ai_why_per_day":FREE_AI_WHY_PER_DAY,
        "plan_size":PLAN_SIZE,"bot_username":BOT_USERNAME,
        "channel_link":CHANNEL_INVITE_LINK,
        "referral_required":REFERRAL_REQUIRED,
        "referral_reward_days":REFERRAL_REWARD_DAYS,
        "logo_url":LOGO_URL,
        "plans":{"monthly":{"price":PREMIUM_PRICE,"text":PREMIUM_PRICE_TEXT,"days":PREMIUM_DAYS},
                 "6months":{"price":PREMIUM_6MONTHS_PRICE,"text":PREMIUM_6MONTHS_TEXT,"days":PREMIUM_6MONTHS_DAYS}}})


@flask_app.route("/api/webapp/leaderboard", methods=["GET"])
def api_webapp_leaderboard():
    total_players = sum(1 for u in USER_DATA.values() if u.get("history"))
    return jsonify({
        "status": "success",
        "leaders": get_leaderboard(limit=10),
        "total_players": total_players,
    })


@flask_app.route("/api/webapp/user", methods=["GET", "OPTIONS"])
def api_webapp_user():
    if request.method=="OPTIONS": return "",204
    uid=_require_session()
    if not uid: return jsonify({"status":"error"}),401
    u=get_user(uid)
    hist=u.get("history",[])
    premium=is_premium(uid)
    used_tutor=u.get("tutor_counts",{}).get(str(date.today()),0)
    _,ai_why_rem=can_use_ai_why(uid)
    invite_code=u.get("invite_code","")
    is_admin=(str(uid)==str(ADMIN_ID)) if ADMIN_ID else False
    return jsonify({"status":"success","uid":uid,
        "username":u.get("username",""),"phone":u.get("phone",""),
        "is_premium":premium,"is_admin":is_admin,
        "premium_until":u.get("premium_until"),
        "plan":u.get("jamb_plan",["english"]),
        "plan_set":u.get("plan_set",False),
        "free_english_used":u.get("free_english_used",False),
        "invite_code":invite_code,"invites":u.get("invites",0),
        "referral_required":REFERRAL_REQUIRED,
        "referral_reward_days":REFERRAL_REWARD_DAYS,
        "referral_link":f"{WEBAPP_URL}?ref={invite_code}",
        "referral_rewards_claimed":u.get("referral_rewards_claimed",0),
        "history":hist[-15:],"last_mock_failed":u.get("last_mock_failed",[]),
        "last_mock_subject":u.get("last_mock_subject"),
        "last_mock_total":u.get("last_mock_total",40),
        "tutor_remaining":-1 if premium else max(0,FREE_TUTOR_PER_DAY-used_tutor),
        "ai_why_remaining":-1 if premium else ai_why_rem,
        "source":u.get("source"),
        "subject_combination":u.get("subject_combination",[])})


@flask_app.route("/api/webapp/plan", methods=["POST", "OPTIONS"])
def api_webapp_plan():
    if request.method=="OPTIONS": return "",204
    uid=_require_session()
    if not uid: return jsonify({"status":"error"}),401
    body=request.get_json(silent=True) or {}
    plan=body.get("plan",[])
    if not isinstance(plan,list) or "english" not in plan:
        return jsonify({"status":"error","message":"english required"}),400
    plan=[str(s).lower() for s in plan if s][:PLAN_SIZE]
    u=get_user(uid)
    u["jamb_plan"]=plan
    u["plan_set"]=len(plan)==PLAN_SIZE
    save_data()
    return jsonify({"status":"success","plan":plan,"plan_set":u["plan_set"]})


@flask_app.route("/api/webapp/mock/start", methods=["POST", "OPTIONS"])
def api_webapp_mock_start():
    if request.method=="OPTIONS": return "",204
    uid=_require_session()
    if not uid: return jsonify({"status":"error"}),401
    body=request.get_json(silent=True) or {}
    mode=body.get("mode","plan")
    subject=str(body.get("subject","")).lower()
    u=get_user(uid); premium=is_premium(uid)
    label=""; qs=[]
    if mode=="free_english":
        if premium or u.get("free_english_used"):
            return jsonify({"status":"error","message":"free english used"}),403
        qs=_fetch_rotated(uid,"english",FREE_ENGLISH_QS); label="english"
        u["free_english_used"]=True; save_data()
    elif mode=="subject":
        if not premium:
            return jsonify({"status":"error","message":"upgrade_required"}),403
        if subject not in LOCAL_DATABANK:
            return jsonify({"status":"error","message":"invalid subject"}),400
        qs=_fetch_rotated(uid,subject,40); label=f"subject_{subject}"
    elif mode=="full":
        if not premium:
            return jsonify({"status":"error","message":"upgrade_required"}),403
        plan=u.get("jamb_plan",[])[:PLAN_SIZE]
        if len(plan)!=PLAN_SIZE:
            return jsonify({"status":"error","message":"plan not set"}),400
        qs=_fetch_rotated_multi(uid,plan,180); label="CBT:"+",".join(plan)
    else:
        plan=u.get("jamb_plan",["english"])
        if len(plan)!=PLAN_SIZE:
            return jsonify({"status":"error","message":"plan not set"}),400
        if not premium:
            if u.get("free_english_used"):
                return jsonify({"status":"error","message":"upgrade_required"}),403
            qs=_fetch_rotated(uid,"english",FREE_ENGLISH_QS); label="english"
            u["free_english_used"]=True; save_data()
        else:
            qs=_fetch_rotated(uid,plan[0],40); label=f"subject_{plan[0]}"
    if not qs or len(qs)<5:
        return jsonify({"status":"error","message":"not enough questions"}),400
    qs=_prepare_questions(qs)
    sid=hashlib.md5(f"{uid}{time.time()}{random.random()}".encode()).hexdigest()[:16]
    WEBAPP_MOCKS[sid]={"uid":uid,"qs":qs,"idx":0,"score":0,"failed":[],
                       "label":label,"started":time.time()}
    return jsonify({"status":"success","session_id":sid,"total":len(qs),"label":label})


@flask_app.route("/api/webapp/mock/question", methods=["POST", "OPTIONS"])
def api_webapp_mock_question():
    if request.method=="OPTIONS": return "",204
    uid=_require_session()
    if not uid: return jsonify({"status":"error"}),401
    body=request.get_json(silent=True) or {}
    s=WEBAPP_MOCKS.get(body.get("session_id",""))
    if not s or s["uid"]!=uid:
        return jsonify({"status":"error","message":"expired"}),404
    idx=s["idx"]
    if idx>=len(s["qs"]):
        return jsonify({"status":"finished"})
    q=s["qs"][idx]
    opts=[{"letter":L,"text":q.get(f"option_{L.lower()}","")}
          for L in ("A","B","C","D") if q.get(f"option_{L.lower()}","").strip()]
    return jsonify({"status":"success","idx":idx,"total":len(s["qs"]),
                    "score":s["score"],
                    "question":{"text":q.get("question",""),"options":opts,
                                "topic":q.get("topic","General"),
                                "subject":q.get("subject","")}})


@flask_app.route("/api/webapp/mock/answer", methods=["POST", "OPTIONS"])
def api_webapp_mock_answer():
    if request.method=="OPTIONS": return "",204
    uid=_require_session()
    if not uid: return jsonify({"status":"error"}),401
    body=request.get_json(silent=True) or {}
    s=WEBAPP_MOCKS.get(body.get("session_id",""))
    if not s or s["uid"]!=uid:
        return jsonify({"status":"error"}),404
    if s["idx"]>=len(s["qs"]):
        return jsonify({"status":"finished"})
    chosen=str(body.get("answer","")).upper()[:1]
    q=s["qs"][s["idx"]]
    correct=q.get("answer","")
    is_correct=chosen==correct
    if is_correct: s["score"]+=1
    else: s["failed"].append(_make_failure_snapshot(q,chosen,correct,s["idx"]+1))
    s["idx"]+=1
    return jsonify({"status":"success","is_correct":is_correct,
                    "next_idx":s["idx"],"total":len(s["qs"]),
                    "score":s["score"],"finished":s["idx"]>=len(s["qs"])})


@flask_app.route("/api/webapp/mock/complete", methods=["POST", "OPTIONS"])
def api_webapp_mock_complete():
    if request.method=="OPTIONS": return "",204
    uid=_require_session()
    if not uid: return jsonify({"status":"error"}),401
    body=request.get_json(silent=True) or {}
    s=WEBAPP_MOCKS.pop(body.get("session_id",""),None)
    if not s or s["uid"]!=uid:
        return jsonify({"status":"error","message":"expired"}),404
    u=get_user(uid)
    score=s["score"]; total=len(s["qs"]); failed=s["failed"]; label=s["label"]
    u["history"].append({"date":str(date.today()),"subject":label,
                         "score":score,"total":total,
                         "percent":score*100//total if total else 0})
    u["last_mock_failed"]=failed; u["last_mock_subject"]=label
    u["last_mock_total"]=total
    save_data()
    return jsonify({"status":"success","score":score,"total":total,
                    "failed":failed,"label":label,"is_premium":is_premium(uid)})


@flask_app.route("/api/webapp/tutor", methods=["POST", "OPTIONS"])
def api_webapp_tutor():
    if request.method=="OPTIONS": return "",204
    uid=_require_session()
    if not uid: return jsonify({"status":"error"}),401
    body=request.get_json(silent=True) or {}
    question=str(body.get("question","")).strip()[:1000]
    subject=str(body.get("subject","")).strip().lower()[:30]
    if not question: return jsonify({"status":"error","message":"empty"}),400
    if not can_use_tutor(uid):
        return jsonify({"status":"limit_reached",
                        "upgrade_url":f"{PAYMENT_URL}/upgrade/{uid}"}),403
    consume_tutor(uid)
    if not HAS_AI_TUTOR:
        return jsonify({"status":"error","message":"tutor offline"}),503
    try:
        answer=_ask_tutor(question,subject)
    except Exception as e:
        return jsonify({"status":"error","message":str(e)[:200]}),500
    u=get_user(uid)
    rem=-1 if is_premium(uid) else max(0,FREE_TUTOR_PER_DAY-u["tutor_counts"].get(str(date.today()),0))
    return jsonify({"status":"success","answer":answer[:3500],
                    "remaining":rem,"tutor":TUTOR_NAME})


@flask_app.route("/api/webapp/voice", methods=["POST", "OPTIONS"])
def api_webapp_voice():
    if request.method=="OPTIONS": return "",204
    uid=_require_session()
    if not uid: return jsonify({"status":"error"}),401
    body=request.get_json(silent=True) or {}
    text=str(body.get("text",""))[:2500]
    if not text.strip(): return jsonify({"status":"error"}),400
    try: buf=_make_voice_professional(text)
    except Exception as e:
        print(f"[webapp voice] {e}"); buf=None
    if buf is None:
        return jsonify({"status":"error","message":"voice failed"}),500
    return send_file(buf,mimetype="audio/mpeg",download_name="ellams.mp3")


@flask_app.route("/api/webapp/failures", methods=["GET", "OPTIONS"])
def api_webapp_failures():
    if request.method=="OPTIONS": return "",204
    uid=_require_session()
    if not uid: return jsonify({"status":"error"}),401
    u=get_user(uid)
    fails=u.get("last_mock_failed",[])
    return jsonify({"status":"success","failures":fails,"count":len(fails)})


@flask_app.route("/api/webapp/failure/analyze", methods=["POST", "OPTIONS"])
def api_webapp_failure_analyze():
    if request.method=="OPTIONS": return "",204
    uid=_require_session()
    if not uid: return jsonify({"status":"error"}),401
    body=request.get_json(silent=True) or {}
    idx=int(body.get("idx",0))
    u=get_user(uid)
    failed=u.get("last_mock_failed",[])
    if idx<0 or idx>=len(failed):
        return jsonify({"status":"error","message":"not found"}),404
    allowed,_=can_use_ai_why(uid)
    if not allowed:
        return jsonify({"status":"limit_reached",
                        "upgrade_url":f"{PAYMENT_URL}/upgrade/{uid}"}),403
    consume_ai_why(uid)
    f=failed[idx]
    mini_q=f"Question: {f.get('question','')}\nTopic: {f.get('topic','General')}"
    try:
        if HAS_AI_TUTOR:
            analysis=_analyze_failure(mini_q,f.get("user_ans",""),
                                       f.get("correct_ans",""),f.get("topic","General"))
        else:
            analysis="AI Tutor unavailable."
    except Exception as e:
        return jsonify({"status":"error","message":str(e)[:200]}),500
    _,rem=can_use_ai_why(uid)
    return jsonify({"status":"success","analysis":analysis[:3500],
                    "remaining":-1 if is_premium(uid) else rem})


@flask_app.route("/api/webapp/referral", methods=["GET", "OPTIONS"])
def api_webapp_referral():
    if request.method=="OPTIONS": return "",204
    uid=_require_session()
    if not uid: return jsonify({"status":"error"}),401
    return jsonify({"status":"success",**_get_referral_status(uid)})


@flask_app.route("/api/webapp/premium/checkout", methods=["POST", "OPTIONS"])
def api_webapp_premium_checkout():
    if request.method=="OPTIONS": return "",204
    uid=_require_session()
    if not uid: return jsonify({"status":"error"}),401
    body=request.get_json(silent=True) or {}
    plan=body.get("plan","monthly")
    if plan not in ("monthly","6months"):
        return jsonify({"status":"error"}),400
    return_url=str(body.get("return_url","")).strip()[:300]
    if not return_url:
        return_url=WEBAPP_URL if uid.startswith("widget_") else f"https://t.me/{BOT_USERNAME}"
    checkout=f"{PAYMENT_URL}/upgrade/{uid}?plan={plan}&return={quote(return_url)}"
    return jsonify({"status":"success","checkout_url":checkout})


@flask_app.route("/api/webapp/admin/stats", methods=["GET", "OPTIONS"])
def api_admin_stats():
    if request.method=="OPTIONS": return "",204
    if not _admin_required():
        return jsonify({"status":"error","message":"admin only"}),403
    total=len(USER_DATA)
    premium_users=sum(1 for u in USER_DATA.values() if u.get("is_premium"))
    widget_users=sum(1 for k in USER_DATA.keys() if k.startswith("widget_"))
    source_counts={}
    for u in USER_DATA.values():
        src=u.get("source") or "unknown"
        source_counts[src]=source_counts.get(src,0)+1
    wa_users=sum(1 for u in USER_DATA.values() if u.get("wa_phone"))
    sorted_users=sorted(USER_DATA.items(),
        key=lambda kv: kv[1].get("joined",""),reverse=True)[:25]
    recent=[]
    for uid_k,u in sorted_users:
        recent.append({"uid":uid_k,"username":u.get("username","User"),
                       "is_premium":bool(u.get("is_premium")),
                       "joined":u.get("joined",""),
                       "source":u.get("source"),
                       "wa_phone":u.get("wa_phone"),
                       "subject_combination":u.get("subject_combination",[])})
    return jsonify({"status":"success","total_users":total,
        "premium_users":premium_users,"free_users":total-premium_users,
        "widget_users":widget_users,"whatsapp_users":wa_users,
        "source_breakdown":source_counts,"recent_users":recent})


@flask_app.route("/api/webapp/admin/grant_premium", methods=["POST", "OPTIONS"])
def api_admin_grant_premium():
    if request.method=="OPTIONS": return "",204
    if not _admin_required():
        return jsonify({"status":"error","message":"admin only"}),403
    body=request.get_json(silent=True) or {}
    target_uid=str(body.get("uid","")).strip()
    try: days=int(body.get("days",30))
    except: days=30
    if not target_uid:
        return jsonify({"status":"error","message":"missing uid"}),400
    if days<1 or days>3650:
        return jsonify({"status":"error","message":"days out of range"}),400
    if target_uid not in USER_DATA:
        try: get_user(target_uid)
        except: pass
        if target_uid not in USER_DATA:
            return jsonify({"status":"error","message":"uid not found"}),404
    add_premium(target_uid,days=days,plan="admin-grant")
    return jsonify({"status":"success","uid":target_uid,"days":days})


@flask_app.route("/api/webapp/admin/broadcast", methods=["POST", "OPTIONS"])
def api_admin_broadcast():
    if request.method=="OPTIONS": return "",204
    if not _admin_required():
        return jsonify({"status":"error","message":"admin only"}),403
    body=request.get_json(silent=True) or {}
    text=str(body.get("text","")).strip()[:4000]
    if not text: return jsonify({"status":"error","message":"empty text"}),400
    sent=0; failed=0
    try:
        loop=asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        async def _do():
            nonlocal sent,failed
            bot_app=ApplicationBuilder().token(BOT_TOKEN).build()
            await bot_app.initialize()
            for target_uid in list(USER_DATA.keys()):
                if target_uid.startswith("widget_"): continue
                try:
                    await bot_app.bot.send_message(chat_id=int(target_uid),
                                                    text=text,parse_mode="Markdown")
                    sent+=1
                except: failed+=1
                await asyncio.sleep(0.05)
            await bot_app.shutdown()
        loop.run_until_complete(_do())
        loop.close()
    except Exception as e:
        return jsonify({"status":"error","message":str(e)[:200]}),500
    return jsonify({"status":"success","sent":sent,"failed":failed})


# ============================================================
# WHATSAPP META INTEGRATION
# ============================================================
def build_web_bot_link(wa_phone, name, subjects):
    clean_phone = re.sub(r"\D", "", str(wa_phone))
    subject_list = list(subjects) if subjects else []
    if "english" in subject_list:
        subject_list.remove("english")
    subject_list.insert(0, "english")
    name_enc = quote(str(name).strip(), safe="")
    subs_enc = quote(",".join(subject_list), safe="")
    return (f"{WEBAPP_URL}?source=whatsapp&wa={clean_phone}"
            f"&name={name_enc}&subjects={subs_enc}")


def send_whatsapp_text(to_phone, message_body):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        return False
    url = f"{WHATSAPP_GRAPH_URL}/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}",
               "Content-Type": "application/json"}
    payload = {"messaging_product":"whatsapp","recipient_type":"individual",
               "to":to_phone,"type":"text","text":{"body":message_body}}
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15)
        return r.status_code == 200
    except: return False


def _wa_get_user_subjects(wa_phone):
    uid = _find_user_by_phone(wa_phone)
    if uid:
        u = get_user(uid)
        subs = u.get("subject_combination") or u.get("jamb_plan") or []
        if subs: return subs
    return ["english", "mathematics", "physics", "chemistry"]


def _wa_should_send_link(text):
    if not text: return False
    t = text.lower().strip()
    triggers = ("web","link","open","start","hi","hello","menu","practise","practice")
    return any(kw in t for kw in triggers)


def _wa_store_user(wa_phone, profile_name, subjects=None):
    try:
        existing = _find_user_by_phone(wa_phone)
        if existing:
            u = get_user(existing)
            u["wa_phone"] = wa_phone
            if profile_name and (not u.get("username") or u.get("username","").startswith("User")):
                u["username"] = profile_name
            if subjects:
                u["subject_combination"] = subjects
                if not u.get("plan_set") and len(subjects) >= 2:
                    ps = list(subjects)
                    if "english" not in ps: ps = ["english"] + ps[:PLAN_SIZE-1]
                    u["jamb_plan"] = ps[:PLAN_SIZE]
                    u["plan_set"] = len(u["jamb_plan"]) == PLAN_SIZE
            if not u.get("source"): u["source"] = "whatsapp"
            if not u.get("first_seen_platform"): u["first_seen_platform"] = "whatsapp"
            USER_DATA[existing] = u
            save_data()
            return existing
        else:
            normalized = re.sub(r"\D", "", str(wa_phone))
            new_uid = "wa_" + normalized[-10:]
            u = get_user(new_uid, profile_name or "WhatsApp User")
            if profile_name: u["username"] = profile_name
            u["phone"] = wa_phone; u["wa_phone"] = wa_phone
            u["source"] = "whatsapp"; u["first_seen_platform"] = "whatsapp"
            if subjects:
                u["subject_combination"] = subjects
                if len(subjects) >= 2:
                    ps = list(subjects)
                    if "english" not in ps: ps = ["english"] + ps[:PLAN_SIZE-1]
                    u["jamb_plan"] = ps[:PLAN_SIZE]
                    u["plan_set"] = len(u["jamb_plan"]) == PLAN_SIZE
            USER_DATA[new_uid] = u
            save_data()
            return new_uid
    except Exception as e:
        print(f"[WA] store_user error: {e}")
        return None


def handle_whatsapp_webhook(payload):
    try:
        entry = payload["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
    except (KeyError, IndexError):
        return
    if "messages" not in value:
        return
    try:
        message = value["messages"][0]
        contact = value["contacts"][0]
        wa_phone = message["from"]
        profile_name = (contact.get("profile") or {}).get("name", "") or "Student"
    except (KeyError, IndexError):
        return
    user_text = ""
    if message.get("type") == "text":
        user_text = message["text"]["body"]
    subjects = _wa_get_user_subjects(wa_phone)
    _wa_store_user(wa_phone, profile_name, subjects)
    if not _wa_should_send_link(user_text):
        return
    link = build_web_bot_link(wa_phone, profile_name, subjects)
    reply = (f"📚 *Free JAMB Prep — Open in your browser:*\n\n"
             f"{link}\n\n_Your progress saves automatically._")
    send_whatsapp_text(wa_phone, reply)


@flask_app.route("/webhook/whatsapp", methods=["GET", "POST", "OPTIONS"])
def whatsapp_webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode", "")
        token = request.args.get("hub.verify_token", "")
        challenge = request.args.get("hub.challenge", "")
        if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
            return challenge, 200
        return "Forbidden", 403
    if request.method == "OPTIONS":
        return "", 204
    payload = request.get_json(silent=True) or {}
    try: handle_whatsapp_webhook(payload)
    except Exception as e: print(f"[WA] Webhook error: {e}")
    return "EVENT_RECEIVED", 200


# ============================================================
# PAYMENT
# ============================================================
@flask_app.route("/api/payment/create_link", methods=["POST", "OPTIONS"])
def api_payment_create_link():
    if request.method=="OPTIONS": return "",204
    body=request.get_json(silent=True) or {}
    uid=str(body.get("uid","")).strip()
    plan_key=str(body.get("plan","monthly")).strip()
    return_url=str(body.get("return_url","")).strip()[:300]
    if not uid: return jsonify({"status":"error","message":"missing uid"}),400
    if plan_key not in PLANS: return jsonify({"status":"error","message":"invalid plan"}),400
    if not FLW_SECRET_KEY: return jsonify({"status":"error","message":"payment not configured"}),503
    plan=PLANS[plan_key]
    tx_ref=f"UTME-{uid}-{int(time.time())}"
    redirect=f"{PAYMENT_URL}/payment/complete?uid={uid}&tx_ref={tx_ref}"
    if return_url: redirect+=f"&return={quote(return_url)}"
    payload={"tx_ref":tx_ref,"amount":str(plan["price"]),"currency":"NGN",
             "redirect_url":redirect,"payment_options":"card,banktransfer,ussd,account",
             "customer":{"email":f"user{uid.replace('_','')}@utmebot.com",
                         "name":get_user(uid).get("username","UTME Student")},
             "customizations":{"title":f"UTME Success Bot — {plan['label']}",
                               "description":f"{plan['label']} Premium",
                               "logo":LOGO_URL},
             "meta":{"user_id":uid,"plan":plan_key,"product":f"premium_{plan_key}"}}
    headers={"Authorization":f"Bearer {FLW_SECRET_KEY.strip()}","Content-Type":"application/json"}
    last_err=None
    for attempt in (1,2):
        try:
            r=requests.post("https://api.flutterwave.com/v3/payments",
                            json=payload,headers=headers,timeout=25)
            data=r.json()
            link=(data.get("data") or {}).get("link")
            if data.get("status")=="success" and link:
                return jsonify({"status":"success","link":link,
                                "tx_ref":tx_ref,"amount":plan["price"]})
            last_err=data.get("message") or "link creation failed"
        except Exception as e:
            last_err=f"{type(e).__name__}: {str(e)[:200]}"
        time.sleep(1.2)
    return jsonify({"status":"error","message":last_err or "payment unavailable"}),502


@flask_app.route("/upgrade/<uid>")
def upgrade_page(uid):
    monthly=_resolve_plan("monthly"); six=_resolve_plan("6months")
    savings=PREMIUM_PRICE*6-PREMIUM_6MONTHS_PRICE
    savings_text=f"\u20a6{savings}" if savings>0 else ""
    invite_link=f"{WEBAPP_URL}?ref={uid}"
    share_link=f"https://t.me/share/url?url={quote(invite_link)}&text={quote('Join UTME Success Bot — free JAMB prep!')}"
    return_url=request.args.get("return",f"https://t.me/{BOT_USERNAME}")[:300]
    html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Upgrade — UTME Success Bot</title>
<meta property="og:image" content="{LOGO_URL}"/>
<link rel="icon" type="image/png" href="{LOGO_URL}"/>
<style>
*{{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:linear-gradient(135deg,#1e1b4b 0%,#5b21b6 50%,#7c3aed 100%);min-height:100vh;padding:20px;color:#0f172a;display:flex;align-items:flex-start;justify-content:center}}
.wrap{{max-width:480px;width:100%;margin:0 auto}}
h1{{color:#fff;text-align:center;font-size:26px;font-weight:900;letter-spacing:-.5px;margin-bottom:6px}}
p.sub{{color:rgba(255,255,255,.85);text-align:center;font-size:14px;margin-bottom:22px;line-height:1.5}}
.card{{background:#fff;border-radius:22px;padding:24px;margin-bottom:16px;box-shadow:0 20px 50px -12px rgba(0,0,0,.4)}}
.plan{{border:2px solid #e2e8f0;border-radius:18px;padding:22px;margin-bottom:14px;position:relative;overflow:hidden}}
.plan.best{{border-color:#f59e0b;background:linear-gradient(135deg,#fffbeb,#fef3c7)}}
.plan-tag{{position:absolute;top:0;right:0;background:linear-gradient(135deg,#f59e0b,#ea580c);color:#fff;font-size:10.5px;font-weight:800;padding:6px 12px;border-bottom-left-radius:14px;letter-spacing:.6px;text-transform:uppercase}}
.plan h3{{font-size:19px;margin-bottom:6px}}
.plan .price{{font-size:32px;font-weight:900;color:#1e1b4b;letter-spacing:-1px;margin:6px 0}}
.plan .price small{{font-size:14px;font-weight:500;color:#64748b}}
.plan .desc{{font-size:13px;color:#64748b;margin-bottom:14px}}
.plan .save{{display:inline-block;background:#10b981;color:#fff;font-size:11px;font-weight:800;padding:4px 10px;border-radius:100px;margin-bottom:10px}}
.pay{{width:100%;padding:16px;border:none;border-radius:14px;font-size:16px;font-weight:800;color:#fff;background:linear-gradient(135deg,#7c3aed,#4c1d95);cursor:pointer;box-shadow:0 8px 20px rgba(124,58,237,.35);display:flex;align-items:center;justify-content:center;gap:8px;font-family:inherit}}
.pay:disabled{{opacity:.55;cursor:not-allowed}}
.plan.best .pay{{background:linear-gradient(135deg,#f59e0b,#ea580c)}}
.trust{{display:flex;align-items:center;justify-content:center;color:rgba(255,255,255,.85);font-size:12.5px;padding:14px;line-height:1.5}}
.alert{{background:#fef2f2;color:#991b1b;padding:14px;border-radius:12px;font-size:13.5px;border-left:4px solid #dc2626;margin-bottom:16px}}
.ref-prog{{display:flex;align-items:center;gap:10px;padding:12px;background:#f8fafc;border-radius:10px;margin:12px 0;border:1px solid #e2e8f0}}
.ref-bar{{flex:1;height:8px;background:#e2e8f0;border-radius:999px;overflow:hidden}}
.ref-fill{{height:100%;background:linear-gradient(90deg,#16a34a,#22c55e);width:0%}}
.ref-txt{{font-size:12px;font-weight:900;color:#16a34a;min-width:34px;text-align:right}}
.logo-top{{display:block;width:80px;height:80px;margin:0 auto 14px;border-radius:18px;box-shadow:0 12px 28px rgba(0,0,0,.35)}}
.btn-copy{{padding:12px;border-radius:12px;border:1.5px solid #e2e8f0;background:#fff;color:#0f172a;font-weight:800;font-size:13px;cursor:pointer;width:100%;font-family:inherit;margin-top:8px}}
.sp{{display:inline-block;width:16px;height:16px;border:2.5px solid rgba(255,255,255,.4);border-top-color:#fff;border-radius:50%;animation:sp .7s linear infinite}}
@keyframes sp{{to{{transform:rotate(360deg)}}}}
</style>
</head>
<body>
<div class="wrap">
<img src="{LOGO_URL}" alt="Logo" class="logo-top"/>
<h1>👑 Upgrade to Premium</h1>
<p class="sub">Unlock unlimited practice. Score higher in JAMB.</p>
{'<div class="alert">⚠️ Payment not configured. Contact support.</div>' if not FLW_SECRET_KEY else ''}
<div class="card" id="main-card">
<div class="plan best">
<div class="plan-tag">Best Value</div>
<h3>6 Months</h3>
<span class="save">SAVE 50% OFF</span>
<div class="price">{six['price_text']} <small>/ {six['days']} days</small></div>
<div class="desc">Full access for 6 months.</div>
<button class="pay" id="pay-6m" onclick="payNow('6months')" {'disabled' if not FLW_SECRET_KEY else ''}>
<span class="btn-label">💳 Pay {six['price_text']}</span>
</button>
</div>
<div class="plan">
<h3>Monthly</h3>
<div class="price">{monthly['price_text']} <small>/ {monthly['days']} days</small></div>
<div class="desc">Try Premium for one month.</div>
<button class="pay" id="pay-1m" onclick="payNow('monthly')" {'disabled' if not FLW_SECRET_KEY else ''}>
<span class="btn-label">💳 Pay {monthly['price_text']}</span>
</button>
</div>
</div>
<div class="card">
<h3 style="font-size:17px;margin-bottom:6px;">🎁 Or earn it FREE</h3>
<p style="font-size:13px;color:#64748b;margin-bottom:12px;">Invite <b>{REFERRAL_REQUIRED} friends</b> → get <b>{REFERRAL_REWARD_DAYS} days free</b>.</p>
<div class="ref-prog">
<div class="ref-bar"><div class="ref-fill"></div></div>
<div class="ref-txt">0/{REFERRAL_REQUIRED}</div>
</div>
<button class="btn-copy" onclick="copyRef()">📋 Copy Referral Link</button>
<a href="{share_link}" target="_blank" rel="noopener" style="display:block;text-align:center;padding:14px;border-radius:14px;background:linear-gradient(135deg,#10b981,#059669);color:#fff;text-decoration:none;font-weight:700;font-size:14.5px;margin-top:12px;">📤 Share Link</a>
</div>
<div class="trust">🔒 Secured by Flutterwave</div>
</div>
<script>
const UID="{uid}";
const API=window.location.origin;
const REF_LINK="{WEBAPP_URL}?ref={uid}";
async function payNow(planKey){{
const btn=document.getElementById(planKey==='6months'?'pay-6m':'pay-1m');
const label=btn.querySelector('.btn-label'); const orig=label.textContent;
document.querySelectorAll('.pay').forEach(b=>b.disabled=true);
label.innerHTML='<span class="sp"></span> Creating…';
try{{
const res=await fetch(API+'/api/payment/create_link',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{uid:UID,plan:planKey,return_url:window.location.href}})}});
const data=await res.json();
if(data.status==='success'&&data.link){{window.location.href=data.link;return;}}
label.textContent=orig;document.querySelectorAll('.pay').forEach(b=>b.disabled=false);
alert('⚠️ '+(data.message||'Failed.'));
}}catch(e){{label.textContent=orig;document.querySelectorAll('.pay').forEach(b=>b.disabled=false);alert('⚠️ Network error.');}}
}}
function copyRef(){{
try{{navigator.clipboard.writeText(REF_LINK);alert('✅ Copied!');}}
catch(e){{const t=document.createElement('textarea');t.value=REF_LINK;document.body.appendChild(t);t.select();document.execCommand('copy');document.body.removeChild(t);alert('✅ Copied!');}}
}}
</script>
</body></html>"""
    return html


@flask_app.route("/payment/complete")
def payment_complete():
    uid=request.args.get("uid",""); tx_ref=request.args.get("tx_ref","")
    return_url=request.args.get("return","")
    transaction_id=request.args.get("transaction_id","")
    verified=False
    if transaction_id and FLW_SECRET_KEY:
        try:
            r=requests.get(f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify",
                headers={"Authorization":f"Bearer {FLW_SECRET_KEY.strip()}"},timeout=15)
            data=r.json(); tx=(data or {}).get("data") or {}
            if data.get("status")=="success" and tx.get("status")=="successful":
                vref=tx.get("tx_ref",tx_ref); vuid=_uid_from_tx_ref(vref)
                plan_key=(tx.get("meta") or {}).get("plan","monthly")
                if vuid and mark_processed(vref):
                    plan=_resolve_plan(plan_key)
                    add_premium(vuid,days=plan["days"],plan=plan["key"])
                    verified=True
        except Exception as e: print(f"[payment/complete] {e}")
    if not return_url:
        return_url=WEBAPP_URL if uid.startswith("widget_") else f"https://t.me/{BOT_USERNAME}"
    icon="🎉" if verified else "⏳"
    title="Payment Successful!" if verified else "Verifying Payment…"
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>body{{margin:0;font-family:-apple-system,sans-serif;background:linear-gradient(135deg,{'#10b981,#059669' if verified else '#7c3aed,#4c1d95'});min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;color:#fff;text-align:center}}.card{{background:rgba(255,255,255,.15);backdrop-filter:blur(10px);border-radius:24px;padding:40px 28px;max-width:420px}}.icon{{font-size:72px}}h1{{font-size:26px;margin:10px 0}}.btn{{display:inline-block;margin-top:22px;padding:14px 28px;border-radius:12px;background:#fff;color:#0f172a;text-decoration:none;font-weight:800}}</style></head><body>
<div class="card"><div class="icon">{icon}</div><h1>{title}</h1><p>{'Premium is now active.' if verified else 'Activation may take up to 60 seconds.'}</p><a class="btn" href="{return_url}">Return →</a></div></body></html>"""


@flask_app.route("/verify/flutterwave", methods=["POST"])
def verify_flutterwave():
    body=request.get_json(silent=True) or {}
    tx_id=body.get("transaction_id")
    expected_uid=str(body.get("expected_uid") or "")
    plan_key=body.get("plan","monthly")
    if not tx_id or not FLW_SECRET_KEY: return jsonify({"status":"failed"}),400
    try:
        r=requests.get(f"https://api.flutterwave.com/v3/transactions/{tx_id}/verify",
            headers={"Authorization":f"Bearer {FLW_SECRET_KEY.strip()}"},timeout=15)
        result=r.json()
    except: return jsonify({"status":"failed"}),502
    data=(result or {}).get("data") or {}
    if not (result.get("status")=="success" and data.get("status")=="successful"):
        return jsonify({"status":"failed"}),400
    vref=data.get("tx_ref",""); vuid=_uid_from_tx_ref(vref)
    if not vuid: return jsonify({"status":"failed"}),400
    if expected_uid and expected_uid!=vuid: return jsonify({"status":"failed"}),400
    meta_plan=(data.get("meta") or {}).get("plan")
    if meta_plan in PLANS: plan_key=meta_plan
    uid=_grant_from_verified(vref,plan_key)
    if not uid: return jsonify({"status":"duplicate_or_invalid"}),200
    return jsonify({"status":"success","uid":uid,"plan":plan_key})


@flask_app.route("/webhook/flutterwave", methods=["POST"])
def flutterwave_webhook():
    sig=request.headers.get("verif-hash","")
    if not FLW_SECRET_HASH or sig!=FLW_SECRET_HASH:
        return jsonify({"status":"unauthorized"}),401
    payload=request.get_json(silent=True) or {}
    data=payload.get("data") or {}
    tx_ref=data.get("tx_ref",""); tx_id=data.get("id")
    if not tx_ref or not tx_id: return jsonify({"status":"ignored"}),200
    try:
        r=requests.get(f"https://api.flutterwave.com/v3/transactions/{tx_id}/verify",
            headers={"Authorization":f"Bearer {FLW_SECRET_KEY.strip()}"},timeout=15)
        v=r.json()
        if not (v.get("status")=="success" and (v.get("data") or {}).get("status")=="successful"):
            return jsonify({"status":"not_verified"}),200
        meta_plan=(v["data"].get("meta") or {}).get("plan","monthly")
    except: return jsonify({"status":"error"}),500
    _grant_from_verified(tx_ref,meta_plan if meta_plan in PLANS else "monthly")
    return jsonify({"status":"success"})


def run_flask():
    flask_app.run(host="0.0.0.0",port=PORT,threaded=True)


# ============================================================
# CHANNEL AUTO-POSTING
# ============================================================
POST_SLOTS=((8,30,"morning"),(13,0,"afternoon"),(20,0,"evening"))
POST_WINDOW_MIN=30


def _now_lagos():
    return datetime.now(timezone.utc)+timedelta(hours=1)


def _build_post(q, slot_name):
    intro=random.choice(["🌅 *Morning JAMB Practice*","☀️ *Quick Challenge*","🌙 *Evening Study*"])
    return (f"{intro}\n\n📚 *{md(q.get('subject','JAMB'))}* | {md(str(q.get('year','')))}\n\n"
            f"{md(q.get('question','')[:340])}\n\n"
            f"A) {md(q.get('option_a','')[:80])}\nB) {md(q.get('option_b','')[:80])}\n"
            f"C) {md(q.get('option_c','')[:80])}\nD) {md(q.get('option_d','')[:80])}\n\n"
            f"💡 *Answer:* {md(q.get('answer',''))}\n\n"
            f"👉 https://t.me/{BOT_USERNAME}")


async def channel_post(app, slot_name="morning", slot_label="manual"):
    if not CHANNEL_ID: raise RuntimeError("CHANNEL_ID not configured")
    q=get_random_question()
    if not q: raise RuntimeError("No questions available")
    msg=_build_post(q,slot_name)
    await app.bot.send_message(chat_id=CHANNEL_ID,text=msg,parse_mode="Markdown")
    print(f"[channel] Posted ({slot_name}) to {CHANNEL_ID}")
    return True


async def channel_posting_job(app):
    print("[channel] Job started")
    if not CHANNEL_ID: return
    posted_slots=set()
    while True:
        try:
            now=_now_lagos(); now_total=now.hour*60+now.minute
            today=now.date().isoformat()
            for (h,m,slot_name) in POST_SLOTS:
                slot_key=f"{today}_{h:02d}{m:02d}"
                target_total=h*60+m
                if (target_total<=now_total<target_total+POST_WINDOW_MIN and slot_key not in posted_slots):
                    try:
                        await channel_post(app,slot_name=slot_name,slot_label=f"{h:02d}:{m:02d}")
                        posted_slots.add(slot_key)
                    except Exception as e: print(f"[channel] {slot_name}: {e}")
            posted_slots={k for k in posted_slots if k.startswith(today)}
            await asyncio.sleep(300)
        except Exception as e:
            print(f"[channel] Loop: {e}"); await asyncio.sleep(600)


async def post_init(app):
    try:
        commands=[BotCommand("start","🏠 Main Menu"),BotCommand("mock","📝 Mock Exam"),
                  BotCommand("past","📚 Past Questions"),BotCommand("study","📖 Study Plan"),
                  BotCommand("syllabus","📋 JAMB Syllabus"),BotCommand("score","📊 My Score"),
                  BotCommand("tutor",f"💬 Ask {TUTOR_NAME}"),BotCommand("invite","👥 Invite Friends"),
                  BotCommand("premium","💎 Upgrade Premium"),BotCommand("help","❓ Help")]
        await app.bot.set_my_commands(commands)
        await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands(text="📋 Menu"))
        print("Commands registered")
        try:
            asyncio.create_task(channel_posting_job(app))
            print("Channel poster launched")
        except Exception as e: print(f"Channel poster: {e}")
    except Exception as e: print(f"Menu setup failed: {e}")


# ============================================================
# MAIN
# ============================================================
def main():
    load_processed_tx()
    print(f"Bot: @{BOT_USERNAME}")
    print(f"Tutor: {TUTOR_NAME}")
    print(f"WebApp: {WEBAPP_URL}")
    print(f"Logo: {LOGO_URL}")
    print(f"WhatsApp: {'configured' if WHATSAPP_TOKEN and PHONE_NUMBER_ID else 'not set'}")
    if not DATABASE_URL:
        print("DATABASE_URL not set!")
        while True: time.sleep(60)
    try:
        init_db(); load_data()
    except Exception as e:
        print(f"FATAL: DB init failed: {e}")
        traceback.print_exc()
        while True: time.sleep(60)
    widget_users=sum(1 for k in USER_DATA.keys() if k.startswith("widget_"))
    linked=sum(1 for u in USER_DATA.values() if u.get("linked_widget_uid"))
    wa_users=sum(1 for u in USER_DATA.values() if u.get("wa_phone"))
    print(f"Widget: {widget_users} anonymous, {linked} linked, {wa_users} WhatsApp")
    print(f"PostgreSQL: {len(USER_DATA)} users")
    if ADMIN_ID: print(f"Admin: {ADMIN_ID}")
    if HAS_AI_TUTOR:
        try:
            print(f"Building {TUTOR_NAME} KB…")
            _build_kb()
            ok,detail=_tutor_ping()
            print(f"Tutor: {detail}")
        except Exception as e: print(f"Tutor init: {e}")
    threading.Thread(target=run_flask,daemon=True).start()
    print(f"Flask on port {PORT}")
    if not BOT_TOKEN or BOT_TOKEN=="YOUR_BOT_TOKEN_HERE" or len(BOT_TOKEN)<20:
        print("BOT_TOKEN not set!")
        while True: time.sleep(60)
    try:
        app=ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start",cmd_start))
        app.add_handler(CommandHandler("menu",cmd_start))
        app.add_handler(CommandHandler("mock",cmd_mock))
        app.add_handler(CommandHandler("past",cmd_past))
        app.add_handler(CommandHandler("study",cmd_study))
        app.add_handler(CommandHandler("syllabus",cmd_syllabus))
        app.add_handler(CommandHandler("score",cmd_score))
        app.add_handler(CommandHandler("tutor",cmd_tutor))
        app.add_handler(CommandHandler("invite",cmd_invite))
        app.add_handler(CommandHandler("premium",cmd_premium))
        app.add_handler(CommandHandler("admin",cmd_admin))
        app.add_handler(CommandHandler("debug",cmd_debug))
        app.add_handler(CommandHandler("kbstats",cmd_kbstats))
        app.add_handler(CommandHandler("postnow",cmd_postnow))
        app.add_handler(CommandHandler("help",cmd_help))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(MessageHandler(
            filters.Regex("^(📚 Past Questions|📝 Mock Exam|📊 My Score|💬 Ask Tutor|"
                          "💎 Premium|👥 Invite Friends|📖 Study Plan|📢 Join Our Channel|"
                          "⚙️ Admin Panel)$"),handle_msg))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle_msg))
        app.post_init=post_init
        print("Bot running")
        app.run_polling()
    except Exception as e:
        print(f"Bot failed: {e}")
        traceback.print_exc()
        while True: time.sleep(60)


if __name__ == "__main__":
    main()
