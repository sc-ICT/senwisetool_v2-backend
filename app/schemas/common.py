from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Enveloppe standard pour toutes les réponses de l'API."""

    success: bool
    message: str
    data: T | None = None


def ok(message: str, data: T | None = None) -> ApiResponse[T]:
    return ApiResponse(success=True, message=message, data=data)


def fail(message: str) -> ApiResponse[None]:
    return ApiResponse(success=False, message=message, data=None)
