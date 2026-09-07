"""
email_service.py

Sends verification emails via SMTP (e.g. Gmail with an App Password - never
a real account password, see README "Email Verification Setup").

DEV MODE: if EMAIL_HOST/EMAIL_USER/EMAIL_APP_PASSWORD are not set in the
environment, this does NOT fail - it prints the verification link to the
backend console instead, so registration/verification works out of the box
for local development and testing without requiring any email setup at all.
This is intentional: the app should be fully runnable without a mail server.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def _clean_env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


EMAIL_HOST = _clean_env("EMAIL_HOST") or None
EMAIL_PORT = int(_clean_env("EMAIL_PORT", "587") or "587")
EMAIL_USER = _clean_env("EMAIL_USER") or None
EMAIL_APP_PASSWORD = _clean_env("EMAIL_APP_PASSWORD") or None
EMAIL_FROM_NAME = _clean_env("EMAIL_FROM_NAME", "PostPulse") or "PostPulse"
FRONTEND_URL = _clean_env("FRONTEND_URL", "http://localhost:5173") or "http://localhost:5173"
BREVO_API_KEY = _clean_env("BREVO_API_KEY") or None
RESEND_API_KEY = _clean_env("RESEND_API_KEY") or None

EMAIL_CONFIGURED = bool(BREVO_API_KEY or RESEND_API_KEY or (EMAIL_HOST and EMAIL_USER and EMAIL_APP_PASSWORD))


def send_verification_email(to_email: str, token: str) -> None:
    verify_link = f"{FRONTEND_URL}/verify-email?token={token}"

    if not EMAIL_CONFIGURED:
        print("\n" + "=" * 70)
        print(f"[DEV MODE - no email service configured] Verification link for {to_email}:")
        print(verify_link)
        print("=" * 70 + "\n")
        return

    text = f"Welcome to PostPulse!\n\nVerify your email by visiting:\n{verify_link}\n\nThis link expires in 24 hours.\n\nIf you don't see this email in your inbox, please check your spam or junk folder."
    html = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
      <h2>Welcome to PostPulse</h2>
      <p>Confirm your email address to start making predictions.</p>
      <p><a href="{verify_link}" style="background:#FF6B4A;color:#fff;padding:12px 24px;
         border-radius:8px;text-decoration:none;display:inline-block;">Verify Email</a></p>
      <p style="color:#888;font-size:13px;">This link expires in 24 hours. If you didn't sign up
      for PostPulse, you can ignore this email. If you don't see this in your inbox, check your
      spam or junk folder.</p>
    </div>
    """

    # 1. If Brevo API Key is set, send over HTTPS (recommended for Render free tier - sends to any email)
    if BREVO_API_KEY:
        try:
            import json
            import urllib.request
            sender_email = EMAIL_USER or "ganeswarikuramdasu@gmail.com"
            payload = {
                "sender": {"name": EMAIL_FROM_NAME, "email": sender_email},
                "to": [{"email": to_email}],
                "subject": "Verify your PostPulse account",
                "htmlContent": html,
            }
            req = urllib.request.Request(
                "https://api.brevo.com/v3/smtp/email",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "api-key": BREVO_API_KEY,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in (200, 201):
                    print(f"[EMAIL] Verification email sent via Brevo API to {to_email}")
                    return
        except Exception as brevo_err:
            print(f"[EMAIL WARNING] Brevo HTTP send failed: {brevo_err}")

    # 2. If Resend API Key is set, send over HTTPS (bypasses cloud host SMTP port blocks)
    if RESEND_API_KEY:
        try:
            import json
            import urllib.request
            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=json.dumps({
                    "from": f"{EMAIL_FROM_NAME} <onboarding@resend.dev>",
                    "to": [to_email],
                    "subject": "Verify your PostPulse account",
                    "html": html,
                }).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                    "User-Agent": "PostPulse/1.0",
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in (200, 201):
                    print(f"[EMAIL] Verification email sent via Resend to {to_email}")
                    return
        except Exception as resend_err:
            print(f"[EMAIL WARNING] Resend HTTP send failed: {resend_err}")

    # 2. Try standard SMTP (e.g. Gmail App Password)
    if EMAIL_HOST and EMAIL_USER and EMAIL_APP_PASSWORD:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Verify your PostPulse account"
            msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_USER}>"
            msg["To"] = to_email
            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10) as server:
                server.starttls()
                server.login(EMAIL_USER, EMAIL_APP_PASSWORD)
                server.sendmail(EMAIL_USER, to_email, msg.as_string())
            print(f"[EMAIL] Verification email sent via SMTP to {to_email}")
            return
        except Exception as smtp_err:
            print("\n" + "=" * 70)
            print(f"[EMAIL ERROR] SMTP connection failed: {smtp_err}")
            print("Note: Render Free Tier blocks outbound SMTP socket ports (25, 465, 587).")
            print(f"[VERIFICATION LINK FOR {to_email}]:")
            print(verify_link)
            print("=" * 70 + "\n")

