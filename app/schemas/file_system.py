from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FileNodeResponse(BaseModel):
    id: int
    user_id: int
    parent_id: int | None
    name: str
    type: str
    storage_key: str | None
    mime_type: str | None
    extension: str | None
    size: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
    }


class CreateFolderRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255,
    )
    parent_id: int | None = None


class RenameFileNodeRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=255,
    )


class MoveFileNodeRequest(BaseModel):
    parent_id: int | None = None


class FileNodeListResponse(BaseModel):
    items: list[FileNodeResponse]
    count: int


class BatchDeleteRequest(BaseModel):
    node_ids: list[int] = Field(
        min_length=1,
    )


class BatchMoveRequest(BaseModel):
    node_ids: list[int] = Field(
        min_length=1,
    )
    parent_id: int | None = None
