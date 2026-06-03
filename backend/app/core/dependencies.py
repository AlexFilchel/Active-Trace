"""Database and auth dependencies."""

from collections.abc import AsyncGenerator
from dataclasses import dataclass
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_factory
from app.core.security import TokenValidationError, decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    roles: list[str]
    email: str | None = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide one async SQLAlchemy session per request.

    Reserved for future changes:
    - get_current_user -> C-03
    - get_tenant -> C-02/C-03
    - require_permission -> C-04
    """

    session_factory = get_session_factory()
    session = session_factory()

    try:
        yield session
    finally:
        await session.close()


async def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    try:
        claims = decode_access_token(credentials.credentials)
        return AuthenticatedUser(
            user_id=uuid.UUID(str(claims["user_id"])),
            tenant_id=uuid.UUID(str(claims["tenant_id"])),
            roles=[str(role) for role in claims["roles"]],
        )
    except (KeyError, ValueError, TypeError, TokenValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.") from exc
