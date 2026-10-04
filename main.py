"""
UTME Success Bot v28 — FINAL
- Free: Quick 5Q mock only + 5 tutor/day
- Premium: Subject mock (40Q) + Full mock (180Q) + unlimited tutor
"""
import os, json, random, time, threading, hashlib, asyncio, re, hmac, traceback
from datetime import date, datetime, timedelta
from pathlib import Path

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
    BOT_USERNAME = os.getenv("BOT_USERNAME", "YourBot")
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
    if not tx_ref:
        return False
    if tx_ref in PROCESSED_TX:
        return False
    PROCESSED_TX.add(tx_ref)
    save_processed_tx()
    return True


def get_user(uid, username=""):
    uid = str(uid)
    if uid not in USER_DATA:
        USER_DATA[uid] = {
            "mock_counts": {}, "tutor_counts": {}, "used_ids": [],
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
    if str(uid) == str(ADMIN_ID):
        return True
    return bool(u.get("is_premium"))


def can_use_mock(uid, c=1):
    if is_premium(uid):
        return True
    u = get_user(uid)
    return u["mock_counts"].get(str(date.today()), 0) + c <= FREE_MOCK_QS_DAILY


def consume_mock(uid, c, ids=None):
    u = get_user(uid)
    today = str(date.today())
    u["mock_counts"][today] = u["mock_counts"].get(today, 0) + c
    if ids:
        u["used_ids"].extend(ids)
        u["used_ids"] = list(dict.fromkeys(u["used_ids"]))[-2000:]
    save_data()


def get_mock_remaining(uid):
    if is_premium(uid):
        return 999
    u = get_user(uid)
    return max(0, FREE_MOCK_QS_DAILY - u["mock_counts"].get(str(date.today()), 0))


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
        f"⏰ *Limit Reached / Premium Feature*\n\n"
        f"Free plan: {FREE_MOCK_QS_DAILY} mock/day + {FREE_TUTOR_PER_DAY} tutor/day\n\n"
        f"💎 *Premium Plans:*\n"
        f"• Monthly — {PREMIUM_PRICE_TEXT} / {PREMIUM_DAYS} days\n"
        f"• 6 Months — {PREMIUM_6MONTHS_TEXT} / {PREMIUM_6MONTHS_DAYS} days\n\n"
        f"✅ Unlimited mocks\n✅ Subject Mock (40Q)\n✅ Full JAMB Mock (180Q)\n"
        f"✅ Unlimited tutor + Voice 🎙️\n✅ {len(ALL_QS)} Qs"
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
        f"📊 {rem}/{FREE_MOCK_QS_DAILY} mocks today | {prem}\n"
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


def _mock_menu_kb(uid):
    """Build the mock menu based on user's premium status."""
    rem = get_mock_remaining(uid)
    if is_premium(uid):
        return [
            [InlineKeyboardButton("⚡ Quick 5 Qs", callback_data="mock_quick")],
            [InlineKeyboardButton("📚 Subject Mock (40 Qs)",
                                  callback_data="mock_by_subject")],
            [InlineKeyboardButton("🔥 Full JAMB Mock (180 Qs)",
                                  callback_data="mock_full")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ]
    return [
        [InlineKeyboardButton(f"⚡ Quick 5 Qs ({rem} left)",
                              callback_data="mock_quick")],
        [InlineKeyboardButton("📚 Subject Mock 🔒",
                              callback_data="mock_by_subject")],
        [InlineKeyboardButton("🔥 Full JAMB Mock 🔒",
                              callback_data="mock_full")],
        [InlineKeyboardButton("💎 Upgrade Now",
                              callback_data="premium_info")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ]


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
    return (
        f"📝 *Mock Exam Menu*\n\n"
        f"🆓 *Free Plan:*\n"
        f"⚡ Quick 5 Qs — {rem}/{FREE_MOCK_QS_DAILY} left today\n\n"
        f"🔒 *Premium Only:*\n"
        f"📚 Subject Mock (40 Qs)\n"
        f"🔥 Full JAMB Mock (180 Qs)\n\n"
        f"💎 Upgrade to unlock all mock types!"
    )


# ============================================================
# COMMAND HANDLERS
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
    await update.message.reply_text(
        _mock_menu_text(uid),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(_mock_menu_kb(uid)))


async def cmd_study(update, context):
    get_user(update.effective_user.id, update.effective_user.first_name or "")
    await update.message.reply_text(
        "📖 *Study Plan — Choose Subject:*",
        reply_markup=subjects_kb("study_subject"),
        parse_mode="Markdown")


async def cmd_syllabus(update, context):
    get_user(update.effective_user.id, update.effective_user.first_name or "")
    await update.message.reply_text(
        "📋 *JAMB Syllabus — Choose Subject:*",
        reply_markup=subjects_kb("syllabus_subject"),
        parse_mode="Markdown")


async def cmd_past(update, context):
    get_user(update.effective_user.id, update.effective_user.first_name or "")
    await update.message.reply_text(
        "📚 *Past Questions — Choose Subject:*",
        reply_markup=subjects_kb("past_subject"),
        parse_mode="Markdown")


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
        f"📊 *Your Scores*\n\n"
        f"Average: *{int(avg)}/400*\n"
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
        f"💬 *Ask Tutor*\n\n"
        f"I know {len(ALL_QS)} past questions + AI brain + Voice 🎙️.\n"
        f"Tutor questions: {remaining_text}\n\n"
        f"Just type your question — any subject, any topic.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))


async def cmd_invite(update, context):
    uid = str(update.effective_user.id)
    u = get_user(uid, update.effective_user.first_name or "")
    link = f"https://t.me/{BOT_USERNAME}?start=invite_{u['invite_code']}"
    invites = u.get("invites", 0)
    await update.message.reply_text(
        f"👥 *Invite Friends — VIRAL BONUS!*\n\n"
        f"🎁 Invite {REFERRAL_REQUIRED} = {REFERRAL_REWARD_DAYS} days FREE!\n\n"
        f"Your link:\n`{link}`\n\nProgress: {invites}/{REFERRAL_REQUIRED}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Share Link",
                url=f"https://t.me/share/url?url={link}&text=Join UTME Success Bot!")],
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
        f"✅ Unlimited mocks\n✅ Subject Mock (40Q)\n✅ Full JAMB Mock (180Q)\n"
        f"✅ Unlimited tutor + Voice 🎙️\n✅ {len(ALL_QS)} Qs",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


async def cmd_help(update, context):
    uid = str(update.effective_user.id)
    get_user(uid, update.effective_user.first_name or "")
    await update.message.reply_text(
        f"❓ *Help — UTME Success Bot*\n\n"
        f"*Commands:*\n"
        f"/start — Main menu\n"
        f"/mock — Start mock exam\n"
        f"/past — Past questions by subject\n"
        f"/study — Study plan\n"
        f"/syllabus — JAMB syllabus\n"
        f"/score — Your scores\n"
        f"/tutor — Ask tutor\n"
        f"/invite — Invite friends\n"
        f"/premium — Upgrade premium\n"
        f"/debug — Databank status\n"
        f"/help — This message\n\n"
        f"*Free plan:*\n"
        f"• Quick 5Q mock — {FREE_MOCK_QS_DAILY}/day\n"
        f"• Tutor — {FREE_TUTOR_PER_DAY}/day\n\n"
        f"*Premium:*\n"
        f"• All mock types unlimited\n"
        f"• Subject Mock (40Q)\n"
        f"• Full JAMB Mock (180Q)\n"
        f"• Unlimited tutor\n\n"
        f"Channel: @{md(CHANNEL_USERNAME)}\n"
        f"Your ID: `{uid}`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))


async def cmd_debug(update, context):
    per_subject = {s: len(LOCAL_DATABANK.get(s, [])) for s in AVAILABLE_SUBJECTS}
    lines = [
        "📊 *Databank Status*",
        f"Total: *{len(ALL_QS)}* questions",
        f"Subjects: *{len(AVAILABLE_SUBJECTS)}*",
        f"Engine: {'✅ loaded' if HAS_ENGINE else '❌ fallback'}",
        "",
    ]
    for s in AVAILABLE_SUBJECTS:
        icon = "✅" if per_subject[s] > 0 else "❌"
        lines.append(f"{icon} {s}: {per_subject[s]}")
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def handle_callback(update, context):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    data = query.data
    u = get_user(uid, query.from_user.first_name or "")

    # ---------- STUDY / SYLLABUS / PAST ----------
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
        if not can_use_mock(uid, 5):
            msg, kb = upgrade_kb(uid)
            await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)
            return
        qs = fetcher.fetch(subj, None, 5)
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

    # ---------- ANSWER HANDLER ----------
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
            
            # Check if free user just finished their daily limit
            finish_msg = f"🎉 *Mock Completed!*\n\nScore: *{score}/{total}* ({percent}%)\n🏆 Leader: {md(leader_name)} — {leader_score}/400"
            
            if not is_premium(uid):
                rem = get_mock_remaining(uid)
                if rem <= 0:
                    finish_msg += f"\n\n🛑 *You have reached your {FREE_MOCK_QS_DAILY} free questions for today.*\nUpgrade to Premium to continue practicing with unlimited questions, Subject Mocks (40 Qs), and Full JAMB Mocks (180 Qs)."
                else:
                    finish_msg += f"\n\n🆓 You have {rem} free questions left today."
                    
            await query.message.reply_text(
                finish_msg,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Another Mock", callback_data="mock_menu")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
            USER_SESSIONS.pop(uid, None)
        return

    # ---------- MOCK MENU ----------
    if data == "mock_menu":
        await query.message.reply_text(
            _mock_menu_text(uid),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(_mock_menu_kb(uid)))
        return

    # ---------- QUICK MOCK (free + premium) ----------
    if data == "mock_quick":
        remaining = get_mock_remaining(uid)
        if remaining <= 0 and not is_premium(uid):
            msg, kb = upgrade_kb(uid)
            await query.message.reply_text(
                f"🛑 *Daily Free Limit Reached*\n\n"
                f"You have completed your {FREE_MOCK_QS_DAILY} free questions for today. "
                f"Upgrade to Premium to unlock unlimited mocks, Subject Mock (40 Qs), "
                f"Full JAMB Mock (180 Qs), and unlimited Tutor access.\n\n{msg}",
                parse_mode="Markdown", reply_markup=kb)
            return

        # Determine how many questions to serve (max 5, or whatever they have left)
        if is_premium(uid):
            limit = 5
        else:
            limit = min(5, remaining)

        pool = AVAILABLE_SUBJECTS or ALL_SUBJECTS
        sample = random.sample(pool, min(3, len(pool)))
        qs = []
        for subj in sample:
            qs.extend(fetcher.fetch(subj, None, 2))
        random.shuffle(qs)
        qs = qs[:limit]
        
        if not qs:
            await query.message.reply_text("⚠️ No questions loaded. Try /debug")
            return
            
        consume_mock(uid, len(qs), [q["id"] for q in qs])
        
        intro_text = f"🚀 *Quick Mock ({len(qs)} Qs)*"
        if not is_premium(uid):
            intro_text += f"\n\n🆓 You have {max(0, remaining - len(qs))} free questions left today."
            
        txt, kb = _start_mock_session(uid, qs, "mixed", intro_text=intro_text)
        await query.message.reply_text(txt, parse_mode="Markdown", reply_markup=kb)
        return

    # ---------- SUBJECT MOCK (PREMIUM ONLY) ----------
    if data == "mock_by_subject":
        if not is_premium(uid):
            msg, kb = upgrade_kb(uid)
            await query.message.reply_text(
                f"🔒 *Subject Mock — Premium Only*\n\n"
                f"Subject Mock gives you *40 questions* from one subject "
                f"of your choice.\n\n{msg}",
                parse_mode="Markdown", reply_markup=kb)
            return
        await query.message.reply_text(
            "📚 *Choose Subject for your 40Q Mock:*",
            reply_markup=subjects_kb("mock_subject"),
            parse_mode="Markdown")
        return

    if data.startswith("mock_subject_"):
        subj = data.replace("mock_subject_", "")
        if not is_premium(uid):
            msg, kb = upgrade_kb(uid)
            await query.message.reply_text(
                f"🔒 *Subject Mock — Premium Only*\n\n"
                f"Upgrade to unlock 40-question subject mocks.\n\n{msg}",
                parse_mode="Markdown", reply_markup=kb)
            return
        qs = fetcher.fetch(subj, None, 40)
        if len(qs) < 5:
            await query.message.reply_text(
                f"⚠️ Not enough questions for "
                f"{SUBJECT_DISPLAY.get(subj, subj)} yet.\n"
                f"Only {len(qs)} available.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="mock_by_subject")],
                    [InlineKeyboardButton("🏠 Main Menu",
                                          callback_data="main_menu")]]))
            return
        display = SUBJECT_DISPLAY.get(subj, subj.title())
        intro = (f"📚 *{display} Subject Mock*\n"
                 f"{len(qs)} questions · Good luck!")
        txt, kb = _start_mock_session(uid, qs, f"subject_{subj}", intro_text=intro)
        await query.message.reply_text(txt, parse_mode="Markdown", reply_markup=kb)
        return

    # ---------- FULL MOCK (PREMIUM ONLY) ----------
    if data == "mock_full":
        if not is_premium(uid):
            msg, kb = upgrade_kb(uid)
            await query.message.reply_text(
                f"🔒 *Full JAMB Mock — Premium Only*\n\n"
                f"Full Mock gives you 180 questions across multiple subjects "
                f"like the real JAMB exam.\n\n{msg}",
                parse_mode="Markdown", reply_markup=kb)
            return
        leader_name, leader_score = get_leading()
        await query.message.reply_text(
            f"🏆 *Leader: {md(leader_name)} — {leader_score}/400*\n\n"
            f"Full Mock 180Q · 2hrs",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Start 180Q", callback_data="mock_full_start")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        return

    if data == "mock_full_start":
        if not is_premium(uid):
            msg, kb = upgrade_kb(uid)
            await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)
            return
        qs = fetcher.fetch("english", None, 60)
        for subj in ["mathematics", "biology", "physics", "chemistry"]:
            if subj in LOCAL_DATABANK:
                qs += fetcher.fetch(subj, None, 40)
        random.shuffle(qs)
        qs = qs[:180]
        if len(qs) < 5:
            qs = fetcher.fetch("english", None, 20)
        if not qs:
            await query.message.reply_text("⚠️ No questions loaded. Try /debug")
            return
        leader_name, leader_score = get_leading()
        intro = (f"🚀 *Full Mock {len(qs)}Q*\n"
                 f"🏆 To beat: {md(leader_name)} — {leader_score}/400")
        txt, kb = _start_mock_session(uid, qs, "full_mock", intro_text=intro)
        await query.message.reply_text(txt, parse_mode="Markdown", reply_markup=kb)
        return

    # ---------- SCORE / TUTOR / PREMIUM / INVITE / HELP ----------
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
            f"💬 *Ask Tutor*\nI know {len(ALL_QS)} Qs + AI brain + Voice 🎙️.\n"
            f"Tutor: {remaining_text}\nAsk anything:",
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
            f"✅ Unlimited mocks\n✅ Subject Mock (40Q)\n✅ Full JAMB Mock (180Q)\n"
            f"✅ Unlimited tutor + Voice 🎙️\n✅ {len(ALL_QS)} Qs",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data == "invite_friends":
        link = f"https://t.me/{BOT_USERNAME}?start=invite_{u['invite_code']}"
        invites = u.get("invites", 0)
        await query.message.reply_text(
            f"👥 *Invite Friends — VIRAL BONUS!*\n\n"
            f"🎁 Invite {REFERRAL_REQUIRED} = {REFERRAL_REWARD_DAYS} days FREE!\n\n"
            f"Your link:\n`{link}`\n\nProgress: {invites}/{REFERRAL_REQUIRED}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 Share Link",
                    url=f"https://t.me/share/url?url={link}&text=Join UTME Success Bot!")],
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

    # Tutor mode
    session = USER_SESSIONS.get(uid, {})
    is_tutor = (session.get("mode") == "tutor" or "?" in text or len(text) > 8)
    if is_tutor:
        if not can_use_tutor(uid):
            msg, kb = upgrade_kb(uid)
            await update.message.reply_text(
                f"⏰ *Tutor Limit Reached*\n\n"
                f"Free: {FREE_TUTOR_PER_DAY} tutor questions/day\n"
                f"Upgrade for unlimited access.\n\n{msg}",
                parse_mode="Markdown", reply_markup=kb)
            return
        consume_tutor(uid)
        relevant = []
        try:
            subj_filter = session.get("subject") or u.get("study_subject")
            relevant = search_databank(text, subject=subj_filter, limit=3)
        except Exception:
            relevant = []
        subj = session.get("subject") or u.get("study_subject") or "general"
        display = SUBJECT_DISPLAY.get(subj, subj.title()) if subj != "general" else "JAMB"

        answer_text = f"💬 *{display} Tutor*\n\n*Q:* {md(text[:400])}\n\n"
        if relevant:
            answer_text += f"*📚 From Databank ({len(relevant)} found):*\n\n"
            for i, rq in enumerate(relevant[:2], 1):
                answer_text += (
                    f"{i}. *{md(rq.get('subject',''))} {md(str(rq.get('year','')))}*\n"
                    f"{md(rq.get('question','')[:180])}...\n"
                    f"✅ Answer: *{md(rq.get('answer',''))}*\n")
                if rq.get("explanation"):
                    answer_text += f"💡 {md(rq.get('explanation')[:180])}...\n"
                answer_text += "\n"
        answer_text += f"*🧠 AI Brain ({display}):*\n\n"
        answer_text += (f"Based on JAMB syllabus for {display}: core concept, "
                        f"steps, example, trap to avoid.\n\n")
        answer_text += "💡 Tip: Appears frequently in UTME."

        await update.message.reply_text(
            answer_text[:4000], parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎙️ Voice", callback_data="ask_tutor")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))

        if HAS_TTS:
            try:
                voice_text = f"Hello! Let's study {display}. Question: {text[:150]}. "
                if relevant:
                    rq = relevant[0]
                    voice_text += (f"From past question: {rq.get('question','')[:100]}. "
                                   f"Answer is {rq.get('answer','')}. ")
                voice_text += "Keep practicing!"
                voice_text = re.sub(r"[*_#`]", "", voice_text)[:600]
                tts = gTTS(text=voice_text, lang="en", tld="com.ng", slow=True)
                vp = f"/tmp/voice_{uid}_{int(time.time())}.mp3"
                tts.save(vp)
                with open(vp, "rb") as f:
                    await update.message.reply_voice(voice=f, caption=f"🎙️ Voice — {display}")
                try:
                    os.remove(vp)
                except Exception:
                    pass
            except Exception as e:
                print(f"TTS error: {e}")
        return

    await update.message.reply_text("Use the menu below 👇", reply_markup=BOTTOM_KEYBOARD)


# ============================================================
# FLASK APP
# ============================================================
flask_app = Flask(__name__)


@flask_app.route("/")
def home():
    return (f"UTME Bot v28 · Monthly {PREMIUM_PRICE_TEXT} · 6mo {PREMIUM_6MONTHS_TEXT} · "
            f"{len(ALL_QS)} Qs across {len(AVAILABLE_SUBJECTS)} subjects · Running")


@flask_app.route("/health")
def health():
    per_subject = {s: len(LOCAL_DATABANK.get(s, [])) for s in AVAILABLE_SUBJECTS}
    return jsonify({
        "status": "ok", "version": "v28",
        "databank": {"total_questions": len(ALL_QS),
                     "available_subjects": AVAILABLE_SUBJECTS,
                     "engine_loaded": HAS_ENGINE,
                     "per_subject": per_subject},
        "pricing": {"monthly": PREMIUM_PRICE_TEXT, "six_months": PREMIUM_6MONTHS_TEXT},
        "free_tier": {"mock_per_day": FREE_MOCK_QS_DAILY,
                      "tutor_per_day": FREE_TUTOR_PER_DAY},
        "gateways": {"flutterwave": bool(FLW_PUBLIC_KEY and FLW_SECRET_KEY)},
        "users": len(USER_DATA),
    })


@flask_app.route("/debug/files")
def debug_files():
    cwd = os.getcwd()
    tree = {}
    for root, dirs, files in os.walk(cwd):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git", ".venv", "venv"}]
        rel = os.path.relpath(root, cwd)
        js = sorted(f for f in files if f.endswith(".json"))
        if js:
            tree[rel] = js
    try:
        import cbt_engine
        found = list(getattr(cbt_engine, "FOUND_FILES", []))
    except Exception:
        found = []
    return jsonify({
        "cwd": cwd,
        "json_files_by_dir": tree,
        "cbt_engine_found_files": found,
        "total_questions": len(ALL_QS),
        "available_subjects": AVAILABLE_SUBJECTS,
    })


UPGRADE_PAGE = r"""
<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Upgrade — UTME Success Bot</title>
<script src="https://checkout.flutterwave.com/v3.js"></script>
<style>
 :root{--bg1:#1e1b4b;--bg2:#4c1d95;--bg3:#7c3aed;--accent:#f59e0b;--accent2:#fbbf24;--success:#10b981;--ink:#0f172a;--muted:#64748b;--card:#fff;--line:#e2e8f0}
 *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
 body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;background:linear-gradient(135deg,var(--bg1) 0%,var(--bg2) 50%,var(--bg3) 100%);background-attachment:fixed;min-height:100vh;color:var(--ink);padding:20px 14px 60px}
 .wrap{max-width:480px;margin:0 auto}
 .hero{text-align:center;color:#fff;margin:10px 0 24px}
 .hero .crown{font-size:52px;line-height:1;filter:drop-shadow(0 4px 12px rgba(245,158,11,.5))}
 .hero h1{margin:8px 0 4px;font-size:26px}
 .hero p{margin:0;opacity:.85;font-size:14px}
 .card{background:var(--card);border-radius:20px;padding:24px 22px;box-shadow:0 20px 50px -12px rgba(0,0,0,.35);margin-bottom:18px}
 .benefits{list-style:none;padding:0;margin:0}
 .benefits li{display:flex;align-items:flex-start;gap:12px;padding:11px 0;font-size:15px;line-height:1.45;border-bottom:1px solid #f1f5f9}
 .benefits li:last-child{border-bottom:0}
 .check{flex:0 0 22px;width:22px;height:22px;border-radius:50%;background:linear-gradient(135deg,var(--success),#059669);color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;margin-top:1px}
 .badge{display:inline-block;background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;font-size:11px;font-weight:700;padding:4px 10px;border-radius:20px;letter-spacing:.4px;text-transform:uppercase}
 .plan{border:2px solid var(--line);border-radius:16px;padding:20px 18px;margin-bottom:14px;position:relative}
 .plan.best{border-color:var(--accent);background:linear-gradient(180deg,#fffbeb,#fff)}
 .plan.best::before{content:"⭐ BEST VALUE";position:absolute;top:-10px;left:50%;transform:translateX(-50%);background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff;font-size:10px;font-weight:800;padding:5px 12px;border-radius:20px;letter-spacing:.6px;box-shadow:0 4px 10px rgba(245,158,11,.35)}
 .plan-head{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px}
 .plan-name{font-size:17px;font-weight:700}
 .plan-price{font-size:26px;font-weight:800;color:var(--bg3)}
 .plan-sub{font-size:13px;color:var(--muted);margin-bottom:14px}
 .plan-sub s{color:#cbd5e1;margin-right:6px}
 .pay{display:block;width:100%;padding:15px 20px;border:none;border-radius:12px;font-size:16px;font-weight:700;color:#fff;cursor:pointer;background:linear-gradient(135deg,var(--bg3),var(--bg2));box-shadow:0 8px 20px -6px rgba(124,58,237,.6)}
 .plan.best .pay{background:linear-gradient(135deg,var(--accent),#d97706);box-shadow:0 8px 20px -6px rgba(245,158,11,.6)}
 .pay:active{transform:translateY(2px)}
 .pay[disabled]{opacity:.5;cursor:not-allowed;box-shadow:none}
 .alt{text-align:center;margin-top:6px;padding-top:18px;border-top:1px dashed var(--line)}
 .alt-title{font-size:13px;color:var(--muted);margin-bottom:10px}
 .btn-alt{display:block;padding:14px 20px;border-radius:12px;text-decoration:none;font-weight:700;color:#fff;font-size:15px;background:linear-gradient(135deg,var(--success),#059669);box-shadow:0 8px 20px -6px rgba(16,185,129,.5)}
 .trust{text-align:center;font-size:11.5px;color:rgba(255,255,255,.7);margin-top:20px;line-height:1.7}
 .trust a{color:rgba(255,255,255,.9);text-decoration:underline}
 .user-badge{text-align:center;color:#fff;font-size:12px;opacity:.75;margin-bottom:16px;font-family:monospace;background:rgba(0,0,0,.2);padding:6px 14px;border-radius:20px;display:inline-block}
 .user-wrap{text-align:center;margin-bottom:6px}
 .alert{background:#fef2f2;color:#991b1b;padding:12px 16px;border-radius:12px;font-size:13px;border-left:4px solid #dc2626;margin-bottom:16px;line-height:1.5}
</style></head>
<body><div class="wrap">
 <div class="hero"><div class="crown">👑</div><h1>Upgrade to Premium</h1><p>Unlock everything. Score higher in UTME.</p></div>
 {% if not gateway_ready %}<div class="alert">⚠️ Payment gateway not configured yet.</div>{% endif %}
 <div class="user-wrap"><span class="user-badge">User ID: {{ uid }}</span></div>
 <div class="card"><div style="display:flex;align-items:center;gap:10px;margin-bottom:6px"><span class="badge">PREMIUM BENEFITS</span></div>
 <ul class="benefits">
  <li><span class="check">✓</span><div><b>Unlimited Quick mocks</b> — no daily limits</div></li>
  <li><span class="check">✓</span><div><b>Subject Mock</b> — 40 questions from any single subject</div></li>
  <li><span class="check">✓</span><div><b>Full JAMB Mock</b> — 180 questions, real exam simulation</div></li>
  <li><span class="check">✓</span><div><b>Unlimited AI Tutor</b> — any subject, any time</div></li>
  <li><span class="check">✓</span><div><b>Voice explanations 🎙️</b></div></li>
  <li><span class="check">✓</span><div><b>{{ total_qs }}+ past questions</b> — full databank</div></li>
  <li><span class="check">✓</span><div><b>Leaderboard &amp; score tracking</b></div></li>
 </ul></div>
 <div class="card"><div style="text-align:center;margin-bottom:14px"><div class="badge">CHOOSE YOUR PLAN</div></div>
  <div class="plan"><div class="plan-head"><span class="plan-name">Monthly</span><span class="plan-price">{{ monthly_price_text }}</span></div>
   <div class="plan-sub">{{ monthly_days }} days of full access</div>
   <button class="pay" onclick="payNow('monthly', {{ monthly_price }})" {% if not gateway_ready %}disabled{% endif %}>💳 Pay {{ monthly_price_text }} — Monthly</button></div>
  <div class="plan best"><div class="plan-head"><span class="plan-name">6 Months</span><span class="plan-price">{{ six_months_text }}</span></div>
   <div class="plan-sub"><s>{{ monthly_price_text }} × 6</s> <b style="color:#d97706">Save {{ savings_text }}!</b> · {{ six_months_days }} days</div>
   <button class="pay" onclick="payNow('6months', {{ six_months_price }})" {% if not gateway_ready %}disabled{% endif %}>💳 Pay {{ six_months_text }} — Save {{ savings_text }}</button></div>
 </div>
 <div class="card"><div class="alt"><div class="alt-title">💚 Invite {{ referral_required }} friends → <b>{{ referral_reward_days }} days FREE</b></div>
  <a class="btn-alt" href="{{ invite_link }}">👥 Invite {{ referral_required }} Friends — Get {{ referral_reward_days }} Days FREE</a></div></div>
 <div class="trust">🔒 Secured by Flutterwave · <a href="https://t.me/{{ bot_username }}">Return to Bot</a></div>
</div>
<script>
const UID="{{ uid }}"; const BOT="{{ bot_username }}"; const FLW_PK="{{ flw_public_key }}"; const API=window.location.origin;
function payNow(planKey, amount){
 if(!FLW_PK){alert("Payment gateway not configured.");return;}
 const txRef="UTME-"+UID+"-"+Date.now();
 FlutterwaveCheckout({
  public_key:FLW_PK, tx_ref:txRef, amount:amount, currency:"NGN",
  payment_options:"card,banktransfer,ussd,account",
  customer:{email:"user"+UID+"@utmebot.com", name:"UTME User "+UID},
  customizations:{title:"UTME Success Bot Premium", description:planKey==="6months"?"6 Months Premium":"Monthly Premium"},
  meta:{user_id:UID, plan:planKey},
  callback:function(resp){
   fetch(API+"/verify/flutterwave",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({transaction_id:resp.transaction_id,tx_ref:resp.tx_ref,expected_uid:UID,plan:planKey})})
   .then(r=>r.json()).then(res=>{
    if(res.status==="success"){alert("✅ Premium activated!");window.location.href="https://t.me/"+BOT;}
    else if(res.status==="duplicate_or_invalid"){alert("ℹ️ Already processed.");window.location.href="https://t.me/"+BOT;}
    else{alert("⚠️ Received. Message bot with ID: "+UID);window.location.href="https://t.me/"+BOT;}
   }).catch(()=>{alert("⚠️ Network error.");window.location.href="https://t.me/"+BOT;});
  }
 });
}
</script></body></html>
"""


@flask_app.route("/upgrade/<uid>")
def upgrade_page(uid):
    monthly = _resolve_plan("monthly")
    six = _resolve_plan("6months")
    savings = PREMIUM_PRICE * 6 - PREMIUM_6MONTHS_PRICE
    savings_text = f"\u20a6{savings}" if savings > 0 else ""
    invite_link = f"https://t.me/{BOT_USERNAME}?start=invite_{uid}"
    gateway_ready = bool(FLW_PUBLIC_KEY and FLW_SECRET_KEY)
    return render_template_string(
        UPGRADE_PAGE, uid=uid, bot_username=BOT_USERNAME,
        flw_public_key=FLW_PUBLIC_KEY, gateway_ready=gateway_ready,
        total_qs=len(ALL_QS),
        monthly_price=monthly["price"], monthly_price_text=monthly["price_text"],
        monthly_days=monthly["days"], six_months_price=six["price"],
        six_months_text=six["price_text"], six_months_days=six["days"],
        savings_text=savings_text, referral_required=REFERRAL_REQUIRED,
        referral_reward_days=REFERRAL_REWARD_DAYS, invite_link=invite_link,
    )


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


def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT, threaded=True)


# ============================================================
# CHANNEL AUTO-POSTING
# ============================================================
async def channel_posting_job(app):
    posted_today = set()
    while True:
        try:
            now = datetime.now()
            lagos_hour = (now.hour + 1) % 24
            key = f"{now.date()}_{lagos_hour}"
            if lagos_hour in (8, 13, 20) and key not in posted_today:
                if not CHANNEL_ID:
                    await asyncio.sleep(3600)
                    continue
                try:
                    q = get_random_question()
                    if not q:
                        await asyncio.sleep(3600)
                        continue
                    intro = random.choice([
                        "🌅 *Good Morning Champions!*",
                        "☀️ *Rise and Shine!*",
                        "🌙 *Evening Practice!*"])
                    msg = (f"{intro}\n\n"
                           f"*{md(q.get('subject','JAMB'))} | {md(str(q.get('year','')))}*\n\n"
                           f"{md(q.get('question','')[:320])}\n\n"
                           f"A) {md(q.get('option_a','')[:70])}\n"
                           f"B) {md(q.get('option_b','')[:70])}\n"
                           f"C) {md(q.get('option_c','')[:70])}\n"
                           f"D) {md(q.get('option_d','')[:70])}\n\n"
                           f"👉 https://t.me/{BOT_USERNAME}")
                    await app.bot.send_message(chat_id=CHANNEL_ID, text=msg, parse_mode="Markdown")
                    posted_today.add(key)
                    if len(posted_today) > 10:
                        posted_today.clear()
                except Exception as e:
                    print(f"Channel error: {e}")
            await asyncio.sleep(1800)
        except Exception as e:
            print(f"Channel job error: {e}")
            await asyncio.sleep(3600)


async def post_init(app):
    try:
        commands = [
            BotCommand("start", "🏠 Main Menu"),
            BotCommand("mock", "📝 Start Mock Exam"),
            BotCommand("past", "📚 Past Questions"),
            BotCommand("study", "📖 Study Plan"),
            BotCommand("syllabus", "📋 JAMB Syllabus"),
            BotCommand("score", "📊 My Score"),
            BotCommand("tutor", "💬 Ask Tutor"),
            BotCommand("invite", "👥 Invite Friends"),
            BotCommand("premium", "💎 Upgrade Premium"),
            BotCommand("debug", "🔍 Databank Status"),
            BotCommand("help", "❓ Help"),
        ]
        await app.bot.set_my_commands(commands)
        await app.bot.set_chat_menu_button(
            menu_button=MenuButtonCommands(text="📋 Menu"))
        print("✅ Bot commands registered")
        asyncio.create_task(channel_posting_job(app))
    except Exception as e:
        print(f"Menu setup failed: {e}")


# ============================================================
# MAIN
# ============================================================
def main():
    load_data()
    load_processed_tx()

    threading.Thread(target=run_flask, daemon=True).start()
    print(f"🌐 Flask on port {PORT}")
    print(f"📚 Loaded: {len(ALL_QS)} questions | {len(AVAILABLE_SUBJECTS)} subjects")
    for s in AVAILABLE_SUBJECTS:
        print(f"   {s}: {len(LOCAL_DATABANK.get(s, []))}")

    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or len(BOT_TOKEN) < 20:
        print("❌ BOT_TOKEN not set!")
        while True:
            time.sleep(60)

    try:
        app = ApplicationBuilder().token(BOT_TOKEN).build()

        app.add_handler(CommandHandler("start",    cmd_start))
        app.add_handler(CommandHandler("menu",     cmd_start))
        app.add_handler(CommandHandler("mock",     cmd_mock))
        app.add_handler(CommandHandler("past",     cmd_past))
        app.add_handler(CommandHandler("questions", cmd_past))
        app.add_handler(CommandHandler("study",    cmd_study))
        app.add_handler(CommandHandler("syllabus", cmd_syllabus))
        app.add_handler(CommandHandler("score",    cmd_score))
        app.add_handler(CommandHandler("tutor",    cmd_tutor))
        app.add_handler(CommandHandler("ask",      cmd_tutor))
        app.add_handler(CommandHandler("invite",   cmd_invite))
        app.add_handler(CommandHandler("premium",  cmd_premium))
        app.add_handler(CommandHandler("debug",    cmd_debug))
        app.add_handler(CommandHandler("help",     cmd_help))

        app.add_handler(CallbackQueryHandler(handle_callback))
        app.add_handler(MessageHandler(
            filters.Regex("^(📚 Past Questions|📝 Mock Exam|📊 My Score|💬 Ask Tutor|"
                          "💎 Premium|👥 Invite Friends|📖 Study Plan|🔵 MENU|MENU|/mock|mock)$"),
            handle_msg))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))

        app.post_init = post_init
        print(f"✅ Bot v28 running | {len(ALL_QS)} Qs | {len(AVAILABLE_SUBJECTS)} subjects")
        app.run_polling()
    except Exception as e:
        print(f"❌ Bot failed: {e}")
        traceback.print_exc()
        while True:
            time.sleep(60)


if __name__ == "__main__":
    main()
