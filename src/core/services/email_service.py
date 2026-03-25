from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import NameEmail, SecretStr

from src.core.config.settings import settings
from src.observability.logging.logging_config import logger

conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=SecretStr(settings.mail_password),
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
        recipients=[NameEmail(email=to, name=to)],
        body=message,
        subtype=MessageType.plain,
    )

    try:
        await fm.send_message(email_message)
        logger.info(f"Email sent to {to}")
        return True
    except Exception as e:
        logger.error(f"Email sending failed: {e}")
        return False
