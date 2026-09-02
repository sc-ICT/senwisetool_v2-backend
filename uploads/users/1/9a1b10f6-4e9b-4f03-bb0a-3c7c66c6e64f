from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO


class StorageService(ABC):
    """
    Contrat commun pour tous les systèmes de stockage.

    L'application ne doit pas savoir si les fichiers sont stockés :
    - sur le disque local ;
    - sur S3 ;
    - sur Cloudflare R2 ;
    - sur MinIO ;
    - etc.

    Elle utilise uniquement ce contrat.
    """

    @abstractmethod
    async def save(
        self,
        *,
        user_id: int,
        source: BinaryIO,
        storage_key: str,
    ) -> int:
        """
        Sauvegarde le contenu et retourne sa taille en octets.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        *,
        storage_key: str,
    ) -> None:
        """
        Supprime un objet du stockage.
        """
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        *,
        storage_key: str,
    ) -> bool:
        """
        Vérifie si un objet existe.
        """
        raise NotImplementedError

    @abstractmethod
    async def open(
        self,
        *,
        storage_key: str,
    ) -> BinaryIO:
        """
        Ouvre un objet pour lecture binaire.
        """
        raise NotImplementedError

    @abstractmethod
    def get_path(
        self,
        *,
        storage_key: str,
    ) -> Path:
        """
        Retourne le chemin physique local.

        Cette méthode sera utile pour le stockage local.
        Une implémentation S3 pourra lever une exception,
        car S3 ne possède pas de chemin local.
        """
        raise NotImplementedError
