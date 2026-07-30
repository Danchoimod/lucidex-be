"""Issuer registration service logic."""

from fastapi import UploadFile

from src.organization.exceptions import (
    DocumentRequiredError,
    FileEmptyError,
    FileTooLargeError,
    InvalidFileTypeError,
)
from src.organization.models import Organization, OrganizationDocument
from src.organization.schemas import IssuerRegistrationRequest
from src.organization.services import issuer_registration_service as org_registration_service
from src.utils.gcs_storage import upload_pdf


class IssuerRegistrationService:
    """Service to handle issuer organization registration and document processing."""

    async def register_issuer(
        self,
        payload: IssuerRegistrationRequest,
        document: UploadFile | None,
    ) -> Organization:
        """Validate uploaded document and register an issuer organization."""
        if document is None or not document.filename:
            raise DocumentRequiredError()

        if not document.filename.lower().endswith(".pdf"):
            raise InvalidFileTypeError("Only PDF files are allowed.")

        content = await document.read()
        if len(content) == 0:
            raise FileEmptyError()
        if len(content) > 20 * 1024 * 1024:
            raise FileTooLargeError()

        organization = await org_registration_service.register(payload)

        if document is not None and content is not None:
            try:
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
            except Exception:
                await organization.delete()
                raise

        return organization


issuer_registration_service = IssuerRegistrationService()
