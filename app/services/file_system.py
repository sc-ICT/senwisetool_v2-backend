from __future__ import annotations

import shutil
from io import BytesIO
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FileNodeType
from app.models.file_node import FileNode
from app.models.project_agent_assignment import (
    ProjectAgentAssignmentZone,
)
from app.services.archive import ArchiveService
from app.services.storage.base import StorageService


class FileSystemError(Exception):
    """Erreur métier générique du système de fichiers."""


class FileNotFoundError(FileSystemError):
    """Le fichier ou dossier demandé n'existe pas."""


class FileAlreadyExistsError(FileSystemError):
    """Un élément portant déjà ce nom existe."""


class InvalidFileOperationError(FileSystemError):
    """L'opération demandée n'est pas autorisée."""


class FileSystemService:
    """
    Service métier du système de fichiers.

    Cette classe coordonne :

        PostgreSQL
            +
        StorageService

    Elle ne connaît pas l'implémentation concrète du stockage.
    """

    def __init__(
        self,
        session: AsyncSession,
        storage: StorageService,
    ) -> None:
        self.session = session
        self.storage = storage

    # ============================================================
    # Helpers internes
    # ============================================================

    async def _get_node(
        self,
        *,
        user_id: int,
        node_id: int,
    ) -> FileNode:
        """
        Récupère un node appartenant obligatoirement à l'utilisateur.
        """

        result = await self.session.execute(
            select(FileNode).where(
                FileNode.id == node_id,
                FileNode.user_id == user_id,
            )
        )

        node = result.scalar_one_or_none()

        if node is None:
            raise FileNotFoundError("Fichier ou dossier introuvable.")

        return node

    async def _ensure_parent(
        self,
        *,
        user_id: int,
        parent_id: int | None,
    ) -> FileNode | None:
        """
        Vérifie que le dossier parent existe et appartient
        à l'utilisateur.
        """

        if parent_id is None:
            return None

        parent = await self._get_node(
            user_id=user_id,
            node_id=parent_id,
        )

        if parent.type != FileNodeType.FOLDER:
            raise InvalidFileOperationError("Le parent doit être un dossier.")

        return parent

    async def _ensure_name_available(
        self,
        *,
        user_id: int,
        parent_id: int | None,
        name: str,
        exclude_node_id: int | None = None,
    ) -> None:
        """
        Vérifie qu'un nom n'est pas déjà utilisé dans le même dossier.
        """

        normalized_name = name.strip().lower()

        query = select(FileNode).where(
            FileNode.user_id == user_id,
            func.lower(FileNode.name) == normalized_name,
        )

        if parent_id is None:
            query = query.where(FileNode.parent_id.is_(None))
        else:
            query = query.where(FileNode.parent_id == parent_id)

        if exclude_node_id is not None:
            query = query.where(FileNode.id != exclude_node_id)

        result = await self.session.execute(query)

        existing = result.scalar_one_or_none()

        if existing is not None:
            raise FileAlreadyExistsError(f"Un élément nommé '{name}' existe déjà dans ce dossier.")

    async def _get_or_create_folder(
        self,
        *,
        user_id: int,
        name: str,
        parent_id: int | None,
    ) -> FileNode:
        """
        Retourne un dossier existant ou le crée.

        Utilisé lors de l'import d'une arborescence.
        """

        existing_query = select(FileNode).where(
            FileNode.user_id == user_id,
            FileNode.parent_id == parent_id,
            func.lower(FileNode.name) == name.strip().lower(),
            FileNode.type == FileNodeType.FOLDER,
        )

        result = await self.session.execute(existing_query)

        existing = result.scalar_one_or_none()

        if existing is not None:
            return existing

        return await self.create_folder(
            user_id=user_id,
            name=name,
            parent_id=parent_id,
        )

    @staticmethod
    def _normalize_relative_path(
        relative_path: str,
    ) -> list[str]:
        """
        Nettoie et valide un chemin relatif provenant d'un import.

        Exemple :
            MonFormulaire/Documents/contrat.pdf

        devient :
            ["MonFormulaire", "Documents", "contrat.pdf"]
        """

        if not relative_path:
            raise InvalidFileOperationError("Le chemin relatif ne peut pas être vide.")

        normalized = relative_path.replace("\\", "/")

        path = Path(normalized)

        if path.is_absolute():
            raise InvalidFileOperationError("Un chemin absolu n'est pas autorisé.")

        parts: list[str] = []

        for part in path.parts:
            if part in ("", "."):
                continue

            if part == "..":
                raise InvalidFileOperationError("Le chemin contient une tentative de remontée.")

            if len(part) > 255:
                raise InvalidFileOperationError("Un élément du chemin dépasse 255 caractères.")

            parts.append(part)

        if not parts:
            raise InvalidFileOperationError("Le chemin relatif est invalide.")

        return parts

    @staticmethod
    def _validate_name(name: str) -> str:
        """
        Nettoie et valide un nom de fichier/dossier.
        """

        name = name.strip()

        if not name:
            raise InvalidFileOperationError("Le nom ne peut pas être vide.")

        if len(name) > 255:
            raise InvalidFileOperationError("Le nom ne peut pas dépasser 255 caractères.")

        if "/" in name or "\\" in name:
            raise InvalidFileOperationError("Le nom ne peut pas contenir de séparateur de chemin.")

        return name

    async def _is_descendant(
        self,
        *,
        node: FileNode,
        potential_parent_id: int,
    ) -> bool:
        """
        Vérifie qu'un dossier ne soit pas déplacé dans lui-même
        ou dans l'un de ses descendants.
        """

        current_id: int | None = potential_parent_id

        while current_id is not None:
            if current_id == node.id:
                return True

            result = await self.session.execute(
                select(FileNode.parent_id).where(
                    FileNode.id == current_id,
                    FileNode.user_id == node.user_id,
                )
            )

            parent_id = result.scalar_one_or_none()

            if parent_id is None:
                return False

            current_id = parent_id

        return False

    def _generate_storage_key(
        self,
        *,
        user_id: int,
    ) -> str:
        """
        Génère une identité physique indépendante du nom du fichier.
        """

        return f"users/{user_id}/" f"{uuid4()}"

    async def _get_descendants(
        self,
        *,
        user_id: int,
        node_id: int,
    ) -> list[FileNode]:
        """
        Retourne le nœud demandé ainsi que tous ses descendants.
        """

        root = await self._get_node(
            user_id=user_id,
            node_id=node_id,
        )

        result: list[FileNode] = [root]

        async def collect_children(
            parent_id: int,
        ) -> None:
            children = await self.list_children(
                user_id=user_id,
                parent_id=parent_id,
            )

            for child in children:
                result.append(child)

                if child.type == FileNodeType.FOLDER:
                    await collect_children(child.id)

        if root.type == FileNodeType.FOLDER:
            await collect_children(root.id)

        return result

    async def cleanup_storage_keys(
        self,
        storage_keys: list[str],
    ) -> None:
        """
        Supprime les objets physiques créés pendant une opération
        qui a ensuite échoué.
        """

        for storage_key in storage_keys:
            try:
                await self.storage.delete(
                    storage_key=storage_key,
                )
            except Exception:
                # On ne masque pas l'erreur originale de l'opération.
                # Le nettoyage est une tentative compensatoire.
                continue

    # ============================================================
    # Navigation
    # ============================================================

    async def list_children(
        self,
        *,
        user_id: int,
        parent_id: int | None = None,
    ) -> list[FileNode]:
        """
        Retourne le contenu d'un dossier.

        parent_id = None signifie la racine.
        """

        if parent_id is not None:
            await self._ensure_parent(
                user_id=user_id,
                parent_id=parent_id,
            )

        result = await self.session.execute(
            select(FileNode)
            .where(
                FileNode.user_id == user_id,
                (
                    FileNode.parent_id.is_(None)
                    if parent_id is None
                    else FileNode.parent_id == parent_id
                ),
            )
            .order_by(
                FileNode.type.asc(),
                func.lower(FileNode.name).asc(),
            )
        )

        return list(result.scalars().all())

    async def get_node(
        self,
        *,
        user_id: int,
        node_id: int,
    ) -> FileNode:
        return await self._get_node(
            user_id=user_id,
            node_id=node_id,
        )

    async def get_descendants(
        self,
        *,
        user_id: int,
        node_id: int,
    ) -> list[FileNode]:
        """
        Retourne le node demandé et tous ses descendants.
        """

        return await self._get_descendants(
            user_id=user_id,
            node_id=node_id,
        )

    # ============================================================
    # Création d'un dossier
    # ============================================================

    async def create_folder(
        self,
        *,
        user_id: int,
        name: str,
        parent_id: int | None = None,
    ) -> FileNode:
        name = self._validate_name(name)

        await self._ensure_parent(
            user_id=user_id,
            parent_id=parent_id,
        )

        await self._ensure_name_available(
            user_id=user_id,
            parent_id=parent_id,
            name=name,
        )

        folder = FileNode(
            user_id=user_id,
            parent_id=parent_id,
            name=name,
            type=FileNodeType.FOLDER,
        )

        self.session.add(folder)

        await self.session.flush()

        await self.session.refresh(folder)

        return folder

    # ============================================================
    # Création d'un fichier
    # ============================================================

    async def create_file(
        self,
        *,
        user_id: int,
        name: str,
        source: BinaryIO,
        parent_id: int | None = None,
        mime_type: str | None = None,
        extension: str | None = None,
    ) -> FileNode:
        name = self._validate_name(name)

        await self._ensure_parent(
            user_id=user_id,
            parent_id=parent_id,
        )

        await self._ensure_name_available(
            user_id=user_id,
            parent_id=parent_id,
            name=name,
        )

        storage_key = self._generate_storage_key(
            user_id=user_id,
        )

        try:
            size = await self.storage.save(
                user_id=user_id,
                source=source,
                storage_key=storage_key,
            )
        except Exception:
            # Si le stockage échoue, aucune métadonnée ne doit
            # rester en base.
            await self.session.rollback()
            raise

        file_node = FileNode(
            user_id=user_id,
            parent_id=parent_id,
            name=name,
            type=FileNodeType.FILE,
            storage_key=storage_key,
            mime_type=mime_type,
            extension=extension,
            size=size,
        )

        try:
            self.session.add(file_node)
            await self.session.flush()
            await self.session.refresh(file_node)

        except Exception:
            await self.storage.delete(
                storage_key=storage_key,
            )

            await self.session.rollback()
            raise

        return file_node

    # ============================================================
    # Renommage
    # ============================================================

    async def rename(
        self,
        *,
        user_id: int,
        node_id: int,
        new_name: str,
    ) -> FileNode:
        node = await self._get_node(
            user_id=user_id,
            node_id=node_id,
        )

        new_name = self._validate_name(new_name)

        await self._ensure_name_available(
            user_id=user_id,
            parent_id=node.parent_id,
            name=new_name,
            exclude_node_id=node.id,
        )

        node.name = new_name

        await self.session.flush()

        await self.session.refresh(node)

        return node

    # ============================================================
    # Déplacement
    # ============================================================

    async def move(
        self,
        *,
        user_id: int,
        node_id: int,
        new_parent_id: int | None,
    ) -> FileNode:
        node = await self._get_node(
            user_id=user_id,
            node_id=node_id,
        )

        if new_parent_id == node.id:
            raise InvalidFileOperationError("Un élément ne peut pas être déplacé dans lui-même.")

        await self._ensure_parent(
            user_id=user_id,
            parent_id=new_parent_id,
        )

        if node.type == FileNodeType.FOLDER:
            if new_parent_id is not None:
                if await self._is_descendant(
                    node=node,
                    potential_parent_id=new_parent_id,
                ):
                    raise InvalidFileOperationError(
                        "Un dossier ne peut pas être déplacé " "dans l'un de ses descendants."
                    )

        await self._ensure_name_available(
            user_id=user_id,
            parent_id=new_parent_id,
            name=node.name,
            exclude_node_id=node.id,
        )

        node.parent_id = new_parent_id

        await self.session.flush()

        await self.session.refresh(node)

        return node

    # ============================================================
    # Suppression
    # ============================================================

    async def delete(
        self,
        *,
        user_id: int,
        node_id: int,
    ) -> None:
        """
        Supprime un fichier ou un dossier ainsi que tout son contenu.

        Les fichiers physiques sont supprimés du storage avant
        la suppression des métadonnées en base.
        """

        nodes = await self._get_descendants(
            user_id=user_id,
            node_id=node_id,
        )

        node_ids = [node.id for node in nodes]

        result = await self.session.execute(
            select(ProjectAgentAssignmentZone.file_node_id)
            .where(
                ProjectAgentAssignmentZone.file_node_id.in_(node_ids),
            )
            .limit(1)
        )

        used_zone_file_id = result.scalar_one_or_none()

        if used_zone_file_id is not None:
            raise InvalidFileOperationError(
                "Ce fichier ou dossier contient une zone KML ou GEOJSON"
                "encore utilisée par une affectation.",
            )

        node_ids = [node.id for node in nodes]

        result = await self.session.execute(
            select(ProjectAgentAssignmentZone.file_node_id)
            .where(ProjectAgentAssignmentZone.file_node_id.in_(node_ids))
            .limit(1)
        )

        used_zone_file_id = result.scalar_one_or_none()

        if used_zone_file_id is not None:
            raise InvalidFileOperationError(
                "Ce fichier ou dossier contient une zone KML ou GEOJSON"
                "encore utilisée par une affectation."
            )

        # --------------------------------------------------------
        # 1. Supprimer les fichiers physiques
        # --------------------------------------------------------

        for node in nodes:
            if node.type != FileNodeType.FILE:
                continue

            if not node.storage_key:
                continue

            exists = await self.storage.exists(
                storage_key=node.storage_key,
            )

            if exists:
                await self.storage.delete(
                    storage_key=node.storage_key,
                )

        # --------------------------------------------------------
        # 2. Supprimer les métadonnées
        # --------------------------------------------------------

        for node in reversed(nodes):
            await self.session.delete(node)

        await self.session.flush()

    # ============================================================
    # Téléchargement
    # ============================================================

    async def get_file_for_download(
        self,
        *,
        user_id: int,
        node_id: int,
    ) -> FileNode:
        """
        Récupère un fichier appartenant à l'utilisateur
        et vérifie qu'il possède bien un contenu physique.
        """

        node = await self._get_node(
            user_id=user_id,
            node_id=node_id,
        )

        if node.type != FileNodeType.FILE:
            raise InvalidFileOperationError("Seuls les fichiers peuvent être téléchargés.")

        if not node.storage_key:
            raise InvalidFileOperationError("Ce fichier ne possède aucun contenu physique.")

        exists = await self.storage.exists(
            storage_key=node.storage_key,
        )

        if not exists:
            raise FileSystemError("Le contenu physique de ce fichier est introuvable.")

        return node

    async def import_file(
        self,
        *,
        user_id: int,
        source: BinaryIO,
        name: str,
        parent_id: int | None = None,
        mime_type: str | None = None,
        extension: str | None = None,
    ) -> FileNode:
        """
        Importe un fichier dans un dossier existant.
        """

        return await self.create_file(
            user_id=user_id,
            name=name,
            source=source,
            parent_id=parent_id,
            mime_type=mime_type,
            extension=extension,
        )

    async def import_files(
        self,
        *,
        user_id: int,
        files: list[tuple[str, BinaryIO, str | None]],
        parent_id: int | None = None,
    ) -> list[FileNode]:
        """
        Importe plusieurs fichiers en respectant leurs chemins relatifs.

        En cas d'échec pendant l'opération, les fichiers physiques
        déjà écrits sont supprimés.
        """

        imported_nodes: list[FileNode] = []

        # Tous les storage_key créés pendant cette opération.
        created_storage_keys: list[str] = []

        # Cache des dossiers déjà résolus.
        folder_cache: dict[
            tuple[int | None, str],
            FileNode,
        ] = {}

        try:
            for relative_path, source, mime_type in files:
                parts = self._normalize_relative_path(
                    relative_path,
                )

                if len(parts) == 1:
                    filename = parts[0]
                    target_parent_id = parent_id

                else:
                    filename = parts[-1]
                    folder_parts = parts[:-1]

                    current_parent_id = parent_id

                    for folder_name in folder_parts:
                        cache_key = (
                            current_parent_id,
                            folder_name.lower(),
                        )

                        folder = folder_cache.get(cache_key)

                        if folder is None:
                            folder = await self._get_or_create_folder(
                                user_id=user_id,
                                name=folder_name,
                                parent_id=current_parent_id,
                            )

                            folder_cache[cache_key] = folder

                        current_parent_id = folder.id

                    target_parent_id = current_parent_id

                extension = None

                if "." in filename:
                    extension = filename.rsplit(
                        ".",
                        1,
                    )[1].lower()

                node = await self.create_file(
                    user_id=user_id,
                    name=filename,
                    source=source,
                    parent_id=target_parent_id,
                    mime_type=mime_type,
                    extension=extension,
                )

                if node.storage_key:
                    created_storage_keys.append(
                        node.storage_key,
                    )

                imported_nodes.append(node)

            return imported_nodes

        except Exception:
            await self.cleanup_storage_keys(
                created_storage_keys,
            )

            raise

    async def import_zip(
        self,
        *,
        user_id: int,
        archive_service: ArchiveService,
        zip_path: Path,
        parent_id: int | None = None,
    ) -> list[FileNode]:
        """
        Importe une archive ZIP dans le File System.

        Les dossiers, sous-dossiers, fichiers et dossiers
        vides sont reconstruits.
        """

        extracted_root = archive_service.extract_zip(
            zip_path=zip_path,
        )

        created_storage_keys: list[str] = []

        try:
            imported_nodes: list[FileNode] = []

            # --------------------------------------------------------
            # Construire la liste des répertoires et fichiers
            # --------------------------------------------------------

            paths = sorted(
                extracted_root.rglob("*"),
                key=lambda path: (
                    len(path.relative_to(extracted_root).parts),
                    str(path),
                ),
            )

            folder_cache: dict[
                tuple[int | None, str],
                FileNode,
            ] = {}

            for path in paths:
                relative_path = path.relative_to(
                    extracted_root,
                )

                parts = relative_path.parts

                if not parts:
                    continue

                current_parent_id = parent_id

                # ----------------------------------------------------
                # Créer/récupérer tous les dossiers du chemin
                # ----------------------------------------------------

                if path.is_dir():
                    folder_parts = parts

                    for folder_name in folder_parts:
                        cache_key = (
                            current_parent_id,
                            folder_name.lower(),
                        )

                        folder = folder_cache.get(
                            cache_key,
                        )

                        if folder is None:
                            folder = await self._get_or_create_folder(
                                user_id=user_id,
                                name=folder_name,
                                parent_id=current_parent_id,
                            )

                            folder_cache[cache_key] = folder

                        current_parent_id = folder.id

                    continue

                # ----------------------------------------------------
                # Fichier
                # ----------------------------------------------------

                filename = parts[-1]

                folder_parts = parts[:-1]

                current_parent_id = parent_id

                for folder_name in folder_parts:
                    cache_key = (
                        current_parent_id,
                        folder_name.lower(),
                    )

                    folder = folder_cache.get(
                        cache_key,
                    )

                    if folder is None:
                        folder = await self._get_or_create_folder(
                            user_id=user_id,
                            name=folder_name,
                            parent_id=current_parent_id,
                        )

                        folder_cache[cache_key] = folder

                    current_parent_id = folder.id

                extension = None

                if "." in filename:
                    extension = filename.rsplit(
                        ".",
                        1,
                    )[1].lower()

                with path.open(
                    "rb",
                ) as source:
                    node = await self.create_file(
                        user_id=user_id,
                        name=filename,
                        source=source,
                        parent_id=current_parent_id,
                        mime_type=None,
                        extension=extension,
                    )

                if node.storage_key:
                    created_storage_keys.append(
                        node.storage_key,
                    )

                imported_nodes.append(node)

            return imported_nodes

        except Exception:
            await self.cleanup_storage_keys(
                created_storage_keys,
            )

            raise

        finally:
            shutil.rmtree(
                extracted_root,
                ignore_errors=True,
            )

    # ==================================================

    async def delete_many(
        self,
        *,
        user_id: int,
        node_ids: list[int],
    ) -> None:
        """
        Supprime plusieurs éléments dans une seule opération
        logique.

        On réutilise la suppression existante afin de conserver
        toutes les règles déjà implémentées :
        - vérification du propriétaire ;
        - suppression récursive des dossiers ;
        - suppression du stockage physique.
        """

        if not node_ids:
            raise InvalidFileOperationError("Aucun élément à supprimer.")

        # Évite de traiter deux fois le même node.
        unique_node_ids = list(dict.fromkeys(node_ids))

        for node_id in unique_node_ids:
            await self.delete(
                user_id=user_id,
                node_id=node_id,
            )

    async def move_many(
        self,
        *,
        user_id: int,
        node_ids: list[int],
        new_parent_id: int | None,
    ) -> None:
        if not node_ids:
            raise InvalidFileOperationError("Aucun élément à déplacer.")

        unique_node_ids = list(dict.fromkeys(node_ids))

        # Vérifie la destination une seule fois.
        await self._ensure_parent(
            user_id=user_id,
            parent_id=new_parent_id,
        )

        for node_id in unique_node_ids:
            await self.move(
                user_id=user_id,
                node_id=node_id,
                new_parent_id=new_parent_id,
            )
