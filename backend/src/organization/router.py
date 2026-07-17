"""Organization module routes."""

from fastapi import APIRouter, status

from src.organization.schemas import IssuerRegistrationData, IssuerRegistrationRequest
from src.organization.service.registration import issuer_registration_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post(
    "/issuers/register",
    response_model=IssuerRegistrationData,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new issuer organization for admin review",
)
async def register_issuer(payload: IssuerRegistrationRequest) -> IssuerRegistrationData:
    organization = await issuer_registration_service.register(payload)
    return IssuerRegistrationData(id=str(organization.id), status=organization.status)