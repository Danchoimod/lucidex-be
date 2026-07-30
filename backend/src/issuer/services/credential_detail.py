"""Service for retrieving issuer credential details."""

from datetime import date

from beanie import PydanticObjectId
from fastapi import HTTPException, status

from src.credential.constants import DEFAULT_DEGREE_TYPE
from src.credential.models import Credential
from src.issuer.schemas import IssuerCredentialDetailData
from src.organization.models import Organization


class CredentialDetailService:
    """Service handling single credential detail retrieval."""

    async def get_credential_detail(
        self,
        *,
        credential_id: str,
        organization: Organization,
    ) -> IssuerCredentialDetailData:
        # 1. Validate credential_id format
        if not PydanticObjectId.is_valid(credential_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid credential_id format.",
            )

        # 2. Query database by credential_id + issuer_org_id + deleted_at == None simultaneously
        cred = await Credential.find_one(
            {
                "_id": PydanticObjectId(credential_id),
                "issuer_org_id": organization.id,
                "deleted_at": None,
            }
        )

        if cred is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found.",
            )

        # 3. DOB to string YYYY-MM-DD
        dob_str = (
            cred.dob.strftime("%Y-%m-%d")
            if isinstance(cred.dob, date)
            else str(cred.dob)
        )

        claimed_at_val = (
            cred.claimed_at.isoformat()
            if getattr(cred, "claimed_at", None)
            else None
        )
        created_at_val = (
            cred.created_at.isoformat()
            if getattr(cred, "created_at", None)
            else None
        )

        # 4. Return detail payload (excluding national_id_hash)
        return IssuerCredentialDetailData(
            id=str(cred.id),
            student_id=cred.student_id,
            class_id=cred.class_id,
            full_name=cred.full_name,
            dob=dob_str,
            major_vi=cred.major_vi,
            major_en=cred.major_en,
            degree_type=getattr(cred, "degree_type", None) or DEFAULT_DEGREE_TYPE,
            graduation_year=cred.graduation_year,
            graduation_classification_vi=cred.graduation_classification_vi,
            graduation_classification_en=cred.graduation_classification_en,
            mode_of_study_vi=cred.mode_of_study_vi,
            mode_of_study_en=cred.mode_of_study_en,
            university_email=cred.university_email,
            status=cred.status,
            claimed_at=claimed_at_val,
            created_at=created_at_val,
        )


credential_detail_service = CredentialDetailService()
