"""
UTME Success Bot v28 — HARD-LOCKED FREE PLAN + AI TUTOR (Mr. Ellams) + CHANNEL + CBT 4-SUBJECT MOCK + ADMIN PANEL
"""
import os, json, random, time, threading, hashlib, asyncio, re, hmac, traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from flask import Flask, render_template_string, jsonify, request

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, MenuButtonCommands, BotCommand,
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)

try:
    from gtts import gTTS
    HAS_TTS = True
except Exception:
    HAS_TTS = False

# ---------- Config ----------
try:
    from config import (
        BOT_TOKEN, BOT_USERNAME, ADMIN_ID, PAYMENT_URL, PORT,
        PREMIUM_PRICE, PREMIUM_PRICE_TEXT,
        PREMIUM_6MONTHS_PRICE, PREMIUM_6MONTHS_TEXT,
        PREMIUM_DAYS, PREMIUM_6MONTHS_DAYS,
        FREE_MOCK_QS_DAILY, FREE_TUTOR_PER_DAY,
        REFERRAL_REQUIRED, REFERRAL_REWARD_DAYS,
        CHANNEL_ID, CHANNEL_USERNAME, USER_DATA_FILE,
        FLW_PUBLIC_KEY, FLW_SECRET_KEY, FLW_SECRET_HASH,
        PAYSTACK_SECRET_KEY, ALL_SUBJECTS,
    )
    print("[config] ✅ loaded")
except Exception as _e:
    print(f"[config] using env defaults ({_e})")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    BOT_USERNAME = os.getenv("BOT_USERNAME", "UTMESucessBot")
    ADMIN_ID = os.getenv("ADMIN_ID", "")
    PAYMENT_URL = os.getenv("PAYMENT_URL", "https://your-app.onrender.com")
    PORT = int(os.getenv("PORT", "5000"))
    PREMIUM_PRICE = int(os.getenv("PREMIUM_PRICE", "2000"))
    PREMIUM_PRICE_TEXT = f"\u20a6{PREMIUM_PRICE}"
    PREMIUM_6MONTHS_PRICE = int(os.getenv("PREMIUM_6MONTHS_PRICE", "6000"))
    PREMIUM_6MONTHS_TEXT = f"\u20a6{PREMIUM_6MONTHS_PRICE}"
    PREMIUM_DAYS = int(os.getenv("PREMIUM_DAYS", "30"))
    PREMIUM_6MONTHS_DAYS = int(os.getenv("PREMIUM_6MONTHS_DAYS", "180"))
    FREE_MOCK_QS_DAILY = int(os.getenv("FREE_MOCK_QS_DAILY", "5"))
    FREE_TUTOR_PER_DAY = int(os.getenv("FREE_TUTOR_PER_DAY", "5"))
    REFERRAL_REQUIRED = int(os.getenv("REFERRAL_REQUIRED", "3"))
    REFERRAL_REWARD_DAYS = int(os.getenv("REFERRAL_REWARD_DAYS", "7"))
    CHANNEL_ID = os.getenv("CHANNEL_ID", "")
    CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "UTMESUCCESS")
    USER_DATA_FILE = os.getenv("USER_DATA_FILE", "user_data.json")
    FLW_PUBLIC_KEY = os.getenv("FLW_PUBLIC_KEY", "")
    FLW_SECRET_KEY = os.getenv("FLW_SECRET_KEY", "")
    FLW_SECRET_HASH = os.getenv("FLW_SECRET_HASH", "")
    PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")
    ALL_SUBJECTS = [
        "english", "mathematics", "biology", "physics", "chemistry",
        "economics", "government", "commerce", "accounting",
        "literature", "crk",
    ]

BOT_USERNAME = "UTMESucessBot"
SUPPORT_HANDLE = "@UTMESUCCESS"
TUTOR_NAME = "Mr. Ellams"
if CHANNEL_ID:
    CHANNEL_ID = str(CHANNEL_ID).strip()

SUBJECT_DISPLAY = {
    "english": "📖 English", "mathematics": "📐 Maths",
    "biology": "🧬 Biology", "physics": "⚛️ Physics",
    "chemistry": "🧪 Chemistry", "economics": "💰 Economics",
    "government": "🏛️ Government", "commerce": "🏪 Commerce",
    "accounting": "📊 Accounting", "literature": "📚 Literature",
    "crk": "✝️ CRK",
}

# ---------- Engine ----------
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
    print(f"[ssmain] ✅ {len(ALL_QS)} questions across {len(AVAILABLE_SUBJECTS)} subjects")
except Exception as _e:
    print(f"[ssmain] ❌ engine failed: {_e}")
    traceback.print_exc()

    def _fmt(q, i, t):
        lines = [f"Q{i}/{t}", q.get("question", "")]
        for L in ("A", "B", "C", "D"):
            v = q.get(f"option_{L.lower()}")
            if v:
                lines.append(f"{L}) {v}")
        return "\n".join(lines)

    def _search(q, s=None, limit=5):
        return []
    def _rnd(s=None):
        return None
    class _F:
        def fetch(self, s, y=None, limit=40):
            return []
    fetcher = _F()
    format_question = _fmt
    search_databank = _search
    get_random_question = _rnd
    LOCAL_DATABANK = {}
    ALL_QS = []
    AVAILABLE_SUBJECTS = list(ALL_SUBJECTS)
    HAS_ENGINE = False

if not AVAILABLE_SUBJECTS:
    AVAILABLE_SUBJECTS = list(ALL_SUBJECTS)

# ---------- AI Tutor ----------
HAS_AI_TUTOR = False
try:
    from tutor import (
        ask_tutor as _ask_tutor,
        build_voice_inputfile as _build_voice,
        build_knowledge_base as _build_kb,
        get_kb_stats as _get_kb_stats,
        ping as _tutor_ping,
    )
    HAS_AI_TUTOR = True
    print(f"[ssmain] ✅ AI Tutor module loaded ({TUTOR_NAME})")
except Exception as _e:
    print(f"[ssmain] ⚠️ AI Tutor unavailable: {_e}")
    HAS_AI_TUTOR = False

    def _ask_tutor(q, s=""):
        return "⚠️ AI Tutor is not available right now."
    def _build_voice(t):
        return None
    def _build_kb(force_rebuild=False):
        return False
    def _get_kb_stats():
        return {}
    def _tutor_ping():
        return False, "not loaded"


# ---------- Helpers ----------
def md(s):
    if s is None:
        return ""
    s = str(s)
    return (s.replace("\\", "\\\\").replace("_", "\\_").replace("*", "\\*")
             .replace("`", "\\`").replace("[", "\\["))


# ---------- Storage ----------
DATA_FILE = Path(USER_DATA_FILE)
PROCESSED_TX_FILE = Path("processed_tx.json")
USER_DATA = {}
USER_SESSIONS = {}
PROCESSED_TX = set()

BOTTOM_KEYBOARD = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📚 Past Questions"), KeyboardButton("📝 Mock Exam")],
        [KeyboardButton("📊 My Score"),       KeyboardButton("💬 Ask Tutor")],
        [KeyboardButton("💎 Premium"),        KeyboardButton("👥 Invite Friends")],
    ],
    resize_keyboard=True, is_persistent=True,
)


def load_data():
    global USER_DATA
    if DATA_FILE.exists():
        try:
            USER_DATA = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception:
            USER_DATA = {}


def save_data():
    try:
        DATA_FILE.write_text(json.dumps(USER_DATA, indent=2), encoding="utf-8")
    except Exception:
        pass


def load_processed_tx():
    global PROCESSED_TX
    if PROCESSED_TX_FILE.exists():
        try:
            PROCESSED_TX = set(json.loads(PROCESSED_TX_FILE.read_text()))
        except Exception:
            PROCESSED_TX = set()


def save_processed_tx():
    try:
        PROCESSED_TX_FILE.write_text(json.dumps(sorted(PROCESSED_TX), indent=2))
    except Exception:
        pass


def mark_processed(tx_ref):
    if not tx_ref or tx_ref in PROCESSED_TX:
        return False
    PROCESSED_TX.add(tx_ref)
    save_processed_tx()
    return True


def get_user(uid, username=""):
    uid = str(uid)
    if uid not in USER_DATA:
        USER_DATA[uid] = {
            "daily_mock_count": 0, "last_mock_time": 0.0,
            "tutor_counts": {}, "used_ids": [],
            "is_premium": False, "premium_until": None, "premium_plan": None,
            "joined": str(date.today()), "history": [],
            "invite_code": hashlib.md5(uid.encode()).hexdigest()[:6].upper(),
            "invited_by": None, "invites": 0, "invited_users": [],
            "username": username or f"User{uid[-4:]}", "study_subject": None,
        }
        save_data()
    u = USER_DATA[uid]
    if username:
        u["username"] = username
    if u.get("premium_until"):
        try:
            if datetime.now() > datetime.fromisoformat(u["premium_until"]):
                u["is_premium"] = False
                u["premium_until"] = None
                u["premium_plan"] = None
                save_data()
        except Exception:
            pass
    return u


def is_premium(uid):
    u = get_user(uid)
    if ADMIN_ID and str(uid) == str(ADMIN_ID):
        return True
    return bool(u.get("is_premium", False))


def _reset_mock_if_24h_passed(u):
    now = time.time()
    if now - u.get("last_mock_time", 0) > 86400:
        u["daily_mock_count"] = 0
        u["last_mock_time"] = 0.0
        return True
    return False


def consume_mock(uid, c, ids=None):
    u = get_user(uid)
    _reset_mock_if_24h_passed(u)
    if u.get("daily_mock_count", 0) == 0:
        u["last_mock_time"] = time.time()
    u["daily_mock_count"] = u.get("daily_mock_count", 0) + c
    if ids:
        u["used_ids"].extend(str(x) for x in ids if x)
        u["used_ids"] = list(dict.fromkeys(u["used_ids"]))[-5000:]
    save_data()


def get_mock_remaining(uid):
    if is_premium(uid):
        return 999
    u = get_user(uid)
    if _reset_mock_if_24h_passed(u):
        save_data()
    return max(0, FREE_MOCK_QS_DAILY - u.get("daily_mock_count", 0))


def can_use_tutor(uid):
    if is_premium(uid):
        return True
    u = get_user(uid)
    return u["tutor_counts"].get(str(date.today()), 0) < FREE_TUTOR_PER_DAY


def consume_tutor(uid):
    u = get_user(uid)
    today = str(date.today())
    u["tutor_counts"][today] = u["tutor_counts"].get(today, 0) + 1
    save_data()


def get_leading():
    best_name, best_score = "No scores yet", 0
    for uid_k, d in USER_DATA.items():
        hist = d.get("history", [])
        if not hist:
            continue
        avg = sum(h.get("percent", 0) for h in hist) / len(hist)
        if avg > best_score:
            best_score, best_name = avg, d.get("username", f"User{str(uid_k)[-4:]}")
    return best_name, int(best_score)


def add_premium(uid, days=None, plan="monthly"):
    uid = str(uid)
    days = days or PREMIUM_DAYS
    u = get_user(uid)
    now = datetime.now()
    base = now
    if u.get("premium_until"):
        try:
            ex = datetime.fromisoformat(u["premium_until"])
            if ex > now:
                base = ex
        except Exception:
            pass
    u["is_premium"] = True
    u["premium_until"] = (base + timedelta(days=days)).isoformat()
    u["premium_plan"] = plan
    save_data()
    print(f"[premium] ✅ {plan} ({days}d) → uid={uid}")
    return True


# ---------- Plans ----------
PLANS = {
    "monthly": {"key": "monthly", "label": "Monthly", "price": PREMIUM_PRICE,
                "price_text": PREMIUM_PRICE_TEXT, "days": PREMIUM_DAYS},
    "6months": {"key": "6months", "label": "6 Months", "price": PREMIUM_6MONTHS_PRICE,
                "price_text": PREMIUM_6MONTHS_TEXT, "days": PREMIUM_6MONTHS_DAYS},
}


def _resolve_plan(key):
    return PLANS.get(key, PLANS["monthly"])


def _uid_from_tx_ref(tx_ref):
    if not tx_ref or not tx_ref.startswith("UTME-"):
        return None
    parts = tx_ref.split("-")
    if len(parts) < 3:
        return None
    return parts[1] if parts[1].isdigit() else None


def _grant_from_verified(tx_ref, plan_key):
    uid = _uid_from_tx_ref(tx_ref)
    if not uid:
        return None
    if not mark_processed(tx_ref):
        return None
    plan = _resolve_plan(plan_key)
    add_premium(uid, days=plan["days"], plan=plan["key"])
    return uid


# ---------- UI builders ----------
def plan_buttons(uid):
    return [
        [InlineKeyboardButton(f"💳 Monthly — {PREMIUM_PRICE_TEXT}",
                              url=f"{PAYMENT_URL}/upgrade/{uid}?plan=monthly")],
        [InlineKeyboardButton(f"💳 6 Months — {PREMIUM_6MONTHS_TEXT} (BEST VALUE)",
                              url=f"{PAYMENT_URL}/upgrade/{uid}?plan=6months")],
    ]


def upgrade_kb(uid):
    msg = (
        f"🔒 *Upgrade Required*\n\n"
        f"Free plan: *{FREE_MOCK_QS_DAILY} mock questions per 24 hours*\n\n"
        f"💎 *Unlock Premium for:*\n"
        f"• ♾️ Unlimited mocks\n"
        f"• 📚 Subject Mock (40 Qs)\n"
        f"• 🔥 Full JAMB CBT Mock (180 Qs · 4 Subjects)\n"
        f"• 💬 Unlimited {TUTOR_NAME} (AI Tutor) + 🎙️ Voice\n\n"
        f"*Plans:*\n"
        f"• Monthly — {PREMIUM_PRICE_TEXT} / {PREMIUM_DAYS} days\n"
        f"• 6 Months — {PREMIUM_6MONTHS_TEXT} / {PREMIUM_6MONTHS_DAYS} days\n\n"
        f"👉 Choose your plan below to unlock everything!"
    )
    kb = plan_buttons(uid)
    kb.append([InlineKeyboardButton(f"👥 Invite {REFERRAL_REQUIRED}=FREE",
                                    callback_data="invite_friends")])
    kb.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return msg, InlineKeyboardMarkup(kb)


def main_menu_text_kb(uid):
    u = get_user(uid)
    rem = get_mock_remaining(uid)
    prem = (f"💎 Premium Active ({u.get('premium_plan','premium')}) ✅"
            if is_premium(uid)
            else f"💎 {PREMIUM_PRICE_TEXT}/mo · {PREMIUM_6MONTHS_TEXT}/6mo")
    leader_name, leader_score = get_leading()
    text = (
        f"🎓 *UTME Success Bot*\n\n"
        f"📊 {rem}/{FREE_MOCK_QS_DAILY} mocks available today | {prem}\n"
        f"🏆 Top: {md(leader_name)} — {leader_score}/400\n\n"
        f"📚 *{len(ALL_QS)} questions* across {len(AVAILABLE_SUBJECTS)} subjects\n\n"
        f"👥 *VIRAL:* Invite {REFERRAL_REQUIRED}={REFERRAL_REWARD_DAYS} days FREE!\n\n"
        f"Choose:"
    )
    kb = [
        [InlineKeyboardButton("📚 Past Questions", callback_data="past_by_subject"),
         InlineKeyboardButton("📝 Mock Exam",      callback_data="mock_menu")],
        [InlineKeyboardButton("📖 Study Plan",     callback_data="study_plan"),
         InlineKeyboardButton("📋 Syllabus",       callback_data="syllabus")],
        [InlineKeyboardButton("📊 My Score",       callback_data="my_score"),
         InlineKeyboardButton("💬 Ask Tutor",      callback_data="ask_tutor")],
        [InlineKeyboardButton(
            f"👥 Invite Friends — {REFERRAL_REQUIRED}={REFERRAL_REWARD_DAYS} Days FREE!",
            callback_data="invite_friends")],
        [InlineKeyboardButton("💎 Premium",        callback_data="premium_info"),
         InlineKeyboardButton("❓ Help",            callback_data="help_menu")],
    ]
    # ── ADMIN-ONLY button ──
    if ADMIN_ID and str(uid) == str(ADMIN_ID):
        kb.append([InlineKeyboardButton("⚙️ Admin Panel (Admin Only)",
                                        callback_data="admin_panel")])
    return text, InlineKeyboardMarkup(kb)


def subjects_kb(prefix):
    buttons, row = [], []
    for subj in AVAILABLE_SUBJECTS[:14]:
        row.append(InlineKeyboardButton(
            SUBJECT_DISPLAY.get(subj, subj.title()),
            callback_data=f"{prefix}_{subj}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def _answer_keyboard(q):
    a = md((q.get("option_a") or "")[:25])
    b = md((q.get("option_b") or "")[:25])
    c = md((q.get("option_c") or "")[:25])
    d = md((q.get("option_d") or "")[:25])
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"A) {a}", callback_data="ans:A"),
         InlineKeyboardButton(f"B) {b}", callback_data="ans:B")],
        [InlineKeyboardButton(f"C) {c}", callback_data="ans:C"),
         InlineKeyboardButton(f"D) {d}", callback_data="ans:D")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ])


def _start_mock_session(uid, qs, subject_label, intro_text=""):
    USER_SESSIONS[uid] = {"mode": "mock", "qs": qs, "idx": 0, "score": 0,
                          "subject": subject_label}
    q = qs[0]
    txt = (intro_text + "\n\n" if intro_text else "") + format_question(q, 1, len(qs))
    return txt, _answer_keyboard(q)


# ══════════════════════════════════════════════════════════
# CBT 4-SUBJECT MOCK
# ══════════════════════════════════════════════════════════
CBT_SUBJECTS_REQUIRED = 4
CBT_TOTAL_QUESTIONS = 180


def _cbt_subject_kb(uid):
    session = USER_SESSIONS.get(uid, {})
    selected = session.get("cbt_subjects", [])

    buttons = []
    row = []
    for subj in AVAILABLE_SUBJECTS:
        display = SUBJECT_DISPLAY.get(subj, subj.title())
        icon = "✅" if subj in selected else "⬜"
        row.append(InlineKeyboardButton(
            f"{icon} {display}",
            callback_data=f"cbt_toggle_{subj}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    if len(selected) == CBT_SUBJECTS_REQUIRED:
        buttons.append([InlineKeyboardButton(
            f"🚀 START CBT MOCK ({CBT_TOTAL_QUESTIONS} Qs)",
            callback_data="cbt_start")])
    if selected:
        buttons.append([InlineKeyboardButton(
            "🗑️ Clear Selection", callback_data="cbt_clear")])
    buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def _cbt_subject_text(uid):
    session = USER_SESSIONS.get(uid, {})
    selected = session.get("cbt_subjects", [])
    n = len(selected)

    text = (
        f"🎯 *Full JAMB CBT Mock — Subject Selection*\n\n"
        f"JAMB requires you to attempt *exactly 4 subjects* in your UTME.\n"
        f"Pick the 4 subjects that match your intended course of study.\n\n"
        f"📊 *Selected:* {n}/{CBT_SUBJECTS_REQUIRED}\n"
    )
    if selected:
        for i, s in enumerate(selected, 1):
            text += f"  {i}. {SUBJECT_DISPLAY.get(s, s.title())}\n"
    else:
        text += "  _Tap a subject below to select it_\n"

    text += "\n"
    if n == CBT_SUBJECTS_REQUIRED:
        text += (
            f"✅ *Ready!*\n"
            f"• {CBT_TOTAL_QUESTIONS} questions total\n"
            f"• ~{CBT_TOTAL_QUESTIONS // CBT_SUBJECTS_REQUIRED} questions per subject\n"
            f"• ⏱️ Recommended time: 2 hours\n\n"
            f"👉 Tap *START CBT MOCK* below to begin."
        )
    else:
        text += f"⬜ Select *{CBT_SUBJECTS_REQUIRED - n}* more subject(s) to continue."
    return text


def _fetch_cbt_questions(uid, subjects, total=CBT_TOTAL_QUESTIONS):
    u = get_user(uid)
    used_ids = set(str(x) for x in u.get("used_ids", []))

    n_subj = len(subjects)
    per_subject = total // n_subj
    remainder = total % n_subj

    all_selected = []
    for i, subj in enumerate(subjects):
        pool = LOCAL_DATABANK.get(subj, [])
        if not pool:
            continue
        need = per_subject + (1 if i < remainder else 0)
        unused = [q for q in pool if str(q.get("id", "")) not in used_ids]
        used = [q for q in pool if str(q.get("id", "")) in used_ids]
        random.shuffle(unused)
        random.shuffle(used)
        if len(unused) >= need:
            selected = unused[:need]
        else:
            selected = unused + used[: need - len(unused)]
        all_selected.extend(selected)
    random.shuffle(all_selected)
    return all_selected[:total]


def _cbt_stats_text(uid, subjects, questions):
    counts = {}
    for q in questions:
        key = q.get("subject_key") or q.get("subject", "").lower()
        counts[key] = counts.get(key, 0) + 1
    lines = [f"  • {SUBJECT_DISPLAY.get(s, s.title())}: {counts.get(s, 0)} Qs"
             for s in subjects]
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════
# MOCK MENU
# ══════════════════════════════════════════════════════════
def _mock_menu_kb(uid):
    if is_premium(uid):
        return [
            [InlineKeyboardButton("⚡ Quick 5 Qs", callback_data="mock_quick")],
            [InlineKeyboardButton("📚 Subject Mock (40 Qs)", callback_data="mock_by_subject")],
            [InlineKeyboardButton("🔥 Full JAMB CBT Mock (180 Qs)",
                                  callback_data="mock_full")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ]
    rem = get_mock_remaining(uid)
    kb = []
    if rem > 0:
        kb.append([InlineKeyboardButton(f"⚡ Free Quick Mock ({rem} Qs left today)",
                                        callback_data="mock_quick")])
    else:
        kb.append([InlineKeyboardButton("🛑 Free Mock Completed — Upgrade for more",
                                        callback_data="premium_info")])
    kb.append([InlineKeyboardButton("🔒 Subject Mock (40 Qs) — Upgrade to unlock",
                                    callback_data="premium_info")])
    kb.append([InlineKeyboardButton("🔒 Full JAMB CBT Mock — Upgrade to unlock",
                                    callback_data="premium_info")])
    kb.append([InlineKeyboardButton("💎 Upgrade to Premium Now",
                                    callback_data="premium_info")])
    kb.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return kb


def _mock_menu_text(uid):
    if is_premium(uid):
        leader_name, leader_score = get_leading()
        return (
            f"📝 *Mock Exam Menu*\n"
            f"💎 Premium — Full Access\n"
            f"🏆 Top: {md(leader_name)} — {leader_score}/400\n\n"
            f"Choose mock type:"
        )
    rem = get_mock_remaining(uid)
    if rem <= 0:
        return (
            f"📝 *Mock Exam Menu*\n\n"
            f"🛑 *Your free mock for the next 24 hours is complete.*\n\n"
            f"🔒 *Unlock with Premium:*\n"
            f"📚 Subject Mock (40 Qs)\n"
            f"🔥 Full JAMB CBT Mock (180 Qs)\n"
            f"♾️ Unlimited Quick Mocks\n\n"
            f"💎 Tap Upgrade below to unlock instantly!"
        )
    return (
        f"📝 *Mock Exam Menu*\n\n"
        f"🆓 *Free Plan:* {rem}/{FREE_MOCK_QS_DAILY} questions left today\n"
        f"⚡ Free Quick Mock — {rem} Qs\n\n"
        f"🔒 *Premium Only:*\n"
        f"📚 Subject Mock (40 Qs)\n"
        f"🔥 Full JAMB CBT Mock (180 Qs)\n\n"
        f"💎 Upgrade to unlock all mock types!"
    )


# ══════════════════════════════════════════════════════════
# ADMIN PANEL
# ══════════════════════════════════════════════════════════
def _admin_only(uid) -> bool:
    return ADMIN_ID and str(uid) == str(ADMIN_ID)


def _admin_menu_text():
    total_users = len(USER_DATA)
    premium_users = sum(1 for u in USER_DATA.values() if u.get("is_premium"))
    free_users = total_users - premium_users
    active_24h = sum(
        1 for u in USER_DATA.values()
        if time.time() - u.get("last_mock_time", 0) <= 86400
    )
    return (
        f"⚙️ *Admin Panel*\n\n"
        f"👥 *Users*\n"
        f"  • Total: {total_users}\n"
        f"  • Premium: {premium_users}\n"
        f"  • Free: {free_users}\n"
        f"  • Active last 24h: {active_24h}\n\n"
        f"📚 *Databank*\n"
        f"  • Total Questions: {len(ALL_QS)}\n"
        f"  • Subjects: {len(AVAILABLE_SUBJECTS)}\n\n"
        f"💬 *AI Tutor ({TUTOR_NAME})*\n"
        f"  • Status: {'✅ Active' if HAS_AI_TUTOR else '❌ Offline'}\n"
        f"  • Voice: Nigerian Male Teacher\n\n"
        f"📢 *Channel*\n"
        f"  • Status: {'✅ Configured' if CHANNEL_ID else '❌ Not set'}\n\n"
        f"Select an action:"
    )


def _admin_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 View Users", callback_data="admin_users"),
         InlineKeyboardButton("💰 Grant Premium", callback_data="admin_grant_prompt")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast_prompt")],
        [InlineKeyboardButton("📤 Post to Channel Now", callback_data="admin_channel_post")],
        [InlineKeyboardButton("🧠 AI Brain Status", callback_data="admin_kb_stats")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ])


async def cmd_admin(update, context):
    uid = str(update.effective_user.id)
    if not _admin_only(uid):
        await update.message.reply_text("🔒 Admin only.")
        return
    await update.message.reply_text(
        _admin_menu_text(),
        parse_mode="Markdown",
        reply_markup=_admin_menu_kb())


async def _admin_handle_callback(query, uid, data, context):
    if not _admin_only(uid):
        await query.message.reply_text("🔒 Admin only.")
        return True

    if data == "admin_panel":
        await query.message.reply_text(
            _admin_menu_text(), parse_mode="Markdown",
            reply_markup=_admin_menu_kb())
        return True

    if data == "admin_users":
        lines = ["👥 *Recent Users* (up to 20)\n"]
        for uid_k, u in list(USER_DATA.items())[-20:]:
            name = u.get("username", "User")[:20]
            prem = "💎" if u.get("is_premium") else "🆓"
            lines.append(f"{prem} {md(name)} · `{uid_k}`")
        lines.append(f"\n_Total: {len(USER_DATA)} users_")
        await query.message.reply_text(
            "\n".join(lines), parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
        return True

    if data == "admin_grant_prompt":
        await query.message.reply_text(
            f"💰 *Grant Premium Manually*\n\n"
            f"Reply to this message with the user's Telegram ID (numbers only).\n\n"
            f"Example:\n`123456789`\n\n"
            f"They will receive {PREMIUM_DAYS} days Premium.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
        USER_SESSIONS[str(uid)] = {"mode": "admin_grant_wait"}
        return True

    if data == "admin_broadcast_prompt":
        await query.message.reply_text(
            f"📢 *Broadcast to All Users*\n\n"
            f"Reply with the exact text you want every user to receive.\n\n"
            f"⚠️ This cannot be undone.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
        USER_SESSIONS[str(uid)] = {"mode": "admin_broadcast_wait"}
        return True

    if data == "admin_channel_post":
        if not CHANNEL_ID:
            await query.message.reply_text("❌ CHANNEL_ID not set.")
            return True
        try:
            await channel_post(context.application, slot_name="morning",
                               slot_label="admin-manual")
            await query.message.reply_text("✅ Posted to channel.")
        except Exception as e:
            await query.message.reply_text(f"❌ Failed: {e}")
        return True

    if data == "admin_kb_stats":
        stats = _get_kb_stats() if HAS_AI_TUTOR else {}
        ok, detail = _tutor_ping() if HAS_AI_TUTOR else (False, "n/a")
        lines = [
            f"🧠 *AI Brain Status ({TUTOR_NAME})*",
            f"DeepSeek: {'✅' if ok else '❌'} {md(str(detail))}",
            f"KB ready: {stats.get('ready', False)}",
            f"Chunks: {stats.get('total_chunks', 0)}",
            f"BM25: {stats.get('bm25_ready', False)}",
            f"Voice engine: {stats.get('voice_engine', 'n/a')}",
            f"Voice name: `{stats.get('voice_name', 'n/a')}`",
        ]
        await query.message.reply_text(
            "\n".join(lines), parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
        return True

    return False


# ============================================================
# COMMANDS
# ============================================================

async def cmd_start(update, context):
    uid = str(update.effective_user.id)
    username = update.effective_user.first_name or ""
    if context.args and context.args[0].startswith("invite_"):
        code = context.args[0].replace("invite_", "")
        u = get_user(uid, username)
        if not u.get("invited_by"):
            for inviter_id, inv_data in USER_DATA.items():
                if inv_data.get("invite_code") == code and inviter_id != uid:
                    if uid not in inv_data.get("invited_users", []):
                        u["invited_by"] = inviter_id
                        inv_data["invites"] = inv_data.get("invites", 0) + 1
                        inv_data.setdefault("invited_users", []).append(uid)
                        if inv_data["invites"] >= REFERRAL_REQUIRED:
                            add_premium(inviter_id, days=REFERRAL_REWARD_DAYS,
                                        plan="referral")
                            inv_data["invites"] = 0
                        save_data()
                    break
    t, kb = main_menu_text_kb(uid)
    await update.message.reply_text(t, reply_markup=kb, parse_mode="Markdown")
    await update.message.reply_text(
        f"Use buttons below 👇\n"
        f"🚀 Invite {REFERRAL_REQUIRED} = {REFERRAL_REWARD_DAYS} days Premium FREE!",
        reply_markup=BOTTOM_KEYBOARD)


async def cmd_mock(update, context):
    uid = str(update.effective_user.id)
    get_user(uid, update.effective_user.first_name or "")
    if not is_premium(uid) and get_mock_remaining(uid) <= 0:
        print(f"[GATE] cmd_mock blocked → uid={uid}")
        msg, kb = upgrade_kb(uid)
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)
        return
    await update.message.reply_text(
        _mock_menu_text(uid), parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(_mock_menu_kb(uid)))


async def cmd_study(update, context):
    get_user(update.effective_user.id, update.effective_user.first_name or "")
    await update.message.reply_text(
        "📖 *Study Plan — Choose Subject:*",
        reply_markup=subjects_kb("study_subject"), parse_mode="Markdown")


async def cmd_syllabus(update, context):
    get_user(update.effective_user.id, update.effective_user.first_name or "")
    await update.message.reply_text(
        "📋 *JAMB Syllabus — Choose Subject:*",
        reply_markup=subjects_kb("syllabus_subject"), parse_mode="Markdown")


async def cmd_past(update, context):
    get_user(update.effective_user.id, update.effective_user.first_name or "")
    await update.message.reply_text(
        "📚 *Past Questions — Choose Subject:*",
        reply_markup=subjects_kb("past_subject"), parse_mode="Markdown")


async def cmd_score(update, context):
    uid = str(update.effective_user.id)
    u = get_user(uid, update.effective_user.first_name or "")
    hist = u.get("history", [])
    if not hist:
        await update.message.reply_text(
            "📊 No scores yet. Take a mock to see your stats!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📝 Take Mock", callback_data="mock_menu")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        return
    avg = sum(h["score"] * 400 // h["total"] for h in hist if h["total"]) / len(hist)
    leader_name, leader_score = get_leading()
    await update.message.reply_text(
        f"📊 *Your Scores*\n\nAverage: *{int(avg)}/400*\n"
        f"Exams taken: {len(hist)}\n"
        f"🏆 Leader: {md(leader_name)} — {leader_score}/400",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 New Mock", callback_data="mock_menu"),
             InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))


async def cmd_tutor(update, context):
    uid = str(update.effective_user.id)
    u = get_user(uid, update.effective_user.first_name or "")
    prev = USER_SESSIONS.get(uid, {}).get("subject") or u.get("study_subject")
    USER_SESSIONS[uid] = {"mode": "tutor", "subject": prev}
    if is_premium(uid):
        remaining_text = "Unlimited"
    else:
        used = u["tutor_counts"].get(str(date.today()), 0)
        remaining_text = f"{max(0, FREE_TUTOR_PER_DAY - used)}/{FREE_TUTOR_PER_DAY} left today"
    await update.message.reply_text(
        f"💬 *Ask Tutor — {TUTOR_NAME}*\n\n"
        f"🧠 AI Brain: {'Active ✅' if HAS_AI_TUTOR else 'Limited'}\n"
        f"🎙️ Voice: Nigerian male teacher\n"
        f"📚 {len(ALL_QS)} past questions\n\n"
        f"Tutor: {remaining_text}\n\n"
        f"Just type any JAMB question — you'll get a text + voice explanation.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))


async def cmd_invite(update, context):
    uid = str(update.effective_user.id)
    u = get_user(uid, update.effective_user.first_name or "")
    link = f"https://t.me/{BOT_USERNAME}?start=invite_{u['invite_code']}"
    invites = u.get("invites", 0)
    share_url = f"https://t.me/share/url?url={quote(link)}&text={quote('Join UTME Success Bot!')}"
    await update.message.reply_text(
        f"👥 *Invite Friends — VIRAL BONUS!*\n\n"
        f"🎁 Invite {REFERRAL_REQUIRED} = {REFERRAL_REWARD_DAYS} days FREE!\n\n"
        f"Your link:\n`{link}`\n\nProgress: {invites}/{REFERRAL_REQUIRED}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Share Link", url=share_url)],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))


async def cmd_premium(update, context):
    uid = str(update.effective_user.id)
    get_user(uid, update.effective_user.first_name or "")
    kb = plan_buttons(uid)
    kb.append([InlineKeyboardButton(
        f"👥 Invite {REFERRAL_REQUIRED}=FREE", callback_data="invite_friends")])
    kb.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    await update.message.reply_text(
        f"💎 *Premium Plans*\n\n"
        f"*Monthly — {PREMIUM_PRICE_TEXT}* / {PREMIUM_DAYS} days\n"
        f"*6 Months — {PREMIUM_6MONTHS_TEXT}* / {PREMIUM_6MONTHS_DAYS} days *(BEST VALUE)*\n\n"
        f"✅ Unlimited mocks\n✅ Subject Mock (40Q)\n"
        f"✅ Full JAMB CBT Mock (180Q · 4 subjects)\n"
        f"✅ Unlimited {TUTOR_NAME} + Voice 🎙️\n✅ {len(ALL_QS)} Qs",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


async def cmd_help(update, context):
    uid = str(update.effective_user.id)
    get_user(uid, update.effective_user.first_name or "")
    help_text = (
        f"❓ *Help — UTME Success Bot*\n\n"
        f"*Commands:*\n"
        f"/start — Main menu\n"
        f"/mock — Start mock exam\n"
        f"/past — Past questions by subject\n"
        f"/study — Study plan\n"
        f"/syllabus — JAMB syllabus\n"
        f"/score — Your scores\n"
        f"/tutor — Ask {TUTOR_NAME} (AI Tutor)\n"
        f"/invite — Invite friends\n"
        f"/premium — Upgrade premium\n"
        f"/help — This message\n\n"
        f"*Free plan:*\n"
        f"• {FREE_MOCK_QS_DAILY} mock questions per 24 hours\n"
        f"• Tutor — {FREE_TUTOR_PER_DAY}/day\n\n"
        f"*Premium:*\n"
        f"• All mock types unlimited\n"
        f"• Subject Mock (40Q)\n"
        f"• Full JAMB CBT Mock (180Q · 4 subjects)\n"
        f"• Unlimited tutor + voice\n\n"
        f"💬 *Chat Mindtech Solutions on Telegram {SUPPORT_HANDLE} for assistance.*"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]])
    if update.callback_query:
        await update.callback_query.message.reply_text(
            help_text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(
            help_text, parse_mode="Markdown", reply_markup=kb)


async def cmd_debug(update, context):
    per_subject = {s: len(LOCAL_DATABANK.get(s, [])) for s in AVAILABLE_SUBJECTS}
    lines = [
        "📊 *Databank Status*",
        f"Total: *{len(ALL_QS)}* questions",
        f"Subjects: *{len(AVAILABLE_SUBJECTS)}*",
        f"Engine: {'✅' if HAS_ENGINE else '❌'}",
        f"AI Tutor ({TUTOR_NAME}): {'✅' if HAS_AI_TUTOR else '❌'}",
        f"Bot: @{md(BOT_USERNAME)}",
        f"Channel: `{CHANNEL_ID or '❌ NOT SET'}`", "",
    ]
    for s in AVAILABLE_SUBJECTS:
        icon = "✅" if per_subject[s] > 0 else "❌"
        lines.append(f"{icon} {s}: {per_subject[s]}")
    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))


async def cmd_kbstats(update, context):
    stats = _get_kb_stats() if HAS_AI_TUTOR else {}
    ok, detail = _tutor_ping() if HAS_AI_TUTOR else (False, "not loaded")
    lines = [
        f"🧠 *AI Tutor ({TUTOR_NAME}) Status*",
        f"DeepSeek: {'✅' if ok else '❌'} {md(str(detail))}",
        f"KB ready: {stats.get('ready', False)}",
        f"Chunks: {stats.get('total_chunks', 0)}",
        f"BM25: {stats.get('bm25_ready', False)}",
        f"Voice engine: {stats.get('voice_engine', 'n/a')}",
        f"Voice name: `{stats.get('voice_name', 'n/a')}`",
    ]
    await update.message.reply_text(
        "\n".join(lines), parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))


async def cmd_postnow(update, context):
    uid = str(update.effective_user.id)
    if str(uid) != str(ADMIN_ID):
        await update.message.reply_text("🔒 Admin only.")
        return
    if not CHANNEL_ID:
        await update.message.reply_text("❌ CHANNEL_ID not set.")
        return
    slot_arg = context.args[0].lower() if context.args else "random"
    valid_slots = {"morning", "afternoon", "evening"}
    if slot_arg == "random" or slot_arg not in valid_slots:
        slot_arg = random.choice(list(valid_slots))
    await update.message.reply_text(f"📤 Sending *{slot_arg}* post…",
                                    parse_mode="Markdown")
    try:
        await channel_post(context.application, slot_name=slot_arg,
                           slot_label="manual-/postnow")
        await update.message.reply_text(
            f"✅ Posted `{slot_arg}` to `{CHANNEL_ID}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(
            f"❌ Failed: `{type(e).__name__}: {e}`", parse_mode="Markdown")


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    data = query.data
    u = get_user(uid, query.from_user.first_name or "")

    # ══════════════════════════════════════════════════════
    # ADMIN PANEL ROUTING
    # ══════════════════════════════════════════════════════
    if data.startswith("admin_"):
        handled = await _admin_handle_callback(query, uid, data, context)
        if handled:
            return

    # ══════════════════════════════════════════════════════
    # HARD GATES
    # ══════════════════════════════════════════════════════
    premium_blocked_callbacks = (
        "mock_by_subject", "mock_full", "cbt_start", "cbt_clear",
    )
    if data in premium_blocked_callbacks and not is_premium(uid):
        print(f"[GATE] BLOCKED {data} for free user uid={uid}")
        msg, kb = upgrade_kb(uid)
        await query.message.reply_text(
            f"🔒 *Premium Feature*\n\n{msg}",
            parse_mode="Markdown", reply_markup=kb)
        return

    if (data.startswith("mock_subject_") or data.startswith("cbt_toggle_")) \
            and not is_premium(uid):
        print(f"[GATE] BLOCKED {data} for free user uid={uid}")
        msg, kb = upgrade_kb(uid)
        await query.message.reply_text(
            f"🔒 *Premium Feature*\n\n{msg}",
            parse_mode="Markdown", reply_markup=kb)
        return

    # ══════════════════════════════════════════════════════
    # STUDY / SYLLABUS / PAST
    # ══════════════════════════════════════════════════════
    if data == "study_plan":
        await query.message.reply_text("📖 *Study Plan — Choose Subject:*",
                                       reply_markup=subjects_kb("study_subject"),
                                       parse_mode="Markdown")
        return

    if data.startswith("study_subject_"):
        subj = data.replace("study_subject_", "")
        u["study_subject"] = subj
        save_data()
        display = SUBJECT_DISPLAY.get(subj, subj.title())
        USER_SESSIONS[uid] = {"mode": "tutor", "subject": subj}
        count = len(LOCAL_DATABANK.get(subj, []))
        await query.message.reply_text(
            f"📖 *Let's study {display}!*\nI know {count} Qs on {display}.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"💬 Ask {display}", callback_data="ask_tutor")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        return

    if data == "syllabus":
        await query.message.reply_text("📋 *JAMB Syllabus — Choose:*",
                                       reply_markup=subjects_kb("syllabus_subject"),
                                       parse_mode="Markdown")
        return

    if data.startswith("syllabus_subject_"):
        subj = data.replace("syllabus_subject_", "")
        display = SUBJECT_DISPLAY.get(subj, subj.title())
        await query.message.reply_text(
            f"📋 *{display} Syllabus*\n\nOfficial: https://jamb.gov.ng/ELibrary",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"📖 Study {display}",
                                      callback_data=f"study_subject_{subj}")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        return

    if data == "past_by_subject":
        await query.message.reply_text("📚 *Past Questions — Choose Subject:*",
                                       reply_markup=subjects_kb("past_subject"),
                                       parse_mode="Markdown")
        return

    if data.startswith("past_subject_"):
        subj = data.replace("past_subject_", "")
        remaining = get_mock_remaining(uid)
        if not is_premium(uid) and remaining <= 0:
            msg, kb = upgrade_kb(uid)
            await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)
            return
        limit = min(5, remaining) if not is_premium(uid) else 5
        qs = fetcher.fetch(subj, None, limit)
        if not qs:
            await query.message.reply_text(
                f"⚠️ No questions for {SUBJECT_DISPLAY.get(subj, subj)}.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="past_by_subject")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
            return
        consume_mock(uid, len(qs), [q["id"] for q in qs])
        txt, kb = _start_mock_session(uid, qs, subj)
        await query.message.reply_text(txt, reply_markup=kb)
        return

    # ══════════════════════════════════════════════════════
    # ANSWER HANDLER
    # ══════════════════════════════════════════════════════
    if data.startswith("ans:"):
        ans = data.split(":")[1]
        session = USER_SESSIONS.get(uid)
        if not session or session.get("mode") != "mock":
            await query.message.reply_text(
                "Session expired.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📝 Mock", callback_data="mock_menu")]]))
            return
        qs = session["qs"]
        idx = session["idx"]
        if idx >= len(qs):
            return
        current_q = qs[idx]
        correct = current_q.get("answer", "")
        is_correct = (ans == correct)
        if is_correct:
            session["score"] += 1
        session["idx"] += 1

        feedback = ("✅ *Correct!* 🎉" if is_correct
                    else f"❌ *Wrong.* Answer is *{md(correct)}*")
        if current_q.get("explanation"):
            feedback += f"\n\n💡 {md(current_q['explanation'][:350])}"
        await query.message.reply_text(feedback, parse_mode="Markdown")

        if session["idx"] < len(qs):
            q = qs[session["idx"]]
            txt = format_question(q, session["idx"] + 1, len(qs))
            await query.message.reply_text(txt, reply_markup=_answer_keyboard(q))
        else:
            score = session["score"]
            total = len(qs)
            percent = score * 100 // total if total else 0
            u["history"].append({
                "date": str(date.today()),
                "subject": session.get("subject", "general"),
                "score": score, "total": total, "percent": percent})
            save_data()
            leader_name, leader_score = get_leading()

            is_free = not is_premium(uid)
            rem_after = get_mock_remaining(uid)

            finish_msg = (f"🎉 *Mock Completed!*\n\n"
                          f"Score: *{score}/{total}* ({percent}%)\n"
                          f"🏆 Leader: {md(leader_name)} — {leader_score}/400\n\n")

            if is_free and rem_after <= 0:
                finish_msg += (
                    f"🛑 *Your free mock for the next 24 hours is complete.*\n\n"
                    f"🔒 *Upgrade to Premium for:*\n"
                    f"✅ Subject Mock (40 Qs)\n"
                    f"✅ Full JAMB CBT Mock (180 Qs)\n"
                    f"✅ Unlimited Quick Mocks\n"
                    f"✅ Unlimited {TUTOR_NAME}"
                )
                buttons = [
                    [InlineKeyboardButton("💎 Upgrade to Premium Now",
                                          callback_data="premium_info")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                ]
            elif is_free:
                finish_msg += f"🆓 You still have *{rem_after}* free questions left today."
                buttons = [
                    [InlineKeyboardButton("⚡ Continue Free Mock",
                                          callback_data="mock_quick")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                ]
            else:
                buttons = [
                    [InlineKeyboardButton("🔄 Another Mock", callback_data="mock_menu")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
                ]

            await query.message.reply_text(
                finish_msg, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons))
            USER_SESSIONS.pop(uid, None)
        return

    # ══════════════════════════════════════════════════════
    # MOCK MENU
    # ══════════════════════════════════════════════════════
    if data == "mock_menu":
        if not is_premium(uid) and get_mock_remaining(uid) <= 0:
            msg, kb = upgrade_kb(uid)
            await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)
            return
        await query.message.reply_text(
            _mock_menu_text(uid), parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(_mock_menu_kb(uid)))
        return

    # ══════════════════════════════════════════════════════
    # QUICK MOCK
    # ══════════════════════════════════════════════════════
    if data == "mock_quick":
        remaining = get_mock_remaining(uid)
        if not is_premium(uid) and remaining <= 0:
            msg, kb = upgrade_kb(uid)
            await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)
            return
        limit = 5 if is_premium(uid) else min(5, remaining)
        pool = AVAILABLE_SUBJECTS or ALL_SUBJECTS
        sample = random.sample(pool, min(3, len(pool)))
        qs = []
        for subj in sample:
            qs.extend(fetcher.fetch(subj, None, 2))
        random.shuffle(qs)
        qs = qs[:limit]
        if not qs:
            await query.message.reply_text("⚠️ No questions loaded.")
            return
        consume_mock(uid, len(qs), [q["id"] for q in qs])
        intro_text = f"🚀 *Quick Mock ({len(qs)} Qs)*"
        if not is_premium(uid):
            after = max(0, remaining - len(qs))
            intro_text += f"\n\n🆓 Free plan: *{after}* question(s) left today."
        txt, kb = _start_mock_session(uid, qs, "mixed", intro_text=intro_text)
        await query.message.reply_text(txt, parse_mode="Markdown", reply_markup=kb)
        return

    # ══════════════════════════════════════════════════════
    # SUBJECT MOCK
    # ══════════════════════════════════════════════════════
    if data == "mock_by_subject":
        await query.message.reply_text(
            "📚 *Choose Subject for your 40Q Mock:*",
            reply_markup=subjects_kb("mock_subject"), parse_mode="Markdown")
        return

    if data.startswith("mock_subject_"):
        subj = data.replace("mock_subject_", "")
        qs = fetcher.fetch(subj, None, 40)
        if len(qs) < 5:
            await query.message.reply_text(
                f"⚠️ Not enough questions for {SUBJECT_DISPLAY.get(subj, subj)}. "
                f"Only {len(qs)}.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="mock_by_subject")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
            return
        display = SUBJECT_DISPLAY.get(subj, subj.title())
        intro = f"📚 *{display} Subject Mock*\n{len(qs)} questions · Good luck!"
        txt, kb = _start_mock_session(uid, qs, f"subject_{subj}", intro_text=intro)
        await query.message.reply_text(txt, parse_mode="Markdown", reply_markup=kb)
        return

    # ══════════════════════════════════════════════════════
    # FULL JAMB CBT MOCK
    # ══════════════════════════════════════════════════════
    if data == "mock_full":
        USER_SESSIONS[uid] = {"mode": "cbt_select", "cbt_subjects": []}
        await query.message.reply_text(
            _cbt_subject_text(uid), parse_mode="Markdown",
            reply_markup=_cbt_subject_kb(uid))
        return

    if data.startswith("cbt_toggle_"):
        subj = data.replace("cbt_toggle_", "")
        if subj not in AVAILABLE_SUBJECTS:
            return
        session = USER_SESSIONS.setdefault(
            uid, {"mode": "cbt_select", "cbt_subjects": []})
        selected = session.get("cbt_subjects", [])
        if subj in selected:
            selected.remove(subj)
        else:
            if len(selected) >= CBT_SUBJECTS_REQUIRED:
                await query.answer(
                    f"JAMB allows only {CBT_SUBJECTS_REQUIRED} subjects!\n"
                    f"Deselect one first.",
                    show_alert=True)
                return
            selected.append(subj)
        session["cbt_subjects"] = selected
        try:
            await query.edit_message_text(
                _cbt_subject_text(uid), parse_mode="Markdown",
                reply_markup=_cbt_subject_kb(uid))
        except Exception:
            await query.message.reply_text(
                _cbt_subject_text(uid), parse_mode="Markdown",
                reply_markup=_cbt_subject_kb(uid))
        return

    if data == "cbt_clear":
        session = USER_SESSIONS.setdefault(
            uid, {"mode": "cbt_select", "cbt_subjects": []})
        session["cbt_subjects"] = []
        try:
            await query.edit_message_text(
                _cbt_subject_text(uid), parse_mode="Markdown",
                reply_markup=_cbt_subject_kb(uid))
        except Exception:
            await query.message.reply_text(
                _cbt_subject_text(uid), parse_mode="Markdown",
                reply_markup=_cbt_subject_kb(uid))
        return

    if data == "cbt_start":
        session = USER_SESSIONS.get(uid, {})
        selected = session.get("cbt_subjects", [])
        if len(selected) != CBT_SUBJECTS_REQUIRED:
            await query.answer(
                f"Please select exactly {CBT_SUBJECTS_REQUIRED} subjects!",
                show_alert=True)
            return
        missing = [s for s in selected if not LOCAL_DATABANK.get(s)]
        if missing:
            names = ", ".join(SUBJECT_DISPLAY.get(s, s) for s in missing)
            await query.message.reply_text(
                f"⚠️ No questions available for: {names}\n"
                f"Please pick different subjects.",
                parse_mode="Markdown",
                reply_markup=_cbt_subject_kb(uid))
            return
        qs = _fetch_cbt_questions(uid, selected, total=CBT_TOTAL_QUESTIONS)
        if len(qs) < 20:
            await query.message.reply_text(
                f"⚠️ Only {len(qs)} questions available. "
                f"Not enough for a full CBT mock.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Reselect", callback_data="mock_full")],
                    [InlineKeyboardButton("🏠 Main Menu",
                                          callback_data="main_menu")]]))
            return
        used_ids = [q.get("id") for q in qs if q.get("id")]
        u2 = get_user(uid)
        u2["used_ids"].extend(str(x) for x in used_ids)
        u2["used_ids"] = list(dict.fromkeys(u2["used_ids"]))[-5000:]
        save_data()

        stats = _cbt_stats_text(uid, selected, qs)
        subj_label = "CBT:" + ",".join(selected)
        intro = (
            f"🚀 *Full JAMB CBT Mock*\n\n"
            f"📚 *Your 4 subjects:*\n{stats}\n\n"
            f"📝 Total: *{len(qs)} questions*\n"
            f"⏱️ Recommended: *2 hours*\n\n"
            f"💡 Tip: Answer steadily. Each correct = +1.\n\n"
            f"Good luck! 🎯"
        )
        txt, kb = _start_mock_session(uid, qs, subj_label, intro_text=intro)
        await query.message.reply_text(txt, parse_mode="Markdown", reply_markup=kb)
        return

    # ══════════════════════════════════════════════════════
    # SCORE / TUTOR / PREMIUM / INVITE / HELP
    # ══════════════════════════════════════════════════════
    if data == "my_score":
        hist = u.get("history", [])
        if not hist:
            await query.message.reply_text(
                "📊 No scores yet",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📝 Mock", callback_data="mock_menu")]]))
            return
        avg = sum(h["score"] * 400 // h["total"] for h in hist if h["total"]) / len(hist)
        leader_name, leader_score = get_leading()
        await query.message.reply_text(
            f"📊 Avg {int(avg)}/400 · Exams {len(hist)}\n"
            f"🏆 Leader: {md(leader_name)} — {leader_score}/400",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        return

    if data == "ask_tutor":
        prev = USER_SESSIONS.get(uid, {}).get("subject") or u.get("study_subject")
        USER_SESSIONS[uid] = {"mode": "tutor", "subject": prev}
        if is_premium(uid):
            remaining_text = "Unlimited"
        else:
            used = u["tutor_counts"].get(str(date.today()), 0)
            remaining_text = f"{max(0, FREE_TUTOR_PER_DAY - used)}/{FREE_TUTOR_PER_DAY} left today"
        await query.message.reply_text(
            f"💬 *Ask {TUTOR_NAME}*\n"
            f"🧠 AI: {'Active ✅' if HAS_AI_TUTOR else 'Limited'}\n"
            f"🎙️ Voice: Nigerian male teacher\n"
            f"Tutor: {remaining_text}\n\n"
            f"Ask anything — any subject:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        return

    if data == "premium_info":
        kb = plan_buttons(uid)
        kb.append([InlineKeyboardButton(f"👥 Invite {REFERRAL_REQUIRED}=FREE",
                                        callback_data="invite_friends")])
        kb.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
        await query.message.reply_text(
            f"💎 *Premium Plans*\n\n"
            f"*Monthly — {PREMIUM_PRICE_TEXT}* / {PREMIUM_DAYS} days\n"
            f"*6 Months — {PREMIUM_6MONTHS_TEXT}* / {PREMIUM_6MONTHS_DAYS} days *(BEST VALUE)*\n\n"
            f"✅ Unlimited mocks\n✅ Subject Mock (40Q)\n"
            f"✅ Full JAMB CBT Mock (180Q · 4 subjects)\n"
            f"✅ Unlimited {TUTOR_NAME} + Voice 🎙️\n✅ {len(ALL_QS)} Qs",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data == "invite_friends":
        link = f"https://t.me/{BOT_USERNAME}?start=invite_{u['invite_code']}"
        invites = u.get("invites", 0)
        share_url = f"https://t.me/share/url?url={quote(link)}&text={quote('Join UTME Success Bot!')}"
        await query.message.reply_text(
            f"👥 *Invite Friends — VIRAL BONUS!*\n\n"
            f"🎁 Invite {REFERRAL_REQUIRED} = {REFERRAL_REWARD_DAYS} days FREE!\n\n"
            f"Your link:\n`{link}`\n\nProgress: {invites}/{REFERRAL_REQUIRED}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Share Link", url=share_url)],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        return

    if data == "help_menu":
        await cmd_help(update, context)
        return

    if data == "main_menu":
        t, kb = main_menu_text_kb(uid)
        await query.message.reply_text(t, reply_markup=kb, parse_mode="Markdown")
        return


# ============================================================
# TEXT HANDLER
# ============================================================

async def handle_msg(update, context):
    uid = str(update.effective_user.id)
    text = (update.message.text or "").strip()
    u = get_user(uid, update.effective_user.first_name or "")

    # ── Admin state handling (grant / broadcast) ──
    if _admin_only(uid):
        admin_session = USER_SESSIONS.get(uid, {})
        admin_mode = admin_session.get("mode")

        if admin_mode == "admin_grant_wait":
            target_id = text.strip()
            if target_id.isdigit():
                add_premium(target_id, days=PREMIUM_DAYS, plan="admin-grant")
                USER_SESSIONS.pop(uid, None)
                await update.message.reply_text(
                    f"✅ Granted {PREMIUM_DAYS}-day Premium to `{target_id}`",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⚙️ Admin Panel",
                                              callback_data="admin_panel")]]))
            else:
                await update.message.reply_text(
                    "❌ Invalid ID. Send the numeric Telegram ID.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back",
                                              callback_data="admin_panel")]]))
            return

        if admin_mode == "admin_broadcast_wait":
            USER_SESSIONS.pop(uid, None)
            broadcast_text = text.strip()
            sent, failed = 0, 0
            status_msg = await update.message.reply_text(
                f"📢 Broadcasting to {len(USER_DATA)} users…")
            for target_uid in list(USER_DATA.keys()):
                try:
                    await context.bot.send_message(
                        chat_id=int(target_uid),
                        text=broadcast_text,
                        parse_mode="Markdown")
                    sent += 1
                    await asyncio.sleep(0.05)
                except Exception:
                    failed += 1
            await status_msg.edit_text(
                f"✅ Broadcast complete\n\n• Sent: {sent}\n• Failed: {failed}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Admin Panel",
                                          callback_data="admin_panel")]]))
            return

    # ── Admin text shortcut ──
    if text == "⚙️ Admin Panel" and _admin_only(uid):
        await cmd_admin(update, context)
        return

    if text == "📚 Past Questions":
        await cmd_past(update, context); return
    if text == "📝 Mock Exam":
        await cmd_mock(update, context); return
    if text == "📊 My Score":
        await cmd_score(update, context); return
    if text == "💬 Ask Tutor":
        await cmd_tutor(update, context); return
    if text == "💎 Premium":
        await cmd_premium(update, context); return
    if text == "👥 Invite Friends":
        await cmd_invite(update, context); return
    if text == "📖 Study Plan":
        await cmd_study(update, context); return

    session = USER_SESSIONS.get(uid, {})
    is_tutor = (session.get("mode") == "tutor" or
                (session.get("mode") != "cbt_select" and
                 ("?" in text or len(text) > 8)))

    if not is_tutor:
        await update.message.reply_text("Use the menu below 👇",
                                        reply_markup=BOTTOM_KEYBOARD)
        return

    if not can_use_tutor(uid):
        msg, kb = upgrade_kb(uid)
        await update.message.reply_text(
            f"⏰ *Tutor Limit Reached*\n\nFree: {FREE_TUTOR_PER_DAY}/day\n\n{msg}",
            parse_mode="Markdown", reply_markup=kb)
        return
    consume_tutor(uid)

    thinking_msg = None
    try:
        thinking_msg = await update.message.reply_text(
            f"🧠 *{TUTOR_NAME} is thinking…*", parse_mode="Markdown")
    except Exception:
        pass

    subj = session.get("subject") or u.get("study_subject") or ""
    display = SUBJECT_DISPLAY.get(subj, subj.title()) if subj else "JAMB"

    try:
        if HAS_AI_TUTOR:
            answer_text = await asyncio.to_thread(_ask_tutor, text, subj)
        else:
            answer_text = "⚠️ *AI Tutor is not available right now.*"
    except Exception:
        answer_text = "⚠️ *Tutor error.* Please try again in a moment."

    if thinking_msg is not None:
        try:
            await thinking_msg.delete()
        except Exception:
            pass

    header = f"💬 *{TUTOR_NAME} — {md(display)}*\n\n*Q:* {md(text[:300])}\n\n"
    footer = "\n\n_📚 Grounded in JAMB databank + DeepSeek reasoning_"
    final_msg = header + answer_text + footer

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎙️ Voice Explanation", callback_data="ask_tutor")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ])

    try:
        await update.message.reply_text(final_msg[:4000], parse_mode="Markdown",
                                        reply_markup=kb)
    except Exception:
        try:
            await update.message.reply_text(final_msg[:4000], reply_markup=kb)
        except Exception as e2:
            print(f"[tutor] send failed: {e2}")

    # ── Voice: Nigerian male teacher, always attached ──
    if HAS_AI_TUTOR:
        try:
            voice_if = await asyncio.to_thread(_build_voice, answer_text)
            if voice_if is not None:
                await update.message.reply_voice(
                    voice=voice_if,
                    caption=f"🎙️ Voice Explanation — {TUTOR_NAME}")
            else:
                print("[tutor] Voice generation returned None")
        except Exception as e:
            print(f"[tutor] Voice send failed: {type(e).__name__}: {e}")


# ============================================================
# FLASK APP
# ============================================================
flask_app = Flask(__name__)


@flask_app.route("/")
def home():
    return (f"UTME Bot v28 · {len(ALL_QS)} Qs · "
            f"AI Tutor ({TUTOR_NAME}): {'ON' if HAS_AI_TUTOR else 'OFF'} · "
            f"Bot: @{BOT_USERNAME} · Channel: {CHANNEL_ID or 'OFF'} · Running")


@flask_app.route("/health")
def health():
    tutor_ok, tutor_detail = _tutor_ping() if HAS_AI_TUTOR else (False, "not loaded")
    return jsonify({
        "status": "ok",
        "bot_username": BOT_USERNAME,
        "tutor_name": TUTOR_NAME,
        "total_questions": len(ALL_QS),
        "free_mock_limit": FREE_MOCK_QS_DAILY,
        "cbt_subjects_required": CBT_SUBJECTS_REQUIRED,
        "cbt_total_questions": CBT_TOTAL_QUESTIONS,
        "tutor_ok": tutor_ok,
        "channel_configured": bool(CHANNEL_ID),
        "users": len(USER_DATA),
    })


def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT, threaded=True)


UPGRADE_PAGE = r"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Upgrade — UTME Success Bot</title>
<script src="https://checkout.flutterwave.com/v3.js"></script>
<style>
 body{margin:0;font-family:-apple-system,sans-serif;background:linear-gradient(135deg,#1e1b4b,#7c3aed);min-height:100vh;padding:20px;color:#0f172a}
 .wrap{max-width:480px;margin:0 auto}
 .card{background:#fff;border-radius:20px;padding:24px;margin-bottom:18px;box-shadow:0 20px 50px -12px rgba(0,0,0,.35)}
 h1{color:#fff;text-align:center;font-size:26px}
 p.sub{color:rgba(255,255,255,.85);text-align:center;margin-top:0}
 .plan{border:2px solid #e2e8f0;border-radius:16px;padding:20px;margin-bottom:14px}
 .plan.best{border-color:#f59e0b;background:#fffbeb}
 .pay{width:100%;padding:15px;border:none;border-radius:12px;font-size:16px;font-weight:700;color:#fff;background:linear-gradient(135deg,#7c3aed,#4c1d95);cursor:pointer;margin-top:10px}
 .plan.best .pay{background:linear-gradient(135deg,#f59e0b,#d97706)}
 .btn-alt{display:block;padding:14px;text-align:center;border-radius:12px;background:linear-gradient(135deg,#10b981,#059669);color:#fff;text-decoration:none;font-weight:700;margin-top:8px}
 .alert{background:#fef2f2;color:#991b1b;padding:12px;border-radius:12px;font-size:13px;border-left:4px solid #dc2626;margin-bottom:16px}
</style></head><body><div class="wrap">
<h1>👑 Upgrade to Premium</h1>
<p class="sub">Unlock unlimited practice. Score higher in UTME.</p>
{% if not gateway_ready %}<div class="alert">⚠️ Payment not configured. Contact support.</div>{% endif %}
<div class="card">
 <div class="plan"><b>Monthly</b> — {{ monthly_price_text }}<br><small>{{ monthly_days }} days full access</small>
 <button class="pay" onclick="payNow('monthly', {{ monthly_price }})" {% if not gateway_ready %}disabled{% endif %}>💳 Pay Monthly</button></div>
 <div class="plan best"><b>⭐ 6 Months</b> — {{ six_months_text }}<br><small>Save {{ savings_text }} · {{ six_months_days }} days</small>
 <button class="pay" onclick="payNow('6months', {{ six_months_price }})" {% if not gateway_ready %}disabled{% endif %}>💳 Pay 6 Months</button></div>
 <a class="btn-alt" href="{{ share_link }}">👥 Invite Friends — Get {{ referral_reward_days }} Days FREE</a>
</div>
<p style="text-align:center;color:rgba(255,255,255,.7);font-size:12px">
🔒 Secured by Flutterwave · <a href="https://t.me/{{ bot_username }}" style="color:#fff">Return to Bot</a></p>
</div>
<script>
const UID="{{ uid }}", BOT="{{ bot_username }}", FLW_PK="{{ flw_public_key }}", API=window.location.origin;
function payNow(planKey, amount){
 if(typeof FlutterwaveCheckout==="undefined"){alert("Payment gateway failed to load.");return;}
 if(!FLW_PK||FLW_PK.length<20){alert("Payment not configured.");return;}
 const txRef="UTME-"+UID+"-"+Date.now();
 FlutterwaveCheckout({
  public_key:FLW_PK, tx_ref:txRef, amount:amount, currency:"NGN",
  payment_options:"card,banktransfer,ussd,account",
  redirect_url:API+"/payment/complete?uid="+UID,
  customer:{email:"user"+UID+"@utmebot.com", name:"UTME User "+UID},
  customizations:{title:"UTME Success Bot Premium", description:planKey==="6months"?"6 Months":"Monthly"},
  meta:{user_id:UID, plan:planKey},
  callback:function(resp){
   fetch(API+"/verify/flutterwave",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({transaction_id:resp.transaction_id,tx_ref:resp.tx_ref,expected_uid:UID,plan:planKey})})
   .then(r=>r.json()).then(res=>{
    if(res.status==="success"){alert("✅ Payment successful!");window.location.href="https://t.me/"+BOT;}
    else{alert("⚠️ Contact support if not activated.");window.location.href="https://t.me/"+BOT;}
   }).catch(()=>{alert("⚠️ Network error.");window.location.href="https://t.me/"+BOT;});
  },
  onclose:function(){console.log("closed");}
 });
}
</script></body></html>"""


@flask_app.route("/upgrade/<uid>")
def upgrade_page(uid):
    monthly = _resolve_plan("monthly")
    six = _resolve_plan("6months")
    savings = PREMIUM_PRICE * 6 - PREMIUM_6MONTHS_PRICE
    savings_text = f"\u20a6{savings}" if savings > 0 else ""
    invite_link = f"https://t.me/{BOT_USERNAME}?start=invite_{uid}"
    share_link = f"https://t.me/share/url?url={quote(invite_link)}&text={quote('Join UTME Success Bot!')}"
    return render_template_string(
        UPGRADE_PAGE, uid=uid, bot_username=BOT_USERNAME,
        flw_public_key=FLW_PUBLIC_KEY,
        gateway_ready=bool(FLW_PUBLIC_KEY and FLW_SECRET_KEY),
        monthly_price=monthly["price"], monthly_price_text=monthly["price_text"],
        monthly_days=monthly["days"], six_months_price=six["price"],
        six_months_text=six["price_text"], six_months_days=six["days"],
        savings_text=savings_text, referral_reward_days=REFERRAL_REWARD_DAYS,
        share_link=share_link)


@flask_app.route("/payment/complete")
def payment_complete():
    uid = request.args.get("uid", "")
    return f"""<html><body style="font-family:sans-serif;text-align:center;padding:60px">
    <h1 style="color:#10b981">✅ Payment Received</h1>
    <p>Activation in progress.</p>
    <p>Message the bot with your ID: <b>{uid}</b> if not activated in 2 minutes.</p>
    <a href="https://t.me/{BOT_USERNAME}" style="padding:14px 28px;background:#7c3aed;color:#fff;text-decoration:none;border-radius:12px;font-weight:700">Return to Bot</a>
    </body></html>"""


@flask_app.route("/verify/flutterwave", methods=["POST"])
def verify_flutterwave():
    body = request.get_json(silent=True) or {}
    tx_id = body.get("transaction_id")
    expected_uid = str(body.get("expected_uid") or "")
    plan_key = body.get("plan", "monthly")
    if not tx_id or not FLW_SECRET_KEY:
        return jsonify({"status": "failed"}), 400
    try:
        r = requests.get(f"https://api.flutterwave.com/v3/transactions/{tx_id}/verify",
                         headers={"Authorization": f"Bearer {FLW_SECRET_KEY}"}, timeout=15)
        result = r.json()
    except Exception:
        return jsonify({"status": "failed"}), 502
    data = (result or {}).get("data") or {}
    if not (result.get("status") == "success" and data.get("status") == "successful"):
        return jsonify({"status": "failed"}), 400
    verified_tx_ref = data.get("tx_ref", "")
    verified_uid = _uid_from_tx_ref(verified_tx_ref)
    if not verified_uid:
        return jsonify({"status": "failed"}), 400
    if expected_uid and expected_uid != verified_uid:
        return jsonify({"status": "failed"}), 400
    meta_plan = (data.get("meta") or {}).get("plan")
    if meta_plan in PLANS:
        plan_key = meta_plan
    uid = _grant_from_verified(verified_tx_ref, plan_key)
    if not uid:
        return jsonify({"status": "duplicate_or_invalid"}), 200
    return jsonify({"status": "success", "uid": uid, "plan": plan_key})


@flask_app.route("/webhook/flutterwave", methods=["POST"])
def flutterwave_webhook():
    sig = request.headers.get("verif-hash", "")
    if not FLW_SECRET_HASH or sig != FLW_SECRET_HASH:
        return jsonify({"status": "unauthorized"}), 401
    payload = request.get_json(silent=True) or {}
    data = payload.get("data") or {}
    tx_ref = data.get("tx_ref", "")
    tx_id = data.get("id")
    if not tx_ref or not tx_id:
        return jsonify({"status": "ignored"}), 200
    try:
        r = requests.get(f"https://api.flutterwave.com/v3/transactions/{tx_id}/verify",
                         headers={"Authorization": f"Bearer {FLW_SECRET_KEY}"}, timeout=15)
        v = r.json()
        if not (v.get("status") == "success" and (v.get("data") or {}).get("status") == "successful"):
            return jsonify({"status": "not_verified"}), 200
        meta_plan = (v["data"].get("meta") or {}).get("plan", "monthly")
    except Exception:
        return jsonify({"status": "error"}), 500
    _grant_from_verified(tx_ref, meta_plan if meta_plan in PLANS else "monthly")
    return jsonify({"status": "success"})


# ============================================================
# CHANNEL AUTO-POSTING
# ============================================================
POST_SLOTS = ((8, 30, "morning"), (13, 0, "afternoon"), (20, 0, "evening"))
POST_WINDOW_MIN = 30


def _now_lagos():
    return datetime.now(timezone.utc) + timedelta(hours=1)


def _build_morning_post(q):
    intro = random.choice(["🌅 *Good Morning, Champion!*", "🌅 *Rise and Grind!*",
                           "🌅 *Morning JAMB Practice*"])
    return (f"{intro}\n\n📚 *{md(q.get('subject','JAMB'))}* | {md(str(q.get('year','')))}\n\n"
            f"{md(q.get('question','')[:340])}\n\n"
            f"A) {md(q.get('option_a','')[:80])}\nB) {md(q.get('option_b','')[:80])}\n"
            f"C) {md(q.get('option_c','')[:80])}\nD) {md(q.get('option_d','')[:80])}\n\n"
            f"💡 *Answer:* {md(q.get('answer',''))}\n\n"
            f"🎯 You've got this!\n👉 Full practice: https://t.me/{BOT_USERNAME}")


def _build_afternoon_post(q):
    intro = random.choice(["☀️ *Afternoon Quick Practice*", "☀️ *Midday JAMB Challenge*"])
    return (f"{intro}\n\nTake 30 seconds:\n\n📚 *{md(q.get('subject','JAMB'))}* | "
            f"{md(str(q.get('year','')))}\n\n"
            f"{md(q.get('question','')[:340])}\n\n"
            f"A) {md(q.get('option_a','')[:80])}\nB) {md(q.get('option_b','')[:80])}\n"
            f"C) {md(q.get('option_c','')[:80])}\nD) {md(q.get('option_d','')[:80])}\n\n"
            f"💡 *Answer:* {md(q.get('answer',''))}\n\n"
            f"⚡ Stay sharp!\n👉 More practice: https://t.me/{BOT_USERNAME}")


def _build_evening_post(q):
    intro = random.choice(["🌙 *Evening Study Session*", "🌙 *End the Day Strong*"])
    body = (f"{intro}\n\n📚 *{md(q.get('subject','JAMB'))}* | "
            f"{md(str(q.get('year','')))}\n\n"
            f"{md(q.get('question','')[:340])}\n\n"
            f"A) {md(q.get('option_a','')[:80])}\nB) {md(q.get('option_b','')[:80])}\n"
            f"C) {md(q.get('option_c','')[:80])}\nD) {md(q.get('option_d','')[:80])}\n\n"
            f"💡 *Answer:* {md(q.get('answer',''))}\n")
    expl = (q.get("explanation") or "").strip()
    if expl:
        body += f"\n📖 *Why?* {md(expl[:350])}\n"
    body += f"\n🛌 Sleep well!\n👉 Full practice: https://t.me/{BOT_USERNAME}"
    return body


def _build_post(q, slot_name):
    if slot_name == "morning":
        return _build_morning_post(q)
    if slot_name == "afternoon":
        return _build_afternoon_post(q)
    if slot_name == "evening":
        return _build_evening_post(q)
    return _build_morning_post(q)


async def channel_post(app, slot_name="morning", slot_label="manual"):
    if not CHANNEL_ID:
        raise RuntimeError("CHANNEL_ID is not configured")
    q = get_random_question()
    if not q:
        raise RuntimeError("No questions available")
    msg = _build_post(q, slot_name)
    await app.bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="Markdown")
    print(f"[channel] ✅ Posted ({slot_name}/{slot_label}) to {CHANNEL_ID}")
    return True


async def channel_posting_job(app):
    print("[channel] ⏰ Job started")
    print(f"[channel]    CHANNEL_ID = {CHANNEL_ID or '❌ NOT SET'}")
    if not CHANNEL_ID:
        print("[channel] ❌ CHANNEL_ID missing — DISABLED")
        return
    try:
        await channel_post(app, slot_name="morning", slot_label="startup-test")
    except Exception as e:
        print(f"[channel] ❌ Startup post failed: {type(e).__name__}: {e}")

    posted_slots = set()
    while True:
        try:
            now = _now_lagos()
            now_total = now.hour * 60 + now.minute
            today = now.date().isoformat()
            for (h, m, slot_name) in POST_SLOTS:
                slot_key = f"{today}_{h:02d}{m:02d}"
                target_total = h * 60 + m
                if (target_total <= now_total < target_total + POST_WINDOW_MIN
                        and slot_key not in posted_slots):
                    try:
                        await channel_post(app, slot_name=slot_name,
                                           slot_label=f"{h:02d}:{m:02d}")
                        posted_slots.add(slot_key)
                    except Exception as e:
                        print(f"[channel] ❌ {slot_name}: {e}")
            posted_slots = {k for k in posted_slots if k.startswith(today)}
            await asyncio.sleep(300)
        except Exception as e:
            print(f"[channel] ❌ Loop error: {e}")
            await asyncio.sleep(600)


async def post_init(app):
    try:
        commands = [
            BotCommand("start", "🏠 Main Menu"),
            BotCommand("mock", "📝 Mock Exam"),
            BotCommand("past", "📚 Past Questions"),
            BotCommand("study", "📖 Study Plan"),
            BotCommand("syllabus", "📋 JAMB Syllabus"),
            BotCommand("score", "📊 My Score"),
            BotCommand("tutor", f"💬 Ask {TUTOR_NAME}"),
            BotCommand("invite", "👥 Invite Friends"),
            BotCommand("premium", "💎 Upgrade Premium"),
            BotCommand("help", "❓ Help"),
        ]
        await app.bot.set_my_commands(commands)
        await app.bot.set_chat_menu_button(
            menu_button=MenuButtonCommands(text="📋 Menu"))
        print("✅ Commands registered")
        try:
            asyncio.create_task(channel_posting_job(app))
            print("✅ Channel poster launched")
        except Exception as e:
            print(f"⚠️ Channel poster: {e}")
    except Exception as e:
        print(f"Menu setup failed: {e}")


# ============================================================
# MAIN
# ============================================================
def main():
    load_data()
    load_processed_tx()

    print(f"🤖 Bot: @{BOT_USERNAME}")
    print(f"👨‍🏫 Tutor: {TUTOR_NAME} (Nigerian male teacher voice)")
    print(f"🔒 Free mock limit: {FREE_MOCK_QS_DAILY}/24h (HARD-LOCKED)")
    print(f"🔒 CBT Mock: {CBT_SUBJECTS_REQUIRED} subjects · "
          f"{CBT_TOTAL_QUESTIONS} Qs · PREMIUM ONLY")
    if ADMIN_ID:
        print(f"⚙️  Admin ID: {ADMIN_ID} (Admin Panel enabled)")

    if HAS_AI_TUTOR:
        try:
            print(f"🧠 Building {TUTOR_NAME} knowledge base…")
            _build_kb()
            ok, detail = _tutor_ping()
            print(f"🧠 Tutor ping: {detail}")
        except Exception as e:
            print(f"⚠️ Tutor init: {e}")

    threading.Thread(target=run_flask, daemon=True).start()
    print(f"🌐 Flask on port {PORT}")
    print(f"📚 Loaded: {len(ALL_QS)} Qs | {len(AVAILABLE_SUBJECTS)} subjects")
    print(f"📢 Channel: {CHANNEL_ID or '❌ NOT CONFIGURED'}")

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or len(BOT_TOKEN) < 20:
        print("❌ BOT_TOKEN not set!")
        while True:
            time.sleep(60)

    try:
        app = ApplicationBuilder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("start", cmd_start))
        app.add_handler(CommandHandler("menu", cmd_start))
        app.add_handler(CommandHandler("mock", cmd_mock))
        app.add_handler(CommandHandler("past", cmd_past))
        app.add_handler(CommandHandler("study", cmd_study))
        app.add_handler(CommandHandler("syllabus", cmd_syllabus))
        app.add_handler(CommandHandler("score", cmd_score))
        app.add_handler(CommandHandler("tutor", cmd_tutor))
        app.add_handler(CommandHandler("invite", cmd_invite))
        app.add_handler(CommandHandler("premium", cmd_premium))
        app.add_handler(CommandHandler("admin", cmd_admin))
        app.add_handler(CommandHandler("debug", cmd_debug))
        app.add_handler(CommandHandler("kbstats", cmd_kbstats))
        app.add_handler(CommandHandler("postnow", cmd_postnow))
        app.add_handler(CommandHandler("help", cmd_help))

        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(MessageHandler(
            filters.Regex("^(📚 Past Questions|📝 Mock Exam|📊 My Score|💬 Ask Tutor|"
                          "💎 Premium|👥 Invite Friends|📖 Study Plan|⚙️ Admin Panel)$"),
            handle_msg))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))

        app.post_init = post_init
        print("✅ Bot running")
        app.run_polling()
    except Exception as e:
        print(f"❌ Bot failed: {e}")
        traceback.print_exc()
        while True:
            time.sleep(60)


if __name__ == "__main__":
    main()
