import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from src.auth.constants import ActorType, SessionStatus
from src.auth.models import DeviceInfo, Session


def hash_refresh_token(token: str) -> str:
    """Hash the refresh token using SHA-256 for secure storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class SessionService:
    async def create_session(
        self,
        actor_id: str,
        actor_type: ActorType,
        device_info: DeviceInfo | None = None,
        org_id: str | None = None,
        expiry_days: int = 30,
    ) -> tuple[Session, str]:
        """Create a new session, save its hashed refresh token, and return the unhashed token."""
        raw_refresh_token = secrets.token_hex(32)
        token_hash = hash_refresh_token(raw_refresh_token)

        now = datetime.now(UTC)
        expires_at = now + timedelta(days=expiry_days)

        session = Session(
            actor_type=actor_type,
            actor_id=actor_id,
            org_id=org_id,
            refresh_token_hash=token_hash,
            device_info=device_info or DeviceInfo(),
            status=SessionStatus.ACTIVE,
            issued_at=now,
            last_used_at=now,
            expires_at=expires_at,
        )
        await session.insert()
        return session, raw_refresh_token


session_service = SessionService()
