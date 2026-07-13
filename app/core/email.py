import smtplib
from email.message import EmailMessage
from typing import Protocol

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailClient(Protocol):
    async def send(self, to: str, subject: str, body: str) -> None: ...


class SMTPClient:
    def __init__(
        self,
        host: str,
        port: int,
        from_addr: str,
        user: str | None = None,
        password: str | None = None,
        use_tls: bool = False,
    ) -> None:
        self._host = host
        self._port = port
        self._from_addr = from_addr
        self._user = user
        self._password = password
        self._use_tls = use_tls

    async def send(self, to: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"] = self._from_addr
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        msg.add_alternative(body, subtype="html")

        try:
            with smtplib.SMTP(self._host, self._port) as server:
                if self._use_tls:
                    server.starttls()
                if self._user and self._password:
                    server.login(self._user, self._password)
                server.send_message(msg)
            logger.info("Email sent to %s via SMTP", to)
        except Exception:
            logger.exception("Failed to send SMTP email to %s", to)
            raise


class ResendClient:
    def __init__(self, api_key: str, from_addr: str) -> None:
        self._api_key = api_key
        self._from_addr = from_addr

    async def send(self, to: str, subject: str, body: str) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": self._from_addr,
                    "to": to,
                    "subject": subject,
                    "html": body,
                },
                timeout=30,
            )
            if response.status_code >= 400:
                logger.error(
                    "Resend API error: %s %s", response.status_code, response.text
                )
                response.raise_for_status()
            logger.info("Email sent to %s via Resend", to)


class NoopEmailClient:
    async def send(self, to: str, subject: str, body: str) -> None:
        logger.info("Skipping email to %s (no-op client)", to)


def get_email_client() -> EmailClient:
    provider = settings.mail_provider.lower()

    if provider == "resend":
        if not settings.resend_api_key:
            raise ValueError("RESEND_API_KEY is required when MAIL_PROVIDER=resend")
        from_addr = settings.resend_from or settings.mail_from
        return ResendClient(api_key=settings.resend_api_key, from_addr=from_addr)

    if provider == "smtp":
        return SMTPClient(
            host=settings.smtp_host,
            port=settings.smtp_port,
            from_addr=settings.mail_from,
            user=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_tls,
        )

    if provider == "mailpit":
        return SMTPClient(
            host=settings.smtp_host,
            port=settings.smtp_port,
            from_addr=settings.mail_from,
        )

    return NoopEmailClient()
