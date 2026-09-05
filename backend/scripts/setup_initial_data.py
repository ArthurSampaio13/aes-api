import asyncio
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

from loguru import logger  # noqa: E402

from scripts.create_aes_defaults import create_aes_defaults  # noqa: E402
from scripts.create_bootstrap_api_key import ensure_bootstrap_api_key  # noqa: E402
from scripts.create_first_superuser import create_first_superuser  # noqa: E402
from scripts.create_first_tier import create_first_tier  # noqa: E402
from src.infrastructure.database.session import create_tables, local_session  # noqa: E402


async def setup_initial_data() -> None:
    """Create tables, the default tier, the superuser, the demo tenant, and a bootstrap API key."""
    logger.info("Setting up initial data...")

    logger.info("Creating database tables...")
    try:
        await create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.exception(f"Error creating database tables: {e}")
        sys.exit(1)

    logger.info("Creating first tier...")
    await create_first_tier()

    logger.info("Creating superuser...")
    await create_first_superuser()

    logger.info("Creating AES defaults and bootstrap API key...")
    async with local_session() as session:
        municipio, rubric, template = await create_aes_defaults(session)
        api_key = await ensure_bootstrap_api_key(session, municipio.id)

    print(f"AES_RUBRIC_ID={rubric.id}")
    print(f"AES_PROMPT_TEMPLATE_ID={template.id}")
    if api_key:
        print(f"AES_BOOTSTRAP_API_KEY={api_key}")

    logger.info("Initial data setup complete")


if __name__ == "__main__":
    asyncio.run(setup_initial_data())
