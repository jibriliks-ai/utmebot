"""
payment.py — Flutterwave v3 API integration (direct HTTP).
Supports two plans: 1 month ₦2,000 and 6 months ₦6,000.
"""
import os
import time
import hmac
import requests

FLW_SECRET_KEY = os.getenv("FLW_SECRET_KEY", "")
FLW_PUBLIC_KEY = os.getenv("FLW_PUBLIC_KEY", "")
FLW_SECRET_HASH = os.getenv("FLW_SECRET_HASH", "")

FLW_BASE = "https://api.flutterwave.com/v3"

PLANS = {
    "1m": {"id": "1m", "label": "1 Month",  "amount": 2000, "days": 30,  "regular": 2000,  "save": 0},
    "6m": {"id": "6m", "label": "6 Months", "amount": 6000, "days": 180, "regular": 12000, "save": 6000},
}


def get_plan(plan_id):
    return PLANS.get(plan_id)


def create_payment_link(user_id: int, plan_id: str, email: str = "student@utmebot.com"):
    """
    Create a Flutterwave hosted checkout link for the given plan.
    Returns (checkout_url, tx_ref) or (None, None).
    """
    if not FLW_SECRET_KEY:
        print("[payment] FLW_SECRET_KEY missing")
        return None, None

    plan = PLANS.get(plan_id)
    if not plan:
        print(f"[payment] unknown plan: {plan_id}")
        return None, None

    tx_ref = f"utmebot_{user_id}_{plan_id}_{int(time.time())}"

    payload = {
        "tx_ref": tx_ref,
        "amount": str(plan["amount"]),
        "currency": "NGN",
        "redirect_url": "https://utmebot.onrender.com/payment/callback",
        "payment_options": "card,banktransfer,ussd",
        "customer": {
            "email": email,
            "name": "UTME Student",
        },
        "customizations": {
            "title": f"UTME Success Coach — {plan['label']} Premium",
            "description": f"{plan['label']} unlimited access: mocks, tutor, all subjects",
        },
        "meta": {
            "user_id": user_id,
            "plan_id": plan_id,
            "product": f"premium_{plan_id}",
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
    """Verify a Flutterwave transaction by ID. Returns (True, data) or (False, None)."""
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
    if not FLW_SECRET_HASH:
        print("[payment] FLW_SECRET_HASH not set")
        return False
    signature = request.headers.get("verif-hash", "")
    return hmac.compare_digest(signature, FLW_SECRET_HASH)


def extract_user_id_from_meta(data: dict):
    try:
        return int(data.get("meta", {}).get("user_id"))
    except (TypeError, ValueError, AttributeError):
        return None


def extract_plan_id_from_meta(data: dict):
    try:
        return str(data.get("meta", {}).get("plan_id", "1m"))
    except Exception:
        return "1m"


def days_for_plan(plan_id: str) -> int:
    plan = PLANS.get(plan_id)
    return plan["days"] if plan else 30
