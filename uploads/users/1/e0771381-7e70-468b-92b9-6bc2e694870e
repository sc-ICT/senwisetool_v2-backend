from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import BinaryIO

from app.services.storage.base import StorageService


class LocalStorageService(StorageService):
    """
    Stockage local sur le serveur.

    Structure physique :

        UPLOAD_DIR/
            users/
                {user_id}/
                    {storage_key}

    Le nom visible du fichier n'est jamais utilisé comme
    nom physique.
    """

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir).expanduser().resolve()

    def _user_directory(self, user_id: int) -> Path:
        return self.base_dir / "users" / str(user_id)

    def _resolve_key(self, storage_key: str) -> Path:
        """
        Transforme une storage_key en chemin physique.

        Une validation stricte est effectuée afin d'empêcher
        toute tentative de path traversal.
        """

        if not storage_key:
            raise ValueError("storage_key ne peut pas être vide.")

        key_path = Path(storage_key)

        if key_path.is_absolute():
            raise ValueError("storage_key ne peut pas être un chemin absolu.")

        if ".." in key_path.parts:
            raise ValueError("storage_key invalide.")

        resolved = (self.base_dir / key_path).resolve()

        try:
            resolved.relative_to(self.base_dir)
        except ValueError as exc:
            raise ValueError("storage_key en dehors du stockage.") from exc

        return resolved

    async def save(
        self,
        *,
        user_id: int,
        source: BinaryIO,
        storage_key: str,
    ) -> int:
        """
        Enregistre un flux binaire sur le disque.

        Retourne la taille du fichier en octets.
        """

        destination = self._resolve_key(storage_key)

        expected_directory = self._user_directory(user_id).resolve()

        try:
            destination.relative_to(expected_directory)
        except ValueError as exc:
            raise ValueError("storage_key doit appartenir au répertoire de l'utilisateur.") from exc

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        def write_file() -> int:
            size = 0

            with destination.open("wb") as output:
                while True:
                    chunk = source.read(1024 * 1024)

                    if not chunk:
                        break

                    output.write(chunk)
                    size += len(chunk)

            return size

        return await asyncio.to_thread(write_file)

    async def delete(
        self,
        *,
        storage_key: str,
    ) -> None:
        path = self._resolve_key(storage_key)

        def remove_file() -> None:
            if path.exists():
                if not path.is_file():
                    raise ValueError("L'objet de stockage n'est pas un fichier.")

                path.unlink()

        await asyncio.to_thread(remove_file)

    async def exists(
        self,
        *,
        storage_key: str,
    ) -> bool:
        path = self._resolve_key(storage_key)

        return await asyncio.to_thread(
            path.is_file,
        )

    async def open(
        self,
        *,
        storage_key: str,
    ) -> BinaryIO:
        path = self._resolve_key(storage_key)

        if not await asyncio.to_thread(path.is_file):
            raise FileNotFoundError(f"Fichier introuvable dans le stockage : {storage_key}")

        return await asyncio.to_thread(
            path.open,
            "rb",
        )

    def get_path(
        self,
        *,
        storage_key: str,
    ) -> Path:
        return self._resolve_key(storage_key)
