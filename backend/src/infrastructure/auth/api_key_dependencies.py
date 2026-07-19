"""API-key authentication for AES routes, falling back to session auth when no key is presented."""

from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ...modules.api_keys.enums import KeyPermissionAction, KeyPermissionResource
from ...modules.api_keys.service import APIKeyService
from ...modules.user.crud import crud_users
from ..database.session import async_session
from .http_exceptions import UnauthorizedException
from .session.dependencies import get_optional_user, verify_csrf_token


def get_current_principal(
    resource: KeyPermissionResource, action: KeyPermissionAction
) -> Callable[..., Awaitable[dict[str, Any]]]:
    """Build a dependency resolving the current principal via API key (if `X-API-Key` is present) or session.

    Uses `get_optional_user` (not `get_current_user`) for the session path because it returns `None` instead of
    raising when there's no session — required so the API-key branch still gets a chance to run. `verify_csrf_token`
    is kept as a dependency for parity with the session-only `get_current_user`/`CurrentUserDep` path used
    elsewhere: it already no-ops for GET/HEAD/OPTIONS and for requests with no session cookie, so depending on it
    unconditionally here is safe for the API-key path too.
    """

    async def _resolve(
        db: Annotated[AsyncSession, Depends(async_session)],
        _csrf: Annotated[None, Depends(verify_csrf_token)],
        x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
        session_user: Annotated[dict[str, Any] | None, Depends(get_optional_user)] = None,
    ) -> dict[str, Any]:
        if x_api_key is None:
            if session_user is None:
                raise UnauthorizedException("Not authenticated")
            return session_user

        validation = await APIKeyService().validate_api_key(x_api_key, resource.value, action.value, db)
        if not validation.is_valid:
            raise UnauthorizedException(validation.error_message or "Invalid API key")

        user = await crud_users.get(db=db, id=validation.user_id, is_deleted=False)
        if user is None:
            raise UnauthorizedException("Not authenticated")

        return user

    return _resolve
