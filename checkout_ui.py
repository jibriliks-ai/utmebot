"""
checkout_ui.py — Professional HTML pages for the payment flow.
Pure CSS, no external assets, mobile-first.
"""

BRAND_GRADIENT = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"


def _base_css():
    return """
    * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      background-attachment: fixed;
      min-height: 100vh;
      padding: 16px;
      color: #1a1a1a;
      display: flex;
      align-items: flex-start;
      justify-content: center;
    }
    .card {
      max-width: 460px;
      width: 100%;
      background: #fff;
      border-radius: 24px;
      padding: 28px 24px 24px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.28);
      margin: 12px 0;
      animation: fadeUp 0.4s ease-out;
    }
    @keyframes fadeUp {
      from { opacity: 0; transform: translateY(12px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 20px;
    }
    .brand-logo {
      width: 40px;
      height: 40px;
      border-radius: 12px;
      background: linear-gradient(135deg, #667eea, #764ba2);
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 18px;
      box-shadow: 0 6px 16px rgba(102,126,234,0.35);
    }
    .brand-name {
      font-weight: 700;
      font-size: 15px;
      color: #1a1a1a;
      line-height: 1.2;
    }
    .brand-sub {
      font-size: 12px;
      color: #888;
      margin-top: 2px;
    }
    .badge {
      display: inline-block;
      background: linear-gradient(135deg, #ff6b6b, #ee5a24);
      color: #fff;
      font-size: 11px;
      font-weight: 800;
      padding: 6px 12px;
      border-radius: 100px;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      margin-bottom: 14px;
    }
    h1 {
      font-size: 26px;
      font-weight: 800;
      line-height: 1.15;
      margin-bottom: 6px;
      letter-spacing: -0.3px;
      color: #111;
    }
    .subtitle {
      color: #666;
      font-size: 14.5px;
      line-height: 1.5;
      margin-bottom: 22px;
    }
    .price-box {
      background: linear-gradient(135deg, #f6f8ff 0%, #eef1ff 100%);
      border-radius: 18px;
      padding: 24px 20px;
      text-align: center;
      margin-bottom: 22px;
      border: 2px solid #667eea;
      position: relative;
      overflow: hidden;
    }
    .price-box::after {
      content: '';
      position: absolute;
      top: -40px;
      right: -40px;
      width: 100px;
      height: 100px;
      background: rgba(102,126,234,0.08);
      border-radius: 50%;
    }
    .price-label {
      font-size: 12px;
      font-weight: 700;
      color: #667eea;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      margin-bottom: 8px;
    }
    .price-main {
      font-size: 44px;
      font-weight: 900;
      color: #1a1a1a;
      line-height: 1;
      letter-spacing: -1px;
    }
    .price-main .currency { font-size: 24px; vertical-align: top; margin-right: 2px; }
    .price-period {
      color: #666;
      font-size: 13.5px;
      margin-top: 6px;
    }
    .price-old {
      color: #999;
      text-decoration: line-through;
      font-size: 15px;
      margin-top: 10px;
      font-weight: 500;
    }
    .savings-pill {
      display: inline-block;
      background: #10b981;
      color: #fff;
      font-size: 12px;
      font-weight: 800;
      padding: 5px 12px;
      border-radius: 100px;
      margin-top: 10px;
      letter-spacing: 0.4px;
    }
    .benefits-title {
      font-size: 13px;
      font-weight: 700;
      color: #333;
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 12px;
    }
    .benefits { list-style: none; margin-bottom: 24px; }
    .benefits li {
      padding: 11px 0 11px 34px;
      position: relative;
      font-size: 14.5px;
      color: #2a2a2a;
      border-bottom: 1px solid #f2f2f5;
      line-height: 1.4;
    }
    .benefits li:last-child { border-bottom: none; }
    .benefits li::before {
      content: '✓';
      position: absolute;
      left: 0;
      top: 11px;
      width: 22px;
      height: 22px;
      background: #10b981;
      color: #fff;
      border-radius: 50%;
      text-align: center;
      line-height: 22px;
      font-weight: 800;
      font-size: 12px;
      box-shadow: 0 3px 8px rgba(16,185,129,0.35);
    }
    .cta {
      display: block;
      width: 100%;
      background: linear-gradient(135deg, #667eea, #764ba2);
      color: #fff;
      border: none;
      padding: 18px;
      border-radius: 14px;
      font-size: 16.5px;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
      text-align: center;
      transition: transform 0.15s, box-shadow 0.15s;
      box-shadow: 0 10px 24px rgba(102,126,234,0.4);
      letter-spacing: 0.2px;
    }
    .cta:hover, .cta:active {
      transform: translateY(-1px);
      box-shadow: 0 14px 30px rgba(102,126,234,0.5);
    }
    .cta.secondary {
      background: #fff;
      color: #667eea;
      border: 2px solid #667eea;
      box-shadow: none;
      margin-top: 10px;
    }
    .trust {
      text-align: center;
      color: #888;
      font-size: 12px;
      margin-top: 16px;
      line-height: 1.7;
    }
    .trust .lock { color: #10b981; font-weight: 700; }
    .support {
      text-align: center;
      margin-top: 22px;
      padding-top: 18px;
      border-top: 1px solid #eee;
      font-size: 13px;
      color: #666;
      line-height: 1.6;
    }
    .support a { color: #667eea; text-decoration: none; font-weight: 700; }
    .success-icon {
      width: 84px;
      height: 84px;
      border-radius: 50%;
      background: linear-gradient(135deg, #10b981, #059669);
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 44px;
      font-weight: 800;
      margin: 8px auto 20px;
      box-shadow: 0 12px 30px rgba(16,185,129,0.4);
      animation: pop 0.5s ease-out;
    }
    @keyframes pop {
      0% { transform: scale(0.4); opacity: 0; }
      60% { transform: scale(1.1); }
      100% { transform: scale(1); opacity: 1; }
    }
    .center { text-align: center; }
    .divider {
      height: 1px;
      background: #f0f0f5;
      margin: 22px 0;
    }
    .compare {
      background: #fafbff;
      border-radius: 14px;
      padding: 16px 18px;
      margin-bottom: 22px;
    }
    .compare-row {
      display: flex;
      justify-content: space-between;
      padding: 8px 0;
      font-size: 14px;
      color: #444;
    }
    .compare-row.bold {
      font-weight: 700;
      color: #111;
      border-top: 1px solid #e8e8f0;
      padding-top: 12px;
      margin-top: 6px;
    }
    .compare-row .win { color: #10b981; font-weight: 700; }
    """


def _page(title, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<meta name="theme-color" content="#667eea">
<title>{title}</title>
<style>{_base_css()}</style>
</head>
<body>
{body}
</body>
</html>"""


def checkout_page(plan: dict, uid: int, bot_link: str = "https://t.me/UTMESUCCESS"):
    """Professional checkout page with benefits and pay button."""
    plan_id = plan["id"]
    label = plan["label"]
    amount = f"{plan['amount']:,}"
    regular = f"{plan['regular']:,}"
    save = f"{plan['save']:,}"
    is_six = plan_id == "6m"

    old_price_html = (
        f'<div class="price-old">Regular price: ₦{regular}</div>'
        if is_six else ""
    )
    save_html = (
        f'<div><span class="savings-pill">🔥 SAVE ₦{save} (50% OFF)</span></div>'
        if is_six else ""
    )

    compare_html = ""
    if is_six:
        compare_html = """
        <div class="compare">
          <div class="compare-row"><span>1 Month plan</span><span>₦2,000</span></div>
          <div class="compare-row"><span>6 × 1 Month =</span><span>₦12,000</span></div>
          <div class="compare-row bold"><span>6 Months plan</span><span class="win">₦6,000 — you save ₦6,000</span></div>
        </div>
        """

    body = f"""
    <div class="card">
      <div class="brand">
        <div class="brand-logo">U</div>
        <div>
          <div class="brand-name">UTME Success Coach</div>
          <div class="brand-sub">JAMB Prep Companion</div>
        </div>
      </div>

      <span class="badge">Premium Upgrade</span>
      <h1>Unlock Unlimited UTME Practice</h1>
      <p class="subtitle">Join thousands of students who practise without limits, learn faster with the AI Tutor, and walk into JAMB fully prepared.</p>

      <div class="price-box">
        <div class="price-label">{label} Plan</div>
        <div class="price-main"><span class="currency">₦</span>{amount}</div>
        <div class="price-period">for {label.lower()} of full access</div>
        {old_price_html}
        {save_html}
      </div>

      {compare_html}

      <div class="benefits-title">What you unlock</div>
      <ul class="benefits">
        <li>Unlimited mock exams, anytime</li>
        <li>All subjects unlocked (Maths, English, Sciences, Arts, Commercial)</li>
        <li>AI Tutor — voice explanations for every question</li>
        <li>No 24-hour wait between mocks</li>
        <li>Instant feedback with detailed answers</li>
        <li>Full access to 3,000+ past questions</li>
        <li>Priority support from our team</li>
        <li>Automatic access to all new features</li>
      </ul>

      <form method="POST" action="/checkout/pay">
        <input type="hidden" name="uid" value="{uid}">
        <input type="hidden" name="plan" value="{plan_id}">
        <button type="submit" class="cta">Pay ₦{amount} with Flutterwave →</button>
      </form>

      <a href="{bot_link}" class="cta secondary">← Cancel &amp; Return to Bot</a>

      <div class="trust">
        <span class="lock">🔒 Secure Payment</span> · Encrypted via Flutterwave<br>
        Cards · Bank Transfer · USSD · Instant activation
      </div>

      <div class="support">
        Need help? Chat with us on Telegram<br>
        <a href="https://t.me/UTMESUCCESS">@UTMESUCCESS</a>
      </div>
    </div>
    """
    return _page(f"Upgrade — {label} | UTME Success Coach", body)


def success_page(plan: dict, bot_link: str = "https://t.me/UTMESUCCESS"):
    label = plan["label"] if plan else "Premium"
    body = f"""
    <div class="card center">
      <div class="success-icon">✓</div>
      <h1>Payment Successful!</h1>
      <p class="subtitle">Your <strong>{label}</strong> Premium is now active. Enjoy unlimited access to every part of the bot.</p>

      <div class="divider"></div>

      <div class="benefits-title">You now have</div>
      <ul class="benefits" style="text-align:left;">
        <li>Unlimited mocks — no daily wait</li>
        <li>Every subject unlocked</li>
        <li>AI Tutor with voice — unlimited</li>
        <li>Priority support</li>
      </ul>

      <a href="{bot_link}" class="cta">Return to Bot →</a>

      <div class="support">
        Questions? <a href="https://t.me/UTMESUCCESS">@UTMESUCCESS</a>
      </div>
    </div>
    """
    return _page("Payment Successful | UTME Success Coach", body)


def pending_page(bot_link: str = "https://t.me/UTMESUCCESS"):
    body = f"""
    <div class="card center">
      <h1>Verifying your payment…</h1>
      <p class="subtitle">We received your payment reference. If your Premium doesn't activate in the bot within 60 seconds, tap the "I've Paid — Verify Now" button and paste your transaction ID.</p>
      <a href="{bot_link}" class="cta">Return to Bot →</a>
      <div class="support">
        Need help? <a href="https://t.me/UTMESUCCESS">@UTMESUCCESS</a>
      </div>
    </div>
    """
    return _page("Verifying Payment | UTME Success Coach", body)


def error_page(message: str = "Something went wrong."):
    body = f"""
    <div class="card center">
      <h1>Payment Error</h1>
      <p class="subtitle">{message}</p>
      <a href="https://t.me/UTMESUCCESS" class="cta">Contact Support →</a>
    </div>
    """
    return _page("Payment Error | UTME Success Coach", body)