import logging

from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConfigurationError, OperationFailure

from src.config import settings
from src.organization.models import Organization
from src.organization.models import TrustedOrganization
from src.organization.models import InstitutionAccount
from src.admin.models import PlatformAdmin
from src.owner.models import Owner
from src.credential.models import Credential
from src.credential.models import Claim
from src.credential.models import VerifiedLink
from src.credential.models import AccessRecord
from src.credential.models import CsvUploadJob
from src.credential.models import CsvUploadRow
from src.ekyc.models import EkycCaptureSession
from src.notification.models import Notification
from src.audit.models import AuditLog
from src.auth.models import OtpCode
from src.auth.models import Session

DOCUMENT_MODELS = [
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

logger = logging.getLogger(__name__)

mongo_client: AsyncIOMotorClient | None = None

async def connect_database() -> None:
    """Connect to MongoDB Atlas and initialize every Beanie document model."""
    global mongo_client
    try:
        mongo_client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=5_000,
            uuidRepresentation="standard",
        )
        await mongo_client.admin.command("ping")
        await init_beanie(
            database=mongo_client[settings.MONGODB_DB_NAME],
            document_models=DOCUMENT_MODELS,
        )
        logger.info("mongodb_connected", extra={"database": settings.MONGODB_DB_NAME})
    except OperationFailure as exc:
        logger.error("mongodb_operation_failed", exc_info=exc, extra={"code": exc.code, "details": str(exc.details)})
        raise RuntimeError(f"MongoDB operation failed: {exc}") from exc
    except ConfigurationError:
        logger.error("mongodb_configuration_invalid")
        raise RuntimeError("Invalid MongoDB configuration") from None


async def disconnect_database() -> None:
    """Close the MongoDB client created during application startup."""
    global mongo_client
    if mongo_client is not None:
        mongo_client.close()
        mongo_client = None
