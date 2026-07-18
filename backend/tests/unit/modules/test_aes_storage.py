import pytest

from src.modules.aes.storage import ObjectStorage


class FakeS3Client:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    async def put_object(self, Bucket, Key, Body, ContentType):
        self.objects[Key] = Body

    async def get_object(self, Bucket, Key):
        class _Body:
            def __init__(self, data):
                self._data = data

            async def read(self):
                return self._data

        return {"Body": _Body(self.objects[Key])}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.mark.asyncio
async def test_put_then_get_roundtrips_bytes():
    fake_client = FakeS3Client()
    storage = ObjectStorage(bucket="test-bucket", client_factory=lambda: fake_client)

    ref = await storage.put(key="submissions/abc.txt", content=b"hello", content_type="text/plain")
    assert ref == "submissions/abc.txt"

    result = await storage.get("submissions/abc.txt")
    assert result == b"hello"
