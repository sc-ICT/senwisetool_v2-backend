from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.dependencies import (
    CurrentUser,
    get_project_definition_service,
)
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.file_system import FileNodeResponse
from app.schemas.form_builder.project_definition import (
    ProjectDefinitionCreate,
    ProjectDefinitionListResponse,
    ProjectDefinitionResponse,
    ProjectDefinitionUpdate,
)
from app.schemas.form_builder.project_files import ProjectFilesResponse
from app.services.file_system import FileAlreadyExistsError, InvalidFileOperationError
from app.services.form_builder.project_defaults import normalize_project_global_config
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

    project.global_config = normalize_project_global_config(project.global_config)

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


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    project_id: int,
    service: ProjectDefinitionService = Depends(
        get_project_definition_service,
    ),
    user: User = CurrentUser,
):
    try:
        await service.delete(
            project_id=project_id,
            user_id=user.id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/{project_id}/files",
    response_model=ApiResponse[ProjectFilesResponse],
)
async def list_project_files(
    project_id: int,
    service: ProjectDefinitionService = Depends(
        get_project_definition_service,
    ),
    user: User = CurrentUser,
):
    try:
        files = await service.list_project_files(
            project_id=project_id,
            user_id=user.id,
        )

        response_items = [FileNodeResponse.model_validate(file) for file in files]

        return ok(
            message="Fichiers du projet récupérés avec succès.",
            data=ProjectFilesResponse(
                items=response_items,
                count=len(response_items),
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc


@router.post(
    "/{project_id}/files",
    response_model=ApiResponse[FileNodeResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_project_file(
    project_id: int,
    file: UploadFile = File(...),
    service: ProjectDefinitionService = Depends(
        get_project_definition_service,
    ),
    user: User = CurrentUser,
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier ne possède aucun nom.",
        )

    filename = Path(file.filename).name

    extension = Path(filename).suffix.lstrip(".").lower() or None

    try:
        project_file = await service.upload_project_file(
            project_id=project_id,
            user_id=user.id,
            name=filename,
            source=file.file,
            mime_type=file.content_type,
            extension=extension,
        )

        return ok(
            message="Fichier ajouté au projet avec succès.",
            data=FileNodeResponse.model_validate(
                project_file,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except FileAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except InvalidFileOperationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{project_id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project_file(
    project_id: int,
    file_id: int,
    service: ProjectDefinitionService = Depends(
        get_project_definition_service,
    ),
    user: User = CurrentUser,
):
    try:
        await service.delete_project_file(
            project_id=project_id,
            file_id=file_id,
            user_id=user.id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
