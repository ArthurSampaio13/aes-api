import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from loguru import logger  # noqa: E402
from sqlalchemy import select, update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from src.modules.api_keys.enums import KeyPermissionAction, KeyPermissionResource  # noqa: E402
from src.modules.api_keys.models import APIKey  # noqa: E402
from src.modules.api_keys.schemas import APIKeyCreate  # noqa: E402
from src.modules.api_keys.service import APIKeyService  # noqa: E402
from src.modules.user.models import User  # noqa: E402

BOOTSTRAP_KEY_NAME = "bootstrap"

BOOTSTRAP_PERMISSIONS = {
    KeyPermissionResource.RUBRICS.value: [KeyPermissionAction.READ.value, KeyPermissionAction.CREATE.value],
    KeyPermissionResource.ESSAY_PROMPTS.value: [KeyPermissionAction.READ.value, KeyPermissionAction.CREATE.value],
    KeyPermissionResource.BATCHES.value: [KeyPermissionAction.READ.value, KeyPermissionAction.CREATE.value],
}


async def ensure_bootstrap_api_key(db: AsyncSession, municipio_id: int) -> str | None:
    """Bind the superuser to the demo tenant and issue one bootstrap key.

    Returns None if a key already exists.
    """
    user = (await db.execute(select(User).where(User.is_superuser.is_(True)))).scalars().first()
    if user is None:
        logger.warning("no superuser found; skipping bootstrap API key")
        return None

    if user.municipio_id != municipio_id:
        await db.execute(update(User).where(User.id == user.id).values(municipio_id=municipio_id))
        await db.commit()
        logger.info(f"bound superuser {user.id} to municipio {municipio_id}")

    existing = (
        (await db.execute(select(APIKey).where(APIKey.user_id == user.id, APIKey.name == BOOTSTRAP_KEY_NAME))).scalars().first()
    )
    if existing is not None:
        logger.info("bootstrap API key already exists; not reissuing")
        return None

    created = await APIKeyService().create_api_key(
        user_id=user.id,
        key_data=APIKeyCreate(name=BOOTSTRAP_KEY_NAME, permissions=BOOTSTRAP_PERMISSIONS),
        db=db,
    )

    logger.info("issued bootstrap API key")
    return str(created["api_key"])
