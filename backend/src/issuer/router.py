from fastapi import APIRouter, status

from src.schemas.common import ApiResponse
from src.organization.schemas import (
    IssuerRegistrationData,
    IssuerRegistrationRequest,
)
from src.organization.service import issuer_registration_service

router = APIRouter(prefix="/issuer", tags=["Issuer"])


@router.get(
    "/health",
    summary="Check issuer API health",
    description=(
        "Allows clients to check whether the Issuer API routes are available. "
        "Returns a success response when the portal router is reachable."
    ),
)
async def health_check():
    return {
        "success": True,
        "data": {"message": "Issuer portal is running."},
        "message": "OK",
        "error_code": None,
    }


@router.post(
    "/register",
    response_model=ApiResponse[IssuerRegistrationData],
    status_code=status.HTTP_201_CREATED,
    summary="Register issuer organization",
    description=(
        "Allows an unauthenticated issuer institution to submit a registration "
        "application for admin review. "
        "The endpoint validates required fields, Gmail address, Vietnamese "
        "phone number, tax code format, and duplicate live issuer applications. "
        "On success, a new organization is created with status "
        "'pending_review'."
    ),
)
async def register_issuer(
    payload: IssuerRegistrationRequest,
) -> ApiResponse[IssuerRegistrationData]:
    organization = await issuer_registration_service.register(payload)

    return ApiResponse[IssuerRegistrationData](
        success=True,
        data=IssuerRegistrationData(
            id=str(organization.id),
            status=organization.status,
        ),
        message=(
            "Your registration application has been submitted successfully "
            "and is pending review."
        ),
        error_code=None,
    )

