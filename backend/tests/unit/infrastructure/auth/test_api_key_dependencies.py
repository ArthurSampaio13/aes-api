from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from src.infrastructure.auth.api_key_dependencies import get_current_principal
from src.modules.api_keys.enums import KeyPermissionAction, KeyPermissionResource
from src.modules.api_keys.schemas import APIKeyValidationResponse


@pytest.mark.asyncio
async def test_get_current_principal_resolves_user_from_valid_api_key():
    dependency = get_current_principal(KeyPermissionResource.RUBRICS, KeyPermissionAction.READ)

    validation = APIKeyValidationResponse(is_valid=True, api_key_id=1, user_id=42)
    fake_user = {"id": 42, "municipio_id": 7, "is_superuser": False}

    with (
        patch(
            "src.infrastructure.auth.api_key_dependencies.APIKeyService.validate_api_key",
            new=AsyncMock(return_value=validation),
        ),
        patch("src.infrastructure.auth.api_key_dependencies.crud_users.get", new=AsyncMock(return_value=fake_user)),
    ):
        result = await dependency(db=AsyncMock(), _csrf=None, x_api_key="fai_somekey_rest", session_user=None)

    assert result == fake_user


@pytest.mark.asyncio
async def test_get_current_principal_rejects_invalid_api_key():
    dependency = get_current_principal(KeyPermissionResource.RUBRICS, KeyPermissionAction.READ)
    validation = APIKeyValidationResponse(is_valid=False, error_message="Invalid API key")

    with patch(
        "src.infrastructure.auth.api_key_dependencies.APIKeyService.validate_api_key",
        new=AsyncMock(return_value=validation),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await dependency(db=AsyncMock(), _csrf=None, x_api_key="fai_bad_key", session_user=None)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_principal_falls_back_to_session_when_no_api_key_header():
    dependency = get_current_principal(KeyPermissionResource.RUBRICS, KeyPermissionAction.READ)
    fake_session_user = {"id": 1, "municipio_id": 3, "is_superuser": True}

    result = await dependency(db=AsyncMock(), _csrf=None, x_api_key=None, session_user=fake_session_user)

    assert result == fake_session_user


@pytest.mark.asyncio
async def test_get_current_principal_rejects_no_api_key_and_no_session():
    dependency = get_current_principal(KeyPermissionResource.RUBRICS, KeyPermissionAction.READ)

    with pytest.raises(HTTPException) as exc_info:
        await dependency(db=AsyncMock(), _csrf=None, x_api_key=None, session_user=None)

    assert exc_info.value.status_code == 401
