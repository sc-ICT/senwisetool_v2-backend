from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectAgentAssignmentCreate(BaseModel):
    agent_id: int = Field(gt=0)
    zone_file_ids: list[int] = Field(default_factory=list)


class ProjectAgentAssignmentAddZones(BaseModel):
    zone_file_ids: list[int] = Field(min_length=1)


class ProjectAgentAssignmentAgentResponse(BaseModel):
    id: int
    full_name: str
    role: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class ProjectAgentAssignmentZoneResponse(BaseModel):
    id: int
    file_node_id: int
    file_name: str

    model_config = ConfigDict(from_attributes=True)


class ProjectAgentAssignmentResponse(BaseModel):
    id: int
    project_id: int
    agent_id: int

    agent: ProjectAgentAssignmentAgentResponse
    zones: list[ProjectAgentAssignmentZoneResponse]

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectAgentAssignmentListResponse(BaseModel):
    items: list[ProjectAgentAssignmentResponse]
    count: int
