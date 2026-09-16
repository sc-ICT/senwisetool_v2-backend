from io import BytesIO

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse, StreamingResponse

from app.dependencies import (
    CurrentAdmin,
    CurrentUser,
    get_plugin_resource_definition_import_service,
    get_plugin_resource_export_service,
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
    PluginResourceRelatedRecordsResponse,
    PluginResourceRelationCreate,
    PluginResourceRelationResponse,
    PluginResourceResponse,
    PluginResourceUpdate,
    PluginResourceUserSchemaResponse,
    PluginResourceUserSchemaUpdate,
    PluginResourceWorkbookImportResponse,
)
from app.schemas.plugin_resource_definition_import import (
    PluginResourceDefinitionImportResponse,
)
from app.services.plugin_resource import (
    PluginResourceService,
)
from app.services.plugin_resource_definition_import import (
    PluginResourceDefinitionImportService,
)
from app.services.plugin_resource_export import (
    PluginResourceExportService,
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
# RESOURCE RELATIONS
# ============================================================================


@router.get(
    "/resources/{resource_id}/relations",
    response_model=ApiResponse[list[PluginResourceRelationResponse]],
)
async def list_relations(
    resource_id: int,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    admin: User = CurrentAdmin,
):
    try:

        relations = await service.list_relations(
            resource_id=resource_id,
        )

        return ok(
            message="Relations récupérées avec succès.",
            data=[
                PluginResourceRelationResponse(
                    id=relation.id,
                    source_resource_id=relation.source_resource_id,
                    source_field_key=relation.source_field_key,
                    target_resource_id=relation.target_resource_id,
                    target_field_key=relation.target_field_key,
                    source_resource_name=relation.source_resource.name,
                    target_resource_name=relation.target_resource.name,
                    label=relation.label,
                    is_active=relation.is_active,
                    created_at=relation.created_at,
                    updated_at=relation.updated_at,
                )
                for relation in relations
            ],
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/resources/{resource_id}/relations",
    response_model=ApiResponse[PluginResourceRelationResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_relation(
    resource_id: int,
    data: PluginResourceRelationCreate,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    admin: User = CurrentAdmin,
):
    try:

        relation = await service.create_relation(
            resource_id=resource_id,
            data=data,
        )

        return ok(
            message="Relation créée avec succès.",
            data=PluginResourceRelationResponse(
                id=relation.id,
                source_resource_id=relation.source_resource_id,
                source_field_key=relation.source_field_key,
                target_resource_id=relation.target_resource_id,
                target_field_key=relation.target_field_key,
                source_resource_name=relation.source_resource.name,
                target_resource_name=relation.target_resource.name,
                label=relation.label,
                is_active=relation.is_active,
                created_at=relation.created_at,
                updated_at=relation.updated_at,
            ),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/resources/{resource_id}/relations/{relation_id}",
    response_model=ApiResponse[None],
)
async def delete_relation(
    resource_id: int,
    relation_id: int,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    admin: User = CurrentAdmin,
):
    try:

        await service.delete_relation(
            resource_id=resource_id,
            relation_id=relation_id,
        )

        return ok(
            message="Relation supprimée avec succès.",
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/resources/{resource_id}/records/{record_id}/relations/{relation_id}",
    response_model=ApiResponse[PluginResourceRelatedRecordsResponse],
)
async def list_related_records(
    resource_id: int,
    record_id: int,
    relation_id: int,
    service: PluginResourceService = Depends(
        get_plugin_resource_service,
    ),
    user: User = CurrentUser,
):
    try:

        relation, direction, records = await service.list_related_records(
            resource_id=resource_id,
            record_id=record_id,
            relation_id=relation_id,
            user_id=user.id,
            is_admin=user.role.value == "ADMIN",
        )

        target_resource_id = (
            relation.target_resource_id
            if direction == "SOURCE_TO_TARGET"
            else relation.source_resource_id
        )

        return ok(
            message="Données liées récupérées avec succès.",
            data=PluginResourceRelatedRecordsResponse(
                relation_id=relation.id,
                source_resource_id=resource_id,
                source_record_id=record_id,
                target_resource_id=target_resource_id,
                direction=direction,
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
# RESOURCE DEFINITION EXCEL IMPORT
# ============================================================================
#
# IMPORTANT :
# Cet endpoint est volontairement différent de :
#
#     POST /{plugin_id}/resources/import
#
# qui correspond à l'ancien import complet RESOURCE/SCHEMA/RELATION/DATA.
#
# Celui-ci gère uniquement le modèle :
#
#     _RESOURCE_(A5:E6)
#
# Une feuille = une ressource.
# ============================================================================


@router.post(
    "/{plugin_id}/resources/import-definitions",
    response_model=ApiResponse[PluginResourceDefinitionImportResponse],
    status_code=status.HTTP_201_CREATED,
)
async def import_plugin_resource_definitions(
    plugin_id: int,
    file: UploadFile = File(...),
    import_service: PluginResourceDefinitionImportService = Depends(
        get_plugin_resource_definition_import_service,
    ),
    admin: User = CurrentAdmin,
):
    filename = (file.filename or "").lower()

    # ------------------------------------------------------------------------
    # Extension
    # ------------------------------------------------------------------------

    if not filename.endswith(".xlsx"):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("Format de fichier invalide. " "Utilisez un fichier .xlsx."),
        )

    try:

        result = await import_service.import_resources(
            plugin_id=plugin_id,
            file=file.file,
            admin_user_id=admin.id,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return ok(
        message=(f"{result.resources_created} ressource(s) " "créée(s) avec succès."),
        data=result,
    )


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


# ============================================================================
# EXCEL EXPORT — DONNÉES D'UNE RESSOURCE
# ============================================================================


@router.get(
    "/resources/{resource_id}/export",
)
async def export_plugin_resource_data(
    resource_id: int,
    export_service: PluginResourceExportService = Depends(
        get_plugin_resource_export_service,
    ),
    admin: User = CurrentAdmin,
):
    try:
        from app.dependencies import get_file_system_service

        file_system = get_file_system_service()

        data = await export_service.export_resource(
            resource_id=resource_id,
            user_id=admin.id,
            is_admin=True,
            storage=file_system.storage,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return StreamingResponse(
        BytesIO(data),
        media_type="application/zip",
        headers={
            "Content-Disposition": (f'attachment; filename="resource-{resource_id}-data.zip"')
        },
    )
