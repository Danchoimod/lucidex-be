import asyncio
import logging
import re
import smtplib
import ssl
from collections.abc import Mapping
from datetime import UTC, datetime
from email.message import EmailMessage
from html import escape, unescape
from pathlib import Path

from src.config import settings
from src.mailer.config import (
    APPLICATION_REVIEW_SLA_DAYS,
    EMAIL_TEMPLATE_CONFIGS,
)
from src.mailer.constants import EmailTemplate
from src.mailer.exceptions import EmailDeliveryError, EmailTemplateError

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")
logger = logging.getLogger("lucidex.mailer")


class MailerService:
    def __init__(
        self,
        *,
        template_dir: Path = TEMPLATE_DIR,
    ) -> None:
        self._template_dir = template_dir

    async def send_otp_email(
        self,
        *,
        email: str,
        otp_code: str,
        template: EmailTemplate,
    ) -> None:
        await self.send_email(
            email=email,
            template=template,
            context={"otp_code": otp_code},
        )

    async def send_welcome_email(
        self,
        *,
        email: str,
        owner_name: str,
    ) -> None:
        try:
            await self.send_email(
                email=email,
                template=EmailTemplate.OWNER_WELCOME,
                context={
                    "owner_name": owner_name,
                    "login_url": (
                        f"{settings.FRONTEND_BASE_URL.rstrip('/')}/login"
                    ),
                },
            )
        except (EmailDeliveryError, EmailTemplateError):
            logger.error(
                "owner_welcome_email_failed",
                extra={"failure_reason": "email_delivery_failed"},
            )

    async def send_email(
        self,
        *,
        email: str,
        template: EmailTemplate,
        context: Mapping[str, object],
    ) -> None:
        self._validate_smtp_config()
        message = self._build_message(email, template, context)

        try:
            await asyncio.to_thread(self._send_sync, message)
        except (smtplib.SMTPException, OSError) as exc:
            raise EmailDeliveryError() from exc

    def _build_message(
        self,
        email: str,
        template: EmailTemplate,
        context: Mapping[str, object],
    ) -> EmailMessage:
        subject_template, file_name = self._get_template_config(template)
        values = {**context, "review_sla_days": APPLICATION_REVIEW_SLA_DAYS}
        subject = self._render(subject_template, values)
        content = self._render(self._read_template(file_name), values, html=True)
        html = (
            self._read_template("base.html")
            .replace("{{ title }}", escape(subject))
            .replace("{{ content }}", content)
            .replace("{{ current_year }}", str(datetime.now(UTC).year))
        )

        message = EmailMessage()
        message["From"] = f"Lucidex Support <{settings.EMAIL_SMTP_USER}>"
        message["To"] = email
        message["Subject"] = subject
        message.set_content(
            f"{subject}\n\n{self._to_plain_text(content)}",
            charset="utf-8",
        )
        message.add_alternative(html, subtype="html", charset="utf-8")
        return message

    @staticmethod
    def _render(
        source: str,
        context: Mapping[str, object],
        *,
        html: bool = False,
    ) -> str:
        missing = set(PLACEHOLDER_PATTERN.findall(source)) - context.keys()
        if missing:
            fields = ", ".join(sorted(missing))
            raise EmailTemplateError(f"Missing template values: {fields}.")

        def replace(match: re.Match[str]) -> str:
            value = str(context[match.group(1)])
            return escape(value) if html else value

        return PLACEHOLDER_PATTERN.sub(replace, source)

    @staticmethod
    def _to_plain_text(content: str) -> str:
        text = re.sub(r"<[^>]+>", " ", content)
        return " ".join(unescape(text).split())

    @staticmethod
    def _get_template_config(
        template: EmailTemplate,
    ) -> tuple[str, str]:
        try:
            return EMAIL_TEMPLATE_CONFIGS[EmailTemplate(template)]
        except (ValueError, KeyError) as exc:
            raise EmailTemplateError(
                f"Unsupported email template: {template!r}."
            ) from exc

    def _read_template(self, file_name: str) -> str:
        try:
            return (self._template_dir / file_name).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise EmailTemplateError(
                f"Unable to load email template: {file_name}."
            ) from exc

    @staticmethod
    def _validate_smtp_config() -> None:
        if not all(
            (
                settings.EMAIL_SMTP_HOST,
                settings.EMAIL_SMTP_USER,
                settings.EMAIL_SMTP_PASSWORD,
            )
        ):
            raise EmailDeliveryError("SMTP configuration is incomplete.")

    @staticmethod
    def _send_sync(
        message: EmailMessage,
    ) -> None:
        with smtplib.SMTP(
            settings.EMAIL_SMTP_HOST,
            settings.EMAIL_SMTP_PORT or 587,
            timeout=10,
        ) as smtp:
            smtp.starttls(
                context=ssl.create_default_context()
            )
            smtp.login(
                settings.EMAIL_SMTP_USER,
                settings.EMAIL_SMTP_PASSWORD,
            )
            smtp.send_message(message)


mailer_service = MailerService()
