"""
referrals.py
Generates each user's unique referral link.
"""
from user_manager import get_referral_count


def build_referral_link(bot_username: str, user_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref_{user_id}"


def referral_message(bot_username: str, user_id: int) -> str:
    link = build_referral_link(bot_username, user_id)
    count = get_referral_count(user_id)
    return (
        "🤝 *Invite Friends, Earn Rewards*\n\n"
        "Share your personal link below. Every friend who joins the bot "
        "through your link counts towards your reward — 5 successful invites "
        "unlock 1 day of free Premium!\n\n"
        f"Your link:\n`{link}`\n\n"
        f"Friends joined so far: *{count}*"
    )


def parse_referral_arg(args):
    if not args:
        return None
    first = args[0]
    if isinstance(first, str) and first.startswith("ref_"):
        try:
            return int(first.replace("ref_", ""))
        except ValueError:
            return None
    return None