import asyncio
import smtplib
import ssl
from datetime import UTC, datetime
from email.message import EmailMessage
from html import escape
from pathlib import Path

from src.config import settings
from src.mailer.constants import EmailTemplate
from src.mailer.exceptions import EmailDeliveryError

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


class MailerService:
    async def send_otp_email(
        self,
        *,
        email: str,
        otp_code: str,
        template: EmailTemplate,
    ) -> None:
        subject, file_name = self._get_template_config(template)

        content = (TEMPLATE_DIR / file_name).read_text(
            encoding="utf-8"
        )
        content = content.replace(
            "{{ otp_code }}",
            escape(otp_code),
        )
        html_content = (TEMPLATE_DIR / "base.html").read_text(
            encoding="utf-8"
        )
        html_content = (
            html_content.replace("{{ title }}", escape(subject))
            .replace("{{ content }}", content)
            .replace(
                "{{ current_year }}",
                str(datetime.now(UTC).year),
            )
        )

        message = EmailMessage()
        message["From"] = (
            f"Lucidex Support <{settings.EMAIL_SMTP_USER}>"
        )
        message["To"] = email
        message["Subject"] = subject
        message.set_content(
            "Your email client does not support HTML email."
        )
        message.add_alternative(
            html_content,
            subtype="html",
        )

        try:
            await asyncio.to_thread(
                self._send_sync,
                message,
            )
        except (smtplib.SMTPException, OSError) as exc:
            raise EmailDeliveryError() from exc

    @staticmethod
    def _get_template_config(
        template: EmailTemplate,
    ) -> tuple[str, str]:
        if template == EmailTemplate.REGISTER_OTP:
            return (
                "Activate your Lucidex account",
                "register_otp.html",
            )

        if template == EmailTemplate.RESET_PASSWORD_OTP:
            return (
                "Reset your Lucidex password",
                "reset_password_otp.html",
            )

        raise ValueError("Unsupported email template.")

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
