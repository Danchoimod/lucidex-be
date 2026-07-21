from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from src.database import DOCUMENT_MODELS
from src.invitation.constants import InviteStatus
from src.invitation.models import InviteLink
from src.organization.constants import OrganizationType
from src.organization.models import Organization

ORG_ID = "507f1f77bcf86cd799439011"
ADMIN_ID = "507f1f77bcf86cd799439012"
TOKEN_HASH = "a" * 64


@pytest.fixture(autouse=True)
async def invitation_test_database():
    """Override the root MongoDB fixture; these are model-only tests."""
    yield


@pytest.fixture(scope="session", autouse=True)
def _drop_test_database_at_session_end():
    """Prevent the root test fixture from dropping an external database."""
    yield


@pytest.fixture
def beanie_models_without_database(monkeypatch):
    for model in (InviteLink, Organization):
        monkeypatch.setattr(
            model,
            "get_motor_collection",
            classmethod(lambda cls: None),
        )


def invite_payload() -> dict:
    return {
        "org_id": ORG_ID,
        "contact_email": "  ADMIN@EXAMPLE.COM ",
        "token_hash": TOKEN_HASH,
        "expires_at": datetime.now(UTC) + timedelta(days=3),
        "created_by": ADMIN_ID,
    }


def test_invite_link_defaults_to_pending_and_normalizes_email(
    beanie_models_without_database,
):
    invite = InviteLink.model_validate(invite_payload())

    assert invite.status == InviteStatus.PENDING
    assert invite.contact_email == "admin@example.com"
    assert invite.used_at is None
    assert invite.revoked_at is None


def test_invite_link_rejects_invalid_token_hash(
    beanie_models_without_database,
):
    payload = {**invite_payload(), "token_hash": "raw-token"}

    with pytest.raises(ValidationError):
        InviteLink.model_validate(payload)


def test_invite_link_indexes_match_contract():
    indexes = {
        index.document["name"]: index.document
        for index in InviteLink.Settings.indexes
    }

    assert indexes["uq_invite_token_hash"]["unique"] is True
    assert indexes["uq_pending_invite_org"]["unique"] is True
    assert indexes["uq_pending_invite_org"]["partialFilterExpression"] == {
        "status": "pending"
    }
    assert "ix_invite_org_status_created" in indexes
    assert "ix_invite_expires_at" in indexes


def test_invite_link_is_registered_with_database():
    assert InviteLink in DOCUMENT_MODELS


def test_organization_ignores_legacy_invite_fields(
    beanie_models_without_database,
):
    organization = Organization.model_validate(
        {
            "type": OrganizationType.ISSUER,
            "name": "Legacy Organization",
            "tax_code": "0123456789",
            "address": "Ho Chi Minh City",
            "legal_rep_name": "Legacy Representative",
            "contact_email": "legacy@example.com",
            "contact_phone": "0900000000",
            "registrant_name": "Legacy Registrant",
            "invite_token": "legacy-raw-token",
            "invite_token_used": False,
        }
    )

    assert not hasattr(organization, "invite_token")
    assert not hasattr(organization, "invite_token_used")
