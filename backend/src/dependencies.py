from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_token_payload(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
    ],
) -> dict[str, Any]:
    """Validate a bearer access token and expose its actor metadata."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    payload = decode_access_token(credentials.credentials)
    request.state.actor_type = payload.get("actor_type")
    return payload


TokenPayload = Annotated[dict[str, Any], Depends(get_token_payload)]


def require_actor(*allowed_actor_types: str) -> Callable[..., dict[str, Any]]:
    async def dependency(payload: TokenPayload) -> dict[str, Any]:
        if payload.get("actor_type") not in allowed_actor_types:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )
        return payload

    return dependency


get_current_owner = require_actor("owner")
get_current_issuer = require_actor("issuer")
get_current_verifier = require_actor("verifier")
get_current_admin = require_actor("admin")


def require_permission(permission: str) -> Callable[..., dict[str, Any]]:
    async def dependency(payload: TokenPayload) -> dict[str, Any]:
        permissions = payload.get("permissions", [])
        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the required permission.",
            )
        return payload

    return dependency
