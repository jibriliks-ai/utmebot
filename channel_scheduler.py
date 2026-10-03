"""
channel_scheduler.py
Posts 3 educational messages per day to your Telegram channel.
"""
import os
import random
import datetime as dt
import pytz

CHANNEL_ID = os.environ.get("CHANNEL_ID", "")
BOT_LINK = os.environ.get("BOT_LINK", "https://t.me/YourBotUsername")

WAT = pytz.timezone("Africa/Lagos")


POSTS = [
    "📐 *Maths Drill*\n\nConvert 234 (base 5) to base 10.\n\nA) 69   B) 65   C) 59   D) 124\n\n_Think first, then tap below for instant explanation._",
    "📐 *Maths Drill*\n\nSimplify 2³ × 2⁴.\n\nA) 128   B) 64   C) 32   D) 256\n\n_Know your indices cold — they appear every year._",
    "📐 *Maths Drill*\n\nIf (x-2) is a factor of x² - 5x + k, find k.\n\nA) 6   B) 5   C) 4   D) -6",
    "📐 *Maths Drill*\n\nSolve: x + y = 7, x − y = 3.\n\nA) x=5,y=2   B) x=2,y=5   C) x=4,y=3   D) x=3,y=4",
    "📚 *English Tip*\n\nChoose the correctly spelt word:\n\nA) Necessary   B) Neccessary   C) Necesary   D) Necessery\n\n_Spelling questions are free marks — don't lose them._",
    "📚 *English Tip*\n\nChoose the correctly spelt word:\n\nA) Occurrence   B) Occurence   C) Occurance   D) Ocurrence",
    "📚 *English Tip*\n\nChoose the correctly spelt word:\n\nA) Embarrass   B) Embarass   C) Embarras   D) Embaras",
    "🧬 *Biology Focus*\n\nWhich organelle is the powerhouse of the cell?\n\nA) Nucleus   B) Ribosome   C) Mitochondrion   D) Golgi body",
    "🧬 *Biology Focus*\n\nThe process by which plants make food using sunlight is called:\n\nA) Respiration   B) Photosynthesis   C) Transpiration   D) Digestion",
    "⚛️ *Physics Focus*\n\nWhich of the following is a fundamental quantity?\n\nA) Force   B) Velocity   C) Mass   D) Pressure",
    "⚛️ *Physics Focus*\n\nAt what angle is the horizontal range of a projectile maximum?\n\nA) 30°   B) 45°   C) 60°   D) 90°",
    "🧪 *Chemistry Focus*\n\nThe atomic number of an element equals the number of:\n\nA) Neutrons   B) Protons   C) Nucleons   D) Electrons + neutrons",
    "💼 *Commerce Focus*\n\nCommerce is best defined as:\n\nA) Production of goods   B) Distribution and exchange of goods   C) Consumption   D) Regulation",
    "🏛 *Government Focus*\n\nThe ability to compel obedience to commands is called:\n\nA) Authority   B) Power   C) Legitimacy   D) Sovereignty",
    "💹 *Economics Focus*\n\nOpportunity cost is best defined as:\n\nA) Money cost   B) The next best alternative forgone   C) Total cost   D) Fixed cost",
    "📖 *Literature Focus*\n\nA play that ends with the downfall or death of the protagonist is:\n\nA) Comedy   B) Tragedy   C) Farce   D) Melodrama",
    "✝️ *CRK Focus*\n\nAccording to Genesis, what did God do on the seventh day?\n\nA) Created man   B) Rested   C) Made light   D) Made animals",
]


def _pick_message():
    return random.choice(POSTS)


def _format_for_channel(text: str) -> str:
    return text + f"\n\n👉 [Start Free Mock or Ask Tutor]({BOT_LINK})"


async def post_to_channel(context):
    if not CHANNEL_ID:
        print("[scheduler] CHANNEL_ID not set — skipping post")
        return
    msg = _format_for_channel(_pick_message())
    try:
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=msg,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
        print("[scheduler] channel post sent")
    except Exception as e:
        print(f"[scheduler] post failed: {e}")


def register_jobs(job_queue):
    job_queue.run_daily(post_to_channel, time=dt.time(8, 30, tzinfo=WAT))
    job_queue.run_daily(post_to_channel, time=dt.time(13, 0, tzinfo=WAT))
    job_queue.run_daily(post_to_channel, time=dt.time(20, 0, tzinfo=WAT))
    print("[scheduler] 3 daily posts scheduled (08:30, 13:00, 20:00 WAT)")