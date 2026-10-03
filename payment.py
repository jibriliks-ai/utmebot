"""
payment.py
Flutterwave payment integration for UTME Bot.
"""
import os
import time
import hmac

try:
    from rave_python import Rave
    RAVE_AVAILABLE = True
except ImportError:
    RAVE_AVAILABLE = False

FLW_PUBLIC_KEY = os.getenv("FLW_PUBLIC_KEY", "")
FLW_SECRET_KEY = os.getenv("FLW_SECRET_KEY", "")
FLW_SECRET_HASH = os.getenv("FLW_SECRET_HASH", "")

if RAVE_AVAILABLE and FLW_PUBLIC_KEY and FLW_SECRET_KEY:
    rave = Rave(
        FLW_PUBLIC_KEY,
        FLW_SECRET_KEY,
        usingEnv=False,
        production=True,
    )
else:
    rave = None


def create_payment_link(user_id: int, amount_ngn: int, email: str = "student@utmebot.com"):
    """Create a Flutterwave payment link. Returns (url, tx_ref) or (None, None)."""
    if rave is None:
        print("[payment] Rave not initialized — check FLW keys")
        return None, None

    tx_ref = f"utmebot_premium_{user_id}_{int(time.time())}"
    try:
        res = rave.Standard.charge(
            {
                "cardno": "",
                "cvv": "",
                "expirymonth": "",
                "expiryyear": "",
                "amount": amount_ngn,
                "email": email,
                "phonenumber": "",
                "firstname": "UTME",
                "lastname": "Student",
                "IP": "0.0.0.0",
                "txRef": tx_ref,
                "currency": "NGN",
                "redirect_url": "https://utmebot.onrender.com/payment/callback",
                "payment_options": "card,banktransfer,ussd",
                "meta": {"user_id": user_id, "product": "premium_30d"},
            }
        )
        if res and res.get("data", {}).get("link"):
            return res["data"]["link"], tx_ref
        return None, None
    except Exception as e:
        print(f"[payment] create link failed: {e}")
        return None, None


def verify_transaction(transaction_id: str):
    """Verify a Flutterwave transaction by ID. Returns (True, data) or (False, None)."""
    if rave is None:
        return False, None
    try:
        res = rave.Transaction.verify(transaction_id)
        if res and res.get("status") == "success":
            data = res.get("data", {})
            if data.get("status") == "successful":
                return True, data
        return False, None
    except Exception as e:
        print(f"[payment] verify failed: {e}")
        return False, None


def verify_webhook_signature(request) -> bool:
    """Verify Flutterwave webhook using the verif-hash header."""
    if not FLW_SECRET_HASH:
        print("[payment] FLW_SECRET_HASH not set")
        return False
    signature = request.headers.get("verif-hash", "")
    return hmac.compare_digest(signature, FLW_SECRET_HASH)


def extract_user_id_from_meta(webhook_data: dict):
    """Pull user_id from webhook meta field."""
    try:
        return int(webhook_data.get("data", {}).get("meta", {}).get("user_id"))
    except (TypeError, ValueError):
        return None
