"""Outbound email over SMTP - the transport, and nothing about what is said.

Provider-agnostic on purpose: Alibaba Cloud DirectMail, Resend, SES and Gmail all
speak SMTP, so switching provider is a change to .env rather than to code.

Delivery is best-effort and never raises into the caller. A reminder is recorded
on the task timeline before any email is attempted, so a mail server being down
loses the nudge's delivery, not the nudge itself - the employee still sees it in
their task view, and the founder's briefing still reports the silence.
"""

import logging
import smtplib
import ssl
import threading
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import make_msgid

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    text: str
    html: str


def _build(message: OutgoingEmail) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = message.to
    msg["Subject"] = message.subject
    msg["Message-ID"] = make_msgid(domain="sentinel.local")
    # Tells out-of-office responders not to reply. Without it an autoresponder can
    # answer every reminder, and the founder's inbox fills with "I'm away".
    msg["Auto-Submitted"] = "auto-generated"
    msg.set_content(message.text)
    msg.add_alternative(message.html, subtype="html")
    return msg


def _connect() -> smtplib.SMTP:
    timeout = settings.smtp_timeout_seconds
    if settings.smtp_use_ssl:
        return smtplib.SMTP_SSL(
            settings.smtp_host, settings.smtp_port, timeout=timeout,
            context=ssl.create_default_context(),
        )
    server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=timeout)
    if settings.smtp_starttls:
        server.starttls(context=ssl.create_default_context())
    return server


def send_all(messages: list[OutgoingEmail]) -> int:
    """Send over one connection. Returns how many were accepted by the server."""
    if not messages:
        return 0
    if not settings.email_enabled:
        logger.info("Email not configured; %d message(s) not sent.", len(messages))
        return 0

    sent = 0
    try:
        with _connect() as server:
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            for message in messages:
                try:
                    server.send_message(_build(message))
                    sent += 1
                except smtplib.SMTPException:
                    # One bad address must not stop the rest of the batch.
                    logger.exception("Email to %s was refused", message.to)
    except (OSError, smtplib.SMTPException):
        logger.exception("Could not reach the SMTP server at %s", settings.smtp_host)

    logger.info("Email: %d of %d sent", sent, len(messages))
    return sent


def dispatch(messages: list[OutgoingEmail]) -> threading.Thread | None:
    """Send in the background so no request waits on a mail server.

    The messages are fully built before this is called, so the thread never
    touches the caller's database session. A daemon thread can be lost if the
    process stops mid-send; that is acceptable for a notification whose content
    is already recorded in-app. Returns the thread so a test can join it.
    """
    if not messages or not settings.email_enabled:
        if messages:
            logger.info("Email not configured; %d message(s) not sent.", len(messages))
        return None
    thread = threading.Thread(
        target=send_all, args=(list(messages),), name="sentinel-mail", daemon=True
    )
    thread.start()
    return thread
