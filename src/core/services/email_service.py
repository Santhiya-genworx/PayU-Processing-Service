# email.py — replace send_email_sync wrapper
import asyncio
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from src.core.config.settings import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

fm = FastMail(conf)

async def send_email(to: str, subject: str, message: str) -> bool:

    email_message = MessageSchema(
        subject=subject,
        recipients=[to],
        body=message,
        subtype=MessageType.plain,
    )

    try:
        await fm.send_message(email_message)
        print(f"Email sent to {to}")
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False