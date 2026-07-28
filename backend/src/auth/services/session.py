import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from src.auth.constants import ActorType, SessionStatus
from src.auth.models import DeviceInfo, Session
from src.config import settings


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
        expiry_days: int | None = None,
    ) -> tuple[Session, str]:
        """Create a new session, save its hashed refresh token, and return the unhashed token."""
        raw_refresh_token = secrets.token_hex(32)
        token_hash = hash_refresh_token(raw_refresh_token)

        now = datetime.now(UTC)
        days = expiry_days if expiry_days is not None else settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        expires_at = now + timedelta(days=days)

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

    async def refresh_access_token(self, refresh_token: str) -> tuple[str, str]:
        """Validate raw refresh token against Session DB, update last_used_at, and return new (access_token, token_type)."""
        from src.auth.services.token import create_access_token
        from src.exceptions import AppError

        token_hash = hash_refresh_token(refresh_token)
        session = await Session.find_one(
            Session.refresh_token_hash == token_hash,
            Session.status == SessionStatus.ACTIVE,
        )
        now = datetime.now(UTC)
        if session is None:
            raise AppError(
                status_code=401,
                message="Invalid or expired refresh token.",
                error_code="INVALID_REFRESH_TOKEN",
            )

        expires_at = session.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= now:
            session.status = SessionStatus.EXPIRED
            await session.save()
            raise AppError(
                status_code=401,
                message="Refresh token has expired.",
                error_code="EXPIRED_REFRESH_TOKEN",
            )

        session.last_used_at = now
        await session.save()

        actor_type_str = session.actor_type.value if hasattr(session.actor_type, "value") else str(session.actor_type)
        access_token = create_access_token(
            subject=str(session.actor_id),
            actor_type=actor_type_str,
            session_id=str(session.id),
            org_id=str(session.org_id) if session.org_id else None,
        )
        return access_token, "bearer"


session_service = SessionService()
