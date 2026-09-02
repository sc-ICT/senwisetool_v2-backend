from __future__ import annotations

from copy import deepcopy
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FileNodeType
from app.models.form_builder.enums import FormStatus
from app.models.form_builder.form_definition import (
    FormDefinition,
)
from app.models.form_builder.project import Project
from app.schemas.form_builder.form_definition import (
    FormDefinitionCreate,
    FormDefinitionUpdate,
)
from app.services.file_system import FileNotFoundError as FileSystemNotFoundError
from app.services.file_system import (
    FileSystemService,
)
from app.services.form_builder.form_code import generate_form_code
from app.services.form_builder.form_defaults import (
    DEFAULT_FORM_GLOBAL_CONFIG,
    merge_form_global_config,
)


class FormDefinitionService:
    def __init__(
        self,
        session: AsyncSession,
        file_system: FileSystemService,
    ) -> None:
        self.session = session
        self.file_system = file_system

    async def create(
        self,
        *,
        user_id: int,
        data: FormDefinitionCreate,
    ) -> FormDefinition:
        return await self._create_for_project(
            user_id=user_id,
            project_id=data.project_id,
            name=data.name,
            description=data.description,
            form_type=data.form_type,
        )

    async def create_for_project(
        self,
        *,
        user_id: int,
        project_id: int,
        name: str,
        description: str | None,
        form_type: str,
    ) -> FormDefinition:
        return await self._create_for_project(
            user_id=user_id,
            project_id=project_id,
            name=name,
            description=description,
            form_type=form_type,
        )

    async def _create_for_project(
        self,
        *,
        user_id: int,
        project_id: int,
        name: str,
        description: str | None,
        form_type: str,
    ) -> FormDefinition:
        name = name.strip()
        form_type = form_type.strip()

        if not name:
            raise ValueError("Le nom du formulaire est obligatoire.")

        if not form_type:
            raise ValueError("Le type du formulaire est obligatoire.")

        # --------------------------------------------------------
        # Vérifier le projet
        # --------------------------------------------------------

        project_result = await self.session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.created_by == user_id,
            )
        )

        project = project_result.scalar_one_or_none()

        if project is None:
            raise ValueError("Le projet spécifié est introuvable.")

        # --------------------------------------------------------
        # Vérifier le dossier du projet
        # --------------------------------------------------------

        if project.project_folder_id is None:
            raise ValueError("Le dossier du projet est introuvable.")

        try:
            project_folder = await self.file_system.get_node(
                user_id=user_id,
                node_id=project.project_folder_id,
            )
        except FileSystemNotFoundError as exc:
            raise ValueError("Le dossier du projet est introuvable.") from exc

        if project_folder.type != FileNodeType.FOLDER:
            raise ValueError("Le dossier du projet est invalide.")

        # --------------------------------------------------------
        # Générer le code
        # --------------------------------------------------------

        code = generate_form_code(user_id)

        # --------------------------------------------------------
        # Créer le formulaire
        # --------------------------------------------------------

        form = FormDefinition(
            code=code,
            name=name,
            description=(description.strip() if description and description.strip() else None),
            form_type=form_type,
            status=FormStatus.DRAFT,
            global_config=deepcopy(
                DEFAULT_FORM_GLOBAL_CONFIG,
            ),
            created_by=user_id,
            project_id=project_id,
        )

        self.session.add(form)

        await self.session.flush()

        # --------------------------------------------------------
        # Créer le dossier du formulaire sous le projet
        # --------------------------------------------------------

        await self.ensure_form_folder(
            form=form,
            user_id=user_id,
            project_folder_id=project_folder.id,
        )

        return form

    async def ensure_form_folder(
        self,
        *,
        form: FormDefinition,
        user_id: int,
        project_folder_id: int,
    ):
        """
        Retourne le dossier associé au formulaire.

        Si form_folder_id existe et que le dossier existe encore,
        il est réutilisé.

        Si la référence existe mais que le dossier a été supprimé,
        un nouveau dossier est créé sous le dossier du projet.
        """

        if form.form_folder_id is not None:
            try:
                folder = await self.file_system.get_node(
                    user_id=user_id,
                    node_id=form.form_folder_id,
                )

                if folder.type == FileNodeType.FOLDER and folder.parent_id == project_folder_id:
                    return folder

            except FileSystemNotFoundError:
                pass

        folder = await self.file_system.create_folder(
            user_id=user_id,
            name=form.code,
            parent_id=project_folder_id,
        )

        form.form_folder_id = folder.id

        await self.session.flush()

        return folder

    async def _get_project_folder(
        self,
        *,
        form: FormDefinition,
        user_id: int,
    ):
        project_result = await self.session.execute(
            select(Project).where(
                Project.id == form.project_id,
                Project.created_by == user_id,
            )
        )

        project = project_result.scalar_one_or_none()

        if project is None:
            raise ValueError("Le projet du formulaire est introuvable.")

        if project.project_folder_id is None:
            raise ValueError("Le dossier du projet est introuvable.")

        try:
            project_folder = await self.file_system.get_node(
                user_id=user_id,
                node_id=project.project_folder_id,
            )
        except FileSystemNotFoundError as exc:
            raise ValueError("Le dossier du projet est introuvable.") from exc

        if project_folder.type != FileNodeType.FOLDER:
            raise ValueError("Le dossier du projet est invalide.")

        return project_folder

    async def _ensure_attachments_enabled(
        self,
        *,
        form: FormDefinition,
    ) -> None:
        config = form.global_config or {}

        attachments = config.get("attachments")

        if not isinstance(attachments, dict):
            raise ValueError("La configuration des fichiers attachés est invalide.")

        if attachments.get("enabled") is not True:
            raise PermissionError("Les fichiers attachés ne sont pas activés pour ce formulaire.")

    async def list(
        self,
        *,
        user_id: int,
        include_archived: bool = False,
    ) -> list[FormDefinition]:
        statement = (
            select(FormDefinition)
            .where(
                FormDefinition.created_by == user_id,
            )
            .order_by(
                FormDefinition.name.asc(),
            )
        )

        if not include_archived:
            statement = statement.where(
                FormDefinition.status != FormStatus.ARCHIVED,
            )

        result = await self.session.execute(
            statement,
        )

        return list(result.scalars().all())

    async def list_by_project(
        self,
        *,
        project_id: int,
        user_id: int,
        include_archived: bool = False,
    ) -> list[FormDefinition]:
        project_result = await self.session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.created_by == user_id,
            )
        )

        project = project_result.scalar_one_or_none()

        if project is None:
            raise ValueError("Projet introuvable.")

        statement = (
            select(FormDefinition)
            .where(
                FormDefinition.project_id == project_id,
                FormDefinition.created_by == user_id,
            )
            .order_by(
                FormDefinition.name.asc(),
            )
        )

        if not include_archived:
            statement = statement.where(
                FormDefinition.status != FormStatus.ARCHIVED,
            )

        result = await self.session.execute(
            statement,
        )

        return list(result.scalars().all())

    async def get(
        self,
        *,
        form_id: int,
        user_id: int,
    ) -> FormDefinition | None:
        result = await self.session.execute(
            select(FormDefinition).where(
                FormDefinition.id == form_id,
                FormDefinition.created_by == user_id,
            )
        )

        return result.scalar_one_or_none()

    async def update(
        self,
        *,
        form_id: int,
        user_id: int,
        data: FormDefinitionUpdate,
    ) -> FormDefinition:
        form = await self.get(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        if data.name is not None:
            name = data.name.strip()

            if not name:
                raise ValueError("Le nom du formulaire est obligatoire.")

            form.name = name

        if data.description is not None:
            form.description = data.description.strip() or None

        if data.form_type is not None:
            form_type = data.form_type.strip()

            if not form_type:
                raise ValueError("Le type du formulaire est obligatoire.")

            form.form_type = form_type

        if data.global_config is not None:
            form.global_config = merge_form_global_config(
                form.global_config,
                data.global_config,
            )

        if data.status is not None:
            form.status = data.status

        await self.session.flush()

        return form

    async def archive(
        self,
        *,
        form_id: int,
        user_id: int,
    ) -> FormDefinition:
        form = await self.get(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        form.status = FormStatus.ARCHIVED

        await self.session.flush()

        return form

    async def delete(
        self,
        *,
        form_id: int,
        user_id: int,
    ) -> None:
        form = await self.get(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        # --------------------------------------------------------
        # 1. Supprimer le dossier du formulaire et tout son contenu
        # --------------------------------------------------------

        if form.form_folder_id is not None:
            try:
                await self.file_system.delete(
                    user_id=user_id,
                    node_id=form.form_folder_id,
                )
            except FileSystemNotFoundError:
                # Le dossier a déjà été supprimé.
                pass

        # --------------------------------------------------------
        # 2. Supprimer le formulaire et ses données associées
        # --------------------------------------------------------

        await self.session.delete(form)

        await self.session.flush()

    async def list_form_files(
        self,
        *,
        form_id: int,
        user_id: int,
    ):
        form = await self.get(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        await self._ensure_attachments_enabled(
            form=form,
        )

        project_folder = await self._get_project_folder(
            form=form,
            user_id=user_id,
        )

        folder = await self.ensure_form_folder(
            form=form,
            user_id=user_id,
            project_folder_id=project_folder.id,
        )

        return await self.file_system.list_children(
            user_id=user_id,
            parent_id=folder.id,
        )

    async def upload_form_file(
        self,
        *,
        form_id: int,
        user_id: int,
        name: str,
        source: BinaryIO,
        mime_type: str | None = None,
        extension: str | None = None,
    ):
        form = await self.get(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        await self._ensure_attachments_enabled(
            form=form,
        )

        project_folder = await self._get_project_folder(
            form=form,
            user_id=user_id,
        )

        folder = await self.ensure_form_folder(
            form=form,
            user_id=user_id,
            project_folder_id=project_folder.id,
        )

        return await self.file_system.create_file(
            user_id=user_id,
            name=name,
            source=source,
            parent_id=folder.id,
            mime_type=mime_type,
            extension=extension,
        )

    async def delete_form_file(
        self,
        *,
        form_id: int,
        file_id: int,
        user_id: int,
    ) -> None:
        form = await self.get(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        await self._ensure_attachments_enabled(
            form=form,
        )

        project_folder = await self._get_project_folder(
            form=form,
            user_id=user_id,
        )

        folder = await self.ensure_form_folder(
            form=form,
            user_id=user_id,
            project_folder_id=project_folder.id,
        )

        file_node = await self.file_system.get_node(
            user_id=user_id,
            node_id=file_id,
        )

        if file_node.parent_id != folder.id:
            raise PermissionError("Ce fichier n'appartient pas à ce formulaire.")

        if file_node.type != FileNodeType.FILE:
            raise ValueError("L'élément indiqué n'est pas un fichier.")

        await self.file_system.delete(
            user_id=user_id,
            node_id=file_id,
        )
