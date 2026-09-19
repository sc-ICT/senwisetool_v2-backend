from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    CurrentAdmin,
    get_plugin_form_template_service,
)
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.plugin_form_template import (
    PluginFormTemplateCreate,
    PluginFormTemplateListResponse,
    PluginFormTemplateResponse,
    PluginFormTemplateUpdate,
)
from app.services.plugin_form_template import (
    PluginFormTemplateService,
)

router = APIRouter(
    prefix="/plugins",
    tags=["Plugin Form Templates"],
)


def _response(
    form,
) -> PluginFormTemplateResponse:
    return PluginFormTemplateResponse.model_validate(form)


# ============================================================
# LIST FORM TEMPLATES
# ============================================================


@router.get(
    "/{plugin_id}/project-templates/{project_template_id}/form-templates",
    response_model=ApiResponse[PluginFormTemplateListResponse],
)
async def list_form_templates(
    plugin_id: int,
    project_template_id: int,
    include_inactive: bool = False,
    service: PluginFormTemplateService = Depends(get_plugin_form_template_service),
    admin: User = CurrentAdmin,
):
    """
    Retourne tous les modèles de formulaires appartenant
    à un modèle de projet donné.

    Par défaut, seuls les formulaires actifs sont retournés.
    """

    try:
        items = await service.list(
            plugin_id=plugin_id,
            project_template_id=project_template_id,
            include_inactive=include_inactive,
        )

        data = PluginFormTemplateListResponse(
            items=[_response(item) for item in items],
            count=len(items),
        )

        return ok(
            message="Modèles de formulaires récupérés avec succès.",
            data=data,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# ============================================================
# GET ONE FORM TEMPLATE
# ============================================================


@router.get(
    "/{plugin_id}/project-templates/{project_template_id}/form-templates/{template_id}",
    response_model=ApiResponse[PluginFormTemplateResponse],
)
async def get_form_template(
    plugin_id: int,
    project_template_id: int,
    template_id: int,
    service: PluginFormTemplateService = Depends(get_plugin_form_template_service),
    admin: User = CurrentAdmin,
):
    """
    Retourne un modèle de formulaire précis.

    Le formulaire doit appartenir au modèle de projet demandé.
    Le modèle de projet doit lui-même appartenir au plugin.
    """

    try:
        item = await service.get(
            plugin_id=plugin_id,
            project_template_id=project_template_id,
            template_id=template_id,
        )

        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle de formulaire introuvable.",
            )

        return ok(
            message="Modèle de formulaire récupéré avec succès.",
            data=_response(item),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# ============================================================
# CREATE FORM TEMPLATE
# ============================================================


@router.post(
    "/{plugin_id}/project-templates/{project_template_id}/form-templates",
    response_model=ApiResponse[PluginFormTemplateResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_form_template(
    plugin_id: int,
    project_template_id: int,
    data: PluginFormTemplateCreate,
    service: PluginFormTemplateService = Depends(get_plugin_form_template_service),
    admin: User = CurrentAdmin,
):
    """
    Crée un modèle de formulaire dans un modèle de projet.

    La validation de la définition du formulaire, des questions,
    des versions de questions et des ressources est effectuée
    par le service.
    """

    try:
        item = await service.create(
            plugin_id=plugin_id,
            project_template_id=project_template_id,
            user_id=admin.id,
            data=data,
        )

        return ok(
            message="Modèle de formulaire créé avec succès.",
            data=_response(item),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================
# UPDATE FORM TEMPLATE
# ============================================================


@router.patch(
    "/{plugin_id}/project-templates/{project_template_id}/form-templates/{template_id}",
    response_model=ApiResponse[PluginFormTemplateResponse],
)
async def update_form_template(
    plugin_id: int,
    project_template_id: int,
    template_id: int,
    data: PluginFormTemplateUpdate,
    service: PluginFormTemplateService = Depends(get_plugin_form_template_service),
    admin: User = CurrentAdmin,
):
    """
    Modifie un modèle de formulaire.

    Si la définition du formulaire est modifiée, le service
    revalide notamment les références aux questions et aux
    ressources.
    """

    try:
        item = await service.update(
            plugin_id=plugin_id,
            project_template_id=project_template_id,
            template_id=template_id,
            user_id=admin.id,
            data=data,
        )

        return ok(
            message="Modèle de formulaire enregistré avec succès.",
            data=_response(item),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================
# DELETE FORM TEMPLATE
# ============================================================


@router.delete(
    "/{plugin_id}/project-templates/{project_template_id}/form-templates/{template_id}",
    response_model=ApiResponse[None],
)
async def delete_form_template(
    plugin_id: int,
    project_template_id: int,
    template_id: int,
    service: PluginFormTemplateService = Depends(get_plugin_form_template_service),
    admin: User = CurrentAdmin,
):
    """
    Supprime un modèle de formulaire.
    """

    try:
        await service.delete(
            plugin_id=plugin_id,
            project_template_id=project_template_id,
            template_id=template_id,
        )

        return ok(
            message="Modèle de formulaire supprimé avec succès.",
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
