"""Module: email_service.py"""

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import NameEmail, SecretStr

from src.config.settings import settings
from src.core.exceptions.exceptions import BadRequestException
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
    """Function to send an email using the FastMail library. This function constructs an email message with the specified recipient, subject, and body, and then attempts to send it using the configured email server settings. It includes error handling to manage any exceptions that may arise during the email sending process, logging any errors encountered and returning a boolean value indicating the success or failure of the operation."""
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
    except BadRequestException as err:
        logger.exception(f"Email sending failed: {err}")
        return False
