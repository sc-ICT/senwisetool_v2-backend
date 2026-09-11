from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    CurrentAdmin,
    get_plugin_service,
)
from app.models.enums import PluginVersionStatus
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.plugin import (
    PluginCreate,
    PluginListResponse,
    PluginResponse,
    PluginUpdate,
    PluginVersionResponse,
)
from app.services.plugin import PluginService

router = APIRouter(
    prefix="/plugins",
    tags=["Plugins"],
)


# ============================================================================
# CREATE
# ============================================================================


@router.post(
    "",
    response_model=ApiResponse[PluginResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_plugin(
    data: PluginCreate,
    service: PluginService = Depends(
        get_plugin_service,
    ),
    admin: User = CurrentAdmin,
):
    try:
        plugin = await service.create(
            user_id=admin.id,
            data=data,
        )

        return ok(
            message="Plugin créé avec succès.",
            data=PluginResponse.model_validate(
                plugin,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# LIST
# ============================================================================


@router.get(
    "",
    response_model=ApiResponse[PluginListResponse],
)
async def list_plugins(
    include_archived: bool = False,
    service: PluginService = Depends(
        get_plugin_service,
    ),
    admin: User = CurrentAdmin,
):
    plugins = await service.list(
        include_archived=include_archived,
    )

    return ok(
        message="Plugins récupérés avec succès.",
        data=PluginListResponse(
            items=[
                PluginResponse.model_validate(
                    plugin,
                )
                for plugin in plugins
            ],
            count=len(plugins),
        ),
    )


# ============================================================================
# VERIFY VERSION INTEGRITY
# ============================================================================


@router.get(
    "/{plugin_id}/versions/{version_id}/integrity",
    response_model=ApiResponse[dict],
)
async def verify_plugin_version_integrity(
    plugin_id: int,
    version_id: int,
    service: PluginService = Depends(
        get_plugin_service,
    ),
    admin: User = CurrentAdmin,
):
    version = await service.get_version(
        plugin_id=plugin_id,
        version_id=version_id,
    )

    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version du plugin introuvable.",
        )

    valid = service.verify_version_integrity(
        version,
    )

    return ok(
        message="Intégrité de la version vérifiée.",
        data={
            "version_id": version.id,
            "version": version.version,
            "status": version.status,
            "valid": valid,
            "definition_hash": version.definition_hash,
        },
    )


# ============================================================================
# GET VERSION
# ============================================================================


@router.get(
    "/{plugin_id}/versions/{version_id}",
    response_model=ApiResponse[PluginVersionResponse],
)
async def get_plugin_version(
    plugin_id: int,
    version_id: int,
    service: PluginService = Depends(
        get_plugin_service,
    ),
    admin: User = CurrentAdmin,
):
    version = await service.get_version(
        plugin_id=plugin_id,
        version_id=version_id,
    )

    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version du plugin introuvable.",
        )

    return ok(
        message="Version du plugin récupérée avec succès.",
        data=PluginVersionResponse.model_validate(
            version,
        ),
    )


# ============================================================================
# GET
# ============================================================================


@router.get(
    "/{plugin_id}",
    response_model=ApiResponse[PluginResponse],
)
async def get_plugin(
    plugin_id: int,
    service: PluginService = Depends(
        get_plugin_service,
    ),
    admin: User = CurrentAdmin,
):
    plugin = await service.get(
        plugin_id=plugin_id,
    )

    if plugin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plugin introuvable.",
        )

    return ok(
        message="Plugin récupéré avec succès.",
        data=PluginResponse.model_validate(
            plugin,
        ),
    )


# ============================================================================
# UPDATE
# ============================================================================


@router.patch(
    "/{plugin_id}",
    response_model=ApiResponse[PluginResponse],
)
async def update_plugin(
    plugin_id: int,
    data: PluginUpdate,
    service: PluginService = Depends(
        get_plugin_service,
    ),
    admin: User = CurrentAdmin,
):
    try:
        plugin = await service.update(
            plugin_id=plugin_id,
            data=data,
        )

        return ok(
            message="Plugin modifié avec succès.",
            data=PluginResponse.model_validate(
                plugin,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# PUBLISH
# ============================================================================


@router.post(
    "/{plugin_id}/publish",
    response_model=ApiResponse[PluginResponse],
)
async def publish_plugin(
    plugin_id: int,
    service: PluginService = Depends(
        get_plugin_service,
    ),
    admin: User = CurrentAdmin,
):
    try:
        plugin = await service.publish(
            plugin_id=plugin_id,
        )

        return ok(
            message="Plugin publié avec succès.",
            data=PluginResponse.model_validate(
                plugin,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# UNPUBLISH
# ============================================================================


@router.post(
    "/{plugin_id}/unpublish",
    response_model=ApiResponse[PluginResponse],
)
async def unpublish_plugin(
    plugin_id: int,
    service: PluginService = Depends(
        get_plugin_service,
    ),
    admin: User = CurrentAdmin,
):
    try:
        plugin = await service.unpublish(
            plugin_id=plugin_id,
        )

        return ok(
            message="Plugin dépublié avec succès.",
            data=PluginResponse.model_validate(
                plugin,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# MOVE TO DRAFT
# ============================================================================


@router.post(
    "/{plugin_id}/draft",
    response_model=ApiResponse[PluginResponse],
)
async def move_plugin_to_draft(
    plugin_id: int,
    service: PluginService = Depends(
        get_plugin_service,
    ),
    admin: User = CurrentAdmin,
):
    try:
        plugin = await service.move_to_draft(
            plugin_id=plugin_id,
        )

        return ok(
            message="Plugin remis en brouillon avec succès.",
            data=PluginResponse.model_validate(
                plugin,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# ARCHIVE
# ============================================================================


@router.post(
    "/{plugin_id}/archive",
    response_model=ApiResponse[PluginResponse],
)
async def archive_plugin(
    plugin_id: int,
    service: PluginService = Depends(
        get_plugin_service,
    ),
    admin: User = CurrentAdmin,
):
    try:
        plugin = await service.archive(
            plugin_id=plugin_id,
        )

        return ok(
            message="Plugin archivé avec succès.",
            data=PluginResponse.model_validate(
                plugin,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# DELETE
# ============================================================================


@router.delete(
    "/{plugin_id}",
    response_model=ApiResponse[None],
)
async def delete_plugin(
    plugin_id: int,
    service: PluginService = Depends(
        get_plugin_service,
    ),
    admin: User = CurrentAdmin,
):
    try:
        await service.delete(
            plugin_id=plugin_id,
        )

        return ok(
            message="Plugin supprimé avec succès.",
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
