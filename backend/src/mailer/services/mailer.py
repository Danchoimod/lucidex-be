import asyncio
import smtplib
import ssl
from datetime import UTC, datetime
from email.message import EmailMessage
from html import escape
from pathlib import Path

from src.config import settings
from src.mailer.config import EMAIL_TEMPLATE_CONFIGS, TemplateConfig
from src.mailer.constants import EmailTemplate
from src.mailer.exceptions import EmailDeliveryError, EmailTemplateError

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


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
        self._validate_smtp_config()
        message = self.build_otp_message(email, otp_code, template)

        try:
            await asyncio.to_thread(self._send_sync, message)
        except (smtplib.SMTPException, OSError) as exc:
            raise EmailDeliveryError() from exc

    def build_otp_message(
        self,
        email: str,
        otp_code: str,
        template: EmailTemplate,
    ) -> EmailMessage:
        subject, file_name = self._get_template_config(template)
        content = self._read_template(file_name).replace(
            "{{ otp_code }}", escape(otp_code)
        )
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
            f"{subject}\n\n"
            f"Your verification code is: {otp_code}\n"
            "This code expires in 5 minutes. Do not share it with anyone."
        )
        message.add_alternative(html, subtype="html")
        return message

    @staticmethod
    def _get_template_config(
        template: EmailTemplate,
    ) -> TemplateConfig:
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
