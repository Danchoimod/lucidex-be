from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from src.issuer.dependencies import require_current_issuer
from src.issuer.schemas import (
    CheckDuplicatesData,
    CredentialImportData,
    IssuerCredentialDetailData,
    IssuerCredentialListData,
    ManualCredentialCreateRequest,
    ManualCredentialResponseData,
)
from src.issuer.services import credential_import_service
from src.issuer.services.credential_check_duplicates import (
    credential_check_duplicates_service,
)
from src.issuer.services.credential_detail import credential_detail_service
from src.issuer.services.credential_list import credential_list_service
from src.issuer.services.credential_manual import credential_manual_service
from src.organization.models import InstitutionAccount, Organization
from src.schemas.common import ApiResponse

router = APIRouter()


@router.get(
    "/credentials/{credential_id}",
    response_model=ApiResponse[IssuerCredentialDetailData],
    status_code=status.HTTP_200_OK,
    summary="[Issuer] Get Issuer Credential Detail",
    description=(
        "Retrieves detailed information for a single graduate credential belonging to the authenticated Issuer organization. "
        "Returns 404 if the credential is not found or belongs to a different organization."
    ),
)
async def get_credential_detail(
    credential_id: str,
    issuer_info: Annotated[
        tuple[InstitutionAccount, Organization], Depends(require_current_issuer)
    ],
) -> ApiResponse[IssuerCredentialDetailData]:
    account, organization = issuer_info

    data = await credential_detail_service.get_credential_detail(
        credential_id=credential_id,
        organization=organization,
    )

    return ApiResponse[IssuerCredentialDetailData](
        success=True,
        data=data,
        message="Credential retrieved successfully.",
        error_code=None,
    )


@router.get(
    "/credentials",
    response_model=ApiResponse[IssuerCredentialListData],
    status_code=status.HTTP_200_OK,
    summary="[Issuer] Get Issuer Credential List",
    description=(
        "Retrieves a paginated list of graduate credentials belonging to the authenticated Issuer organization. "
        "Supports filtering by student_id, class_id, graduation_year, status ('claimed' or 'unclaimed'), "
        "searching by student_id, full_name or email, and sorting."
    ),
)
async def list_credentials(
    issuer_info: Annotated[
        tuple[InstitutionAccount, Organization], Depends(require_current_issuer)
    ],
    page: int = Query(default=1, ge=1, description="Current page number"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    student_id: str | None = Query(default=None, description="Filter by student ID"),
    class_id: str | None = Query(default=None, description="Filter by class ID"),
    graduation_year: int | None = Query(default=None, description="Filter by graduation year"),
    status_val: str | None = Query(default=None, alias="status", description="Filter by status ('claimed' or 'unclaimed')"),
    search: str | None = Query(default=None, description="Search by student_id, full_name, or university_email"),
    sort: str | None = Query(default="created_at:desc", description="Sort string (e.g. 'created_at:desc')"),
) -> ApiResponse[IssuerCredentialListData]:
    account, organization = issuer_info

    data = await credential_list_service.list_credentials(
        organization=organization,
        page=page,
        limit=limit,
        student_id=student_id,
        class_id=class_id,
        graduation_year=graduation_year,
        status=status_val,
        search=search,
        sort=sort,
    )

    return ApiResponse[IssuerCredentialListData](
        success=True,
        data=data,
        message="Credentials retrieved successfully.",
        error_code=None,
    )


@router.post(
    "/credentials/manual",
    response_model=ApiResponse[ManualCredentialResponseData],
    status_code=status.HTTP_200_OK,
    summary="[Issuer] Import/Create single graduate credential manually",
    description=(
        "Manually imports or creates an individual graduate credential via JSON. "
        "Supports updating existing student credential if overwrite is set to true."
    ),
)
async def manual_import_credential(
    issuer_info: Annotated[
        tuple[InstitutionAccount, Organization], Depends(require_current_issuer)
    ],
    payload: ManualCredentialCreateRequest,
) -> ApiResponse[ManualCredentialResponseData]:
    account, organization = issuer_info

    data = await credential_manual_service.create_or_update_credential(
        payload=payload,
        organization=organization,
        actor=account,
    )

    message = (
        "Credential updated successfully."
        if data.action == "updated"
        else "Credential created successfully."
    )

    return ApiResponse[ManualCredentialResponseData](
        success=True,
        data=data,
        message=message,
        error_code=None,
    )


@router.post(
    "/credentials/check-duplicates",
    response_model=ApiResponse[CheckDuplicatesData],
    status_code=status.HTTP_200_OK,
    summary="[Issuer] Check duplicate graduate credentials from CSV/XLSX (v2)",
    description=(
        "Checks duplicate graduate credentials from a CSV or Excel (.xlsx) file using the standard "
        "17-column Vietnamese template. Checks checksum against last successful import, "
        "performs a single $in query against database (excluding soft-deleted), applies 90% threshold "
        "summary rule for >= 50 rows, and returns detailed duplicates."
    ),
)
async def check_duplicates(
    issuer_info: Annotated[
        tuple[InstitutionAccount, Organization], Depends(require_current_issuer)
    ],
    file: UploadFile | None = File(default=None),
) -> ApiResponse[CheckDuplicatesData]:
    account, organization = issuer_info

    data = await credential_check_duplicates_service.check_duplicates(
        file=file,
        organization=organization,
        actor=account,
    )

    message = (
        "Duplicate check completed."
        if data.has_duplicates
        else "No duplicate credentials found."
    )

    return ApiResponse[CheckDuplicatesData](
        success=True,
        data=data,
        message=message,
        error_code=None,
    )


@router.post(
    "/credentials/import",
    response_model=ApiResponse[CredentialImportData],
    status_code=status.HTTP_200_OK,
    summary="[Issuer] Import graduate credentials from CSV/XLSX",
    description=(
        "Imports graduate credentials from a CSV or Excel (.xlsx) file using the 17-column Vietnamese template. "
        "Supports re-checking duplicates and overwriting business fields when overwrite_all is true, "
        "or skipping duplicates when overwrite_all is false."
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
