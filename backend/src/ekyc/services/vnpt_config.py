import hmac

from src.debug.vnpt_models import VnptEkycConfig
from src.ekyc.exceptions import InvalidVnptAccessTokenError


class VnptEkycConfigService:
    async def require_valid_access_token(self, access_token: str) -> None:
        config = await VnptEkycConfig.find_one(
            {"config_key": "global_vnpt_config"}
        )
        configured_token = config.access_token if config is not None else None
        if not configured_token or not hmac.compare_digest(
            access_token,
            configured_token,
        ):
            raise InvalidVnptAccessTokenError()


vnpt_ekyc_config_service = VnptEkycConfigService()
