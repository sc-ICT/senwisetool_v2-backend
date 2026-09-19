from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    CurrentAdmin,
    get_plugin_project_template_service,
)
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.plugin_project_template import (
    PluginProjectTemplateCreate,
    PluginProjectTemplateListResponse,
    PluginProjectTemplateResponse,
    PluginProjectTemplateUpdate,
)
from app.services.plugin_project_template import (
    PluginProjectTemplateService,
)

router = APIRouter(
    prefix="/plugins",
    tags=["Plugin Project Templates"],
)


def _response(
    template,
) -> PluginProjectTemplateResponse:
    return PluginProjectTemplateResponse.model_validate(template)


# ============================================================
# LIST
# ============================================================


@router.get(
    "/{plugin_id}/project-templates",
    response_model=ApiResponse[PluginProjectTemplateListResponse],
)
async def list_project_templates(
    plugin_id: int,
    include_inactive: bool = False,
    service: PluginProjectTemplateService = Depends(get_plugin_project_template_service),
    admin: User = CurrentAdmin,
):
    """
    Retourne les modèles de projet disponibles pour un plugin.

    Par défaut, seuls les modèles actifs sont retournés.

    include_inactive=true permet à l'administrateur de récupérer
    également les modèles désactivés.
    """

    try:
        items = await service.list(
            plugin_id=plugin_id,
            include_inactive=include_inactive,
        )

        data = PluginProjectTemplateListResponse(
            items=[_response(item) for item in items],
            count=len(items),
        )

        return ok(
            message="Modèles de projets récupérés avec succès.",
            data=data,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# ============================================================
# GET ONE
# ============================================================


@router.get(
    "/{plugin_id}/project-templates/{template_id}",
    response_model=ApiResponse[PluginProjectTemplateResponse],
)
async def get_project_template(
    plugin_id: int,
    template_id: int,
    service: PluginProjectTemplateService = Depends(get_plugin_project_template_service),
    admin: User = CurrentAdmin,
):
    """
    Retourne un modèle de projet précis.

    Le modèle doit appartenir au plugin demandé.
    """

    try:
        item = await service.get(
            plugin_id=plugin_id,
            template_id=template_id,
        )

        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle de projet introuvable.",
            )

        return ok(
            message="Modèle de projet récupéré avec succès.",
            data=_response(item),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# ============================================================
# CREATE
# ============================================================


@router.post(
    "/{plugin_id}/project-templates",
    response_model=ApiResponse[PluginProjectTemplateResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_project_template(
    plugin_id: int,
    data: PluginProjectTemplateCreate,
    service: PluginProjectTemplateService = Depends(get_plugin_project_template_service),
    admin: User = CurrentAdmin,
):
    """
    Crée un modèle de projet pour un plugin.

    La validation métier est déléguée au service.
    """

    try:
        item = await service.create(
            plugin_id=plugin_id,
            creator=admin,
            data=data,
        )

        return ok(
            message="Modèle de projet créé avec succès.",
            data=_response(item),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================
# UPDATE
# ============================================================


@router.patch(
    "/{plugin_id}/project-templates/{template_id}",
    response_model=ApiResponse[PluginProjectTemplateResponse],
)
async def update_project_template(
    plugin_id: int,
    template_id: int,
    data: PluginProjectTemplateUpdate,
    service: PluginProjectTemplateService = Depends(get_plugin_project_template_service),
    admin: User = CurrentAdmin,
):
    """
    Modifie un modèle de projet existant.
    """

    try:
        item = await service.update(
            plugin_id=plugin_id,
            template_id=template_id,
            data=data,
        )

        return ok(
            message="Modèle de projet enregistré avec succès.",
            data=_response(item),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================
# DELETE
# ============================================================


@router.delete(
    "/{plugin_id}/project-templates/{template_id}",
    response_model=ApiResponse[None],
)
async def delete_project_template(
    plugin_id: int,
    template_id: int,
    service: PluginProjectTemplateService = Depends(get_plugin_project_template_service),
    admin: User = CurrentAdmin,
):
    """
    Supprime un modèle de projet.
    """

    try:
        await service.delete(
            plugin_id=plugin_id,
            template_id=template_id,
        )

        return ok(
            message="Modèle de projet supprimé avec succès.",
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
