from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from app.models.enums import FileNodeType
from app.models.file_node import FileNode
from app.services.storage.base import StorageService


class ArchiveService:
    """
    Service responsable de la création des archives ZIP.
    """

    def __init__(
        self,
        storage: StorageService,
    ) -> None:
        self.storage = storage

    async def create_zip(
        self,
        *,
        root: FileNode,
        nodes: list[FileNode],
    ) -> Path:
        """
        Crée une archive ZIP temporaire contenant root
        et toute son arborescence.

        Le dossier racine est toujours conservé dans le ZIP.
        """

        if root.type != FileNodeType.FOLDER:
            raise ValueError("create_zip() attend un dossier racine.")

        # --------------------------------------------------------
        # Construire l'arborescence logique
        # --------------------------------------------------------

        children_by_parent: dict[
            int,
            list[FileNode],
        ] = {}

        for node in nodes:
            if node.parent_id is None:
                continue

            children_by_parent.setdefault(
                node.parent_id,
                [],
            ).append(node)

        # --------------------------------------------------------
        # Créer un fichier ZIP temporaire
        # --------------------------------------------------------

        temporary_file = NamedTemporaryFile(
            prefix="swt-export-",
            suffix=".zip",
            delete=False,
        )

        zip_path = Path(temporary_file.name)

        temporary_file.close()

        try:
            with ZipFile(
                zip_path,
                mode="w",
                compression=ZIP_DEFLATED,
            ) as archive:

                # Le dossier racine doit toujours exister
                # dans le ZIP, même lorsqu'il est vide.
                root_path = f"{root.name}/"

                archive.writestr(
                    root_path,
                    b"",
                )

                async def add_node(
                    node: FileNode,
                    relative_path: str,
                ) -> None:
                    if node.type == FileNodeType.FOLDER:
                        directory_path = f"{relative_path}/"

                        # Cela conserve également les dossiers vides.
                        archive.writestr(
                            directory_path,
                            b"",
                        )

                        children = children_by_parent.get(
                            node.id,
                            [],
                        )

                        children.sort(
                            key=lambda child: (
                                child.type.value,
                                child.name.lower(),
                            )
                        )

                        for child in children:
                            child_path = f"{relative_path}/" f"{child.name}"

                            await add_node(
                                child,
                                child_path,
                            )

                        return

                    if not node.storage_key:
                        raise ValueError(
                            f"Le fichier '{node.name}' " "ne possède aucune storage_key."
                        )

                    file_path = self.storage.get_path(
                        storage_key=node.storage_key,
                    )

                    if not file_path.is_file():
                        raise FileNotFoundError(
                            "Le contenu physique est introuvable " f"pour '{node.name}'."
                        )

                    archive.write(
                        file_path,
                        arcname=relative_path,
                    )

                children = children_by_parent.get(
                    root.id,
                    [],
                )

                children.sort(
                    key=lambda child: (
                        child.type.value,
                        child.name.lower(),
                    )
                )

                for child in children:
                    child_path = f"{root.name}/" f"{child.name}"

                    await add_node(
                        child,
                        child_path,
                    )

            return zip_path

        except Exception:
            if zip_path.exists():
                zip_path.unlink()

            raise

    @staticmethod
    def _validate_zip_member_path(
        member_name: str,
    ) -> Path:
        """
        Valide le chemin d'un élément contenu dans une archive ZIP.

        Interdit :
        - les chemins absolus ;
        - les remontées avec .. ;
        - les chemins Windows absolus ;
        - les entrées invalides.
        """

        normalized = member_name.replace(
            "\\",
            "/",
        )

        path = Path(normalized)

        if path.is_absolute():
            raise ValueError("Le ZIP contient un chemin absolu interdit.")

        parts = path.parts

        if not parts:
            raise ValueError("Le ZIP contient un chemin vide.")

        for part in parts:
            if part in ("", "."):
                continue

            if part == "..":
                raise ValueError("Le ZIP contient un chemin dangereux.")

        return Path(
            *[part for part in parts if part not in ("", ".")],
        )

    def extract_zip(
        self,
        *,
        zip_path: Path,
    ) -> Path:
        """
        Extrait un ZIP dans un répertoire temporaire sécurisé.

        Le répertoire temporaire est retourné au caller,
        qui devra assurer son nettoyage.
        """

        temporary_directory = Path(
            TemporaryDirectory(
                prefix="swt-import-",
            ).name,
        )

        temporary_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            with ZipFile(
                zip_path,
                mode="r",
            ) as archive:
                for info in archive.infolist():
                    relative_path = self._validate_zip_member_path(
                        info.filename,
                    )

                    destination = temporary_directory / relative_path

                    destination_resolved = destination.resolve()

                    root_resolved = temporary_directory.resolve()

                    if (
                        destination_resolved != root_resolved
                        and root_resolved not in destination_resolved.parents
                    ):
                        raise ValueError(
                            "Le ZIP contient un chemin " "qui sort du répertoire d'extraction."
                        )

                    if info.is_dir():
                        destination.mkdir(
                            parents=True,
                            exist_ok=True,
                        )
                    else:
                        destination.parent.mkdir(
                            parents=True,
                            exist_ok=True,
                        )

                        with archive.open(
                            info,
                            "r",
                        ) as source:
                            with destination.open(
                                "wb",
                            ) as target:
                                shutil.copyfileobj(
                                    source,
                                    target,
                                )

            return temporary_directory

        except (BadZipFile, OSError, ValueError):
            shutil.rmtree(
                temporary_directory,
                ignore_errors=True,
            )
            raise
