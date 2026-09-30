"""
Minimal transactional email sender, used only for password-reset codes (see auth.py /
api_server.py's forgot_password). Uses Resend (a single HTTP POST, no SMTP setup) rather than
pulling in an SMTP library - same "optional key, feature degrades gracefully" pattern as
api.pexels_key/api.semantic_scholar_key in config.py: without PAPERBITES_RESEND_KEY set, this
logs a warning and returns False instead of raising, so the rest of the request (forgot_password
always returns a generic 200) doesn't depend on email actually being configured yet.
"""
import logging

import requests

from config import Config

logger = logging.getLogger("paperbites.email")

RESEND_API_URL = "https://api.resend.com/emails"


def send_password_reset_code(to_email: str, code: str) -> bool:
    """Send a password reset code by email. Returns whether it was actually sent."""
    config = Config()
    api_key = config.get("api.resend_key")
    if not api_key:
        logger.warning("PAPERBITES_RESEND_KEY not configured - skipping password reset email (code: %s)", code)
        return False

    from_email = config.get("api.resend_from_email")
    try:
        response = requests.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "from": from_email,
                "to": [to_email],
                "subject": "Your PaperBites password reset code",
                "html": (
                    f"<p>Your PaperBites password reset code is:</p>"
                    f"<p style=\"font-size: 24px; font-weight: bold; letter-spacing: 4px;\">{code}</p>"
                    f"<p>This code expires in 15 minutes. If you didn't request this, you can ignore this email.</p>"
                ),
            },
            timeout=10,
        )
        if response.status_code >= 300:
            logger.error("Resend API error %s: %s", response.status_code, response.text)
            return False
        return True
    except requests.RequestException as e:
        logger.error("Failed to send password reset email: %s", e)
        return False
