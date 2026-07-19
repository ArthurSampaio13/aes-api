import pytest
from loguru import logger
from sqlalchemy.exc import NoResultFound

from src.modules.common.exceptions import UserNotFoundError
from src.modules.user import service as user_service_module
from src.modules.user.service import UserService


async def test_anonymize_user_failure_logs_bound_audit_fields(monkeypatch):
    async def fake_get(*args, **kwargs):
        raise NoResultFound

    monkeypatch.setattr(user_service_module.crud_users, "get", fake_get)

    records = []
    sink_id = logger.add(records.append)

    try:
        with pytest.raises(UserNotFoundError):
            await UserService().anonymize_user(user_id=999, db=None)
    finally:
        logger.remove(sink_id)

    assert records
    bound_extra = records[-1].record["extra"]
    assert bound_extra["action"] == "user_anonymization_failed"
    assert bound_extra["user_id"] == 999
    assert bound_extra["reason"] == "user_not_found"
