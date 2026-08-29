from __future__ import annotations

from pydantic import BaseModel

from app.schemas.file_system import FileNodeResponse


class ProjectFilesResponse(BaseModel):
    items: list[FileNodeResponse]
    count: int
