from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def set_tenant_context(db: AsyncSession, municipio_id: int | None, is_superuser: bool) -> None:
    if municipio_id is not None:
        await db.execute(text("SELECT set_config('app.municipio_id', :v, true)"), {"v": str(municipio_id)})
    await db.execute(text("SELECT set_config('app.is_superuser', :v, true)"), {"v": "true" if is_superuser else "false"})
