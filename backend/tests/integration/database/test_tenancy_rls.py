"""Proves tenant isolation holds at the database level, not just in application code."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.tenancy import set_tenant_context
from src.modules.municipio.models import Municipio


@pytest.mark.integration
async def test_rls_blocks_cross_tenant_read_even_without_app_filter(rls_db: AsyncSession):
    municipio_a = Municipio(nome="Municipio A")
    municipio_b = Municipio(nome="Municipio B")
    rls_db.add_all([municipio_a, municipio_b])
    await rls_db.commit()

    await set_tenant_context(rls_db, municipio_id=municipio_a.id, is_superuser=False)
    await rls_db.execute(
        text("INSERT INTO rubrics (municipio_id, version, criteria) VALUES (:mid, 1, '{}'::jsonb)"),
        {"mid": municipio_a.id},
    )
    await rls_db.commit()

    await set_tenant_context(rls_db, municipio_id=municipio_b.id, is_superuser=False)
    result = await rls_db.execute(text("SELECT * FROM rubrics WHERE municipio_id = :mid"), {"mid": municipio_a.id})
    assert result.fetchall() == []

    result = await rls_db.execute(text("SELECT * FROM rubrics"))
    assert result.fetchall() == []

    await set_tenant_context(rls_db, municipio_id=None, is_superuser=True)
    result = await rls_db.execute(text("SELECT * FROM rubrics"))
    assert len(result.fetchall()) == 1
