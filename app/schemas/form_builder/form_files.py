from __future__ import annotations

from pydantic import BaseModel

from app.schemas.file_system import FileNodeResponse


class FormFilesResponse(BaseModel):
    items: list[FileNodeResponse]
    count: int
