"""Service for manual creation/import of individual graduate credentials."""

import logging

from src.credential.models import Credential
from src.credential.services.hashing import hash_imported_national_id
from src.issuer.exceptions import CredentialAlreadyExistsError, InvalidFileFormatError
from src.issuer.schemas import (
    ManualCredentialCreateRequest,
    ManualCredentialResponseData,
)
from src.issuer.services.credential_import import _parse_dob
from src.models import utc_now
from src.organization.models import InstitutionAccount, Organization

logger = logging.getLogger(__name__)


class CredentialManualService:
    """Service handling manual credential creation and updates."""

    async def create_or_update_credential(
        self,
        *,
        payload: ManualCredentialCreateRequest,
        organization: Organization,
        actor: InstitutionAccount,
    ) -> ManualCredentialResponseData:
        # 1. Parse date of birth & national ID hash
        try:
            dob_val = _parse_dob(payload.dob)
        except ValueError as exc:
            raise InvalidFileFormatError(str(exc)) from exc

        national_id_hash = None
        if payload.national_id_hash:
            try:
                national_id_hash = hash_imported_national_id(payload.national_id_hash)
            except ValueError as exc:
                raise InvalidFileFormatError(str(exc)) from exc

        student_id = payload.student_id.strip()
        major_summary = payload.major_vi or payload.major_en or ""
        class_summary = (
            payload.graduation_classification_vi
            or payload.graduation_classification_en
            or ""
        )

        # 2. Check DB for existing credential
        existing_cred = await Credential.find_one(
            {
                "issuer_org_id": organization.id,
                "student_id": student_id,
            }
        )

        if existing_cred is not None:
            if getattr(existing_cred, "deleted_at", None) is not None:
                existing_cred.deleted_at = None
                existing_cred.restored_at = utc_now()
            elif not payload.overwrite:
                raise CredentialAlreadyExistsError(
                    f"Credential for student_id '{student_id}' already exists."
                )

            # Update business fields
            existing_cred.full_name = payload.full_name.strip()
            existing_cred.dob = dob_val
            existing_cred.graduation_year = payload.graduation_year
            existing_cred.university_email = payload.university_email.strip()
            existing_cred.major = major_summary
            existing_cred.major_vi = payload.major_vi
            existing_cred.major_en = payload.major_en
            existing_cred.classification = class_summary
            existing_cred.graduation_classification_vi = payload.graduation_classification_vi
            existing_cred.graduation_classification_en = payload.graduation_classification_en
            existing_cred.mode_of_study_vi = payload.mode_of_study_vi
            existing_cred.mode_of_study_en = payload.mode_of_study_en
            existing_cred.class_id = payload.class_id
            existing_cred.national_id_hash = national_id_hash
            existing_cred.phone = payload.phone

            await existing_cred.save()

            return ManualCredentialResponseData(
                id=str(existing_cred.id),
                student_id=existing_cred.student_id,
                full_name=existing_cred.full_name,
                status=existing_cred.status,
                action="updated",
            )
        else:
            new_cred = Credential(
                issuer_org_id=organization.id,
                student_id=student_id,
                full_name=payload.full_name.strip(),
                dob=dob_val,
                graduation_year=payload.graduation_year,
                university_email=payload.university_email.strip(),
                major=major_summary,
                major_vi=payload.major_vi,
                major_en=payload.major_en,
                classification=class_summary,
                graduation_classification_vi=payload.graduation_classification_vi,
                graduation_classification_en=payload.graduation_classification_en,
                mode_of_study_vi=payload.mode_of_study_vi,
                mode_of_study_en=payload.mode_of_study_en,
                class_id=payload.class_id,
                national_id_hash=national_id_hash,
                phone=payload.phone,
                status="unclaimed",
                unclaimed_reason_code="AWAITING_CLAIM",
                created_at=utc_now(),
                created_by=actor.id,
            )
            await new_cred.insert()

            return ManualCredentialResponseData(
                id=str(new_cred.id),
                student_id=new_cred.student_id,
                full_name=new_cred.full_name,
                status=new_cred.status,
                action="created",
            )


credential_manual_service = CredentialManualService()
