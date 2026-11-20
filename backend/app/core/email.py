import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

import json
import os

logger = logging.getLogger(__name__)

# In-memory and file-based test mailbox for multi-process test verification without log exposure
_test_mailbox: dict[str, str] = {}
SCRATCH_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scratch"))
TEST_MAILBOX_FILE = os.path.join(SCRATCH_DIR, "test_mailbox.json")


def _save_test_mailbox(email: str, otp: str) -> None:
    try:
        os.makedirs(SCRATCH_DIR, exist_ok=True)
        data = {}
        if os.path.exists(TEST_MAILBOX_FILE):
            try:
                with open(TEST_MAILBOX_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data[email.strip().lower()] = otp
        with open(TEST_MAILBOX_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def get_last_test_otp(email: str) -> str | None:
    """Retrieve the most recent OTP sent to the given email during test execution."""
    mem_otp = _test_mailbox.get(email.strip().lower())
    if mem_otp:
        return mem_otp
    try:
        if os.path.exists(TEST_MAILBOX_FILE):
            with open(TEST_MAILBOX_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(email.strip().lower())
    except Exception:
        pass
    return None


def clear_test_mailbox() -> None:
    """Clear the test mailbox."""
    _test_mailbox.clear()
    try:
        if os.path.exists(TEST_MAILBOX_FILE):
            os.remove(TEST_MAILBOX_FILE)
    except Exception:
        pass


async def send_password_reset_otp_email(to_email: str, otp: str) -> bool:
    """
    Sends a 6-digit password reset OTP email.
    If SMTP credentials are provided in configuration, delivers email via SMTP.
    If not configured, records delivery safely in test mailbox and logs dispatch
    WITHOUT exposing the OTP value in application logs.
    """
    normalized_email = to_email.strip().lower()
    _test_mailbox[normalized_email] = otp
    if not (settings.smtp_host and settings.smtp_username):
        _save_test_mailbox(normalized_email, otp)


    subject = "Password Reset OTP - AI Interview Platform"
    text_content = f"""Hello,

We received a request to reset your password.

Your password reset OTP is: {otp}

This OTP is valid for 10 minutes.

If you did not request a password reset, you can safely ignore this email.
For security, never share this OTP with anyone.

Best regards,
AI Interview Platform Team
"""
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Password Reset OTP</title>
</head>
<body style="margin: 0; padding: 0; background-color: #030511; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f8fafc;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #030511; padding: 40px 10px;">
    <tr>
      <td align="center">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 540px; background: linear-gradient(180deg, #0e1326 0%, #070a18 100%); border-radius: 16px; border: 1px solid rgba(255,255,255,0.08); padding: 36px 28px; box-shadow: 0 20px 40px rgba(0,0,0,0.6);">
          <tr>
            <td align="center" style="padding-bottom: 24px;">
              <span style="display: inline-block; padding: 8px 18px; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); border-radius: 8px; color: #ffffff; font-weight: 700; font-size: 15px; letter-spacing: 1px;">
                AI INTERVIEW
              </span>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding-bottom: 12px;">
              <h2 style="margin: 0; font-size: 22px; font-weight: 600; color: #ffffff;">Password Reset Request</h2>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding-bottom: 28px;">
              <p style="margin: 0; font-size: 14px; line-height: 1.6; color: #94a3b8;">
                We received a request to reset your password. Use the single-use verification code below to proceed:
              </p>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding-bottom: 28px;">
              <div style="background: rgba(99, 102, 241, 0.08); border: 1px dashed rgba(99, 102, 241, 0.4); border-radius: 12px; padding: 18px 24px; display: inline-block;">
                <span style="font-family: 'Courier New', Courier, monospace; font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #818cf8;">
                  {otp}
                </span>
              </div>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding-bottom: 24px;">
              <p style="margin: 0; font-size: 13px; line-height: 1.5; color: #64748b;">
                This code will expire in <strong>10 minutes</strong>. If you did not request a password reset, you can safely ignore this email.
              </p>
            </td>
          </tr>
          <tr>
            <td style="border-top: 1px solid rgba(255,255,255,0.06); padding-top: 20px;" align="center">
              <p style="margin: 0; font-size: 12px; color: #475569;">
                AI-Powered Intelligent Interview & Career Preparation Platform
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    if settings.smtp_host and settings.smtp_username:
        def _send():
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.email_from
            msg["To"] = to_email
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(settings.email_from, [to_email], msg.as_string())

        try:
            await asyncio.to_thread(_send)
            logger.info("Password reset OTP email delivered via SMTP to %s", normalized_email)
            return True
        except Exception as exc:
            logger.error("Failed to deliver OTP email via SMTP to %s: %s", normalized_email, exc)
            return False
    else:
        logger.info("Password reset OTP email processed for %s (simulated mode)", normalized_email)
        return True
