from typing import Any

from src.organization.constants import OrganizationStatus, OrganizationType
from src.organization.models import Organization
from src.owner.schemas import VerifierItemResponse


async def list_verifiers() -> list[VerifierItemResponse]:
    query: dict[str, Any] = {
        "type": OrganizationType.VERIFIER.value,
        "status": OrganizationStatus.APPROVED.value,
    }

    orgs = await Organization.find(query).sort("name").to_list()
    return [
        VerifierItemResponse(
            id=str(org.id),
            name=org.name,
        )
        for org in orgs
    ]

