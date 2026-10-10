"""
UTME Success Bot v36 — Join Channel Button + Two-Step AI Why + All Features
- 📢 Join Our Channel button everywhere
- Real exam mode (no answer reveal during mock)
- 2-step Ask AI Why: recap → full AI explanation
- 3 free AI Why/day for free users, 4th locked
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
        FREE_TUTOR_PER_DAY,
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

# ⭐ CHANNEL INVITE LINK
CHANNEL_INVITE_LINK = "https://t.me/+Qw3DqGwCSM4wMDk0"

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

PLAN_SIZE = 4
FREE_ENGLISH_QS = 40
FREE_AI_WHY_PER_DAY = 3

# ══════════════════════════════════════════════════════════
# NIGERIAN DATA
# ══════════════════════════════════════════════════════════
NIGERIAN_STATES = [
    "Delta", "Edo", "Lagos", "Ondo", "Anambra", "Oyo", "Kano",
    "Rivers", "Kaduna", "Enugu", "Imo", "Abia", "Akwa Ibom",
    "Cross River", "Plateau", "Benue", "Kogi", "Kwara", "Osun",
    "Ekiti", "Ogun", "Bayelsa", "Ebonyi", "Nasarawa", "Niger",
    "Sokoto", "Kebbi", "Zamfara", "Yobe", "Borno", "Adamawa",
    "Taraba", "Gombe", "Jigawa", "Katsina", "Bauchi",
]

NIGERIAN_CITIES = [
    "Warri", "Lagos", "Benin", "Enugu", "Kano", "Ibadan", "Port Harcourt",
    "Kaduna", "Aba", "Jos", "Uyo", "Owerri", "Maiduguri", "Abeokuta",
    "Akure", "Sokoto", "Calabar", "Asaba", "Makurdi", "Bauchi",
]

NIGERIAN_NAMES = [
    "Chinedu O.", "Amina B.", "Tunde A.", "Ngozi E.", "Emeka N.",
    "Fatima Y.", "Blessing I.", "Yusuf M.", "Chioma U.", "Segun F.",
    "Aisha K.", "Kelechi A.", "Ifeoma O.", "Ibrahim S.", "Adaeze M.",
    "Oluwaseun T.", "Halima G.", "Nkem C.", "Bolanle A.", "Uche O.",
    "Zainab M.", "Obinna E.", "Folake B.", "Bashir A.", "Ebere N.",
    "Yemi O.", "Hauwa A.", "Chidi N.", "Funmi D.", "Mustapha K.",
]

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
        analyze_failure as _analyze_failure,
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
    def _analyze_failure(q, ua, ca, t=""):
        return "⚠️ Trap Detector not available."
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


# ══════════════════════════════════════════════════════════
# OPTION SHUFFLER
# ══════════════════════════════════════════════════════════
def _shuffle_options(q):
    if not isinstance(q, dict):
        return q
    opts = [
        q.get("option_a", "") or "",
        q.get("option_b", "") or "",
        q.get("option_c", "") or "",
        q.get("option_d", "") or "",
    ]
    valid_pairs = [(chr(65 + i), opts[i]) for i in range(4) if str(opts[i]).strip()]
    if len(valid_pairs) < 2:
        return q
    orig_ans = str(q.get("answer", "") or "").upper().strip()[:1]
    answer_text = None
    for letter, text in valid_pairs:
        if letter == orig_ans:
            answer_text = text
            break
    if not answer_text:
        ans_txt_alt = str(q.get("answer_text", "") or "").strip()
        if ans_txt_alt:
            for letter, text in valid_pairs:
                if text.strip() == ans_txt_alt:
                    answer_text = text
                    break
    if not answer_text:
        return q
    random.shuffle(valid_pairs)
    new_q = dict(q)
    new_letters = ["A", "B", "C", "D"]
    new_answer = orig_ans
    for i, (old_letter, text) in enumerate(valid_pairs):
        new_q[f"option_{new_letters[i].lower()}"] = text
        if text == answer_text:
            new_answer = new_letters[i]
    for j in range(len(valid_pairs), 4):
        new_q[f"option_{new_letters[j].lower()}"] = ""
    new_q["answer"] = new_answer
    return new_q


def _prepare_questions(qs):
    return [_shuffle_options(q) for q in qs]


def _make_failure_snapshot(q, user_ans, correct_ans, q_num):
    return {
        "q_num": int(q_num),
        "question": str(q.get("question", "") or "")[:300],
        "option_a": str(q.get("option_a", "") or "")[:200],
        "option_b": str(q.get("option_b", "") or "")[:200],
        "option_c": str(q.get("option_c", "") or "")[:200],
        "option_d": str(q.get("option_d", "") or "")[:200],
        "user_ans": str(user_ans or "")[:1],
        "correct_ans": str(correct_ans or "")[:1],
        "topic": str(q.get("topic", "General") or "General")[:60],
    }


def _fetch_rotated(uid, subject, limit):
    u = get_user(uid)
    used = set(str(x) for x in u.get("used_ids", []))
    pool = LOCAL_DATABANK.get(subject, [])
    if not pool:
        return []
    unused = [q for q in pool if str(q.get("id", "")) not in used]
    used_qs = [q for q in pool if str(q.get("id", "")) in used]
    random.shuffle(unused)
    random.shuffle(used_qs)
    combined = unused + used_qs
    selected = combined[:limit]
    new_ids = [str(q.get("id", "")) for q in selected if q.get("id")]
    if new_ids:
        u["used_ids"] = (u.get("used_ids", []) + new_ids)[-5000:]
        save_data()
    return selected


def _fetch_rotated_multi(uid, subjects, total):
    u = get_user(uid)
    used = set(str(x) for x in u.get("used_ids", []))
    n = len(subjects)
    if n == 0:
        return []
    per_subject = total // n
    remainder = total % n
    picked = []
    picked_ids = []
    for i, subj in enumerate(subjects):
        pool = LOCAL_DATABANK.get(subj, [])
        if not pool:
            continue
        need = per_subject + (1 if i < remainder else 0)
        unused = [q for q in pool if str(q.get("id", "")) not in used]
        used_qs = [q for q in pool if str(q.get("id", "")) in used]
        random.shuffle(unused)
        random.shuffle(used_qs)
        selected = (unused + used_qs)[:need]
        picked.extend(selected)
        picked_ids.extend(str(q.get("id", "")) for q in selected if q.get("id"))
    random.shuffle(picked)
    picked = picked[:total]
    if picked_ids:
        u["used_ids"] = (u.get("used_ids", []) + picked_ids)[-5000:]
        save_data()
    return picked


def _get_user_state(uid):
    seed_str = f"{uid}_{date.today().isoformat()}_state"
    h = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    return NIGERIAN_STATES[h % len(NIGERIAN_STATES)]


def _get_user_rank_number(uid, user_score, total):
    seed_str = f"{uid}_{date.today().isoformat()}_rank"
    h = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    if user_score >= 35:
        return (h % 15) + 1
    elif user_score >= 25:
        return (h % 40) + 15
    elif user_score >= 15:
        return (h % 80) + 40
    else:
        return (h % 100) + 80


def _generate_rank(uid, subject_display, user_score, total):
    state = _get_user_state(uid)
    seed_str = f"{uid}_{subject_display}_{date.today().isoformat()}"
    seed_int = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % (2**32)
    rng = random.Random(seed_int)
    names = rng.sample(NIGERIAN_NAMES, 5)
    min_score = 35
    max_score = max(min_score, total)
    if total < min_score:
        min_score = max(1, total - 5)
        max_score = total
    scores = [rng.randint(min_score, max_score) for _ in range(5)]
    scores.sort(reverse=True)
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    lines = [f"🏆 *{state} State Ranking — {subject_display} Mock*\n"]
    for i, (n, s) in enumerate(zip(names, scores)):
        lines.append(f"{medals[i]} {md(n)} — *{s}/{total}*")
    user_rank = _get_user_rank_number(uid, user_score, total)
    lines.append(f"\n📊 *Your Score:* *{user_score}/{total}*")
    lines.append(f"🎯 *Your Rank:* *#{user_rank}* in {state} State")
    lines.append(f"\n_Simulated based on state benchmarks. Keep practising to climb the ranks!_")
    return "\n".join(lines)


def _social_proof_line(uid, prev_score, total):
    seed_str = f"{uid}_{date.today().isoformat()}_sp"
    rng = random.Random(seed_str)
    name = rng.choice(NIGERIAN_NAMES).split()[0]
    city = rng.choice(NIGERIAN_CITIES)
    new_score = min(total, prev_score + rng.randint(6, 12))
    return f"→ *{name}* from {city}: Now scoring *{new_score}/{total}*"


def _build_completion_message(uid, score, total, failed, subject_label, subj_display):
    n_failed = len(failed)
    header = f"🎉 *Mock Completed!* You scored *{score}/{total}*\n"

    if n_failed == 0:
        state = _get_user_state(uid)
        rank = _get_user_rank_number(uid, score, total)
        return (
            f"{header}\n"
            f"🎯 *Perfect score!* You got everything right.\n\n"
            f"🏆 You're currently ranked *#{rank}* in *{state} State*.\n\n"
            f"Keep the momentum going! 🚀",
            True
        )

    topic_losses = {}
    for f in failed:
        t = f.get("topic", "General") or "General"
        topic_losses[t] = topic_losses.get(t, 0) + 1
    sorted_t = sorted(topic_losses.items(), key=lambda x: -x[1])

    loss_lines = []
    for t, c in sorted_t[:5]:
        loss_lines.append(f"  • *{md(t)}* — {c} mark{'s' if c > 1 else ''} LOST")

    marks_line = (
        f"\n❌ *You lost {n_failed} mark{'s' if n_failed > 1 else ''} from:*\n"
        + "\n".join(loss_lines)
    )
    fear_line = (
        f"\n\n⚠️ *In JAMB, {n_failed} mark{'s' if n_failed > 1 else ''} = "
        f"You will lose admission to your dream course.*"
    )
    social_line = (
        f"\n\n*Your mates who scored {score} yesterday fixed it today:*\n"
        f"{_social_proof_line(uid, score, total)}"
    )
    msg = header + marks_line + fear_line + social_line
    return msg, False


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
        [KeyboardButton("📢 Join Our Channel")],
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
    except Exception as e:
        print(f"[save_data] ⚠️ failed to write: {e}")


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
            "tutor_counts": {}, "used_ids": [],
            "is_premium": False, "premium_until": None, "premium_plan": None,
            "joined": str(date.today()), "history": [],
            "invite_code": hashlib.md5(uid.encode()).hexdigest()[:6].upper(),
            "invited_by": None, "invites": 0, "invited_users": [],
            "username": username or f"User{uid[-4:]}", "study_subject": None,
            "jamb_plan": ["english"],
            "plan_set": False,
            "free_english_used": False,
            "ai_why_counts": {},
            "last_mock_failed": [],
            "last_mock_subject": None,
            "last_mock_total": 40,
        }
        save_data()
    u = USER_DATA[uid]
    if username:
        u["username"] = username
    u.setdefault("jamb_plan", ["english"])
    u.setdefault("plan_set", False)
    u.setdefault("free_english_used", False)
    u.setdefault("used_ids", [])
    u.setdefault("ai_why_counts", {})
    u.setdefault("last_mock_failed", [])
    u.setdefault("last_mock_subject", None)
    u.setdefault("last_mock_total", 40)
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


def can_use_ai_why(uid):
    if is_premium(uid):
        return True, 999
    u = get_user(uid)
    today = str(date.today())
    used = u.get("ai_why_counts", {}).get(today, 0)
    remaining = max(0, FREE_AI_WHY_PER_DAY - used)
    return remaining > 0, remaining


def consume_ai_why(uid):
    u = get_user(uid)
    today = str(date.today())
    u.setdefault("ai_why_counts", {})
    u["ai_why_counts"][today] = u["ai_why_counts"].get(today, 0) + 1
    save_data()


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
        f"💎 *Unlock Premium for:*\n"
        f"• ♾️ Unlimited mocks on all your subjects\n"
        f"• 📚 Subject Mock (40 Qs per subject)\n"
        f"• 🔥 Full JAMB CBT Mock (180 Qs · 4 Subjects)\n"
        f"• 💬 Unlimited {TUTOR_NAME} + 🎙️ Voice\n"
        f"• 🎯 Unlimited AI Why analysis on failed questions\n\n"
        f"*Plans:*\n"
        f"• Monthly — {PREMIUM_PRICE_TEXT} / {PREMIUM_DAYS} days\n"
        f"• 6 Months — {PREMIUM_6MONTHS_TEXT} / {PREMIUM_6MONTHS_DAYS} days\n\n"
        f"👉 Choose your plan below to unlock everything!"
    )
    kb = plan_buttons(uid)
    kb.append([InlineKeyboardButton(f"👥 Invite {REFERRAL_REQUIRED}=FREE",
                                    callback_data="invite_friends")])
    kb.append([InlineKeyboardButton("📢 Join Our Channel",
                                    url=CHANNEL_INVITE_LINK)])
    kb.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return msg, InlineKeyboardMarkup(kb)


def ai_why_limit_kb(uid):
    msg = (
        f"🔒 *Free AI Why limit reached*\n\n"
        f"You've used your *{FREE_AI_WHY_PER_DAY} free AI Why analyses* today.\n\n"
        f"💎 *Unlock Premium* ({PREMIUM_PRICE_TEXT}) to get:\n"
        f"• ♾️ *Unlimited* AI Why analyses\n"
        f"• 🎯 JAMB Trap Detector on every failed question\n"
        f"• ♾️ Unlimited mocks on all subjects\n"
        f"• 🔥 Full 180Q JAMB CBT Mock\n"
        f"• 🎙️ Voice explanations from {TUTOR_NAME}\n\n"
        f"👉 *Pay {PREMIUM_PRICE_TEXT} now to continue.*"
    )
    kb = plan_buttons(uid)
    kb.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return msg, InlineKeyboardMarkup(kb)


def main_menu_text_kb(uid):
    u = get_user(uid)
    plan = u.get("jamb_plan", ["english"])
    plan_str = " • ".join(SUBJECT_DISPLAY.get(s, s.title()) for s in plan)

    if is_premium(uid):
        status_badge = "💎 *PREMIUM MEMBER*"
        status_line = "✨ _Unlimited access on all subjects_"
    else:
        status_badge = "🆓 *FREE ACCOUNT*"
        if not u.get("free_english_used", False):
            status_line = "🎁 _1 free English mock available_"
        else:
            status_line = "🔒 _Upgrade to unlock more mocks_"

    leader_name, leader_score = get_leading()
    total_users = len(USER_DATA)
    _, ai_remaining = can_use_ai_why(uid) if not is_premium(uid) else (True, 999)
    ai_str = "♾️ Unlimited" if is_premium(uid) else f"{ai_remaining}/{FREE_AI_WHY_PER_DAY} today"
    qs_str = f"{len(ALL_QS):,}"

    text = (
        f"╔══════════════════════════╗\n"
        f"     🎓  *UTME SUCCESS BOT*  🎓\n"
        f"╚══════════════════════════╝\n\n"
        f"👋 *Welcome back, Champion!*\n"
        f"_{status_line}_\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋  *YOUR JAMB PLAN*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 {plan_str}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊  *YOUR STATS*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  {status_badge}\n"
        f"  🤖 AI Tutor:  `{ai_str}`\n"
        f"  👥 Students:  `{total_users:,}`\n"
        f"  📚 Questions:  `{qs_str}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆  *TOP PERFORMER*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  🥇  {md(leader_name)}\n"
        f"  🎯  *{leader_score}/400*\n\n"
        f"💡 _Tap any button below to begin._"
    )

    kb = [
        [InlineKeyboardButton("🎯  Start Mock from My Plan",
                              callback_data="start_plan_mock")],
        [InlineKeyboardButton("📚  Past Questions", callback_data="past_by_subject"),
         InlineKeyboardButton("📝  Mock Menu",      callback_data="mock_menu")],
        [InlineKeyboardButton("📖  Study Plan",     callback_data="study_plan"),
         InlineKeyboardButton("📋  Syllabus",       callback_data="syllabus")],
        [InlineKeyboardButton("📊  My Score",       callback_data="my_score"),
         InlineKeyboardButton("💬  Ask AI Tutor",   callback_data="ask_tutor")],
        [InlineKeyboardButton(
            f"👥  Invite {REFERRAL_REQUIRED} = {REFERRAL_REWARD_DAYS} Days FREE",
            callback_data="invite_friends")],
        [InlineKeyboardButton("📢  Join Our Channel", url=CHANNEL_INVITE_LINK)],
        [InlineKeyboardButton("💎  Upgrade to Premium",
                              callback_data="premium_info"),
         InlineKeyboardButton("❓  Help", callback_data="help_menu")],
        [InlineKeyboardButton("✏️  Change My Plan", callback_data="plan_builder")],
    ]
    if ADMIN_ID and str(uid) == str(ADMIN_ID):
        kb.append([InlineKeyboardButton("⚙️  Admin Panel",
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
    buttons.append([InlineKeyboardButton("📢 Join Our Channel",
                                         url=CHANNEL_INVITE_LINK)])
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
    qs = _prepare_questions(qs)
    USER_SESSIONS[uid] = {
        "mode": "mock",
        "qs": qs,
        "idx": 0,
        "score": 0,
        "subject": subject_label,
        "failed": [],
    }
    q = qs[0]
    txt = (intro_text + "\n\n" if intro_text else "") + format_question(q, 1, len(qs))
    return txt, _answer_keyboard(q)


PLAN_OPTIONAL_SUBJECTS = [
    "mathematics", "biology", "physics", "chemistry",
    "economics", "government", "commerce", "accounting",
    "literature", "crk",
]


def _plan_builder_text(uid):
    u = get_user(uid)
    plan = u.get("jamb_plan", ["english"])
    others = [s for s in plan if s != "english"]
    n = len(others)
    filled = n + 1
    bar = "▰" * filled + "▱" * (PLAN_SIZE - filled)

    text = (
        f"╔══════════════════════════╗\n"
        f"    🔥  *WELCOME TO UTME*  🔥\n"
        f"         *SUCCESS BOT*\n"
        f"╚══════════════════════════╝\n\n"
        f"🎓 _Nigeria's smartest JAMB practice bot._\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨  *WHY STUDENTS LOVE US*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  📚  *{len(ALL_QS):,}+* past questions\n"
        f"  🤖  *AI Tutor* (Mr. Ellams) with voice 🎙️\n"
        f"  🎯  *Real exam mode* — no answer hints\n"
        f"  📊  *State rankings* to test your level\n"
        f"  🆓  *1 free English mock* for new students\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋  *BUILD YOUR JAMB PLAN*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"_Pick 3 more subjects. English is compulsory._\n\n"
        f"  `{bar}`  *{filled}/{PLAN_SIZE}*\n\n"
        f"  1️⃣  📖 English  ✅ _(compulsory)_\n\n"
    )
    for i, s in enumerate(PLAN_OPTIONAL_SUBJECTS, 2):
        icon = "✅" if s in plan else "⬜"
        text += f"  {i}️⃣  {SUBJECT_DISPLAY.get(s, s.title())}  {icon}\n"

    if plan:
        text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        text += "📌  *YOUR SELECTED PLAN*\n"
        text += "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, s in enumerate(plan, 1):
            text += f"  {i}.  {SUBJECT_DISPLAY.get(s, s.title())}\n"

    if filled == PLAN_SIZE:
        text += (
            f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅  *READY TO START!*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"_Tap 🚀 Start Mock below to begin._\n"
            f"💡 _Your first mock is FREE._\n\n"
            f"📢 _Follow our channel for daily JAMB questions!_"
        )
    else:
        remaining = PLAN_SIZE - filled
        text += (
            f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⬜  Select *{remaining}* more subject"
            f"{'s' if remaining > 1 else ''} to continue.\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    return text


def _plan_builder_kb(uid):
    u = get_user(uid)
    plan = u.get("jamb_plan", ["english"])
    buttons = []
    row = []
    for subj in PLAN_OPTIONAL_SUBJECTS:
        icon = "✅" if subj in plan else "⬜"
        row.append(InlineKeyboardButton(
            f"{icon} {SUBJECT_DISPLAY.get(subj, subj.title())}",
            callback_data=f"plan_toggle_{subj}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    if len(plan) == PLAN_SIZE:
        buttons.append([InlineKeyboardButton("🚀 Start Mock",
                                             callback_data="plan_start")])
    if len(plan) > 1:
        buttons.append([InlineKeyboardButton("🗑️ Reset Plan",
                                             callback_data="plan_reset")])
    buttons.append([InlineKeyboardButton("📢 Join Our Channel",
                                         url=CHANNEL_INVITE_LINK)])
    buttons.append([InlineKeyboardButton("🏠 Main Menu",
                                         callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def can_take_subject(uid, subject) -> tuple:
    if is_premium(uid):
        return True, "premium"
    u = get_user(uid)
    if subject == "english":
        if not u.get("free_english_used", False):
            return True, "free_english"
        return False, "english_used"
    return False, "premium_only"


def _mock_menu_kb(uid):
    u = get_user(uid)
    kb = []
    if is_premium(uid):
        kb.append([InlineKeyboardButton("🎯 Start Mock from My Plan",
                                        callback_data="start_plan_mock")])
        kb.append([InlineKeyboardButton("📚 Subject Mock (40 Qs)",
                                        callback_data="mock_by_subject")])
        kb.append([InlineKeyboardButton("🔥 Full JAMB CBT Mock (180 Qs)",
                                        callback_data="mock_full")])
        kb.append([InlineKeyboardButton("📢 Join Our Channel",
                                        url=CHANNEL_INVITE_LINK)])
        kb.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
        return kb
    if not u.get("free_english_used", False):
        kb.append([InlineKeyboardButton("🆓 Free English Mock (40 Qs) — One-time",
                                        callback_data="start_free_english")])
    else:
        kb.append([InlineKeyboardButton("🛑 Free English Mock — Already Used",
                                        callback_data="premium_info")])
    kb.append([InlineKeyboardButton("🔒 Subject Mocks — Upgrade",
                                    callback_data="premium_info")])
    kb.append([InlineKeyboardButton("🔒 Full CBT Mock — Upgrade",
                                    callback_data="premium_info")])
    kb.append([InlineKeyboardButton("💎 Upgrade Now",
                                    callback_data="premium_info")])
    kb.append([InlineKeyboardButton("📢 Join Our Channel",
                                    url=CHANNEL_INVITE_LINK)])
    kb.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return kb


def _mock_menu_text(uid):
    u = get_user(uid)
    if is_premium(uid):
        leader_name, leader_score = get_leading()
        return (
            f"📝 *Mock Exam Menu*\n"
            f"💎 Premium — Full Access\n"
            f"🏆 Top: {md(leader_name)} — {leader_score}/400\n\n"
            f"Choose mock type:"
        )
    if not u.get("free_english_used", False):
        return (
            f"📝 *Mock Exam Menu*\n\n"
            f"🆓 *Free Plan:* 1 × 40Q English Mock\n\n"
            f"After your free English mock, all other subjects "
            f"require Premium.\n\n"
            f"💎 Upgrade for unlimited access!"
        )
    return (
        f"📝 *Mock Exam Menu*\n\n"
        f"🛑 *You've used your free English mock.*\n\n"
        f"🔒 *Upgrade to Premium for:*\n"
        f"✅ Unlimited English Mocks\n"
        f"✅ All subjects in your JAMB plan\n"
        f"✅ Full 180Q CBT Mock\n"
        f"✅ Unlimited AI Why analysis\n\n"
        f"💎 Tap Upgrade below!"
    )


def _admin_only(uid) -> bool:
    return ADMIN_ID and str(uid) == str(ADMIN_ID)


def _admin_menu_text():
    total_users = len(USER_DATA)
    premium_users = sum(1 for u in USER_DATA.values() if u.get("is_premium"))
    free_users = total_users - premium_users
    plans_set = sum(1 for u in USER_DATA.values() if u.get("plan_set"))
    return (
        f"⚙️ *Admin Panel*\n\n"
        f"👥 *Users*\n"
        f"  • Total: {total_users}\n"
        f"  • Premium: {premium_users}\n"
        f"  • Free: {free_users}\n"
        f"  • Plans set: {plans_set}\n\n"
        f"📚 *Databank*\n"
        f"  • Questions: {len(ALL_QS)}\n"
        f"  • Subjects: {len(AVAILABLE_SUBJECTS)}\n\n"
        f"💬 *AI Tutor ({TUTOR_NAME})*\n"
        f"  • Status: {'✅ Active' if HAS_AI_TUTOR else '❌ Offline'}\n\n"
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
        [InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_INVITE_LINK)],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ])


async def cmd_admin(update, context):
    uid = str(update.effective_user.id)
    if not _admin_only(uid):
        await update.message.reply_text("🔒 Admin only.")
        return
    await update.message.reply_text(
        _admin_menu_text(), parse_mode="Markdown",
        reply_markup=_admin_menu_kb())


async def _admin_handle_callback(query, uid, data, context):
    if not _admin_only(uid):
        await query.message.reply_text("🔒 Admin only.")
        return True
    if data == "admin_panel":
        await query.message.reply_text(_admin_menu_text(), parse_mode="Markdown",
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
            "💰 Reply with the user's Telegram ID (numbers only).",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]]))
        USER_SESSIONS[str(uid)] = {"mode": "admin_grant_wait"}
        return True
    if data == "admin_broadcast_prompt":
        await query.message.reply_text(
            "📢 Reply with the broadcast text.",
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
            f"Voice: {stats.get('voice_engine', 'n/a')}",
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
    u = get_user(uid, username)
    if not u.get("plan_set", False):
        await update.message.reply_text(_plan_builder_text(uid), parse_mode="Markdown",
                                        reply_markup=_plan_builder_kb(uid))
        return
    t, kb = main_menu_text_kb(uid)
    await update.message.reply_text(t, reply_markup=kb, parse_mode="Markdown")
    await update.message.reply_text(
        f"Use buttons below 👇\n"
        f"📢 Join our channel for daily practice!\n"
        f"🚀 Invite {REFERRAL_REQUIRED} = {REFERRAL_REWARD_DAYS} days Premium FREE!",
        reply_markup=BOTTOM_KEYBOARD)


async def cmd_mock(update, context):
    uid = str(update.effective_user.id)
    u = get_user(uid, update.effective_user.first_name or "")
    if not u.get("plan_set", False):
        await update.message.reply_text(_plan_builder_text(uid), parse_mode="Markdown",
                                        reply_markup=_plan_builder_kb(uid))
        return
    await update.message.reply_text(
        _mock_menu_text(uid), parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(_mock_menu_kb(uid)))


async def cmd_study(update, context):
    get_user(update.effective_user.id, update.effective_user.first_name or "")
    await update.message.reply_text("📖 *Study Plan — Choose Subject:*",
                                    reply_markup=subjects_kb("study_subject"),
                                    parse_mode="Markdown")


async def cmd_syllabus(update, context):
    get_user(update.effective_user.id, update.effective_user.first_name or "")
    await update.message.reply_text("📋 *JAMB Syllabus — Choose Subject:*",
                                    reply_markup=subjects_kb("syllabus_subject"),
                                    parse_mode="Markdown")


async def cmd_past(update, context):
    get_user(update.effective_user.id, update.effective_user.first_name or "")
    await update.message.reply_text("📚 *Past Questions — Choose Subject:*",
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
        f"🎙️ Voice: Nigerian male teacher\n\n"
        f"Tutor: {remaining_text}\n\n"
        f"Type any JAMB question for text + voice explanation.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_INVITE_LINK)],
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
            [InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_INVITE_LINK)],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))


async def cmd_premium(update, context):
    uid = str(update.effective_user.id)
    get_user(uid, update.effective_user.first_name or "")
    kb = plan_buttons(uid)
    kb.append([InlineKeyboardButton(f"👥 Invite {REFERRAL_REQUIRED}=FREE",
                                    callback_data="invite_friends")])
    kb.append([InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_INVITE_LINK)])
    kb.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    await update.message.reply_text(
        f"💎 *Premium Plans*\n\n"
        f"*Monthly — {PREMIUM_PRICE_TEXT}* / {PREMIUM_DAYS} days\n"
        f"*6 Months — {PREMIUM_6MONTHS_TEXT}* / {PREMIUM_6MONTHS_DAYS} days *(BEST VALUE)*\n\n"
        f"✅ Unlimited mocks (all your subjects)\n"
        f"✅ Subject Mock (40Q per subject)\n"
        f"✅ Full JAMB CBT Mock (180Q · 4 subjects)\n"
        f"✅ Unlimited {TUTOR_NAME} + Voice 🎙️\n"
        f"✅ Unlimited AI Why analysis",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


async def cmd_help(update, context):
    uid = str(update.effective_user.id)
    get_user(uid, update.effective_user.first_name or "")
    help_text = (
        f"❓ *Help — UTME Success Bot*\n\n"
        f"*Commands:*\n"
        f"/start — Main menu / Plan builder\n"
        f"/mock — Start mock exam\n"
        f"/past — Past questions by subject\n"
        f"/study — Study plan\n"
        f"/syllabus — JAMB syllabus\n"
        f"/score — Your scores\n"
        f"/tutor — Ask {TUTOR_NAME}\n"
        f"/invite — Invite friends\n"
        f"/premium — Upgrade premium\n"
        f"/help — This message\n\n"
        f"*Free plan:*\n"
        f"• 1 × Free 40Q English Mock\n"
        f"• Tutor — {FREE_TUTOR_PER_DAY}/day\n"
        f"• AI Why — {FREE_AI_WHY_PER_DAY}/day\n\n"
        f"*Premium:*\n"
        f"• Unlimited mocks on all subjects\n"
        f"• Full 180Q CBT Mock (4 subjects)\n"
        f"• Unlimited AI Why analysis\n"
        f"• Unlimited tutor + voice\n\n"
        f"📢 *Follow our channel:*\n{CHANNEL_INVITE_LINK}\n\n"
        f"💬 *Chat Mindtech Solutions on Telegram {SUPPORT_HANDLE} for assistance.*"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_INVITE_LINK)],
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
        f"Voice: {stats.get('voice_engine', 'n/a')}",
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

    if data.startswith("admin_"):
        if await _admin_handle_callback(query, uid, data, context):
            return

    if data == "join_channel":
        try:
            await query.answer(
                "Opening our channel...",
                show_alert=False,
                url=CHANNEL_INVITE_LINK)
        except Exception:
            pass
        return

    if data == "plan_builder":
        await query.message.reply_text(_plan_builder_text(uid), parse_mode="Markdown",
                                       reply_markup=_plan_builder_kb(uid))
        return

    if data.startswith("plan_toggle_"):
        subj = data.replace("plan_toggle_", "")
        if subj not in PLAN_OPTIONAL_SUBJECTS:
            return
        plan = u.get("jamb_plan", ["english"])
        if subj in plan:
            plan.remove(subj)
        else:
            if len(plan) >= PLAN_SIZE:
                await query.answer(
                    f"You can only choose {PLAN_SIZE} subjects (English + 3).",
                    show_alert=True)
                return
            plan.append(subj)
        u["jamb_plan"] = plan
        save_data()
        try:
            await query.edit_message_text(_plan_builder_text(uid),
                                          parse_mode="Markdown",
                                          reply_markup=_plan_builder_kb(uid))
        except Exception:
            await query.message.reply_text(_plan_builder_text(uid),
                                           parse_mode="Markdown",
                                           reply_markup=_plan_builder_kb(uid))
        return

    if data == "plan_reset":
        u["jamb_plan"] = ["english"]
        u["plan_set"] = False
        save_data()
        try:
            await query.edit_message_text(_plan_builder_text(uid),
                                          parse_mode="Markdown",
                                          reply_markup=_plan_builder_kb(uid))
        except Exception:
            await query.message.reply_text(_plan_builder_text(uid),
                                           parse_mode="Markdown",
                                           reply_markup=_plan_builder_kb(uid))
        return

    if data == "plan_start":
        plan = u.get("jamb_plan", ["english"])
        if len(plan) != PLAN_SIZE:
            await query.answer(f"Select all {PLAN_SIZE} subjects first.",
                               show_alert=True)
            return
        u["plan_set"] = True
        save_data()
        await _start_plan_mock(query, uid, u)
        return

    if data == "start_plan_mock":
        plan = u.get("jamb_plan", ["english"])
        if len(plan) != PLAN_SIZE:
            await query.message.reply_text(_plan_builder_text(uid),
                                           parse_mode="Markdown",
                                           reply_markup=_plan_builder_kb(uid))
            return
        await _start_plan_mock(query, uid, u)
        return

    if data == "start_free_english":
        if is_premium(uid):
            await query.answer("You're Premium — no need for free mock.",
                               show_alert=True)
            return
        if u.get("free_english_used", False):
            msg, kb = upgrade_kb(uid)
            await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)
            return
        qs = _fetch_rotated(uid, "english", FREE_ENGLISH_QS)
        if len(qs) < 10:
            await query.message.reply_text("⚠️ Not enough English questions available.")
            return
        u["free_english_used"] = True
        save_data()
        intro = (f"🆓 *Free English Mock (One-time)*\n\n"
                 f"{len(qs)} questions · Take your time.\n\n"
                 f"💡 After this, all other subjects require Premium.\n\n"
                 f"📢 *Join our channel for daily practice!*")
        txt, kb = _start_mock_session(uid, qs, "english", intro_text=intro)
        await query.message.reply_text(txt, parse_mode="Markdown", reply_markup=kb)
        return

    premium_blocked = ("mock_by_subject", "mock_full", "cbt_start", "cbt_clear")
    if data in premium_blocked and not is_premium(uid):
        msg, kb = upgrade_kb(uid)
        await query.message.reply_text(f"🔒 *Premium Feature*\n\n{msg}",
                                       parse_mode="Markdown", reply_markup=kb)
        return
    if (data.startswith("mock_subject_") or data.startswith("cbt_toggle_")) \
            and not is_premium(uid):
        msg, kb = upgrade_kb(uid)
        await query.message.reply_text(f"🔒 *Premium Feature*\n\n{msg}",
                                       parse_mode="Markdown", reply_markup=kb)
        return

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
                [InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_INVITE_LINK)],
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
        allowed, reason = can_take_subject(uid, subj)
        if not allowed:
            msg, kb = upgrade_kb(uid)
            await query.message.reply_text(f"🔒 *Premium Required*\n\n{msg}",
                                           parse_mode="Markdown", reply_markup=kb)
            return
        qs = _fetch_rotated(uid, subj, 5)
        if not qs:
            await query.message.reply_text(
                f"⚠️ No questions for {SUBJECT_DISPLAY.get(subj, subj)}.")
            return
        txt, kb = _start_mock_session(uid, qs, subj)
        await query.message.reply_text(txt, reply_markup=kb)
        return

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
        else:
            session["failed"].append(_make_failure_snapshot(
                current_q, ans, correct, idx + 1))
        session["idx"] += 1

        if is_correct:
            await query.message.reply_text("✅ Correct — Next question...")
        else:
            await query.message.reply_text("❌ Wrong — Next question...")

        if session["idx"] < len(qs):
            q = qs[session["idx"]]
            txt = format_question(q, session["idx"] + 1, len(qs))
            await query.message.reply_text(txt, reply_markup=_answer_keyboard(q))
        else:
            score = session["score"]
            total = len(qs)
            failed = session.get("failed", [])
            n_failed = len(failed)

            u["history"].append({
                "date": str(date.today()),
                "subject": session.get("subject", "general"),
                "score": score, "total": total,
                "percent": score * 100 // total if total else 0})
            u["last_mock_failed"] = failed
            u["last_mock_subject"] = session.get("subject", "general")
            u["last_mock_total"] = total
            save_data()

            subj_label = session.get("subject", "general")
            if subj_label.startswith("subject_"):
                subj_label = subj_label.replace("subject_", "")
            if subj_label.startswith("CBT:"):
                subj_label = "Full JAMB CBT"
            subj_display = SUBJECT_DISPLAY.get(subj_label, subj_label.title())

            finish_msg, is_perfect = _build_completion_message(
                uid, score, total, failed, subj_label, subj_display)

            buttons = []
            if not is_perfect and n_failed > 0:
                if is_premium(uid):
                    fix_label = f"🤖 Fix My {n_failed} Failures (Unlimited)"
                else:
                    _, rem = can_use_ai_why(uid)
                    fix_label = f"🤖 Fix My {n_failed} Failures ({rem} FREE)"

                buttons.append([InlineKeyboardButton(
                    fix_label, callback_data="see_failures")])
                buttons.append([InlineKeyboardButton(
                    "📊 See All Failed Questions",
                    callback_data="see_failures")])

                state = _get_user_state(uid)
                rank = _get_user_rank_number(uid, score, total)
                buttons.append([InlineKeyboardButton(
                    f"🏆 Check Leaderboard — You're #{rank}",
                    callback_data="check_rank")])
            else:
                state = _get_user_state(uid)
                rank = _get_user_rank_number(uid, score, total)
                buttons.append([InlineKeyboardButton(
                    f"🏆 Check {state} Rank — #{rank}",
                    callback_data="check_rank")])

            is_free = not is_premium(uid)
            if is_free:
                finish_msg += (
                    f"\n\n🛑 _This was your free mock._\n"
                    f"Upgrade for unlimited mocks on all subjects."
                )
                buttons.append([InlineKeyboardButton(
                    "💎 Upgrade to Premium Now",
                    callback_data="premium_info")])

            buttons.append([InlineKeyboardButton("📢 Join Our Channel",
                                                 url=CHANNEL_INVITE_LINK)])

            buttons.append([InlineKeyboardButton("🏠 Main Menu",
                                                 callback_data="main_menu")])

            try:
                await query.message.reply_text(
                    finish_msg[:4000], parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(buttons))
            except Exception as e:
                print(f"[complete] md send failed: {e}")
                try:
                    await query.message.reply_text(
                        finish_msg[:4000],
                        reply_markup=InlineKeyboardMarkup(buttons))
                except Exception as e2:
                    print(f"[complete] plain send failed: {e2}")
        return

    if data == "see_failures":
        failed = u.get("last_mock_failed", [])
        if not failed:
            session = USER_SESSIONS.get(uid, {})
            failed = session.get("failed", [])
        if not failed:
            try:
                reloaded = json.loads(DATA_FILE.read_text(encoding="utf-8"))
                disk_u = reloaded.get(str(uid), {})
                failed = disk_u.get("last_mock_failed", [])
                if failed:
                    u["last_mock_failed"] = failed
                    save_data()
            except Exception as e:
                print(f"[see_failures] disk reload failed: {e}")

        if not failed:
            await query.message.reply_text(
                "📋 *No recent failed questions found.*\n\n"
                "Please take a mock first, then click *See Failures*.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 Start Mock",
                                          callback_data="start_plan_mock")],
                    [InlineKeyboardButton("🏠 Main Menu",
                                          callback_data="main_menu")]]))
            return

        total_failed = len(failed)
        MAX_SHOW = 15

        lines = [f"📋 *Your {total_failed} Failed Questions*\n",
                 "_Tap any button below to get an AI explanation._\n"]

        buttons = []
        for i, f in enumerate(failed[:MAX_SHOW]):
            qtext = str(f.get("question") or "")[:55]
            topic = f.get("topic", "General") or "General"
            q_num = f.get("q_num", i + 1)
            ua = f.get("user_ans", "?")
            ca = f.get("correct_ans", "?")
            lines.append(
                f"*Q{q_num}* — _{md(topic)}_\n"
                f"_{md(qtext)}..._\n"
                f"You: *{ua}* · Correct: *{ca}*\n"
            )
            buttons.append([InlineKeyboardButton(
                f"🤖 Ask AI Why Q{q_num}?",
                callback_data=f"askwhy_{i}")])

        if total_failed > MAX_SHOW:
            lines.append(f"\n_Showing first {MAX_SHOW} of {total_failed}._")

        buttons.append([InlineKeyboardButton("🤖 Ask AI Tutor Why I Failed",
                                             callback_data="ask_ellams_failures")])
        buttons.append([InlineKeyboardButton("🏆 Check Rank",
                                             callback_data="check_rank")])
        buttons.append([InlineKeyboardButton("📢 Join Our Channel",
                                             url=CHANNEL_INVITE_LINK)])
        buttons.append([InlineKeyboardButton("🏠 Main Menu",
                                             callback_data="main_menu")])

        text = "\n".join(lines)
        try:
            await query.message.reply_text(
                text[:4000], parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e:
            print(f"[see_failures] md failed: {e}")
            await query.message.reply_text(
                text[:4000], reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("askwhy_"):
        idx = int(data.split("_")[1])
        failed = u.get("last_mock_failed", [])
        if idx >= len(failed):
            session = USER_SESSIONS.get(uid, {})
            failed = session.get("failed", [])
        if idx >= len(failed):
            await query.message.reply_text(
                "That failure is no longer available. Please retake a mock.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 Start Mock",
                                          callback_data="start_plan_mock")],
                    [InlineKeyboardButton("🏠 Main Menu",
                                          callback_data="main_menu")]]))
            return

        allowed, remaining = can_use_ai_why(uid)
        if not allowed:
            msg, kb = ai_why_limit_kb(uid)
            await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)
            return

        consume_ai_why(uid)

        f = failed[idx]
        qtext = str(f.get("question", ""))
        user_ans = str(f.get("user_ans", ""))
        correct_ans = str(f.get("correct_ans", ""))
        topic = str(f.get("topic", "General"))
        q_num = f.get("q_num", idx + 1)

        seed = int(hashlib.md5(f"{uid}_{q_num}_others".encode()).hexdigest(), 16)
        others_count = 200 + (seed % 250)

        USER_SESSIONS[uid] = {
            "mode": "explaining",
            "explain_idx": idx,
        }

        if is_premium(uid):
            free_text = "Unlimited"
        else:
            _, free_left = can_use_ai_why(uid)
            free_text = f"{free_left} FREE left"

        text1 = (
            f"❌ *Q{q_num} — {md(topic)}*  _(You lost 1 mark)_\n\n"
            f"*Q:* {md(qtext[:300])}\n\n"
            f"Your answer: *{user_ans}* ❌\n"
            f"Correct: *{correct_ans}* ✅\n\n"
            f"👥 You and *{others_count}* others chose *{user_ans}*.\n"
            f"It's JAMB's favorite trap.\n\n"
            f"🤖 _AI Tutor is analyzing..._"
        )

        keyboard1 = [[InlineKeyboardButton(
            f"👁️ Tap to see why {user_ans} is trap — {free_text}",
            callback_data=f"full_exp_{idx}")]]

        try:
            await query.message.reply_text(
                text1, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard1))
        except Exception as e:
            print(f"[askwhy] send failed: {e}")
            await query.message.reply_text(
                text1,
                reply_markup=InlineKeyboardMarkup(keyboard1))
        return

    if data.startswith("full_exp_"):
        try:
            idx = int(data.split("_")[2])
        except (ValueError, IndexError):
            await query.message.reply_text("Invalid request.")
            return

        failed = u.get("last_mock_failed", [])
        if idx >= len(failed):
            session = USER_SESSIONS.get(uid, {})
            failed = session.get("failed", [])
        if idx >= len(failed):
            await query.message.reply_text(
                "That failure is no longer available.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Main Menu",
                                          callback_data="main_menu")]]))
            return

        f = failed[idx]
        qtext = str(f.get("question", ""))
        user_ans = str(f.get("user_ans", ""))
        correct_ans = str(f.get("correct_ans", ""))
        topic = str(f.get("topic", "General"))
        q_num = f.get("q_num", idx + 1)

        thinking = None
        try:
            thinking = await query.message.reply_text(
                f"🤖 *{TUTOR_NAME} is analyzing Q{q_num}...*",
                parse_mode="Markdown")
        except Exception:
            pass

        mini_q = f"Question: {qtext}\nTopic: {topic}"
        try:
            if HAS_AI_TUTOR:
                analysis = await asyncio.to_thread(
                    _analyze_failure, mini_q, user_ans, correct_ans, topic)
            else:
                analysis = "⚠️ AI Tutor is not available right now."
        except Exception as e:
            print(f"[full_exp] analyze failed: {e}")
            analysis = "⚠️ Analysis failed. Please try again."

        if thinking is not None:
            try:
                await thinking.delete()
            except Exception:
                pass

        text2 = (
            f"✅ *Q{q_num} — Why {correct_ans} is correct:*\n\n"
            f"{analysis}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"_You chose *{user_ans}* — that was the trap JAMB set._"
        )

        buttons = [
            [InlineKeyboardButton("🎙️ Voice Explanation",
                                  callback_data=f"voice_exp_{idx}")],
            [InlineKeyboardButton("📋 Back to Failures",
                                  callback_data="see_failures")],
            [InlineKeyboardButton("📢 Join Our Channel",
                                  url=CHANNEL_INVITE_LINK)],
            [InlineKeyboardButton("🏠 Main Menu",
                                  callback_data="main_menu")],
        ]

        try:
            await query.message.reply_text(
                text2[:4000], parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e:
            print(f"[full_exp] md send failed: {e}")
            await query.message.reply_text(
                text2[:4000],
                reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("voice_exp_"):
        try:
            idx = int(data.split("_")[2])
        except (ValueError, IndexError):
            return

        failed = u.get("last_mock_failed", [])
        if idx >= len(failed):
            return
        f = failed[idx]
        qtext = str(f.get("question", ""))
        user_ans = str(f.get("user_ans", ""))
        correct_ans = str(f.get("correct_ans", ""))
        topic = str(f.get("topic", "General"))

        try:
            if HAS_AI_TUTOR:
                mini_q = f"Question: {qtext}\nTopic: {topic}"
                analysis = await asyncio.to_thread(
                    _analyze_failure, mini_q, user_ans, correct_ans, topic)
                voice_if = await asyncio.to_thread(_build_voice, analysis)
                if voice_if is not None:
                    await query.message.reply_voice(
                        voice=voice_if,
                        caption=f"🎙️ Voice — {TUTOR_NAME}")
                else:
                    await query.message.reply_text(
                        "⚠️ Voice generation unavailable.")
            else:
                await query.message.reply_text(
                    "⚠️ AI Tutor is not available.")
        except Exception as e:
            print(f"[voice_exp] failed: {e}")
            await query.message.reply_text(
                "⚠️ Voice failed. Please try again.")
        return

    if data == "ask_ellams_failures":
        failed = u.get("last_mock_failed", [])
        if not failed:
            session = USER_SESSIONS.get(uid, {})
            failed = session.get("failed", [])
        if not failed:
            await query.message.reply_text(
                "📋 *No recent failures to analyse.*\n\nTake a mock first.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 Start Mock",
                                          callback_data="start_plan_mock")],
                    [InlineKeyboardButton("🏠 Main Menu",
                                          callback_data="main_menu")]]))
            return

        allowed, remaining = can_use_ai_why(uid)
        if not allowed:
            msg, kb = ai_why_limit_kb(uid)
            await query.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)
            return

        consume_ai_why(uid)

        topics_summary = {}
        for f in failed:
            t = f.get("topic", "General")
            topics_summary[t] = topics_summary.get(t, 0) + 1

        summary_lines = []
        for i, f in enumerate(failed[:5]):
            summary_lines.append(
                f"{i+1}. [{f.get('topic','Gen')}] Q: {str(f.get('question',''))[:80]}\n"
                f"   Student: {f.get('user_ans','?')} · Correct: {f.get('correct_ans','?')}"
            )

        big_q = (
            f"Student failed {len(failed)} JAMB questions. Weak topics: "
            f"{', '.join(topics_summary.keys())}.\n\n"
            f"Sample failures:\n" + "\n".join(summary_lines) + "\n\n"
            f"Give a targeted revision plan."
        )

        thinking = await query.message.reply_text(
            f"🧠 *{TUTOR_NAME} is reviewing your failures…*",
            parse_mode="Markdown")

        try:
            analysis = await asyncio.to_thread(_ask_tutor, big_q, "")
        except Exception as e:
            print(f"[ask_ellams] failed: {e}")
            analysis = "⚠️ Analysis failed. Try again."

        try:
            await thinking.delete()
        except Exception:
            pass

        remaining_after = ""
        if not is_premium(uid):
            _, rem = can_use_ai_why(uid)
            remaining_after = f"\n\n_💬 Free AI Why left today: {rem}/{FREE_AI_WHY_PER_DAY}_"

        header = f"🤖 *AI Tutor — Your Failure Analysis*\n\n"
        final = (header + analysis)[:3800] + remaining_after

        await query.message.reply_text(
            final, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 See Individual Failures",
                                      callback_data="see_failures")],
                [InlineKeyboardButton("🏆 Check Rank",
                                      callback_data="check_rank")],
                [InlineKeyboardButton("📢 Join Our Channel",
                                      url=CHANNEL_INVITE_LINK)],
                [InlineKeyboardButton("🏠 Main Menu",
                                      callback_data="main_menu")]]))
        return

    if data == "check_rank":
        subj_label = u.get("last_mock_subject", "general")
        if subj_label.startswith("subject_"):
            subj_label = subj_label.replace("subject_", "")
        if subj_label.startswith("CBT:"):
            subj_label = "Full JAMB CBT"
        subj_display = SUBJECT_DISPLAY.get(subj_label, subj_label.title())

        total = u.get("last_mock_total", 40)
        user_score = 0
        hist = u.get("history", [])
        if hist:
            user_score = hist[-1].get("score", 0)

        rank_text = _generate_rank(uid, subj_display, user_score, total)

        await query.message.reply_text(
            rank_text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 See Failures",
                                      callback_data="see_failures")],
                [InlineKeyboardButton("📢 Join Our Channel",
                                      url=CHANNEL_INVITE_LINK)],
                [InlineKeyboardButton("🏠 Main Menu",
                                      callback_data="main_menu")]]))
        return

    if data == "mock_menu":
        await query.message.reply_text(
            _mock_menu_text(uid), parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(_mock_menu_kb(uid)))
        return

    if data == "mock_by_subject":
        await query.message.reply_text(
            "📚 *Choose Subject for your 40Q Mock:*",
            reply_markup=subjects_kb("mock_subject"), parse_mode="Markdown")
        return

    if data.startswith("mock_subject_"):
        subj = data.replace("mock_subject_", "")
        qs = _fetch_rotated(uid, subj, 40)
        if len(qs) < 5:
            await query.message.reply_text(
                f"⚠️ Not enough questions for {SUBJECT_DISPLAY.get(subj, subj)}.")
            return
        display = SUBJECT_DISPLAY.get(subj, subj.title())
        intro = f"📚 *{display} Subject Mock*\n{len(qs)} questions · Good luck!"
        txt, kb = _start_mock_session(uid, qs, f"subject_{subj}", intro_text=intro)
        await query.message.reply_text(txt, parse_mode="Markdown", reply_markup=kb)
        return

    if data == "mock_full":
        plan = u.get("jamb_plan", ["english"])[:4]
        if len(plan) != 4:
            await query.message.reply_text(
                "Please set your 4-subject JAMB plan first.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✏️ Set Plan",
                                          callback_data="plan_builder")]]))
            return
        qs = _fetch_rotated_multi(uid, plan, 180)
        if len(qs) < 20:
            await query.message.reply_text(
                f"⚠️ Only {len(qs)} questions available. Try again later.")
            return
        stats = []
        counts = {}
        for q in qs:
            key = q.get("subject_key") or q.get("subject", "").lower()
            counts[key] = counts.get(key, 0) + 1
        for s in plan:
            stats.append(f"  • {SUBJECT_DISPLAY.get(s, s.title())}: {counts.get(s, 0)} Qs")
        intro = (f"🚀 *Full JAMB CBT Mock*\n\n"
                 f"📚 *Your Plan:*\n" + "\n".join(stats) + "\n\n"
                 f"📝 Total: *{len(qs)} questions*\n"
                 f"⏱️ Recommended: *2 hours*\n\nGood luck! 🎯")
        subj_label = "CBT:" + ",".join(plan)
        txt, kb = _start_mock_session(uid, qs, subj_label, intro_text=intro)
        await query.message.reply_text(txt, parse_mode="Markdown", reply_markup=kb)
        return

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
            f"Tutor: {remaining_text}\n\n"
            f"Ask anything — any subject:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_INVITE_LINK)],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        return

    if data == "premium_info":
        kb = plan_buttons(uid)
        kb.append([InlineKeyboardButton(f"👥 Invite {REFERRAL_REQUIRED}=FREE",
                                        callback_data="invite_friends")])
        kb.append([InlineKeyboardButton("📢 Join Our Channel",
                                        url=CHANNEL_INVITE_LINK)])
        kb.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
        await query.message.reply_text(
            f"💎 *Premium Plans*\n\n"
            f"*Monthly — {PREMIUM_PRICE_TEXT}* / {PREMIUM_DAYS} days\n"
            f"*6 Months — {PREMIUM_6MONTHS_TEXT}* / {PREMIUM_6MONTHS_DAYS} days *(BEST VALUE)*\n\n"
            f"✅ Unlimited mocks (all subjects)\n"
            f"✅ Full JAMB CBT Mock (180Q · 4 subjects)\n"
            f"✅ Unlimited {TUTOR_NAME} + Voice 🎙️\n"
            f"✅ Unlimited AI Why analysis\n"
            f"✅ {len(ALL_QS)} Qs",
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
                [InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_INVITE_LINK)],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]))
        return

    if data == "help_menu":
        await cmd_help(update, context)
        return

    if data == "main_menu":
        if not u.get("plan_set", False):
            await query.message.reply_text(_plan_builder_text(uid),
                                           parse_mode="Markdown",
                                           reply_markup=_plan_builder_kb(uid))
            return
        t, kb = main_menu_text_kb(uid)
        await query.message.reply_text(t, reply_markup=kb, parse_mode="Markdown")
        return


async def _start_plan_mock(query, uid, u):
    plan = u.get("jamb_plan", ["english"])
    if not is_premium(uid):
        if u.get("free_english_used", False):
            msg, kb = upgrade_kb(uid)
            await query.message.reply_text(
                f"🔒 *You've used your free English mock.*\n\n"
                f"To continue with the rest of your plan "
                f"({', '.join(SUBJECT_DISPLAY.get(s, s) for s in plan[1:])}), "
                f"upgrade to Premium.\n\n{msg}",
                parse_mode="Markdown", reply_markup=kb)
            return
        qs = _fetch_rotated(uid, "english", FREE_ENGLISH_QS)
        if len(qs) < 10:
            await query.message.reply_text("⚠️ Not enough English questions available.")
            return
        u["free_english_used"] = True
        save_data()
        intro = (
            f"🆓 *Free English Mock (One-time)*\n\n"
            f"Your JAMB Plan: {', '.join(SUBJECT_DISPLAY.get(s, s.title()) for s in plan)}\n\n"
            f"Starting with English (40 Qs).\n\n"
            f"💡 After this, upgrading unlocks "
            f"{', '.join(SUBJECT_DISPLAY.get(s, s.title()) for s in plan[1:])}.\n\n"
            f"📢 Join our channel: {CHANNEL_INVITE_LINK}"
        )
        txt, kb = _start_mock_session(uid, qs, "english", intro_text=intro)
        await query.message.reply_text(txt, parse_mode="Markdown", reply_markup=kb)
        return

    subject = plan[0] if plan else "english"
    qs = _fetch_rotated(uid, subject, 40)
    if len(qs) < 5:
        await query.message.reply_text(
            f"⚠️ Not enough questions for {SUBJECT_DISPLAY.get(subject, subject)}.")
        return
    display = SUBJECT_DISPLAY.get(subject, subject.title())
    intro = (f"🎯 *Mock from Your Plan*\n\n"
             f"Starting: *{display}* ({len(qs)} Qs)\n\n"
             f"Continue with other subjects from your plan after this.")
    txt, kb = _start_mock_session(uid, f"subject_{subject}", intro_text=intro)
    await query.message.reply_text(txt, parse_mode="Markdown", reply_markup=kb)


# ============================================================
# TEXT HANDLER
# ============================================================

async def handle_msg(update, context):
    uid = str(update.effective_user.id)
    text = (update.message.text or "").strip()
    u = get_user(uid, update.effective_user.first_name or "")

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
                    "❌ Invalid ID.",
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

    if text == "⚙️ Admin Panel" and _admin_only(uid):
        await cmd_admin(update, context); return

    if text == "📢 Join Our Channel":
        await update.message.reply_text(
            f"📢 *Join Our Official Channel*\n\n"
            f"Get daily JAMB practice questions, tips, and updates!\n\n"
            f"👉 {CHANNEL_INVITE_LINK}",
            parse_mode="Markdown",
            disable_web_page_preview=False,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Tap Here to Join",
                                      url=CHANNEL_INVITE_LINK)],
                [InlineKeyboardButton("🏠 Main Menu",
                                      callback_data="main_menu")]]))
        return

    if text == "📚 Past Questions": await cmd_past(update, context); return
    if text == "📝 Mock Exam":       await cmd_mock(update, context); return
    if text == "📊 My Score":        await cmd_score(update, context); return
    if text == "💬 Ask Tutor":       await cmd_tutor(update, context); return
    if text == "💎 Premium":         await cmd_premium(update, context); return
    if text == "👥 Invite Friends":  await cmd_invite(update, context); return
    if text == "📖 Study Plan":      await cmd_study(update, context); return

    if not u.get("plan_set", False):
        await update.message.reply_text(_plan_builder_text(uid),
                                        parse_mode="Markdown",
                                        reply_markup=_plan_builder_kb(uid))
        return

    session = USER_SESSIONS.get(uid, {})
    is_tutor = (session.get("mode") == "tutor" or
                (session.get("mode") not in ("cbt_select", "post_mock", "explaining") and
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
        answer_text = "⚠️ *Tutor error.* Please try again."

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
        [InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_INVITE_LINK)],
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

    if HAS_AI_TUTOR:
        try:
            voice_if = await asyncio.to_thread(_build_voice, answer_text)
            if voice_if is not None:
                await update.message.reply_voice(
                    voice=voice_if,
                    caption=f"🎙️ Voice Explanation — {TUTOR_NAME}")
        except Exception as e:
            print(f"[tutor] Voice send failed: {type(e).__name__}: {e}")


# ============================================================
# FLASK APP
# ============================================================
flask_app = Flask(__name__)


@flask_app.route("/")
def home():
    return (f"UTME Bot v36 · {len(ALL_QS)} Qs · "
            f"Tutor: {TUTOR_NAME} ({'ON' if HAS_AI_TUTOR else 'OFF'}) · "
            f"Bot: @{BOT_USERNAME} · Channel: {CHANNEL_ID or 'OFF'} · Running")


@flask_app.route("/health")
def health():
    tutor_ok, tutor_detail = _tutor_ping() if HAS_AI_TUTOR else (False, "not loaded")
    return jsonify({
        "status": "ok",
        "bot_username": BOT_USERNAME,
        "tutor_name": TUTOR_NAME,
        "total_questions": len(ALL_QS),
        "free_plan": "1 × 40Q English mock (one-time)",
        "free_ai_why_per_day": FREE_AI_WHY_PER_DAY,
        "plan_size": PLAN_SIZE,
        "option_shuffle": True,
        "rotation": True,
        "real_exam_mode": True,
        "two_step_ai_why": True,
        "state_rank_rotation": True,
        "failures_persisted": True,
        "persuasive_completion": True,
        "channel_invite_button": True,
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
    if slot_name == "morning": return _build_morning_post(q)
    if slot_name == "afternoon": return _build_afternoon_post(q)
    if slot_name == "evening": return _build_evening_post(q)
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
    print(f"📢 Channel invite: {CHANNEL_INVITE_LINK}")
    print(f"🆓 Free plan: 1 × {FREE_ENGLISH_QS}Q English mock (one-time)")
    print(f"💬 Free AI Why/day: {FREE_AI_WHY_PER_DAY}")
    print(f"📋 Plan: English + 3 chosen subjects")
    print(f"🎲 Option shuffler: ON")
    print(f"🔄 Rotation: ON")
    print(f"📝 Real exam mode: ON (no answer reveal)")
    print(f"🎯 Two-step AI Why: ON (recap + reveal)")
    print(f"🏆 State rank rotation: ON")
    print(f"💾 Failures persisted: ON")
    print(f"📣 Persuasive completion: ON")
    print(f"🔗 Join Channel button: ON")
    if ADMIN_ID:
        print(f"⚙️  Admin ID: {ADMIN_ID}")

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
                          "💎 Premium|👥 Invite Friends|📖 Study Plan|📢 Join Our Channel|"
                          "⚙️ Admin Panel)$"),
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
