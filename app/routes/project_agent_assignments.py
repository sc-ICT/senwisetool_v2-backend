from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.dependencies import (
    CurrentUser,
    get_project_agent_assignment_service,
)
from app.models.project_agent_assignment import ProjectAgentAssignment
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.project_agent_assignment import (
    ProjectAgentAssignmentAddZones,
    ProjectAgentAssignmentAgentResponse,
    ProjectAgentAssignmentCreate,
    ProjectAgentAssignmentListResponse,
    ProjectAgentAssignmentResponse,
    ProjectAgentAssignmentZoneResponse,
)
from app.services.file_system import (
    FileAlreadyExistsError,
    InvalidFileOperationError,
)
from app.services.project_agent_assignment import (
    ProjectAgentAssignmentService,
)

router = APIRouter(
    prefix="/projects/{project_id}/assignments",
    tags=["Project Agent Assignments"],
)


def _to_response(
    assignment: ProjectAgentAssignment,
) -> ProjectAgentAssignmentResponse:
    return ProjectAgentAssignmentResponse(
        id=assignment.id,
        project_id=assignment.project_id,
        agent_id=assignment.agent_id,
        agent=ProjectAgentAssignmentAgentResponse(
            id=assignment.agent.id,
            full_name=assignment.agent.full_name,
            role=assignment.agent.role.value,
            status=assignment.agent.status.value,
        ),
        zones=[
            ProjectAgentAssignmentZoneResponse(
                id=zone.id,
                file_node_id=zone.file_node_id,
                file_name=zone.file_node.name,
            )
            for zone in assignment.zones
        ],
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


# ============================================================================
# LIST
# ============================================================================


@router.get(
    "",
    response_model=ApiResponse[ProjectAgentAssignmentListResponse],
)
async def list_assignments(
    project_id: int,
    service: ProjectAgentAssignmentService = Depends(
        get_project_agent_assignment_service,
    ),
    user: User = CurrentUser,
):
    try:
        assignments = await service.list_by_project(
            user_id=user.id,
            project_id=project_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    items = [_to_response(assignment) for assignment in assignments]

    return ok(
        message="Affectations récupérées avec succès.",
        data=ProjectAgentAssignmentListResponse(
            items=items,
            count=len(items),
        ),
    )


# ============================================================================
# CREATE
# ============================================================================


@router.post(
    "",
    response_model=ApiResponse[ProjectAgentAssignmentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_assignment(
    project_id: int,
    data: ProjectAgentAssignmentCreate,
    service: ProjectAgentAssignmentService = Depends(
        get_project_agent_assignment_service,
    ),
    user: User = CurrentUser,
):
    try:
        assignment = await service.create(
            user_id=user.id,
            project_id=project_id,
            agent_id=data.agent_id,
            zone_file_ids=data.zone_file_ids,
        )

    except ValueError as exc:
        message = str(exc)

        if message in {
            "Projet introuvable.",
            "Agent introuvable.",
        }:
            code = status.HTTP_404_NOT_FOUND
        elif "déjà affecté" in message:
            code = status.HTTP_409_CONFLICT
        else:
            code = status.HTTP_400_BAD_REQUEST

        raise HTTPException(
            status_code=code,
            detail=message,
        ) from exc

    return ok(
        message="Agent affecté au projet avec succès.",
        data=_to_response(assignment),
    )


# ============================================================================
# ADD EXISTING ZONES
# ============================================================================


@router.post(
    "/{assignment_id}/zones",
    response_model=ApiResponse[ProjectAgentAssignmentResponse],
)
async def add_existing_zones(
    project_id: int,
    assignment_id: int,
    data: ProjectAgentAssignmentAddZones,
    service: ProjectAgentAssignmentService = Depends(
        get_project_agent_assignment_service,
    ),
    user: User = CurrentUser,
):
    try:
        assignment = await service.add_existing_zones(
            user_id=user.id,
            project_id=project_id,
            assignment_id=assignment_id,
            zone_file_ids=data.zone_file_ids,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ok(
        message="Zones ajoutées à l'affectation.",
        data=_to_response(assignment),
    )


# ============================================================================
# UPLOAD KML OR GEOJSON FILES AND ADD THEM AS ZONES
# ============================================================================


@router.post(
    "/{assignment_id}/zones/upload",
    response_model=ApiResponse[ProjectAgentAssignmentResponse],
)
async def upload_zones(
    project_id: int,
    assignment_id: int,
    files: list[UploadFile] = File(...),
    service: ProjectAgentAssignmentService = Depends(
        get_project_agent_assignment_service,
    ),
    user: User = CurrentUser,
):
    try:
        assignment = await service.upload_zones(
            user_id=user.id,
            project_id=project_id,
            assignment_id=assignment_id,
            files=files,
        )

    except FileAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except InvalidFileOperationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ok(
        message="Zones KML / GEOJSON ajoutées avec succès.",
        data=_to_response(assignment),
    )


# ============================================================================
# REMOVE ZONE FROM ASSIGNMENT
# ============================================================================


@router.delete(
    "/{assignment_id}/zones/{zone_id}",
    response_model=ApiResponse[ProjectAgentAssignmentResponse],
)
async def remove_zone(
    project_id: int,
    assignment_id: int,
    zone_id: int,
    service: ProjectAgentAssignmentService = Depends(
        get_project_agent_assignment_service,
    ),
    user: User = CurrentUser,
):
    try:
        assignment = await service.remove_zone(
            user_id=user.id,
            project_id=project_id,
            assignment_id=assignment_id,
            zone_id=zone_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ok(
        message="Zone retirée de l'affectation.",
        data=_to_response(assignment),
    )


# ============================================================================
# DELETE ASSIGNMENT
# ============================================================================


@router.delete(
    "/{assignment_id}",
    response_model=ApiResponse[None],
)
async def delete_assignment(
    project_id: int,
    assignment_id: int,
    service: ProjectAgentAssignmentService = Depends(
        get_project_agent_assignment_service,
    ),
    user: User = CurrentUser,
):
    try:
        await service.delete(
            user_id=user.id,
            project_id=project_id,
            assignment_id=assignment_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ok(
        message="Affectation supprimée avec succès.",
        data=None,
    )
