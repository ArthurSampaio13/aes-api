from typing import Annotated

from fastapi import Depends

from .service import AesService


def get_aes_service() -> AesService:
    return AesService()


AesServiceDep = Annotated[AesService, Depends(get_aes_service)]
