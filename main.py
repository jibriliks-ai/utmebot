"""
main.py — UTME Success Coach Bot
Persistent 6-item menu, Top Scorer banner, 180Q paid mock,
DeepSeek tutor, Flutterwave checkout, 6s verdict delay.
"""
import os
import time
import random
import asyncio
import threading

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters,
)
from flask import Flask, request, jsonify, redirect

import cbt_engine
from user_manager import (
    init_db, get_or_create_user, is_premium, set_premium,
    can_take_mock, record_mock_taken, record_referral, get_referral_count,
    get_mock_stats, record_top_score, get_top_scorer, get_top_scorers,
)
from tutor import ask_tutor, build_voice_inputfile, ping as tutor_ping
from referrals import referral_message, parse_referral_arg
from channel_scheduler import register_jobs
from payment import (
    PLANS, get_plan, create_payment_link, verify_transaction,
    verify_webhook_signature, extract_user_id_from_meta,
    extract_plan_id_from_meta, days_for_plan,
)
from checkout_ui import checkout_page, success_page, pending_page, error_page

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_LINK = os.getenv("BOT_LINK", "https://t.me/UTMESUCCESS")
FREE_MOCK_SIZE = 5
PAID_MOCK_SIZE = 180
VERDICT_DELAY_SECONDS = 6
BASE_URL = os.getenv("BASE_URL", "https://utmebot.onrender.com")

MENU, MOCK_A, TUTOR_ASK, AWAIT_TX_ID = range(4)

MENU_BUTTONS = {
    "📝 Mock Exam": "menu_mock",
    "🧠 Ask Tutor": "menu_tutor",
    "💎 Premium": "menu_upgrade",
    "🤝 Invite Friends": "menu_invite",
    "❓ Help": "menu_help",
    "📊 My Score": "menu_stats",
}


# ---------- keyboards ----------
def persistent_menu_keyboard():
    keyboard = [
        [KeyboardButton("📝 Mock Exam"), KeyboardButton("🧠 Ask Tutor")],
        [KeyboardButton("💎 Premium"), KeyboardButton("🤝 Invite Friends")],
        [KeyboardButton("❓ Help"), KeyboardButton("📊 My Score")],
    ]
    return ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, is_persistent=True,
        input_field_placeholder="Choose an option…",
    )


def main_menu_inline():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Mock Exam", callback_data="menu_mock"),
         InlineKeyboardButton("🧠 Ask Tutor", callback_data="menu_tutor")],
        [InlineKeyboardButton("💎 Premium", callback_data="menu_upgrade"),
         InlineKeyboardButton("🤝 Invite Friends", callback_data="menu_invite")],
        [InlineKeyboardButton("❓ Help", callback_data="menu_help"),
         InlineKeyboardButton("📊 My Score", callback_data="menu_stats")],
    ])


def back_to_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="menu_back")]])


def plan_selection_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 1 Month — ₦2,000", callback_data="plan_1m")],
        [InlineKeyboardButton("🔥 6 Months — ₦6,000  (SAVE ₦6,000)", callback_data="plan_6m")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="menu_back")],
    ])


# ---------- TOP SCORER banner ----------
def top_scorer_banner():
    """Return a short string showing the current top scorer, or None."""
    top = get_top_scorer()
    if not top:
        return None
    pct = round((top["score"] / top["total"]) * 100) if top["total"] else 0
    return (
        f"🏆 *TOP SCORER CHALLENGE*\n"
        f"👑 {top['display_name']} — *{top['score']}/{top['total']}* ({pct}%)\n"
        f"_Can you beat this score? Take the paid mock and find out._"
    )


# ---------- /start ----------
async def cmd_start(update, context):
    user = update.effective_user
    uid = user.id
    get_or_create_user(uid, user.username, user.first_name)

    referrer = parse_referral_arg(context.args)
    if referrer:
        if record_referral(referrer, uid):
            try:
                await context.bot.send_message(
                    referrer,
                    "🎉 Someone just joined through your invite link! Keep sharing — "
                    "you unlock Premium rewards as your referrals grow.",
                )
            except Exception:
                pass

    premium = is_premium(uid)
    status = "💎 Premium" if premium else "🆓 Free"

    text = (
        f"👋 Welcome, *{user.first_name}*!\n\n"
        f"Status: *{status}*\n\n"
        "📚 *UTME Success Coach* — your personal JAMB prep bot.\n\n"
        "• 📝 Free daily mock exam (5 questions)\n"
        "• 🧠 AI Tutor with voice explanations\n"
        "• 🏆 Top Scorer Challenge (paid mock)\n"
        "• 🤝 Invite friends to earn rewards\n\n"
        "Use the menu below 👇"
    )
    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=persistent_menu_keyboard(),
    )
    return MENU


# ---------- menu actions ----------
async def _send(update, text, reply_markup=None, parse_mode="Markdown"):
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, parse_mode=parse_mode, reply_markup=reply_markup,
            )
        else:
            await update.message.reply_text(
                text, parse_mode=parse_mode, reply_markup=reply_markup,
            )
    except Exception:
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)


async def do_mock(update, context, uid):
    premium = is_premium(uid)
    allowed, wait = can_take_mock(uid)

    # ---- PREMIUM: 180-question paid mock with Top Scorer banner ----
    if premium:
        banner = top_scorer_banner()
        text = "💎 *Paid Mock — 180 Questions*\n\n"
        text += "This is the full UTME simulation. Your score will be recorded "
        text += "and compared with other students.\n\n"
        if banner:
            text += banner + "\n\n"
        else:
            text += "🏆 *Be the first top scorer!*\n\n"
        text += f"📝 *{PAID_MOCK_SIZE} questions · All subjects · Timed*\n\n"
        text += "_Tap below to begin._"

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("▶️ Start 180-Question Mock", callback_data="start_paid_mock")],
            [InlineKeyboardButton("⬅️ Main Menu", callback_data="menu_back")],
        ])
        await _send(update, text, kb)
        return MENU

    # ---- FREE user: 5-question mock with 24h limit ----
    if not allowed:
        text = (
            f"⏳ *You've used your free daily mock!*\n\n"
            f"Next free mock in *{wait}*.\n\n"
            "💎 Upgrade to Premium for *unlimited mocks*, all subjects, "
            "and the *Top Scorer Challenge* (180 questions)."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Upgrade Now", callback_data="menu_upgrade")],
            [InlineKeyboardButton("⬅️ Main Menu", callback_data="menu_back")],
        ])
        await _send(update, text, kb)
        return MENU

    try:
        pool = cbt_engine.ALL_QS or []
        if len(pool) < FREE_MOCK_SIZE:
            await _send(update, "Databank is empty. Try again later.")
            return MENU
        qs = random.sample(pool, FREE_MOCK_SIZE)
    except Exception as e:
        await _send(update, f"Could not start mock: {e}")
        return MENU

    context.user_data["mock"] = {
        "index": 0, "score": 0, "questions": qs, "type": "free",
    }
    await _send(update, "📝 *Loading your free mock...*")
    return await send_next_mock_question(update, context, via="message")


async def start_paid_mock(update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if not is_premium(uid):
        await q.edit_message_text(
            "💎 This is a Premium feature.\n\nUpgrade to unlock the full "
            "180-question mock and the Top Scorer Challenge.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Upgrade", callback_data="menu_upgrade")],
                [InlineKeyboardButton("⬅️ Main Menu", callback_data="menu_back")],
            ]),
        )
        return MENU

    pool = cbt_engine.ALL_QS or []
    if len(pool) < PAID_MOCK_SIZE:
        await q.edit_message_text(
            f"Only {len(pool)} questions available — need {PAID_MOCK_SIZE}."
        )
        return MENU

    qs = random.sample(pool, PAID_MOCK_SIZE)
    context.user_data["mock"] = {
        "index": 0, "score": 0, "questions": qs, "type": "paid",
    }
    await q.edit_message_text("📝 *Starting your 180-question mock...*", parse_mode="Markdown")
    return await send_next_mock_question(update, context, via="callback")


async def do_tutor(update, context, uid):
    text = (
        "🧠 *AI Tutor — Ask Any UTME Question*\n\n"
        "Type your question (Maths, English, Physics, Chemistry, Biology, "
        "Economics, Government, Literature, etc.).\n\n"
        "You'll get a clear step-by-step explanation plus a *voice note* "
        "you can replay.\n\n"
        "_Type /cancel or /menu to go back._"
    )
    await _send(update, text)
    return TUTOR_ASK


async def do_upgrade(update, context, uid):
    if is_premium(uid):
        text = (
            "💎 *You're already Premium!*\n\n"
            "You have unlimited access — including the 180-question Top Scorer mock.\n\n"
            "Thanks for supporting UTME Success Coach 🙏"
        )
        kb = back_to_menu()
    else:
        text = (
            "💎 *Upgrade to Premium*\n\n"
            "Choose a plan to unlock unlimited access:\n\n"
            "🎯 *1 Month* — ₦2,000\n"
            "   Perfect for a focused month of prep\n\n"
            "🔥 *6 Months* — ₦6,000\n"
            "   Best value — SAVE ₦6,000 (50% OFF)\n\n"
            "_Tap a plan below to see full benefits and pay securely._"
        )
        kb = plan_selection_keyboard()
    await _send(update, text, kb)
    return MENU


async def do_invite(update, context, uid):
    bot_username = context.bot.username
    msg = referral_message(bot_username, uid)
    await _send(update, msg, back_to_menu())
    return MENU


async def do_help(update, context, uid):
    text = (
        "❓ *Help & Support*\n\n"
        "Need assistance? We're here to help!\n\n"
        "📩 *Chat with us on Telegram:* @UTMESUCCESS\n\n"
        "You can reach us for:\n"
        "• Payment issues\n"
        "• Premium activation\n"
        "• Bug reports\n"
        "• Feature requests\n\n"
        "Tap the button below to open a chat 👇"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Chat with @UTMESUCCESS", url="https://t.me/UTMESUCCESS")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="menu_back")],
    ])
    await _send(update, text, kb)
    return MENU


async def do_stats(update, context, uid):
    premium = is_premium(uid)
    total_mocks, best_score, best_total, avg = get_mock_stats(uid)
    if total_mocks == 0:
        stats_text = "You haven't taken any mock yet. Tap *Mock Exam* to start!"
    else:
        best_pct = round((best_score / best_total * 100), 1) if best_total else 0
        stats_text = (
            f"📝 Mocks taken: *{total_mocks}*\n"
            f"🏆 Best score: *{best_score}/{best_total}* ({best_pct}%)\n"
            f"📈 Average: *{avg}%*"
        )

    # Top Scorer leaderboard
    leaders = get_top_scorers(limit=5)
    if leaders:
        lines = ["\n\n🏆 *Top Scorer Leaderboard*"]
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        for i, row in enumerate(leaders):
            pct = round((row["score"] / row["total"]) * 100) if row["total"] else 0
            lines.append(f"{medals[i]} {row['display_name']} — {row['score']}/{row['total']} ({pct}%)")
        leaderboard = "\n".join(lines)
    else:
        leaderboard = "\n\n🏆 *No top scorers yet — be the first!*"

    text = (
        f"📊 *Your Scorecard*\n\n"
        f"Status: {'💎 Premium' if premium else '🆓 Free'}\n"
        f"Referrals: *{get_referral_count(uid)}*\n\n"
        f"{stats_text}"
        f"{leaderboard}\n\n"
        f"📚 Questions in databank: *{len(cbt_engine.ALL_QS)}*\n"
        f"📖 Subjects available: *{len(cbt_engine.LOCAL_DATABANK)}*"
    )
    await _send(update, text, back_to_menu())
    return MENU


ACTION_MAP = {
    "menu_mock": do_mock,
    "menu_tutor": do_tutor,
    "menu_upgrade": do_upgrade,
    "menu_invite": do_invite,
    "menu_help": do_help,
    "menu_stats": do_stats,
}


async def menu_callback(update, context):
    q = update.callback_query
    await q.answer()
    data = q.data
    uid = q.from_user.id

    if data == "menu_back":
        premium = is_premium(uid)
        status = "💎 Premium" if premium else "🆓 Free"
        await q.edit_message_text(
            f"*Main Menu* — Status: {status}\n\nUse the menu below 👇",
            parse_mode="Markdown", reply_markup=main_menu_inline(),
        )
        return MENU

    action = ACTION_MAP.get(data)
    if action:
        return await action(update, context, uid)
    return MENU


async def handle_menu_text(update, context):
    text = (update.message.text or "").strip()
    data = MENU_BUTTONS.get(text)
    if not data:
        return None
    user = update.effective_user
    get_or_create_user(user.id, user.username, user.first_name)
    action = ACTION_MAP.get(data)
    if action:
        return await action(update, context, user.id)
    return MENU


async def select_plan(update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    plan_id = q.data.replace("plan_", "")
    plan = get_plan(plan_id)
    if not plan:
        await q.edit_message_text("Unknown plan. Please try again.")
        return MENU
    checkout_url = f"{BASE_URL}/checkout?uid={uid}&plan={plan_id}"
    text = (
        f"🎯 *{plan['label']} Plan — ₦{plan['amount']:,}*\n\n"
        "Tap the button below to see full benefits and complete your "
        "secure payment via Flutterwave.\n\n"
        "_After paying, return here and tap *I've Paid* if Premium "
        "doesn't activate automatically._"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 Open Secure Checkout", url=checkout_url)],
        [InlineKeyboardButton("🔄 I've Paid — Verify Now", callback_data="verify_payment")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="menu_back")],
    ])
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    return MENU


async def verify_payment_entry(update, context):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "📋 *Send your Flutterwave transaction ID.*\n\n"
        "You'll find it on the payment confirmation page. It's a number like `1234567`.\n\n"
        "_Type /cancel to go back._",
        parse_mode="Markdown",
    )
    return AWAIT_TX_ID


async def receive_tx_id(update, context):
    txt = (update.message.text or "").strip()
    if txt in MENU_BUTTONS:
        return await handle_menu_text(update, context)
    uid = update.effective_user.id
    if not txt.isdigit():
        await update.message.reply_text("❌ Please send the transaction ID as a number.")
        return AWAIT_TX_ID
    ok, data = verify_transaction(txt)
    if ok:
        plan_id = extract_plan_id_from_meta(data)
        days = days_for_plan(plan_id)
        set_premium(uid, days=days)
        plan = get_plan(plan_id) or {"label": "Premium"}
        await update.message.reply_text(
            f"✅ *Payment confirmed! {plan['label']} Premium is now active.*\n\n"
            f"Enjoy unlimited access for {days} days 🎉\n"
            f"Includes the 180-question Top Scorer mock!",
            parse_mode="Markdown",
            reply_markup=persistent_menu_keyboard(),
        )
        return MENU
    await update.message.reply_text(
        "❌ Couldn't verify that transaction. Please check the ID and try again, "
        "or contact support at @UTMESUCCESS if you were debited."
    )
    return AWAIT_TX_ID


# ---------- mock flow ----------
async def send_next_mock_question(update, context, via="callback"):
    mock = context.user_data.get("mock")
    if not mock:
        return MENU
    idx = mock["index"]
    total = len(mock["questions"])
    if idx >= total:
        return await finish_mock(update, context, via=via)

    qd = mock["questions"][idx]
    mock_type = mock.get("type", "free")

    # Show Top Scorer banner on the FIRST question of a paid mock
    prefix = ""
    if mock_type == "paid" and idx == 0:
        banner = top_scorer_banner()
        if banner:
            prefix = banner + "\n\n" + "━" * 20 + "\n\n"

    text = prefix + cbt_engine.format_question(qd, idx + 1, total)

    buttons = []
    for L in ("A", "B", "C", "D", "E"):
        if qd.get(f"option_{L.lower()}"):
            buttons.append(InlineKeyboardButton(L, callback_data=f"ans_{L}"))
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    kb = InlineKeyboardMarkup(rows)

    if via == "callback" and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")
    return MOCK_A


async def mock_answer(update, context):
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    if not data.startswith("ans_"):
        return MOCK_A
    chosen = data.replace("ans_", "")
    mock = context.user_data.get("mock")
    if not mock:
        return MENU
    current = mock["questions"][mock["index"]]
    correct = str(current.get("answer", "")).upper()[:1]
    if chosen == correct:
        mock["score"] += 1
        feedback = "✅ *Correct!*"
    else:
        feedback = f"❌ *Wrong.* Correct answer: *{correct}*"
    expl = current.get("explanation", "")
    text = feedback + (f"\n\n_{expl}_" if expl else "")
    try:
        await q.edit_message_text(text, parse_mode="Markdown")
    except Exception:
        await q.edit_message_text(text)
    mock["index"] += 1
    await asyncio.sleep(VERDICT_DELAY_SECONDS)
    return await send_next_mock_question(update, context, via="callback")


async def finish_mock(update, context, via="callback"):
    mock = context.user_data.get("mock") or {}
    score = mock.get("score", 0)
    total = len(mock.get("questions", [])) or 1
    mock_type = mock.get("type", "free")
    uid = update.effective_user.id if update.effective_user else update.callback_query.from_user.id

    record_mock_taken(uid, score=score, total=total, mock_type=mock_type)

    # Record top score if paid mock
    top_msg = ""
    if mock_type == "paid":
        user = get_or_create_user(uid)
        display = user.get("first_name") or user.get("username") or f"User{uid}"
        was_record = record_top_score(uid, display, score, total)
        top = get_top_scorer()
        if top:
            pct = round((top["score"] / top["total"]) * 100) if top["total"] else 0
            if was_record:
                top_msg = f"\n\n👑 *NEW TOP SCORER!* You're now #1: *{score}/{total}* ({pct}%)."
            else:
                top_msg = (
                    f"\n\n🏆 *Current Top Scorer:* {top['display_name']} — "
                    f"*{top['score']}/{top['total']}* ({pct}%)\n"
                    f"Can you beat that? Try again!"
                )

    pct = round(score / total * 100)
    if pct >= 80:
        verdict = "🔥 Excellent! You're on fire."
    elif pct >= 60:
        verdict = "🌟 Good job! Keep pushing."
    elif pct >= 40:
        verdict = "💪 Fair. A bit more practice and you'll ace it."
    else:
        verdict = "📚 Keep studying — every attempt makes you sharper."

    text = (
        f"🎯 *Mock Complete!*\n\n"
        f"Score: *{score}/{total}* ({pct}%)\n\n"
        f"{verdict}{top_msg}\n\n"
        "💎 Want more? Upgrade for unlimited mocks.\n"
        "🧠 Need explanations? Tap Ask Tutor."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Upgrade", callback_data="menu_upgrade")],
        [InlineKeyboardButton("🧠 Ask Tutor", callback_data="menu_tutor")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="menu_back")],
    ])
    if via == "callback" and update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
    context.user_data.pop("mock", None)
    return MENU


# ---------- tutor ----------
async def tutor_ask(update, context):
    txt = (update.message.text or "").strip()
    if txt in MENU_BUTTONS:
        return await handle_menu_text(update, context)
    if len(txt) < 5:
        await update.message.reply_text("Please type your full question.")
        return TUTOR_ASK

    thinking_msg = await update.message.reply_text("🧠 Thinking...")
    explanation = ask_tutor(txt)

    try:
        await thinking_msg.delete()
    except Exception:
        pass

    await update.message.reply_text(explanation)

    voice = build_voice_inputfile(explanation)
    if voice:
        try:
            await update.message.reply_voice(voice=voice)
        except Exception as e:
            print(f"[tutor] voice send failed: {e}")

    await update.message.reply_text(
        "Ask another question, or tap a menu option below."
    )
    return TUTOR_ASK


async def cancel(update, context):
    premium = is_premium(update.effective_user.id)
    status = "💎 Premium" if premium else "🆓 Free"
    await update.message.reply_text(
        f"*Main Menu* — Status: {status}",
        parse_mode="Markdown",
        reply_markup=persistent_menu_keyboard(),
    )
    return MENU


async def unknown(update, context):
    await update.message.reply_text(
        "Use the menu below 👇", reply_markup=persistent_menu_keyboard()
    )
    return MENU


# ---------- Flask ----------
flask_app = Flask(__name__)


@flask_app.route("/")
def health():
    return "UTME Bot is running ✅", 200


@flask_app.route("/checkout", methods=["GET"])
def checkout():
    try:
        uid = int(request.args.get("uid", "0"))
    except ValueError:
        return error_page("Invalid user ID.")
    plan_id = request.args.get("plan", "1m")
    plan = get_plan(plan_id)
    if not plan or uid <= 0:
        return error_page("Invalid plan or user.")
    return checkout_page(plan, uid, bot_link=BOT_LINK)


@flask_app.route("/checkout/pay", methods=["POST"])
def checkout_pay():
    try:
        uid = int(request.form.get("uid", "0"))
    except ValueError:
        return error_page("Invalid user ID.")
    plan_id = request.form.get("plan", "1m")
    plan = get_plan(plan_id)
    if not plan or uid <= 0:
        return error_page("Invalid plan or user.")
    link, tx_ref = create_payment_link(uid, plan_id)
    if not link:
        return error_page(
            "We couldn't reach the payment gateway right now. "
            "Please try again in a moment, or contact @UTMESUCCESS."
        )
    print(f"[checkout] redirecting user {uid} plan {plan_id} to Flutterwave")
    return redirect(link, code=302)


@flask_app.route("/payment/callback", methods=["GET"])
def payment_callback():
    tx_id = request.args.get("transaction_id")
    if not tx_id:
        return pending_page(bot_link=BOT_LINK)
    ok, data = verify_transaction(tx_id)
    if ok:
        uid = extract_user_id_from_meta(data)
        plan_id = extract_plan_id_from_meta(data)
        plan = get_plan(plan_id)
        if uid:
            set_premium(uid, days=days_for_plan(plan_id))
            print(f"[callback] premium activated for {uid} plan {plan_id}")
        return success_page(plan, bot_link=BOT_LINK)
    return pending_page(bot_link=BOT_LINK)


@flask_app.route("/webhook/flutterwave", methods=["POST"])
def flutterwave_webhook():
    if not verify_webhook_signature(request):
        return jsonify({"status": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    if data.get("event") == "charge.completed" and data.get("data", {}).get("status") == "successful":
        tx = data.get("data", {})
        uid = extract_user_id_from_meta(tx)
        plan_id = extract_plan_id_from_meta(tx)
        if uid:
            set_premium(uid, days=days_for_plan(plan_id))
            print(f"[webhook] premium activated for {uid} plan {plan_id}")
    return jsonify({"status": "ok"}), 200


def run_flask():
    port = int(os.getenv("PORT", "8080"))
    flask_app.run(host="0.0.0.0", port=port)


# ---------- main ----------
def main():
    init_db()

    # Verify DeepSeek at startup
    ok, msg = tutor_ping()
    if ok:
        print(f"[startup] DeepSeek tutor OK: {msg}")
    else:
        print(f"[startup] DeepSeek tutor NOT working: {msg}")

    threading.Thread(target=run_flask, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    menu_text_handler = MessageHandler(
        filters.TEXT & filters.Regex(
            "^(" + "|".join([b.replace("+", r"\+") for b in MENU_BUTTONS]) + ")$"
        ),
        handle_menu_text,
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            MENU: [
                CallbackQueryHandler(menu_callback, pattern="^menu_"),
                CallbackQueryHandler(select_plan, pattern="^plan_"),
                CallbackQueryHandler(start_paid_mock, pattern="^start_paid_mock$"),
                CallbackQueryHandler(verify_payment_entry, pattern="^verify_payment$"),
                menu_text_handler,
            ],
            MOCK_A: [CallbackQueryHandler(mock_answer, pattern="^ans_")],
            TUTOR_ASK: [
                CommandHandler("cancel", cancel),
                CommandHandler("menu", cancel),
                CallbackQueryHandler(menu_callback, pattern="^menu_"),
                menu_text_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_ask),
            ],
            AWAIT_TX_ID: [
                CommandHandler("cancel", cancel),
                menu_text_handler,
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_tx_id),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("menu", cancel))

    register_jobs(app.job_queue)

    print("[bot] starting polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
