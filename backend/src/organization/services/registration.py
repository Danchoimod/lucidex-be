"""Organization registration business logic."""

from pymongo.errors import DuplicateKeyError

from src.mailer import EmailTemplate, mailer_service
from src.organization.constants import OrganizationStatus, OrganizationType
from src.organization.exceptions import (
    OrganizationEmailSendingFailedError,
    TaxCodeAlreadyRegisteredError,
)
from src.organization.models import Organization
from src.organization.schemas import IssuerRegistrationRequest
from src.utils.check_validation import is_tax_code_available


class OrganizationRegistrationService:
    """Register an issuer or verifier organization for admin review."""

    async def register(
        self,
        data: IssuerRegistrationRequest,
        *,
        organization_type: OrganizationType = OrganizationType.ISSUER,
    ) -> Organization:
        # 1. Check duplicate tax code among live organizations
        await self._check_duplicates(data, organization_type)

        # 2. Create and insert the Organization
        organization = Organization(
            type=organization_type,
            status=OrganizationStatus.PENDING_REVIEW,
            name=data.name,
            tax_code=data.tax_code,
            address=data.address,
            legal_rep_name=data.legal_rep_name,
            contact_email=data.contact_email,
            contact_phone=data.contact_phone,
            registrant_name=data.registrant_name,
        )

        try:
            await organization.insert()
        except DuplicateKeyError as exc:
            raise TaxCodeAlreadyRegisteredError() from exc

        # 3. Send registration confirmation email.
        # Use the normal mailer flow with dedicated templates for issuer and
        # verifier applications.
        try:
            if organization.type == OrganizationType.ISSUER:
                await mailer_service.send_email(
                    email=organization.contact_email,
                    template=EmailTemplate.ISSUER_APPLICATION_RECEIVED,
                    context={
                        "organization_name": organization.name,
                        "registrant_name": organization.registrant_name,
                    },
                )
            else:
                await mailer_service.send_email(
                    email=organization.contact_email,
                    template=EmailTemplate.VERIFIER_APPLICATION_RECEIVED,
                    context={
                        "institution_name": organization.name,
                        "registrant_name": organization.registrant_name,
                    },
                )
        except Exception as exc:
            raise OrganizationEmailSendingFailedError() from exc

        return organization

    async def _check_duplicates(
        self,
        data: IssuerRegistrationRequest,
        organization_type: OrganizationType,
    ) -> None:
        if not await is_tax_code_available(
            data.tax_code,
            organization_type,
        ):
            raise TaxCodeAlreadyRegisteredError()


issuer_registration_service = OrganizationRegistrationService()