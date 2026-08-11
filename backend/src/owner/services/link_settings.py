"""Owner link settings service."""

from beanie import PydanticObjectId
from bson.errors import InvalidId

from src.owner.exceptions import InvalidDefaultSettingsError
from src.owner.models import DefaultLinkSettings, Owner
from src.owner.schemas import DefaultLinkSettingsData, PatchLinkSettingsRequest


def _to_settings_data(settings: DefaultLinkSettings) -> DefaultLinkSettingsData:
    return DefaultLinkSettingsData(
        default_consent_mode=settings.default_consent_mode,
        default_max_access_count=settings.default_max_access_count,
        default_expiry_hours=settings.default_expiry_hours,
        default_allowed_org_ids=[str(org_id) for org_id in settings.default_allowed_org_ids],
    )


async def get_link_settings(owner: Owner) -> DefaultLinkSettingsData:
    """Get the authenticated owner's default link settings."""
    if owner.default_link_settings is None:
        owner.default_link_settings = DefaultLinkSettings()
    return _to_settings_data(owner.default_link_settings)


async def update_link_settings(
    owner: Owner, payload: PatchLinkSettingsRequest
) -> DefaultLinkSettingsData:
    """Update the authenticated owner's default link settings (partial update)."""
    if owner.default_link_settings is None:
        owner.default_link_settings = DefaultLinkSettings()

    current = owner.default_link_settings

    # Track fields set in payload
    fields_set = payload.model_fields_set

    new_mode = payload.default_consent_mode if "default_consent_mode" in fields_set else current.default_consent_mode
    new_max_count = (
        payload.default_max_access_count
        if "default_max_access_count" in fields_set
        else current.default_max_access_count
    )
    new_expiry_hours = (
        payload.default_expiry_hours
        if "default_expiry_hours" in fields_set
        else current.default_expiry_hours
    )

    if "default_allowed_org_ids" in fields_set:
        if payload.default_allowed_org_ids is None:
            new_allowed_org_ids: list[PydanticObjectId] = []
        else:
            new_allowed_org_ids = []
            for org_str in payload.default_allowed_org_ids:
                try:
                    new_allowed_org_ids.append(PydanticObjectId(org_str))
                except (InvalidId, TypeError):
                    pass
    else:
        new_allowed_org_ids = current.default_allowed_org_ids

    # Custom mode validation: at least 2 of 3 value dimensions set
    if new_mode == "custom":
        dimensions_count = sum([
            new_max_count is not None,
            new_expiry_hours is not None,
            bool(new_allowed_org_ids),
        ])
        if dimensions_count < 2:
            raise InvalidDefaultSettingsError()

    current.default_consent_mode = new_mode
    current.default_max_access_count = new_max_count
    current.default_expiry_hours = new_expiry_hours
    current.default_allowed_org_ids = new_allowed_org_ids

    owner.default_link_settings = current
    await owner.save()

    return _to_settings_data(current)
