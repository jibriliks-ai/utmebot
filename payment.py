"""
payment.py — Flutterwave v3 API integration (direct HTTP, no SDK).
Creates hosted checkout links and verifies transactions.
"""
import os
import time
import hmac
import requests

FLW_SECRET_KEY = os.getenv("FLW_SECRET_KEY", "")
FLW_PUBLIC_KEY = os.getenv("FLW_PUBLIC_KEY", "")
FLW_SECRET_HASH = os.getenv("FLW_SECRET_HASH", "")

FLW_BASE = "https://api.flutterwave.com/v3"


def create_payment_link(user_id: int, amount_ngn: int, email: str = "student@utmebot.com"):
    """
    Create a Flutterwave hosted checkout link.
    Returns (checkout_url, tx_ref) or (None, None) on failure.
    """
    if not FLW_SECRET_KEY:
        print("[payment] FLW_SECRET_KEY missing")
        return None, None

    tx_ref = f"utmebot_{user_id}_{int(time.time())}"
    payload = {
        "tx_ref": tx_ref,
        "amount": str(amount_ngn),
        "currency": "NGN",
        "redirect_url": "https://utmebot.onrender.com/payment/callback",
        "payment_options": "card,banktransfer,ussd",
        "customer": {
            "email": email,
            "name": "UTME Student",
        },
        "customizations": {
            "title": "UTME Success Coach — Premium",
            "description": "30-day unlimited access: mocks, tutor, all subjects",
        },
        "meta": {
            "user_id": user_id,
            "product": "premium_30d",
        },
    }

    headers = {
        "Authorization": f"Bearer {FLW_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    try:
        r = requests.post(f"{FLW_BASE}/payments", json=payload, headers=headers, timeout=20)
        data = r.json()
        if data.get("status") == "success" and data.get("data", {}).get("link"):
            return data["data"]["link"], tx_ref
        print(f"[payment] create link failed: {data}")
        return None, None
    except Exception as e:
        print(f"[payment] create link error: {e}")
        return None, None


def verify_transaction(transaction_id: str):
    """
    Verify a Flutterwave transaction by its transaction_id.
    Returns (True, data) or (False, None).
    """
    if not FLW_SECRET_KEY:
        return False, None

    headers = {"Authorization": f"Bearer {FLW_SECRET_KEY}"}
    try:
        r = requests.get(
            f"{FLW_BASE}/transactions/{transaction_id}/verify",
            headers=headers,
            timeout=20,
        )
        data = r.json()
        if data.get("status") == "success":
            tx = data.get("data", {})
            if tx.get("status") == "successful":
                return True, tx
        return False, None
    except Exception as e:
        print(f"[payment] verify error: {e}")
        return False, None


def verify_webhook_signature(request) -> bool:
    """
    Flutterwave sends the plain secret hash in the verif-hash header.
    Compare it directly against FLW_SECRET_HASH.
    """
    if not FLW_SECRET_HASH:
        print("[payment] FLW_SECRET_HASH not set")
        return False
    signature = request.headers.get("verif-hash", "")
    return hmac.compare_digest(signature, FLW_SECRET_HASH)


def extract_user_id_from_meta(data: dict):
    """Pull user_id from Flutterwave meta field."""
    try:
        return int(data.get("meta", {}).get("user_id"))
    except (TypeError, ValueError, AttributeError):
        return None
