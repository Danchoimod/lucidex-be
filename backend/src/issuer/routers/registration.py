"""Registration router for issuer organization applications."""

from fastapi import APIRouter, File, Form, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from src.issuer.services import issuer_registration_service
from src.organization.schemas import IssuerRegistrationData, IssuerRegistrationRequest
from src.schemas.common import ApiResponse

router = APIRouter()


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
    request: Request,
    name: str | None = Form(default=None),
    tax_code: str | None = Form(default=None),
    address: str | None = Form(default=None),
    legal_rep_name: str | None = Form(default=None),
    contact_email: str | None = Form(default=None),
    contact_phone: str | None = Form(default=None),
    registrant_name: str | None = Form(default=None),
    document: UploadFile | None = File(default=None),
) -> ApiResponse[IssuerRegistrationData]:
    try:
        if request.headers.get("content-type", "").startswith("application/json"):
            payload = IssuerRegistrationRequest.model_validate(await request.json())
        else:
            payload = IssuerRegistrationRequest(
                name=name,
                tax_code=tax_code,
                address=address,
                legal_rep_name=legal_rep_name,
                contact_email=contact_email,
                contact_phone=contact_phone,
                registrant_name=registrant_name,
            )
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc

    organization = await issuer_registration_service.register_issuer(
        payload=payload,
        document=document,
    )

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
