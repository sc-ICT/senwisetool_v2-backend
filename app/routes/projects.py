from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    CurrentUser,
    get_project_definition_service,
)
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.form_builder.project_definition import (
    ProjectDefinitionCreate,
    ProjectDefinitionListResponse,
    ProjectDefinitionResponse,
    ProjectDefinitionUpdate,
)
from app.services.form_builder.project_definition import (
    ProjectDefinitionService,
)

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


@router.post(
    "",
    response_model=ApiResponse[ProjectDefinitionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    data: ProjectDefinitionCreate,
    service: ProjectDefinitionService = Depends(
        get_project_definition_service,
    ),
    user: User = CurrentUser,
):
    try:
        project = await service.create(
            user_id=user.id,
            data=data,
        )

        return ok(
            message="Projet créé avec succès.",
            data=ProjectDefinitionResponse.model_validate(
                project,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=ApiResponse[ProjectDefinitionListResponse],
)
async def list_projects(
    include_archived: bool = False,
    service: ProjectDefinitionService = Depends(
        get_project_definition_service,
    ),
    user: User = CurrentUser,
):
    projects = await service.list(
        user_id=user.id,
        include_archived=include_archived,
    )

    return ok(
        message="Projets récupérés avec succès.",
        data=ProjectDefinitionListResponse(
            items=[
                ProjectDefinitionResponse.model_validate(
                    project,
                )
                for project in projects
            ],
            count=len(projects),
        ),
    )


@router.get(
    "/{project_id}",
    response_model=ApiResponse[ProjectDefinitionResponse],
)
async def get_project(
    project_id: int,
    service: ProjectDefinitionService = Depends(
        get_project_definition_service,
    ),
    user: User = CurrentUser,
):
    project = await service.get(
        project_id=project_id,
        user_id=user.id,
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet introuvable.",
        )

    return ok(
        message="Projet récupéré avec succès.",
        data=ProjectDefinitionResponse.model_validate(
            project,
        ),
    )


@router.patch(
    "/{project_id}",
    response_model=ApiResponse[ProjectDefinitionResponse],
)
async def update_project(
    project_id: int,
    data: ProjectDefinitionUpdate,
    service: ProjectDefinitionService = Depends(
        get_project_definition_service,
    ),
    user: User = CurrentUser,
):
    try:
        project = await service.update(
            project_id=project_id,
            user_id=user.id,
            data=data,
        )

        return ok(
            message="Projet modifié avec succès.",
            data=ProjectDefinitionResponse.model_validate(
                project,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{project_id}/archive",
    response_model=ApiResponse[ProjectDefinitionResponse],
)
async def archive_project(
    project_id: int,
    service: ProjectDefinitionService = Depends(
        get_project_definition_service,
    ),
    user: User = CurrentUser,
):
    try:
        project = await service.archive(
            project_id=project_id,
            user_id=user.id,
        )

        return ok(
            message="Projet archivé avec succès.",
            data=ProjectDefinitionResponse.model_validate(
                project,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
