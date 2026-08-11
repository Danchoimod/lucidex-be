"""Service for manual creation/import of individual graduate credentials."""

import logging

from src.credential.constants import DEFAULT_DEGREE_TYPE
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
        major_summary = (
            getattr(payload, "major", None)
            or getattr(payload, "major_vi", None)
            or getattr(payload, "major_en", None)
            or ""
        )
        class_summary = (
            getattr(payload, "classification", None)
            or getattr(payload, "graduation_classification", None)
            or getattr(payload, "graduation_classification_vi", None)
            or getattr(payload, "graduation_classification_en", None)
            or ""
        )
        mode_summary = (
            getattr(payload, "mode_of_study", None)
            or getattr(payload, "mode_of_study_vi", None)
            or getattr(payload, "mode_of_study_en", None)
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

            degree_type_val = (payload.degree_type.strip() if payload.degree_type else None) or DEFAULT_DEGREE_TYPE

            # Update business fields
            existing_cred.full_name = payload.full_name.strip()
            existing_cred.dob = dob_val
            existing_cred.graduation_year = payload.graduation_year
            existing_cred.university_email = payload.university_email.strip() if payload.university_email else None
            existing_cred.major = major_summary
            existing_cred.major_vi = getattr(payload, "major_vi", None) or major_summary
            existing_cred.major_en = getattr(payload, "major_en", None)
            existing_cred.classification = class_summary
            existing_cred.graduation_classification_vi = getattr(payload, "graduation_classification_vi", None) or class_summary
            existing_cred.graduation_classification_en = getattr(payload, "graduation_classification_en", None)
            existing_cred.mode_of_study_vi = getattr(payload, "mode_of_study_vi", None) or mode_summary
            existing_cred.mode_of_study_en = getattr(payload, "mode_of_study_en", None)
            existing_cred.class_id = payload.class_id
            existing_cred.place_of_birth = payload.place_of_birth
            existing_cred.gender = payload.gender
            existing_cred.degree_type = degree_type_val
            existing_cred.faculty = payload.faculty
            existing_cred.specialization = payload.specialization
            existing_cred.cpa = payload.cpa
            existing_cred.degree_number = payload.degree_number
            existing_cred.register_number = payload.register_number
            existing_cred.notes = payload.notes
            existing_cred.national_id_hash = national_id_hash

            await existing_cred.save()

            return ManualCredentialResponseData(
                id=str(existing_cred.id),
                student_id=existing_cred.student_id,
                full_name=existing_cred.full_name,
                status=existing_cred.status,
                action="updated",
            )
        else:
            degree_type_val = (payload.degree_type.strip() if payload.degree_type else None) or DEFAULT_DEGREE_TYPE
            new_cred = Credential(
                issuer_org_id=organization.id,
                student_id=student_id,
                full_name=payload.full_name.strip(),
                dob=dob_val,
                graduation_year=payload.graduation_year,
                university_email=payload.university_email.strip() if payload.university_email else None,
                major=major_summary,
                major_vi=getattr(payload, "major_vi", None) or major_summary,
                major_en=getattr(payload, "major_en", None),
                classification=class_summary,
                graduation_classification_vi=getattr(payload, "graduation_classification_vi", None) or class_summary,
                graduation_classification_en=getattr(payload, "graduation_classification_en", None),
                mode_of_study_vi=getattr(payload, "mode_of_study_vi", None) or mode_summary,
                mode_of_study_en=getattr(payload, "mode_of_study_en", None),
                class_id=payload.class_id,
                place_of_birth=payload.place_of_birth,
                gender=payload.gender,
                degree_type=degree_type_val,
                faculty=payload.faculty,
                specialization=payload.specialization,
                cpa=payload.cpa,
                degree_number=payload.degree_number,
                register_number=payload.register_number,
                notes=payload.notes,
                national_id_hash=national_id_hash,
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
