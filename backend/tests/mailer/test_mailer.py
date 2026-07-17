from pathlib import Path

import pytest

from src.mailer import (
    EmailTemplate,
    EmailTemplateError,
    MailerService,
)

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "src" / "mailer" / "templates"


@pytest.mark.parametrize(
    ("template", "subject_fragment", "body_fragment"),
    [
        (
            EmailTemplate.OWNER_REGISTER_OTP,
            "Activate your Lucidex account",
            "activate your account",
        ),
        (
            EmailTemplate.OWNER_RESET_PASSWORD_OTP,
            "Reset your Lucidex password",
            "reset your account password",
        ),
        (
            EmailTemplate.ORGANIZATION_REGISTER_OTP,
            "Activate your Lucidex organization account",
            "activate your organization account",
        ),
        (
            EmailTemplate.ORGANIZATION_RESET_PASSWORD_OTP,
            "Reset your Lucidex organization password",
            "reset your organization account password",
        ),
    ],
)
def test_builds_each_otp_template(
    template: EmailTemplate,
    subject_fragment: str,
    body_fragment: str,
) -> None:
    service = MailerService(template_dir=TEMPLATE_DIR)

    message = service.build_otp_message(
        email="recipient@example.com",
        otp_code="012345",
        template=template,
    )

    assert subject_fragment in str(message["Subject"])
    assert "012345" in message.get_body(preferencelist=("plain",)).get_content()
    assert body_fragment in message.get_body(preferencelist=("html",)).get_content()


def test_escapes_dynamic_otp_value_in_html() -> None:
    service = MailerService(template_dir=TEMPLATE_DIR)

    message = service.build_otp_message(
        email="recipient@example.com",
        otp_code="<script>alert(1)</script>",
        template=EmailTemplate.OWNER_REGISTER_OTP,
    )
    html = message.get_body(preferencelist=("html",)).get_content()

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_rejects_unregistered_template() -> None:
    service = MailerService(template_dir=TEMPLATE_DIR)

    with pytest.raises(EmailTemplateError):
        service.build_otp_message(
            email="recipient@example.com",
            otp_code="012345",
            template="UNKNOWN",  # type: ignore[arg-type]
        )
