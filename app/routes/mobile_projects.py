from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.dependencies import (
    CurrentAgent,
    get_mobile_project_service,
    get_project_service,
)
from app.models.agent import Agent
from app.schemas.common import ApiResponse, ok
from app.schemas.mobile_project import (
    MobileFormDownloadResponse,
    MobileProjectFormResponse,
    MobileProjectListItemResponse,
    MobileProjectListResponse,
    MobileProjectResponse,
    MobileProjectSyncResponse,
)
from app.services.mobile_project import MobileProjectService
from app.services.project import ProjectService

router = APIRouter(
    prefix="/mobile/projects",
    tags=["Mobile Projects"],
)


@router.get(
    "",
    response_model=ApiResponse[MobileProjectListResponse],
)
async def list_mobile_projects(
    service: ProjectService = Depends(
        get_project_service,
    ),
    agent: Agent = CurrentAgent,
):
    rows = await service.list_assigned_to_agent(
        agent_id=agent.id,
    )

    items = [
        MobileProjectListItemResponse(
            id=project.id,
            code=project.code,
            name=project.name,
            description=project.description,
            project_type=project.project_type,
            status=project.status,
            global_config=project.global_config,
            published_form_count=published_form_count,
            assigned_at=(
                assigned_at
                if isinstance(assigned_at, datetime)
                else (
                    datetime.fromisoformat(assigned_at)
                    if isinstance(assigned_at, str)
                    else datetime.fromisoformat(str(assigned_at))
                )
            ),
        )
        for (
            project,
            published_form_count,
            assigned_at,
        ) in rows
    ]

    return ok(
        message="Projets affectés récupérés avec succès.",
        data=MobileProjectListResponse(
            items=items,
            count=len(items),
        ),
    )


@router.get(
    "/{project_id}/sync",
    response_model=ApiResponse[MobileProjectSyncResponse],
)
async def sync_mobile_project(
    project_id: int,
    service: MobileProjectService = Depends(
        get_mobile_project_service,
    ),
    agent: Agent = CurrentAgent,
):
    manifest = await service.get_sync_manifest(
        project_id=project_id,
        agent_id=agent.id,
    )

    if manifest is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet introuvable ou non affecté à cet agent.",
        )

    return ok(
        message="Manifeste de synchronisation récupéré avec succès.",
        data=MobileProjectSyncResponse.model_validate(
            manifest,
        ),
    )


@router.get(
    "/{project_id}/files/{file_id}/download",
)
async def download_mobile_project_file(
    project_id: int,
    file_id: int,
    service: MobileProjectService = Depends(
        get_mobile_project_service,
    ),
    agent: Agent = CurrentAgent,
):
    file_node = await service.get_authorized_file_for_agent(
        project_id=project_id,
        agent_id=agent.id,
        file_id=file_id,
    )

    if file_node is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fichier introuvable ou accès non autorisé.",
        )

    # Vérifier que le fichier possède bien une ressource physique.
    if not file_node.storage_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Le fichier ne possède aucune ressource physique.",
        )

    # Récupérer le chemin physique du fichier.
    file_path = service.file_system_service.storage.get_path(
        storage_key=file_node.storage_key,
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Le fichier physique est introuvable.",
        )

    return FileResponse(
        path=file_path,
        media_type=file_node.mime_type or "application/octet-stream",
        filename=file_node.name,
    )


@router.get(
    "/{project_id}/forms/{form_id}/download",
    response_model=ApiResponse[MobileFormDownloadResponse],
)
async def download_mobile_project_form(
    project_id: int,
    form_id: int,
    service: MobileProjectService = Depends(
        get_mobile_project_service,
    ),
    agent: Agent = CurrentAgent,
):
    form = await service.get_form_for_agent(
        project_id=project_id,
        form_id=form_id,
        agent_id=agent.id,
    )

    if form is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=("Formulaire introuvable ou accès non autorisé."),
        )

    return ok(
        message="Formulaire téléchargé avec succès.",
        data=MobileFormDownloadResponse.model_validate(form),
    )


@router.get(
    "/{project_id}",
    response_model=ApiResponse[MobileProjectResponse],
)
async def get_mobile_project(
    project_id: int,
    service: ProjectService = Depends(
        get_project_service,
    ),
    agent: Agent = CurrentAgent,
):
    result = await service.get_assigned_to_agent(
        project_id=project_id,
        agent_id=agent.id,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projet introuvable ou non affecté à cet agent.",
        )

    project, assigned_at, forms = result

    return ok(
        message="Projet récupéré avec succès.",
        data=MobileProjectResponse(
            id=project.id,
            code=project.code,
            name=project.name,
            description=project.description,
            project_type=project.project_type,
            status=project.status,
            global_config=project.global_config,
            published_form_count=len(forms),
            assigned_at=(
                assigned_at
                if isinstance(assigned_at, datetime)
                else (
                    datetime.fromisoformat(assigned_at)
                    if isinstance(assigned_at, str)
                    else datetime.fromisoformat(str(assigned_at))
                )
            ),
            forms=[
                MobileProjectFormResponse.model_validate(
                    form,
                )
                for form in forms
            ],
        ),
    )
