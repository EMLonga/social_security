import smtplib
from email.message import EmailMessage

from config import settings


def send_password_reset_code_email(to_email: str, code: str) -> dict:
    subject = "Community Safety Alert - Password Reset Code"
    body = (
        "You requested to reset your password.\n\n"
        f"Verification code: {code}\n"
        "This code will expire in 5 minutes.\n\n"
        "If you did not request this, please ignore this email."
    )

    if settings.EMAIL_DEV_MODE:
        return {
            "sent": False,
            "debug_code": code,
            "reason": "dev_mode",
        }

    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        return {
            "sent": False,
            "debug_code": code,
            "reason": "smtp_not_configured",
        }

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        if settings.SMTP_USE_TLS:
            smtp.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(message)
    return {"sent": True}
