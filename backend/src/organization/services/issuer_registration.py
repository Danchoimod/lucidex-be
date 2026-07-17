"""Issuer registration business logic."""

from pymongo.errors import DuplicateKeyError

from src.exceptions import AppError
from src.organization.models import OrganizationStatus
from src.organization.models import Organization
from src.organization.schemas import IssuerRegistrationRequest
from src.utils.check_validation import is_tax_code_available


class TaxCodeAlreadyRegisteredError(AppError):
    """Raised when an issuer tax code already has a live registration."""

    def __init__(self) -> None:
        super().__init__(
            status_code=409,
            message="A live registration with this tax code already exists.",
            error_code="TAX_CODE_ALREADY_REGISTERED",
        )


class IssuerRegistrationService:
    """Register an issuer organization for admin review."""

    async def register(
        self,
        data: IssuerRegistrationRequest,
    ) -> Organization:
        await self._check_duplicates(data)

        organization = Organization(
            type="issuer",
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
            raise TaxCodeAlreadyRegisteredError from exc

        return organization

    async def _check_duplicates(
        self,
        data: IssuerRegistrationRequest,
    ) -> None:
        if not await is_tax_code_available(
            data.tax_code,
            "issuer",
        ):
            raise TaxCodeAlreadyRegisteredError


issuer_registration_service = IssuerRegistrationService()
