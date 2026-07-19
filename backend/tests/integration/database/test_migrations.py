"""Proves the real Alembic migration chain builds a working schema, not just Base.metadata.create_all."""

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[3]

EXPECTED_TABLES = {
    "municipios",
    "rubrics",
    "prompt_templates",
    "essay_prompts",
    "batches",
    "submissions",
    "correction_jobs",
    "correction_attempts",
    "correction_results",
}


async def _inspect_schema(async_url: str) -> tuple[set[str], bool]:
    engine = create_async_engine(async_url)
    try:
        async with engine.connect() as conn:
            tables = set(await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names()))
            rls_enabled = (
                await conn.execute(text("SELECT relrowsecurity FROM pg_class WHERE relname = 'correction_attempts'"))
            ).scalar_one()
            return tables, bool(rls_enabled)
    finally:
        await engine.dispose()


@pytest.mark.integration
def test_alembic_upgrade_head_from_scratch_creates_expected_schema(test_db_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", test_db_url)

    alembic_cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))

    command.upgrade(alembic_cfg, "head")
    try:
        tables, rls_enabled = asyncio.run(_inspect_schema(test_db_url))

        assert EXPECTED_TABLES.issubset(tables), f"Missing tables: {EXPECTED_TABLES - tables}"
        assert rls_enabled is True
    finally:
        command.downgrade(alembic_cfg, "base")
