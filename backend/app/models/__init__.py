from beanie import Document

from app.models.access_record import AccessRecord
from app.models.audit_log import AuditLog
from app.models.claim import Claim
from app.models.credential import Credential
from app.models.csv_upload_job import CsvUploadJob
from app.models.csv_upload_row import CsvUploadRow
from app.models.ekyc_capture_session import EkycCaptureSession
from app.models.institution_account import InstitutionAccount
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.otp_code import OtpCode
from app.models.owner import Owner
from app.models.platform_admin import PlatformAdmin
from app.models.session import Session
from app.models.trusted_organization import TrustedOrganization
from app.models.verified_link import VerifiedLink

DOCUMENT_MODELS: list[type[Document]] = [
    Organization,
    InstitutionAccount,
    PlatformAdmin,
    Owner,
    Credential,
    Claim,
    CsvUploadJob,
    CsvUploadRow,
    VerifiedLink,
    AccessRecord,
    TrustedOrganization,
    Notification,
    AuditLog,
    OtpCode,
    Session,
    EkycCaptureSession,
]

__all__ = [
    "AccessRecord",
    "AuditLog",
    "Claim",
    "Credential",
    "CsvUploadJob",
    "CsvUploadRow",
    "DOCUMENT_MODELS",
    "EkycCaptureSession",
    "InstitutionAccount",
    "Notification",
    "Organization",
    "OtpCode",
    "Owner",
    "PlatformAdmin",
    "Session",
    "TrustedOrganization",
    "VerifiedLink",
]
