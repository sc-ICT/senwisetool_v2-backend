from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse

from app.dependencies import (
    CurrentAdmin,
    CurrentUser,
    get_plugin_resource_import_service,
    get_plugin_resource_service,
)
from app.models.user import User
from app.schemas.common import (
    ApiResponse,
    ok,
)
from app.schemas.plugin_resource import (
    PluginResourceCreate,
    PluginResourceEffectiveSchemaResponse,
    PluginResourceFieldCreate,
    PluginResourceFieldUpdate,
    PluginResourceImportResponse,
    PluginResourceListResponse,
    PluginResourceRecordCreate,
    PluginResourceRecordListResponse,
    PluginResourceRecordResponse,
    PluginResourceRecordUpdate,
    PluginResourceResponse,
    PluginResourceUpdate,
    PluginResourceUserSchemaResponse,
    PluginResourceUserSchemaUpdate,
)
from app.services.plugin_resource import (
    PluginResourceService,
)
from app.services.plugin_resource_import import (
    PluginResourceImportService,
)

router = APIRouter(
    prefix="/plugins",
    tags=["Plugin Resources"],
)


# ============================================================================
# RESOURCE
# ============================================================================


@router.get(
    "/{plugin_id}/resources",
    response_model=ApiResponse[PluginResourceListResponse],
)
async def list_resources(
    plugin_id: int,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    admin: User = CurrentAdmin,
):
    try:

        resources = await service.list(
            plugin_id=plugin_id,
        )

        return ok(
            message="Ressources récupérées avec succès.",
            data=PluginResourceListResponse(
                items=[
                    PluginResourceResponse.model_validate(
                        resource,
                    )
                    for resource in resources
                ],
                count=len(resources),
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/resources/{resource_id}",
    response_model=ApiResponse[PluginResourceResponse],
)
async def get_resource(
    resource_id: int,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    admin: User = CurrentAdmin,
):
    resource = await service.get(
        resource_id=resource_id,
    )

    if resource is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ressource introuvable.",
        )

    return ok(
        message="Ressource récupérée avec succès.",
        data=PluginResourceResponse.model_validate(
            resource,
        ),
    )


@router.post(
    "/{plugin_id}/resources",
    response_model=ApiResponse[PluginResourceResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_resource(
    plugin_id: int,
    data: PluginResourceCreate,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    admin: User = CurrentAdmin,
):
    try:

        resource = await service.create(
            plugin_id=plugin_id,
            data=data,
        )

        return ok(
            message="Ressource créée avec succès.",
            data=PluginResourceResponse.model_validate(
                resource,
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/resources/{resource_id}",
    response_model=ApiResponse[PluginResourceResponse],
)
async def update_resource(
    resource_id: int,
    data: PluginResourceUpdate,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    admin: User = CurrentAdmin,
):
    try:

        resource = await service.update(
            resource_id=resource_id,
            data=data,
        )

        return ok(
            message="Ressource modifiée avec succès.",
            data=PluginResourceResponse.model_validate(
                resource,
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/resources/{resource_id}",
    response_model=ApiResponse[None],
)
async def delete_resource(
    resource_id: int,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    admin: User = CurrentAdmin,
):
    try:

        await service.delete(
            resource_id=resource_id,
        )

        return ok(
            message="Ressource supprimée avec succès.",
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# FIELDS
# ============================================================================


@router.post(
    "/resources/{resource_id}/fields",
    response_model=ApiResponse[PluginResourceResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_field(
    resource_id: int,
    data: PluginResourceFieldCreate,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    admin: User = CurrentAdmin,
):
    try:

        resource = await service.add_field(
            resource_id=resource_id,
            data=data,
        )

        return ok(
            message="Champ ajouté avec succès.",
            data=PluginResourceResponse.model_validate(
                resource,
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/resources/{resource_id}/fields/{field_id}",
    response_model=ApiResponse[PluginResourceResponse],
)
async def update_field(
    resource_id: int,
    field_id: int,
    data: PluginResourceFieldUpdate,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    admin: User = CurrentAdmin,
):
    try:

        resource = await service.update_field(
            resource_id=resource_id,
            field_id=field_id,
            data=data,
        )

        return ok(
            message="Champ modifié avec succès.",
            data=PluginResourceResponse.model_validate(
                resource,
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/resources/{resource_id}/fields/{field_id}",
    response_model=ApiResponse[PluginResourceResponse],
)
async def delete_field(
    resource_id: int,
    field_id: int,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    admin: User = CurrentAdmin,
):
    try:

        resource = await service.delete_field(
            resource_id=resource_id,
            field_id=field_id,
        )

        return ok(
            message="Champ supprimé avec succès.",
            data=PluginResourceResponse.model_validate(
                resource,
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# EFFECTIVE SCHEMA
# ============================================================================


@router.get(
    "/resources/{resource_id}/schema/effective",
    response_model=ApiResponse[PluginResourceEffectiveSchemaResponse],
)
async def get_effective_schema(
    resource_id: int,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    user: User = CurrentUser,
):
    try:

        payload = await service.get_effective_schema_payload(
            resource_id=resource_id,
            user_id=user.id,
        )

        return ok(
            message="Schema effectif récupéré avec succès.",
            data=PluginResourceEffectiveSchemaResponse(
                **payload,
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# USER SCHEMA OVERRIDE
# ============================================================================


@router.put(
    "/resources/{resource_id}/schema/override",
    response_model=ApiResponse[PluginResourceUserSchemaResponse],
)
async def update_user_schema(
    resource_id: int,
    data: PluginResourceUserSchemaUpdate,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    user: User = CurrentUser,
):
    try:

        override = await service.update_user_schema(
            resource_id=resource_id,
            user_id=user.id,
            data=data,
        )

        return ok(
            message="Schema utilisateur enregistré avec succès.",
            data=PluginResourceUserSchemaResponse.model_validate(
                override,
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/resources/{resource_id}/schema/override",
    response_model=ApiResponse[None],
)
async def reset_user_schema(
    resource_id: int,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    user: User = CurrentUser,
):
    try:

        await service.reset_user_schema(
            resource_id=resource_id,
            user_id=user.id,
        )

        return ok(
            message="Schema utilisateur réinitialisé.",
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# RECORDS
# ============================================================================


@router.get(
    "/resources/{resource_id}/records",
    response_model=ApiResponse[PluginResourceRecordListResponse],
)
async def list_records(
    resource_id: int,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    user: User = CurrentUser,
):
    try:

        is_admin = user.role.value == "ADMIN"

        records = await service.list_records(
            resource_id=resource_id,
            user_id=user.id,
            is_admin=is_admin,
        )

        return ok(
            message="Données récupérées avec succès.",
            data=PluginResourceRecordListResponse(
                items=[
                    PluginResourceRecordResponse.model_validate(
                        record,
                    )
                    for record in records
                ],
                count=len(records),
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/resources/{resource_id}/records",
    response_model=ApiResponse[PluginResourceRecordResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_record(
    resource_id: int,
    data: PluginResourceRecordCreate,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    user: User = CurrentUser,
):
    try:

        is_admin = user.role.value == "ADMIN"

        record = await service.create_record(
            resource_id=resource_id,
            data=data,
            user_id=user.id,
            is_admin=is_admin,
        )

        return ok(
            message="Donnée enregistrée avec succès.",
            data=PluginResourceRecordResponse.model_validate(
                record,
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/resources/{resource_id}/records/{record_id}",
    response_model=ApiResponse[PluginResourceRecordResponse],
)
async def update_record(
    resource_id: int,
    record_id: int,
    data: PluginResourceRecordUpdate,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    user: User = CurrentUser,
):
    try:

        is_admin = user.role.value == "ADMIN"

        record = await service.update_record(
            resource_id=resource_id,
            record_id=record_id,
            data=data,
            user_id=user.id,
            is_admin=is_admin,
        )

        return ok(
            message="Donnée modifiée avec succès.",
            data=PluginResourceRecordResponse.model_validate(
                record,
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/resources/{resource_id}/records/{record_id}",
    response_model=ApiResponse[None],
)
async def delete_record(
    resource_id: int,
    record_id: int,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    user: User = CurrentUser,
):
    try:

        is_admin = user.role.value == "ADMIN"

        await service.delete_record(
            resource_id=resource_id,
            record_id=record_id,
            user_id=user.id,
            is_admin=is_admin,
        )

        return ok(
            message="Donnée supprimée avec succès.",
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ============================================================================
# EXCEL IMPORT
# ============================================================================


@router.post(
    "/resources/{resource_id}/records/import",
    response_model=ApiResponse[PluginResourceImportResponse],
)
async def import_records(
    resource_id: int,
    file: UploadFile = File(...),
    import_service: PluginResourceImportService = Depends(
        get_plugin_resource_import_service,
    ),
    user: User = CurrentUser,
):
    # ------------------------------------------------------------------------
    # Extension
    # ------------------------------------------------------------------------

    filename = (file.filename or "").lower()

    if not filename.endswith(
        ".xlsx",
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("Format de fichier invalide. " "Utilisez un fichier .xlsx."),
        )

    # ------------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------------

    try:

        result = await import_service.import_excel(
            resource_id=resource_id,
            file=file.file,
            user_id=user.id,
            is_admin=user.role.value == "ADMIN",
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # ------------------------------------------------------------------------
    # Validation Excel échouée
    # ------------------------------------------------------------------------

    if result.errors:

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "message": (
                    "Le fichier Excel contient des erreurs. " "Aucune donnée n'a été importée."
                ),
                "data": result.model_dump(
                    mode="json",
                ),
            },
        )

    return ok(
        message=(f"{result.imported} donnée(s) importée(s) " "avec succès."),
        data=result,
    )
