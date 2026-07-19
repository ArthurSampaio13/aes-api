from collections.abc import AsyncGenerator, Awaitable, Callable
from typing import Annotated, Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.database.session import async_session
from ...infrastructure.database.tenancy import set_tenant_context
from .service import AesService


def get_aes_service() -> AesService:
    return AesService()


AesServiceDep = Annotated[AesService, Depends(get_aes_service)]


def get_aes_tenant_session(
    principal_dependency: Callable[..., Awaitable[dict[str, Any]]],
) -> Callable[..., AsyncGenerator[AsyncSession, None]]:
    """Build a tenant-scoped DB session dependency bound to a specific `get_current_principal(...)` instance.

    Must be passed the *same* dependency object used for the route's own `current_user` parameter, so FastAPI's
    per-request dependency cache resolves the underlying auth check exactly once instead of twice.
    """

    async def _tenant_session(
        db: Annotated[AsyncSession, Depends(async_session)],
        current_user: Annotated[dict[str, Any], Depends(principal_dependency)],
    ) -> AsyncGenerator[AsyncSession, None]:
        await set_tenant_context(
            db, municipio_id=current_user.get("municipio_id"), is_superuser=current_user.get("is_superuser", False)
        )
        yield db

    return _tenant_session
