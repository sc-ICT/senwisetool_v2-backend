from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.dependencies import (
    CurrentUser,
    get_current_user,
    get_form_definition_service,
)
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.file_system import FileNodeResponse
from app.schemas.form_builder.form_definition import (
    FormDefinitionCreate,
    FormDefinitionListResponse,
    FormDefinitionResponse,
    FormDefinitionUpdate,
)
from app.schemas.form_builder.form_files import FormFilesResponse
from app.services.file_system import FileAlreadyExistsError, InvalidFileOperationError
from app.services.form_builder.form_defaults import normalize_form_global_config
from app.services.form_builder.form_definition import (
    FormDefinitionService,
)

router = APIRouter(
    prefix="/forms",
    tags=["Forms"],
)


@router.post(
    "",
    response_model=ApiResponse[FormDefinitionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_form(
    data: FormDefinitionCreate,
    service: FormDefinitionService = Depends(
        get_form_definition_service,
    ),
    user: User = CurrentUser,
):
    try:
        form = await service.create(
            user_id=user.id,
            data=data,
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


@router.get(
    "",
    response_model=ApiResponse[FormDefinitionListResponse],
)
async def list_forms(
    include_archived: bool = False,
    service: FormDefinitionService = Depends(
        get_form_definition_service,
    ),
    user: User = CurrentUser,
):
    forms = await service.list(
        user_id=user.id,
        include_archived=include_archived,
    )

    return ok(
        message="Formulaires récupérés avec succès.",
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


@router.get(
    "/{form_id}",
    response_model=ApiResponse[FormDefinitionResponse],
)
async def get_form(
    form_id: int,
    service: FormDefinitionService = Depends(
        get_form_definition_service,
    ),
    user: User = CurrentUser,
):
    form = await service.get(
        form_id=form_id,
        user_id=user.id,
    )

    if form is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Formulaire introuvable.",
        )

    form.global_config = normalize_form_global_config(form.global_config)

    return ok(
        message="Formulaire récupéré avec succès.",
        data=FormDefinitionResponse.model_validate(
            form,
        ),
    )


@router.patch(
    "/{form_id}",
    response_model=ApiResponse[FormDefinitionResponse],
)
async def update_form(
    form_id: int,
    data: FormDefinitionUpdate,
    service: FormDefinitionService = Depends(
        get_form_definition_service,
    ),
    user: User = CurrentUser,
):
    try:
        form = await service.update(
            form_id=form_id,
            user_id=user.id,
            data=data,
        )

        return ok(
            message="Formulaire modifié avec succès.",
            data=FormDefinitionResponse.model_validate(
                form,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{form_id}/archive",
    response_model=ApiResponse[FormDefinitionResponse],
)
async def archive_form(
    form_id: int,
    service: FormDefinitionService = Depends(
        get_form_definition_service,
    ),
    user: User = CurrentUser,
):
    try:
        form = await service.archive(
            form_id=form_id,
            user_id=user.id,
        )

        return ok(
            message="Formulaire archivé avec succès.",
            data=FormDefinitionResponse.model_validate(
                form,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{form_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_form(
    form_id: int,
    service: FormDefinitionService = Depends(
        get_form_definition_service,
    ),
    user: User = CurrentUser,
):
    try:
        await service.delete(
            form_id=form_id,
            user_id=user.id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/{form_id}/files",
    response_model=ApiResponse[FormFilesResponse],
)
async def list_form_files(
    form_id: int,
    service: FormDefinitionService = Depends(
        get_form_definition_service,
    ),
    user: User = CurrentUser,
):
    try:
        # --------------------------------------------------------
        # 1. Récupérer le formulaire
        # --------------------------------------------------------

        form = await service.get(
            form_id=form_id,
            user_id=user.id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        # --------------------------------------------------------
        # 2. Vérifier si les pièces jointes sont activées
        # --------------------------------------------------------

        global_config = form.global_config or {}
        attachments_config = global_config.get("attachments")

        attachments_enabled = (
            isinstance(attachments_config, dict) and attachments_config.get("enabled") is True
        )

        # --------------------------------------------------------
        # 3. Si les pièces jointes ne sont pas activées,
        #    les activer automatiquement
        # --------------------------------------------------------

        if not attachments_enabled:
            form = await service.update(
                form_id=form_id,
                user_id=user.id,
                data=FormDefinitionUpdate(
                    global_config={
                        "attachments": {
                            "enabled": True,
                        },
                    },
                ),
            )

        # --------------------------------------------------------
        # 4. Maintenant que les pièces jointes sont activées,
        #    récupérer les fichiers du formulaire
        # --------------------------------------------------------

        files = await service.list_form_files(
            form_id=form_id,
            user_id=user.id,
        )

        response_items = [FileNodeResponse.model_validate(file) for file in files]

        return ok(
            message="Fichiers du formulaire récupérés avec succès.",
            data=FormFilesResponse(
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
    "/{form_id}/files",
    response_model=ApiResponse[FileNodeResponse],
    status_code=status.HTTP_201_CREATED,
)
async def upload_form_file(
    form_id: int,
    file: UploadFile = File(...),
    service: FormDefinitionService = Depends(
        get_form_definition_service,
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
        form_file = await service.upload_form_file(
            form_id=form_id,
            user_id=user.id,
            name=filename,
            source=file.file,
            mime_type=file.content_type,
            extension=extension,
        )

        return ok(
            message="Fichier ajouté au formulaire avec succès.",
            data=FileNodeResponse.model_validate(
                form_file,
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
    "/{form_id}/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_form_file(
    form_id: int,
    file_id: int,
    service: FormDefinitionService = Depends(
        get_form_definition_service,
    ),
    user: User = CurrentUser,
):
    try:
        await service.delete_form_file(
            form_id=form_id,
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
