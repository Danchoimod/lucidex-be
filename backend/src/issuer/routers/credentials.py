"""Credentials router for issuer module."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from src.issuer.dependencies import require_current_issuer
from src.issuer.schemas import CredentialImportData
from src.issuer.services import credential_import_service
from src.organization.models import InstitutionAccount, Organization
from src.schemas.common import ApiResponse

router = APIRouter()


@router.post(
    "/credentials/import",
    response_model=ApiResponse[CredentialImportData],
    status_code=status.HTTP_200_OK,
    summary="[Issuer] Import graduate credentials from CSV",
    description=(
        "Imports graduate credentials from a CSV file. Supports re-checking duplicates "
        "and overwriting business fields when overwrite_all is true, or skipping duplicates "
        "when overwrite_all is false."
    ),
)
async def import_credentials(
    issuer_info: Annotated[
        tuple[InstitutionAccount, Organization], Depends(require_current_issuer)
    ],
    file: UploadFile | None = File(default=None),
    overwrite_all: Any = Form(default=False, description="Set to true to overwrite existing credential business fields, or false to skip. Default is false."),
) -> ApiResponse[CredentialImportData]:
    account, organization = issuer_info

    data = await credential_import_service.import_credentials(
        file=file,
        overwrite_all_raw=overwrite_all,
        organization=organization,
        actor=account,
    )

    return ApiResponse[CredentialImportData](
        success=True,
        data=data,
        message="Credentials imported successfully.",
        error_code=None,
    )
