from __future__ import annotations

from copy import deepcopy

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FileNodeType
from app.models.form_builder.enums import FormStatus, ProjectStatus
from app.models.form_builder.form_definition import FormDefinition
from app.models.form_builder.project import Project
from app.models.project_agent_assignment import ProjectAgentAssignment
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.file_system import FileNotFoundError as FileSystemNotFoundError
from app.services.file_system import (
    FileSystemService,
)
from app.services.project_code import generate_project_code
from app.services.project_defaults import (
    DEFAULT_PROJECT_GLOBAL_CONFIG,
    merge_project_global_config,
)


class ProjectService:

    def __init__(
        self,
        session: AsyncSession,
        file_system: FileSystemService,
    ) -> None:
        self.session = session
        self.file_system = file_system

    async def get(
        self,
        *,
        project_id: int,
        user_id: int,
    ) -> Project | None:

        result = await self.session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.created_by == user_id,
            )
        )

        return result.scalar_one_or_none()

    async def update(
        self,
        *,
        project_id: int,
        user_id: int,
        data: ProjectUpdate,
    ) -> Project:
        project = await self.get(
            project_id=project_id,
            user_id=user_id,
        )

        if project is None:
            raise ValueError("Projet introuvable.")

        if data.name is not None:
            name = data.name.strip()

            if not name:
                raise ValueError(
                    "Le nom du projet est obligatoire.",
                )

            project.name = name

        if data.description is not None:
            project.description = data.description.strip() if data.description.strip() else None

        if data.project_type is not None:
            project_type = data.project_type.strip()

            if not project_type:
                raise ValueError(
                    "Le type du projet est obligatoire.",
                )

            project.project_type = project_type

        if data.global_config is not None:
            project.global_config = merge_project_global_config(
                project.global_config,
                data.global_config,
            )

        await self.session.flush()

        return project

    async def create(
        self,
        *,
        user_id: int,
        data: ProjectCreate,
    ) -> Project:

        name = data.name.strip()
        project_type = data.project_type.strip()

        if not name:
            raise ValueError("Le nom du projet est obligatoire.")

        if not project_type:
            raise ValueError("Le type du projet est obligatoire.")

        # --------------------------------------------------------
        # 1. Générer le code du projet
        # --------------------------------------------------------

        code = generate_project_code(
            user_id,
        )

        existing = await self.session.execute(
            select(Project.id).where(
                Project.code == code,
            )
        )

        if existing.scalar_one_or_none() is not None:
            raise ValueError("Impossible de générer un code projet unique.")

        # --------------------------------------------------------
        # 2. Créer le projet en DRAFT
        # --------------------------------------------------------

        project = Project(
            code=code,
            name=name,
            description=(
                data.description.strip() if data.description and data.description.strip() else None
            ),
            project_type=project_type,
            status=ProjectStatus.DRAFT,
            global_config=deepcopy(
                DEFAULT_PROJECT_GLOBAL_CONFIG,
            ),
            created_by=user_id,
            parent_folder_id=data.parent_folder_id,
        )

        self.session.add(project)

        await self.session.flush()

        # --------------------------------------------------------
        # 3. Garantir le dossier parent
        # --------------------------------------------------------

        parent_folder = await self._ensure_parent_folder(
            user_id=user_id,
            parent_folder_id=data.parent_folder_id,
        )

        # --------------------------------------------------------
        # 4. Créer le dossier du projet
        # --------------------------------------------------------

        project_folder = await self.file_system.create_folder(
            user_id=user_id,
            name=project.code,
            parent_id=(parent_folder.id if parent_folder is not None else None),
        )

        # --------------------------------------------------------
        # 5. Enregistrer le dossier dans le projet
        # --------------------------------------------------------

        project.project_folder_id = project_folder.id

        await self.session.flush()

        return project

    async def _ensure_parent_folder(
        self,
        *,
        user_id: int,
        parent_folder_id: int | None,
    ):
        """
        Retourne le dossier parent du projet.

        Si aucun parent n'est configuré,
        None représente la racine du filesystem.

        Si un parent est configuré mais n'existe plus,
        une erreur est levée.
        """

        if parent_folder_id is None:
            return None

        try:
            parent = await self.file_system.get_node(
                user_id=user_id,
                node_id=parent_folder_id,
            )

        except FileSystemNotFoundError as exc:
            raise ValueError("Le dossier parent du projet est introuvable.") from exc

        if parent.type != FileNodeType.FOLDER:
            raise ValueError("Le dossier parent du projet doit être un dossier.")

        return parent

    async def list(
        self,
        *,
        user_id: int,
        include_archived: bool = False,
    ) -> list[Project]:
        query = select(Project).where(
            Project.created_by == user_id,
        )

        if not include_archived:
            query = query.where(
                Project.status != ProjectStatus.ARCHIVED,
            )

        query = query.order_by(
            Project.created_at.desc(),
        )

        result = await self.session.execute(query)

        return list(result.scalars().all())

    def _validate_status_transition(
        self,
        *,
        current_status: ProjectStatus,
        target_status: ProjectStatus,
    ) -> None:
        if current_status == target_status:
            raise ValueError("Le projet possède déjà cet état.")

        allowed_transitions = {
            ProjectStatus.DRAFT: {
                ProjectStatus.PUBLISHED,
                ProjectStatus.ARCHIVED,
            },
            ProjectStatus.PUBLISHED: {
                ProjectStatus.DRAFT,
                ProjectStatus.ARCHIVED,
            },
            ProjectStatus.ARCHIVED: {
                ProjectStatus.DRAFT,
            },
        }

        if target_status not in allowed_transitions[current_status]:
            raise ValueError(
                f"Transition impossible : " f"{current_status.value} → {target_status.value}."
            )

    async def publish(
        self,
        *,
        project_id: int,
        user_id: int,
    ) -> Project:
        project = await self.get(
            project_id=project_id,
            user_id=user_id,
        )

        if project is None:
            raise ValueError("Projet introuvable.")

        self._validate_status_transition(
            current_status=project.status,
            target_status=ProjectStatus.PUBLISHED,
        )

        project.status = ProjectStatus.PUBLISHED

        await self.session.flush()

        return project

    async def archive(
        self,
        *,
        project_id: int,
        user_id: int,
    ) -> Project:
        project = await self.get(
            project_id=project_id,
            user_id=user_id,
        )

        if project is None:
            raise ValueError("Projet introuvable.")

        self._validate_status_transition(
            current_status=project.status,
            target_status=ProjectStatus.ARCHIVED,
        )

        project.status = ProjectStatus.ARCHIVED

        await self.session.flush()

        return project

    async def restore_to_draft(
        self,
        *,
        project_id: int,
        user_id: int,
    ) -> Project:
        project = await self.get(
            project_id=project_id,
            user_id=user_id,
        )

        if project is None:
            raise ValueError("Projet introuvable.")

        self._validate_status_transition(
            current_status=project.status,
            target_status=ProjectStatus.DRAFT,
        )

        project.status = ProjectStatus.DRAFT

        await self.session.flush()

        return project

    async def list_assigned_to_agent(
        self,
        *,
        agent_id: int,
    ) -> list[tuple[Project, int, object]]:
        query = (
            select(
                Project,
                func.count(FormDefinition.id).label(
                    "published_form_count",
                ),
                ProjectAgentAssignment.created_at.label(
                    "assigned_at",
                ),
            )
            .join(
                ProjectAgentAssignment,
                ProjectAgentAssignment.project_id == Project.id,
            )
            .outerjoin(
                FormDefinition,
                (
                    (FormDefinition.project_id == Project.id)
                    & (FormDefinition.status == FormStatus.PUBLISHED)
                ),
            )
            .where(
                ProjectAgentAssignment.agent_id == agent_id,
                Project.status == ProjectStatus.PUBLISHED,
            )
            .group_by(
                Project.id,
                ProjectAgentAssignment.created_at,
            )
            .order_by(
                Project.updated_at.desc(),
            )
        )

        result = await self.session.execute(query)

        return [
            (
                project,
                int(published_form_count),
                assigned_at,
            )
            for project, published_form_count, assigned_at in result.all()
        ]

    async def get_assigned_to_agent(
        self,
        *,
        project_id: int,
        agent_id: int,
    ) -> tuple[Project, object, list[FormDefinition]] | None:
        project_result = await self.session.execute(
            select(
                Project,
                ProjectAgentAssignment.created_at,
            )
            .join(
                ProjectAgentAssignment,
                ProjectAgentAssignment.project_id == Project.id,
            )
            .where(
                Project.id == project_id,
                ProjectAgentAssignment.agent_id == agent_id,
                Project.status == ProjectStatus.PUBLISHED,
            )
        )

        row = project_result.one_or_none()

        if row is None:
            return None

        project, assigned_at = row

        forms_result = await self.session.execute(
            select(FormDefinition)
            .where(
                FormDefinition.project_id == project_id,
                FormDefinition.status == FormStatus.PUBLISHED,
            )
            .order_by(
                FormDefinition.name.asc(),
            )
        )

        forms = list(forms_result.scalars().all())

        return project, assigned_at, forms
