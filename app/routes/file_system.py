from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, BinaryIO
from zipfile import BadZipFile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.background import BackgroundTasks
from fastapi.responses import FileResponse

# IMPORTANT :
# Remplace cette dépendance par celle déjà utilisée
# par ton application pour récupérer l'utilisateur connecté.
from app.dependencies import CurrentUser, get_archive_service, get_file_system_service
from app.models.enums import FileNodeType
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.file_system import (
    BatchDeleteRequest,
    BatchMoveRequest,
    CreateFolderRequest,
    FileNodeListResponse,
    FileNodeResponse,
    MoveFileNodeRequest,
    RenameFileNodeRequest,
)
from app.services.archive import ArchiveService
from app.services.file_system import (
    FileAlreadyExistsError,
    FileNotFoundError,
    FileSystemError,
    FileSystemService,
    InvalidFileOperationError,
)

router = APIRouter(
    prefix="/files",
    tags=["File System"],
)


@router.get(
    "/",
    response_model=ApiResponse[FileNodeListResponse],
)
async def list_root(
    service: FileSystemService = Depends(
        get_file_system_service,
    ),
    user: User = CurrentUser,
):
    items = await service.list_children(
        user_id=user.id,
        parent_id=None,
    )

    response_items = [FileNodeResponse.model_validate(item) for item in items]

    data = FileNodeListResponse(
        items=response_items,
        count=len(response_items),
    )

    return ok(
        message="Contenu de la racine récupéré.",
        data=data,
    )


@router.get(
    "/{node_id}/children",
    response_model=ApiResponse[FileNodeListResponse],
)
async def list_children(
    node_id: int,
    service: FileSystemService = Depends(
        get_file_system_service,
    ),
    user: User = CurrentUser,
):
    try:
        items = await service.list_children(
            user_id=user.id,
            parent_id=node_id,
        )

        response_items = [FileNodeResponse.model_validate(item) for item in items]

        data = FileNodeListResponse(
            items=response_items,
            count=len(response_items),
        )

        return ok(
            message="Contenu du dossier récupéré.",
            data=data,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/folders",
    response_model=ApiResponse[FileNodeResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_folder(
    payload: CreateFolderRequest,
    service: FileSystemService = Depends(
        get_file_system_service,
    ),
    user: User = CurrentUser,
):
    try:
        folder = await service.create_folder(
            user_id=user.id,
            name=payload.name,
            parent_id=payload.parent_id,
        )

        return ok(
            message="Dossier créé avec succès.",
            data=FileNodeResponse.model_validate(
                folder,
            ),
        )

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


@router.patch(
    "/{node_id}",
    response_model=ApiResponse[FileNodeResponse],
)
async def rename_node(
    node_id: int,
    payload: RenameFileNodeRequest,
    service: FileSystemService = Depends(
        get_file_system_service,
    ),
    user: User = CurrentUser,
):
    try:
        node = await service.rename(
            user_id=user.id,
            node_id=node_id,
            new_name=payload.name,
        )

        return ok(
            message="Élément renommé avec succès.",
            data=FileNodeResponse.model_validate(node),
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

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


@router.patch(
    "/{node_id}/move",
    response_model=ApiResponse[FileNodeResponse],
)
async def move_node(
    node_id: int,
    payload: MoveFileNodeRequest,
    service: FileSystemService = Depends(
        get_file_system_service,
    ),
    user: User = CurrentUser,
):
    try:
        node = await service.move(
            user_id=user.id,
            node_id=node_id,
            new_parent_id=payload.parent_id,
        )

        return ok(
            message="Élément déplacé avec succès.",
            data=FileNodeResponse.model_validate(node),
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

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


@router.post(
    "/import",
    response_model=ApiResponse[list[FileNodeResponse]],
    status_code=status.HTTP_201_CREATED,
)
async def import_files(
    files: Annotated[
        list[UploadFile],
        File(...),
    ],
    relative_paths: Annotated[
        list[str],
        File(...),
    ],
    parent_id: int | None = None,
    service: FileSystemService = Depends(
        get_file_system_service,
    ),
    user: User = CurrentUser,
):
    try:
        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Aucun fichier à importer.",
            )

        if len(files) != len(relative_paths):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Le nombre de fichiers doit correspondre " "au nombre de chemins relatifs."
                ),
            )

        import_items: list[tuple[str, BinaryIO, str | None]] = []

        for file, relative_path in zip(
            files,
            relative_paths,
            strict=True,
        ):
            if not file.filename:
                raise InvalidFileOperationError("Un fichier importé ne possède aucun nom.")

            if not relative_path.strip():
                raise InvalidFileOperationError("Un chemin relatif ne peut pas être vide.")

            import_items.append(
                (
                    relative_path,
                    file.file,
                    file.content_type,
                )
            )

        nodes = await service.import_files(
            user_id=user.id,
            files=import_items,
            parent_id=parent_id,
        )

        created_storage_keys = [node.storage_key for node in nodes if node.storage_key is not None]

        try:
            await service.session.commit()

        except Exception:
            await service.session.rollback()

            await service.cleanup_storage_keys(
                created_storage_keys,
            )

            raise

        return ok(
            message="Import effectué avec succès.",
            data=[FileNodeResponse.model_validate(node) for node in nodes],
        )

    except FileAlreadyExistsError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except FileNotFoundError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except InvalidFileOperationError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except FileSystemError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{node_id}",
    response_model=ApiResponse[None],
)
async def delete_node(
    node_id: int,
    service: FileSystemService = Depends(
        get_file_system_service,
    ),
    user: User = CurrentUser,
):
    try:
        await service.delete(
            user_id=user.id,
            node_id=node_id,
        )

        await service.session.commit()

        return ok(
            message="Élément supprimé avec succès.",
        )

    except FileNotFoundError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except InvalidFileOperationError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except FileSystemError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/{node_id}/download",
)
async def download_file(
    node_id: int,
    service: FileSystemService = Depends(
        get_file_system_service,
    ),
    user: User = CurrentUser,
):
    try:
        node = await service.get_file_for_download(
            user_id=user.id,
            node_id=node_id,
        )

        if node.storage_key is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Le fichier ne possède aucun emplacement de stockage.",
            )

        path = service.storage.get_path(
            storage_key=node.storage_key,
        )

        return FileResponse(
            path=path,
            media_type=node.mime_type or "application/octet-stream",
            filename=node.name,
        )

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

    except FileSystemError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/{node_id}/export",
)
async def export_node(
    node_id: int,
    background_tasks: BackgroundTasks,
    service: FileSystemService = Depends(
        get_file_system_service,
    ),
    archive_service: ArchiveService = Depends(
        get_archive_service,
    ),
    user: User = CurrentUser,
):

    def _remove_temporary_file(
        path: Path,
    ) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            pass

    try:
        node = await service.get_node(
            user_id=user.id,
            node_id=node_id,
        )

        # ========================================================
        # CAS 1 : FICHIER
        # ========================================================

        if node.type == FileNodeType.FILE:
            if node.storage_key is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=("Le fichier ne possède aucun " "emplacement de stockage."),
                )

            path = service.storage.get_path(
                storage_key=node.storage_key,
            )

            if not path.is_file():
                raise FileSystemError("Le contenu physique du fichier est introuvable.")

            return FileResponse(
                path=path,
                media_type=node.mime_type or "application/octet-stream",
                filename=node.name,
            )

        # ========================================================
        # CAS 2 : DOSSIER
        # ========================================================

        nodes = await service.get_descendants(
            user_id=user.id,
            node_id=node.id,
        )

        zip_path = await archive_service.create_zip(
            root=node,
            nodes=nodes,
        )

        background_tasks.add_task(
            _remove_temporary_file,
            zip_path,
        )

        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=f"{node.name}.zip",
            background=background_tasks,
        )

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

    except FileSystemError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.get(
    "/{node_id}/descendants",
    response_model=ApiResponse[list[FileNodeResponse]],
)
async def list_descendants(
    node_id: int,
    service: FileSystemService = Depends(
        get_file_system_service,
    ),
    user: User = CurrentUser,
):
    try:
        nodes = await service.get_descendants(
            user_id=user.id,
            node_id=node_id,
        )

        return ok(
            message="Descendants récupérés.",
            data=[FileNodeResponse.model_validate(node) for node in nodes],
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/import-zip",
    response_model=ApiResponse[list[FileNodeResponse]],
    status_code=status.HTTP_201_CREATED,
)
async def import_zip(
    file: UploadFile = File(...),
    parent_id: int | None = None,
    service: FileSystemService = Depends(
        get_file_system_service,
    ),
    archive_service: ArchiveService = Depends(
        get_archive_service,
    ),
    user: User = CurrentUser,
):
    temporary_path: Path | None = None

    try:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'archive doit posséder un nom.",
            )

        if not file.filename.lower().endswith(
            ".zip",
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les fichiers ZIP sont acceptés.",
            )

        with NamedTemporaryFile(
            prefix="swt-upload-",
            suffix=".zip",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(
                temporary_file.name,
            )

            while True:
                chunk = await file.read(
                    1024 * 1024,
                )

                if not chunk:
                    break

                temporary_file.write(
                    chunk,
                )

        nodes = await service.import_zip(
            user_id=user.id,
            archive_service=archive_service,
            zip_path=temporary_path,
            parent_id=parent_id,
        )

        created_storage_keys = [node.storage_key for node in nodes if node.storage_key is not None]

        try:
            await service.session.commit()

        except Exception:
            await service.session.rollback()

            await service.cleanup_storage_keys(
                created_storage_keys,
            )

            raise

        return ok(
            message="Archive importée avec succès.",
            data=[
                FileNodeResponse.model_validate(
                    node,
                )
                for node in nodes
            ],
        )

    except BadZipFile as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'archive ZIP est invalide ou corrompue.",
        ) from exc

    except ValueError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except FileAlreadyExistsError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except FileNotFoundError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except InvalidFileOperationError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except FileSystemError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    finally:
        if temporary_path is not None:
            temporary_path.unlink(
                missing_ok=True,
            )


@router.post(
    "/batch-delete",
    response_model=ApiResponse[None],
)
async def batch_delete(
    payload: BatchDeleteRequest,
    service: FileSystemService = Depends(
        get_file_system_service,
    ),
    user: User = CurrentUser,
):
    try:
        await service.delete_many(
            user_id=user.id,
            node_ids=payload.node_ids,
        )

        await service.session.commit()

        return ok(
            message="Éléments supprimés avec succès.",
        )

    except FileNotFoundError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except InvalidFileOperationError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except FileSystemError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/batch-move",
    response_model=ApiResponse[None],
)
async def batch_move(
    payload: BatchMoveRequest,
    service: FileSystemService = Depends(
        get_file_system_service,
    ),
    user: User = CurrentUser,
):
    try:
        await service.move_many(
            user_id=user.id,
            node_ids=payload.node_ids,
            new_parent_id=payload.parent_id,
        )

        await service.session.commit()

        return ok(
            message="Éléments déplacés avec succès.",
        )

    except FileAlreadyExistsError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except FileNotFoundError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except InvalidFileOperationError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except FileSystemError as exc:
        await service.session.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
