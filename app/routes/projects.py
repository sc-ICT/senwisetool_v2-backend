from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    CurrentUser,
    get_form_definition_service,
    get_project_service,
)
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.form_builder.form_definition import (
    FormDefinitionListResponse,
    FormDefinitionResponse,
    ProjectFormCreate,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.file_system import (
    FileAlreadyExistsError,
    InvalidFileOperationError,
)
from app.services.form_builder.form_definition import FormDefinitionService
from app.services.project import ProjectService

router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


@router.post(
    "",
    response_model=ApiResponse[ProjectResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    data: ProjectCreate,
    service: ProjectService = Depends(
        get_project_service,
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
            data=ProjectResponse.model_validate(
                project,
            ),
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


@router.get(
    "",
    response_model=ApiResponse[ProjectListResponse],
)
async def list_projects(
    include_archived: bool = False,
    service: ProjectService = Depends(
        get_project_service,
    ),
    user: User = CurrentUser,
):
    projects = await service.list(
        user_id=user.id,
        include_archived=include_archived,
    )

    return ok(
        message="Projets récupérés avec succès.",
        data=ProjectListResponse(
            items=[
                ProjectResponse.model_validate(
                    project,
                )
                for project in projects
            ],
            count=len(projects),
        ),
    )


@router.get(
    "/{project_id}",
    response_model=ApiResponse[ProjectResponse],
)
async def get_project(
    project_id: int,
    service: ProjectService = Depends(
        get_project_service,
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
        data=ProjectResponse.model_validate(
            project,
        ),
    )


@router.patch(
    "/{project_id}",
    response_model=ApiResponse[ProjectResponse],
)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    service: ProjectService = Depends(
        get_project_service,
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
            data=ProjectResponse.model_validate(
                project,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{project_id}/forms",
    response_model=ApiResponse[FormDefinitionListResponse],
)
async def list_project_forms(
    project_id: int,
    include_archived: bool = False,
    service: FormDefinitionService = Depends(
        get_form_definition_service,
    ),
    user: User = CurrentUser,
):
    forms = await service.list_by_project(
        project_id=project_id,
        user_id=user.id,
        include_archived=include_archived,
    )

    return ok(
        message="Formulaires du projet récupérés avec succès.",
        data=FormDefinitionListResponse(
            items=[
                FormDefinitionResponse.model_validate(
                    form,
                )
                for form in forms
            ],
            count=len(forms),
        ),
    )


@router.post(
    "/{project_id}/forms",
    response_model=ApiResponse[FormDefinitionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_project_form(
    project_id: int,
    data: ProjectFormCreate,
    service: FormDefinitionService = Depends(
        get_form_definition_service,
    ),
    user: User = CurrentUser,
):
    try:
        form = await service.create_for_project(
            user_id=user.id,
            project_id=project_id,
            name=data.name,
            description=data.description,
            form_type=data.form_type,
        )

        return ok(
            message="Formulaire créé avec succès.",
            data=FormDefinitionResponse.model_validate(
                form,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{project_id}/publish",
    response_model=ApiResponse[ProjectResponse],
)
async def publish_project(
    project_id: int,
    service: ProjectService = Depends(
        get_project_service,
    ),
    user: User = CurrentUser,
):
    try:
        project = await service.publish(
            project_id=project_id,
            user_id=user.id,
        )

        return ok(
            message="Projet publié avec succès.",
            data=ProjectResponse.model_validate(
                project,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{project_id}/archive",
    response_model=ApiResponse[ProjectResponse],
)
async def archive_project(
    project_id: int,
    service: ProjectService = Depends(
        get_project_service,
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
            data=ProjectResponse.model_validate(
                project,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{project_id}/draft",
    response_model=ApiResponse[ProjectResponse],
)
async def restore_project_to_draft(
    project_id: int,
    service: ProjectService = Depends(
        get_project_service,
    ),
    user: User = CurrentUser,
):
    try:
        project = await service.restore_to_draft(
            project_id=project_id,
            user_id=user.id,
        )

        return ok(
            message="Projet remis en brouillon avec succès.",
            data=ProjectResponse.model_validate(
                project,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
