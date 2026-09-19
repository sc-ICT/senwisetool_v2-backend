from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    CurrentAdmin,
    get_plugin_program_service,
)
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.plugin_program import (
    PluginProgramCreate,
    PluginProgramListResponse,
    PluginProgramResponse,
    PluginProgramUpdate,
)
from app.services.plugin_program import PluginProgramService

router = APIRouter(
    prefix="/plugins",
    tags=["Plugin Programs"],
)


def _response(
    program,
) -> PluginProgramResponse:
    return PluginProgramResponse.model_validate(
        program,
    )


# ============================================================================
# LIST
# ============================================================================


@router.get(
    "/{plugin_id}/programs",
    response_model=ApiResponse[PluginProgramListResponse],
)
async def list_programs(
    plugin_id: int,
    include_inactive: bool = False,
    service: PluginProgramService = Depends(
        get_plugin_program_service,
    ),
    admin: User = CurrentAdmin,
):
    try:
        items = await service.list(
            plugin_id=plugin_id,
            include_inactive=include_inactive,
        )

        data = PluginProgramListResponse(
            items=[_response(item) for item in items],
            count=len(items),
        )

        return ok(
            message="Programmes récupérés avec succès.",
            data=data,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# ============================================================================
# GET
# ============================================================================


@router.get(
    "/{plugin_id}/programs/{program_id}",
    response_model=ApiResponse[PluginProgramResponse],
)
async def get_program(
    plugin_id: int,
    program_id: int,
    service: PluginProgramService = Depends(
        get_plugin_program_service,
    ),
    admin: User = CurrentAdmin,
):
    try:
        item = await service.get(
            plugin_id=plugin_id,
            program_id=program_id,
        )

        if item is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Programme introuvable.",
            )

        return ok(
            message="Programme récupéré avec succès.",
            data=_response(item),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# ============================================================================
# CREATE
# ============================================================================


@router.post(
    "/{plugin_id}/programs",
    response_model=ApiResponse[PluginProgramResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_program(
    plugin_id: int,
    data: PluginProgramCreate,
    service: PluginProgramService = Depends(
        get_plugin_program_service,
    ),
    admin: User = CurrentAdmin,
):
    try:
        item = await service.create(
            plugin_id=plugin_id,
            creator=admin,
            data=data,
        )

        return ok(
            message="Programme créé avec succès.",
            data=_response(item),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# UPDATE
# ============================================================================


@router.patch(
    "/{plugin_id}/programs/{program_id}",
    response_model=ApiResponse[PluginProgramResponse],
)
async def update_program(
    plugin_id: int,
    program_id: int,
    data: PluginProgramUpdate,
    service: PluginProgramService = Depends(
        get_plugin_program_service,
    ),
    admin: User = CurrentAdmin,
):
    try:
        item = await service.update(
            plugin_id=plugin_id,
            program_id=program_id,
            data=data,
        )

        return ok(
            message="Programme enregistré avec succès.",
            data=_response(item),
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
    "/{plugin_id}/programs/{program_id}",
    response_model=ApiResponse[None],
)
async def delete_program(
    plugin_id: int,
    program_id: int,
    service: PluginProgramService = Depends(
        get_plugin_program_service,
    ),
    admin: User = CurrentAdmin,
):
    try:
        await service.delete(
            plugin_id=plugin_id,
            program_id=program_id,
        )

        return ok(
            message="Programme supprimé avec succès.",
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
