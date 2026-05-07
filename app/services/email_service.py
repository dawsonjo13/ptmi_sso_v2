import smtplib
from email.message import EmailMessage
from app.core.config import get_settings

settings = get_settings()


def send_password_reset_email(to_email: str, recipient_name: str | None, reset_url: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = "Reset your SSO password"
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    msg["To"] = to_email

    name = recipient_name or "there"
    text_body = f"""Hi {name},

We received a request to reset your SSO password.

Open this link to reset your password:
{reset_url}

This link will expire soon. If you did not request this, please ignore this email.
"""
    html_body = f"""
    <html>
      <body>
        <p>Hi {name},</p>
        <p>We received a request to reset your SSO password.</p>
        <p><a href="{reset_url}">Reset your password</a></p>
        <p>This link will expire soon. If you did not request this, please ignore this email.</p>
      </body>
    </html>
    """

    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        if settings.smtp_use_tls:
            server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
