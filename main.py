"""
main.py — UTME Success Coach Bot
Complete entry point. Wires together cbt_engine, user_manager, tutor,
channel_scheduler, referrals, and payment.
"""
import os
import time
import random
import asyncio
import threading

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters,
)
from flask import Flask, request, jsonify

import cbt_engine
from user_manager import (
    init_db, get_or_create_user, is_premium, set_premium,
    can_take_mock, record_mock_taken, record_referral, get_referral_count,
)
from tutor import ask_tutor, build_voice_inputfile
from referrals import referral_message, parse_referral_arg
from channel_scheduler import register_jobs
from payment import (
    create_payment_link, verify_transaction,
    verify_webhook_signature, extract_user_id_from_meta,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
PREMIUM_PRICE_NGN = 500
FREE_MOCK_SIZE = 5

MENU, MOCK_A, TUTOR_ASK, AWAIT_TX_ID = range(4)


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Free Mock Exam", callback_data="menu_mock")],
        [InlineKeyboardButton("🧠 Ask Tutor (Voice)", callback_data="menu_tutor")],
        [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="menu_upgrade")],
        [InlineKeyboardButton("🤝 Invite Friends", callback_data="menu_invite")],
        [InlineKeyboardButton("📊 My Stats", callback_data="menu_stats")],
    ])


def back_to_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data="menu_back")]])


def upgrade_keyboard(link=None):
    rows = []
    if link:
        rows.append([InlineKeyboardButton("💳 Pay ₦500 with Flutterwave", url=link)])
    rows.append([InlineKeyboardButton("🔄 I've paid — Verify", callback_data="verify_payment")])
    rows.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="menu_back")])
    return InlineKeyboardMarkup(rows)


async def cmd_start(update, context):
    user = update.effective_user
    uid = user.id
    get_or_create_user(uid, user.username)

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
        "• 📖 Past questions across all subjects\n"
        "• 🤝 Invite friends to earn rewards\n\n"
        "Choose an option below to begin 👇"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    return MENU


async def menu_callback(update, context):
    q = update.callback_query
    await q.answer()
    data = q.data
    uid = q.from_user.id

    if data == "menu_back":
        premium = is_premium(uid)
        status = "💎 Premium" if premium else "🆓 Free"
        await q.edit_message_text(
            f"*Main Menu* — Status: {status}\n\nChoose an option:",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
        return MENU

    if data == "menu_mock":
        allowed, wait = can_take_mock(uid)
        if not allowed:
            text = (
                f"⏳ *You've used your free daily mock!*\n\n"
                f"Next free mock in *{wait}*.\n\n"
                "💎 Upgrade to Premium for *unlimited mocks*, all subjects, "
                "and unlimited AI Tutor with voice."
            )
            await q.edit_message_text(
                text, parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💎 Upgrade Now", callback_data="menu_upgrade")],
                    [InlineKeyboardButton("⬅️ Main Menu", callback_data="menu_back")],
                ]),
            )
            return MENU

        n = FREE_MOCK_SIZE
        try:
            pool = cbt_engine.ALL_QS or []
            if len(pool) < n:
                await q.edit_message_text("Databank is empty. Try again later.")
                return MENU
            qs = random.sample(pool, n)
        except Exception as e:
            await q.edit_message_text(f"Could not start mock: {e}")
            return MENU

        context.user_data["mock"] = {"index": 0, "score": 0, "questions": qs}
        await q.edit_message_text("📝 *Loading your free mock...*", parse_mode="Markdown")
        return await send_next_mock_question(update, context, via="callback")

    if data == "menu_tutor":
        text = (
            "🧠 *AI Tutor — Ask Any UTME Question*\n\n"
            "Type your question (Maths, English, Physics, Chemistry, Biology, "
            "Economics, Government, Literature, etc.).\n\n"
            "You'll get a clear step-by-step explanation plus a *voice note* "
            "you can replay.\n\n"
            "_Type /cancel or /menu to go back._"
        )
        await q.edit_message_text(text, parse_mode="Markdown")
        return TUTOR_ASK

    if data == "menu_upgrade":
        return await show_upgrade(update, context)

    if data == "menu_invite":
        bot_username = context.bot.username
        msg = referral_message(bot_username, uid)
        await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=back_to_menu())
        return MENU

    if data == "menu_stats":
        premium = is_premium(uid)
        text = (
            f"📊 *Your Stats*\n\n"
            f"Status: {'💎 Premium' if premium else '🆓 Free'}\n"
            f"Referrals: *{get_referral_count(uid)}*\n"
            f"Questions available: *{len(cbt_engine.ALL_QS)}*\n"
            f"Subjects loaded: *{len(cbt_engine.LOCAL_DATABANK)}*"
        )
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=back_to_menu())
        return MENU


async def send_next_mock_question(update, context, via="callback"):
    mock = context.user_data.get("mock")
    if not mock:
        return MENU

    idx = mock["index"]
    total = len(mock["questions"])
    if idx >= total:
        return await finish_mock(update, context, via=via)

    qd = mock["questions"][idx]
    text = cbt_engine.format_question(qd, idx + 1, total)

    buttons = []
    for L in ("A", "B", "C", "D", "E"):
        if qd.get(f"option_{L.lower()}"):
            buttons.append(InlineKeyboardButton(L, callback_data=f"ans_{L}"))
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    kb = InlineKeyboardMarkup(rows)

    if via == "callback" and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb)
    else:
        await update.message.reply_text(text, reply_markup=kb)
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
    await asyncio.sleep(1.2)
    return await send_next_mock_question(update, context, via="callback")


async def finish_mock(update, context, via="callback"):
    mock = context.user_data.get("mock") or {}
    score = mock.get("score", 0)
    total = len(mock.get("questions", [])) or 1
    uid = update.effective_user.id if update.effective_user else update.callback_query.from_user.id
    record_mock_taken(uid)

    text = (
        f"🎯 *Mock Complete!*\n\n"
        f"Score: *{score}/{total}*\n\n"
        f"{'Great job! 🌟' if score >= total * 0.6 else 'Keep practising! 💪'}\n\n"
        "💎 Want unlimited mocks and all subjects? Upgrade to Premium.\n"
        "🧠 Need explanations? Tap Ask Tutor."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="menu_upgrade")],
        [InlineKeyboardButton("🧠 Ask Tutor", callback_data="menu_tutor")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="menu_back")],
    ])
    if via == "callback" and update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
    context.user_data.pop("mock", None)
    return MENU


async def tutor_ask(update, context):
    text = (update.message.text or "").strip()
    if len(text) < 5:
        await update.message.reply_text("Please type your full question.")
        return TUTOR_ASK

    await update.message.reply_text("🧠 Thinking...")
    explanation = ask_tutor(text)
    await update.message.reply_text(explanation)

    voice = build_voice_inputfile(explanation)
    if voice:
        try:
            await update.message.reply_voice(voice=voice)
        except Exception as e:
            print(f"[tutor] voice send failed: {e}")

    await update.message.reply_text(
        "Ask another question, or tap /menu to return to the main menu."
    )
    return TUTOR_ASK


async def cancel(update, context):
    premium = is_premium(update.effective_user.id)
    status = "💎 Premium" if premium else "🆓 Free"
    await update.message.reply_text(
        f"*Main Menu* — Status: {status}",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )
    return MENU


async def show_upgrade(update, context):
    uid = update.effective_user.id if update.effective_user else update.callback_query.from_user.id
    link, tx_ref = create_payment_link(uid, amount_ngn=PREMIUM_PRICE_NGN)

    if not link:
        text = "⚠️ Payment link is unavailable right now. Please try again shortly."
        kb = back_to_menu()
    else:
        text = (
            f"💎 *Upgrade to Premium — ₦{PREMIUM_PRICE_NGN} / 30 days*\n\n"
            "✅ Unlimited mock exams\n"
            "✅ All subjects unlocked\n"
            "✅ Unlimited AI Tutor with voice\n"
            "✅ No daily limits\n"
            "✅ Priority access to new features\n\n"
            "Tap below to pay securely via Flutterwave 👇"
        )
        kb = upgrade_keyboard(link)

    if update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
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
    uid = update.effective_user.id
    tx_id = (update.message.text or "").strip()
    if not tx_id.isdigit():
        await update.message.reply_text("❌ Please send the transaction ID as a number.")
        return AWAIT_TX_ID

    ok, data = verify_transaction(tx_id)
    if ok:
        set_premium(uid, days=30)
        await update.message.reply_text(
            "✅ *Payment confirmed! Premium is active for 30 days.*\n\n"
            "Enjoy unlimited access 🎉",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
        return MENU

    await update.message.reply_text(
        "❌ Couldn't verify that transaction. Please check the ID and try again, "
        "or contact support if you were debited."
    )
    return AWAIT_TX_ID


async def unknown(update, context):
    await update.message.reply_text(
        "Use the menu below 👇", reply_markup=main_menu_keyboard()
    )
    return MENU


flask_app = Flask(__name__)


@flask_app.route("/")
def health():
    return "UTME Bot is running ✅", 200


@flask_app.route("/payment/callback", methods=["GET"])
def payment_callback():
    tx_id = request.args.get("transaction_id")
    if tx_id:
        ok, data = verify_transaction(tx_id)
        if ok:
            uid = extract_user_id_from_meta(data)
            if uid:
                set_premium(uid, days=30)
                return "✅ Payment successful! Return to the bot. Premium is active.", 200
    return "Payment received. Return to the bot to verify.", 200


@flask_app.route("/webhook/flutterwave", methods=["POST"])
def flutterwave_webhook():
    if not verify_webhook_signature(request):
        return jsonify({"status": "unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    if data.get("event") == "charge.completed" and data.get("data", {}).get("status") == "successful":
        uid = extract_user_id_from_meta(data)
        if uid:
            set_premium(uid, days=30)
            print(f"[webhook] premium activated for {uid}")
    return jsonify({"status": "ok"}), 200


def run_flask():
    port = int(os.getenv("PORT", "8080"))
    flask_app.run(host="0.0.0.0", port=port)


def main():
    init_db()
    threading.Thread(target=run_flask, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            MENU: [
                CallbackQueryHandler(menu_callback, pattern="^menu_"),
                CallbackQueryHandler(verify_payment_entry, pattern="^verify_payment$"),
            ],
            MOCK_A: [CallbackQueryHandler(mock_answer, pattern="^ans_")],
            TUTOR_ASK: [
                CommandHandler("cancel", cancel),
                CommandHandler("menu", cancel),
                CallbackQueryHandler(menu_callback, pattern="^menu_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, tutor_ask),
            ],
            AWAIT_TX_ID: [
                CommandHandler("cancel", cancel),
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
