from fastapi import APIRouter, File, Form, Request, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from src.organization.models import OrganizationDocument
from src.organization.schemas import IssuerRegistrationData, IssuerRegistrationRequest
from src.organization.services import issuer_registration_service
from src.schemas.common import ApiResponse
from src.utils.gcs_storage import upload_pdf

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

    organization = await issuer_registration_service.register(payload)

    if document is not None:
        if not document.filename or not document.filename.lower().endswith(".pdf"):
            raise ValueError("Only PDF files are allowed.")

        content = await document.read()
        if len(content) == 0:
            raise ValueError("PDF file is empty.")
        if len(content) > 20 * 1024 * 1024:
            raise ValueError("PDF file must be 20MB or smaller.")

        object_name = f"organizations/{organization.id}/{document.filename}"
        public_url = upload_pdf(file_content=content, object_name=object_name)
        documents = getattr(organization, "documents", None)
        if documents is None:
            organization.documents = []
        organization.documents.append(
            OrganizationDocument(
                name=document.filename,
                url=public_url,
                type="application/pdf",
            )
        )
        if hasattr(organization, "save"):
            await organization.save()

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

