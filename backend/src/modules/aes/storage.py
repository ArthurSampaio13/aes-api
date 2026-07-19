"""S3-compatible object storage for submission originals, OCR transcriptions, and raw provider responses."""

from collections.abc import Callable
from typing import Any, cast

import aioboto3

from ...infrastructure.config.settings import get_settings

settings = get_settings()


class ObjectStorage:
    def __init__(self, bucket: str, client_factory: Callable[[], Any] | None = None) -> None:
        self._bucket = bucket
        self._client_factory = client_factory or self._default_client_factory

    def _default_client_factory(self) -> Any:
        session = aioboto3.Session()
        return session.client(
            "s3",
            endpoint_url=settings.AES_STORAGE_ENDPOINT_URL or None,
            aws_access_key_id=settings.AES_STORAGE_ACCESS_KEY,
            aws_secret_access_key=settings.AES_STORAGE_SECRET_KEY,
        )

    async def put(self, key: str, content: bytes, content_type: str) -> str:
        async with self._client_factory() as client:
            await client.put_object(Bucket=self._bucket, Key=key, Body=content, ContentType=content_type)
        return key

    async def get(self, key: str) -> bytes:
        async with self._client_factory() as client:
            response = await client.get_object(Bucket=self._bucket, Key=key)
            return cast(bytes, await response["Body"].read())


def get_object_storage() -> ObjectStorage:
    return ObjectStorage(bucket=settings.AES_STORAGE_BUCKET)
