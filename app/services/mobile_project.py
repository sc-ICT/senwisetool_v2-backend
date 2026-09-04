from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import FileNodeType
from app.models.file_node import FileNode
from app.models.form_builder.enums import FormStatus, ProjectStatus
from app.models.form_builder.form_definition import FormDefinition
from app.models.form_builder.form_question import FormQuestion
from app.models.form_builder.form_question_dependency import (
    FormQuestionDependency,
)
from app.models.form_builder.form_section import FormSection
from app.models.form_builder.project import Project
from app.models.form_builder.question_definition import QuestionDefinition
from app.models.form_builder.question_option import QuestionOption
from app.models.form_builder.question_version import QuestionVersion
from app.models.project_agent_assignment import (
    ProjectAgentAssignment,
    ProjectAgentAssignmentZone,
)
from app.services.file_system import FileSystemService


class MobileProjectService:
    """
    Service dédié aux opérations de synchronisation
    des projets côté application mobile.
    """

    def __init__(
        self,
        session: AsyncSession,
        file_system_service: FileSystemService,
    ) -> None:
        self.session = session
        self.file_system_service = file_system_service

    # =====================================================================
    # ASSIGNMENT
    # =====================================================================

    async def _get_agent_assignment(
        self,
        *,
        project_id: int,
        agent_id: int,
    ) -> ProjectAgentAssignment | None:
        result = await self.session.execute(
            select(ProjectAgentAssignment)
            .where(
                ProjectAgentAssignment.project_id == project_id,
                ProjectAgentAssignment.agent_id == agent_id,
            )
            .options(
                selectinload(ProjectAgentAssignment.zones).selectinload(
                    ProjectAgentAssignmentZone.file_node
                ),
            )
        )

        return result.scalar_one_or_none()

    # =====================================================================
    # FORM HASH
    # =====================================================================

    async def _build_form_hash(
        self,
        *,
        form: FormDefinition,
    ) -> str:
        """
        Construit une empreinte déterministe de l'intégralité
        de la configuration publiée du formulaire.

        Toute modification significative du formulaire produit
        une nouvelle empreinte.
        """

        # -------------------------------------------------------------
        # Questions du formulaire
        # -------------------------------------------------------------

        question_ids: list[int] = []

        for section in form.sections:
            for question in section.questions:
                question_ids.append(question.id)

        # -------------------------------------------------------------
        # Dépendances
        # -------------------------------------------------------------

        dependencies_by_question: dict[int, list[dict[str, Any]]] = {}

        if question_ids:
            dependency_result = await self.session.execute(
                select(FormQuestionDependency)
                .where(FormQuestionDependency.target_question_id.in_(question_ids))
                .order_by(FormQuestionDependency.id.asc())
            )

            dependencies = list(dependency_result.scalars().all())

            for dependency in dependencies:
                dependencies_by_question.setdefault(
                    dependency.target_question_id,
                    [],
                ).append(
                    {
                        "id": dependency.id,
                        "condition": dependency.condition,
                        "actions_if_true": dependency.actions_if_true,
                        "actions_if_false": dependency.actions_if_false,
                    }
                )

        # -------------------------------------------------------------
        # Construction canonique
        # -------------------------------------------------------------

        canonical: dict[str, Any] = {
            "id": form.id,
            "code": form.code,
            "name": form.name,
            "description": form.description,
            "form_type": form.form_type,
            "global_config": form.global_config,
            "sections": [],
        }

        for section in form.sections:
            section_data: dict[str, Any] = {
                "id": section.id,
                "name": section.name,
                "description": section.description,
                "position": section.position,
                "config": section.config,
                "questions": [],
            }

            for question in section.questions:
                question_definition = question.question_definition
                question_version = question.question_version

                question_data: dict[str, Any] = {
                    "id": question.id,
                    "question_definition_id": question.question_definition_id,
                    "question_version_id": question.question_version_id,
                    "position": question.position,
                    "config": question.config,
                    "question_definition": {
                        "id": question_definition.id,
                        "code": question_definition.code,
                        "name": question_definition.name,
                        "description": question_definition.description,
                    },
                    "question_version": {
                        "id": question_version.id,
                        "version": question_version.version,
                        "label": question_version.label,
                        "help_text": question_version.help_text,
                        "question_type": question_version.question_type.value,
                        "base_config": question_version.base_config,
                        "options": [
                            {
                                "id": option.id,
                                "value": option.value,
                                "label": option.label,
                                "position": option.position,
                                "option_metadata": option.option_metadata,
                            }
                            for option in question_version.options
                        ],
                    },
                    "dependencies": dependencies_by_question.get(
                        question.id,
                        [],
                    ),
                }

                section_data["questions"].append(question_data)

            canonical["sections"].append(section_data)

        # -------------------------------------------------------------
        # JSON déterministe
        # -------------------------------------------------------------

        serialized = json.dumps(
            canonical,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    # =====================================================================
    # FORMS
    # =====================================================================

    async def _get_published_forms(
        self,
        *,
        project_id: int,
    ) -> list[FormDefinition]:
        result = await self.session.execute(
            select(FormDefinition)
            .where(
                FormDefinition.project_id == project_id,
                FormDefinition.status == FormStatus.PUBLISHED,
            )
            .options(
                selectinload(FormDefinition.sections)
                .selectinload(FormSection.questions)
                .selectinload(FormQuestion.question_definition),
                selectinload(FormDefinition.sections)
                .selectinload(FormSection.questions)
                .selectinload(FormQuestion.question_version)
                .selectinload(QuestionVersion.options),
            )
            .order_by(
                FormDefinition.name.asc(),
            )
        )

        return list(result.scalars().unique().all())

    # =====================================================================
    # PROJECT ATTACHMENTS
    # =====================================================================

    async def _get_project_attachments(
        self,
        *,
        project: Project,
    ) -> list[FileNode]:
        """
        Retourne uniquement les fichiers directement présents
        dans le dossier du projet.

        Ils sont considérés comme les fichiers généraux du projet.

        Les dossiers de formulaires et le dossier zones sont
        volontairement exclus puisqu'ils ne sont pas des
        attachments généraux.
        """

        if project.project_folder_id is None:
            return []

        result = await self.session.execute(
            select(FileNode)
            .where(
                FileNode.parent_id == project.project_folder_id,
                FileNode.type == FileNodeType.FILE,
            )
            .order_by(
                FileNode.name.asc(),
            )
        )

        return list(result.scalars().all())

    # =====================================================================
    # SYNC HASH
    # =====================================================================

    def _build_sync_hash(
        self,
        *,
        project: Project,
        assignment: ProjectAgentAssignment,
        forms: list[dict[str, Any]],
        files: list[dict[str, Any]],
        zones: list[dict[str, Any]],
    ) -> str:
        """
        Construit une empreinte globale représentant l'état
        synchronisable du projet pour un agent donné.

        Toute modification des éléments présents dans le manifest
        produit une nouvelle empreinte.
        """

        canonical: dict[str, Any] = {
            "project": {
                "id": project.id,
                "code": project.code,
                "name": project.name,
                "description": project.description,
                "project_type": project.project_type,
                "status": project.status.value,
                "global_config": project.global_config,
                "updated_at": project.updated_at.isoformat(),
            },
            "assignment": {
                "id": assignment.id,
            },
            "forms": [
                {
                    "id": form["id"],
                    "code": form["code"],
                    "updated_at": form["updated_at"].isoformat(),
                    "hash": form["hash"],
                }
                for form in forms
            ],
            "files": [
                {
                    "file_id": file["file_id"],
                    "name": file["name"],
                    "mime_type": file["mime_type"],
                    "extension": file["extension"],
                    "size": file["size"],
                    "updated_at": file["updated_at"].isoformat(),
                }
                for file in files
            ],
            "zones": [
                {
                    "assignment_zone_id": zone["assignment_zone_id"],
                    "file_id": zone["file_id"],
                    "name": zone["name"],
                    "mime_type": zone["mime_type"],
                    "extension": zone["extension"],
                    "size": zone["size"],
                    "updated_at": zone["updated_at"].isoformat(),
                }
                for zone in zones
            ],
        }

        serialized = json.dumps(
            canonical,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    # =====================================================================
    # SYNC MANIFEST
    # =====================================================================

    async def get_sync_manifest(
        self,
        *,
        project_id: int,
        agent_id: int,
    ) -> dict[str, Any] | None:
        """
        Construit le manifeste de synchronisation d'un projet
        pour un agent précis.
        """

        # -------------------------------------------------------------
        # 1. Vérifier l'affectation
        # -------------------------------------------------------------

        assignment = await self._get_agent_assignment(
            project_id=project_id,
            agent_id=agent_id,
        )

        if assignment is None:
            return None

        # -------------------------------------------------------------
        # 2. Charger le projet
        # -------------------------------------------------------------

        project_result = await self.session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.status == ProjectStatus.PUBLISHED,
            )
        )

        project = project_result.scalar_one_or_none()

        if project is None:
            return None

        # -------------------------------------------------------------
        # 3. Formulaires publiés
        # -------------------------------------------------------------

        forms = await self._get_published_forms(
            project_id=project.id,
        )

        form_items: list[dict[str, Any]] = []

        for form in forms:
            form_hash = await self._build_form_hash(
                form=form,
            )

            form_items.append(
                {
                    "id": form.id,
                    "code": form.code,
                    "name": form.name,
                    "description": form.description,
                    "form_type": form.form_type,
                    "updated_at": form.updated_at,
                    "hash": form_hash,
                }
            )

        # -------------------------------------------------------------
        # 4. Attachments généraux du projet
        # -------------------------------------------------------------

        global_config = project.global_config or {}

        attachments_config = global_config.get(
            "attachments",
            {},
        )

        attachments_enabled = (
            isinstance(attachments_config, dict) and attachments_config.get("enabled") is True
        )

        project_files: list[FileNode] = []

        if attachments_enabled:
            project_files = await self._get_project_attachments(
                project=project,
            )

        # -------------------------------------------------------------
        # 5. Zones affectées à l'agent
        # -------------------------------------------------------------

        zone_items: list[dict[str, Any]] = []

        for assignment_zone in assignment.zones:
            file_node = assignment_zone.file_node

            if file_node.type != FileNodeType.FILE:
                continue

            zone_items.append(
                {
                    "assignment_zone_id": assignment_zone.id,
                    "file_id": file_node.id,
                    "name": file_node.name,
                    "mime_type": file_node.mime_type,
                    "extension": file_node.extension,
                    "size": file_node.size,
                    "updated_at": file_node.updated_at,
                }
            )

        # -------------------------------------------------------------
        # 6. Attachments projet
        # -------------------------------------------------------------

        file_items: list[dict[str, Any]] = []

        for file_node in project_files:
            file_items.append(
                {
                    "file_id": file_node.id,
                    "name": file_node.name,
                    "mime_type": file_node.mime_type,
                    "extension": file_node.extension,
                    "size": file_node.size,
                    "updated_at": file_node.updated_at,
                }
            )

        # -------------------------------------------------------------
        # 7. Empreinte globale de synchronisation
        # -------------------------------------------------------------

        sync_hash = self._build_sync_hash(
            project=project,
            assignment=assignment,
            forms=form_items,
            files=file_items,
            zones=zone_items,
        )

        # -------------------------------------------------------------
        # 8. Manifeste
        # -------------------------------------------------------------

        return {
            "project": {
                "id": project.id,
                "code": project.code,
                "name": project.name,
                "description": project.description,
                "project_type": project.project_type,
                "status": project.status,
                "global_config": project.global_config,
                "updated_at": project.updated_at,
            },
            "assignment": {
                "id": assignment.id,
                "assigned_at": assignment.created_at,
                "updated_at": assignment.updated_at,
            },
            "sync_hash": sync_hash,
            "forms": form_items,
            "files": file_items,
            "zones": zone_items,
        }

    async def get_form_for_agent(
        self,
        *,
        project_id: int,
        form_id: int,
        agent_id: int,
    ) -> dict[str, Any] | None:
        # ---------------------------------------------------------
        # 1. Vérifier que l'agent est affecté au projet
        # ---------------------------------------------------------
        assignment_result = await self.session.execute(
            select(ProjectAgentAssignment.id).where(
                ProjectAgentAssignment.project_id == project_id,
                ProjectAgentAssignment.agent_id == agent_id,
            )
        )

        assignment_id = assignment_result.scalar_one_or_none()

        if assignment_id is None:
            return None

        # ---------------------------------------------------------
        # 2. Vérifier que le projet existe et est publié
        # ---------------------------------------------------------
        project_result = await self.session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.status == ProjectStatus.PUBLISHED,
            )
        )

        project = project_result.scalar_one_or_none()

        if project is None:
            return None

        # ---------------------------------------------------------
        # 3. Charger le formulaire publié appartenant au projet
        # ---------------------------------------------------------
        form_result = await self.session.execute(
            select(FormDefinition)
            .where(
                FormDefinition.id == form_id,
                FormDefinition.project_id == project_id,
                FormDefinition.status == FormStatus.PUBLISHED,
            )
            .options(
                selectinload(FormDefinition.sections)
                .selectinload(FormSection.questions)
                .selectinload(FormQuestion.question_definition),
                selectinload(FormDefinition.sections)
                .selectinload(FormSection.questions)
                .selectinload(FormQuestion.question_version)
                .selectinload(QuestionVersion.options),
            )
        )

        form = form_result.scalar_one_or_none()

        if form is None:
            return None

        # ---------------------------------------------------------
        # 4. Récupérer les IDs des questions
        # ---------------------------------------------------------
        question_ids: list[int] = []

        for section in form.sections:
            for question in section.questions:
                question_ids.append(question.id)

        # ---------------------------------------------------------
        # 5. Charger les dépendances du formulaire
        # ---------------------------------------------------------
        dependencies_by_question: dict[
            int,
            list[FormQuestionDependency],
        ] = {}

        if question_ids:
            dependency_result = await self.session.execute(
                select(FormQuestionDependency)
                .where(FormQuestionDependency.target_question_id.in_(question_ids))
                .order_by(FormQuestionDependency.id.asc())
            )

            dependencies = list(dependency_result.scalars().all())

            for dependency in dependencies:
                dependencies_by_question.setdefault(
                    dependency.target_question_id,
                    [],
                ).append(dependency)

        # ---------------------------------------------------------
        # 6. Construire les sections
        # ---------------------------------------------------------
        sections_data: list[dict[str, Any]] = []

        for section in sorted(
            form.sections,
            key=lambda item: item.position,
        ):
            questions_data: list[dict[str, Any]] = []

            for question in sorted(
                section.questions,
                key=lambda item: item.position,
            ):
                question_definition = question.question_definition
                question_version = question.question_version

                options_data: list[dict[str, Any]] = []

                for option in sorted(
                    question_version.options,
                    key=lambda item: item.position,
                ):
                    options_data.append(
                        {
                            "id": option.id,
                            "value": option.value,
                            "label": option.label,
                            "position": option.position,
                            "option_metadata": option.option_metadata,
                        }
                    )

                dependencies_data: list[dict[str, Any]] = []

                for dependency in dependencies_by_question.get(
                    question.id,
                    [],
                ):
                    dependencies_data.append(
                        {
                            "id": dependency.id,
                            "condition": dependency.condition,
                            "actions_if_true": dependency.actions_if_true,
                            "actions_if_false": dependency.actions_if_false,
                        }
                    )

                questions_data.append(
                    {
                        "id": question.id,
                        "form_id": question.form_id,
                        "section_id": question.section_id,
                        "question_definition_id": (question.question_definition_id),
                        "question_version_id": (question.question_version_id),
                        "position": question.position,
                        "config": question.config,
                        "question_code": question_definition.code,
                        "question_name": question_definition.name,
                        "question_definition": {
                            "id": question_definition.id,
                            "code": question_definition.code,
                            "name": question_definition.name,
                            "description": (question_definition.description),
                        },
                        "question_version": {
                            "id": question_version.id,
                            "version": question_version.version,
                            "label": question_version.label,
                            "help_text": question_version.help_text,
                            "question_type": (question_version.question_type.value),
                            "base_config": (question_version.base_config),
                            "options": options_data,
                        },
                        "dependencies": dependencies_data,
                    }
                )

            sections_data.append(
                {
                    "id": section.id,
                    "name": section.name,
                    "description": section.description,
                    "position": section.position,
                    "config": section.config,
                    "questions": questions_data,
                }
            )

        # ---------------------------------------------------------
        # 7. Retourner le formulaire complet
        # ---------------------------------------------------------
        return {
            "id": form.id,
            "project_id": form.project_id,
            "code": form.code,
            "name": form.name,
            "description": form.description,
            "form_type": form.form_type,
            "status": form.status,
            "global_config": form.global_config,
            "created_at": form.created_at,
            "updated_at": form.updated_at,
            "sections": sections_data,
        }

    async def get_authorized_file_for_agent(
        self,
        *,
        project_id: int,
        agent_id: int,
        file_id: int,
    ) -> FileNode | None:
        """
        Retourne un fichier que l'agent est autorisé à télécharger
        dans le contexte du projet.

        Autorisations possibles :

        1. Fichier directement attaché au dossier du projet
          ET attachments.enabled == True.

        2. Fichier de zone explicitement attribué à cet agent
          via ProjectAgentAssignmentZone.
        """

        # ---------------------------------------------------------
        # 1. Vérifier que l'agent est bien affecté au projet
        # ---------------------------------------------------------
        assignment_result = await self.session.execute(
            select(ProjectAgentAssignment).where(
                ProjectAgentAssignment.project_id == project_id,
                ProjectAgentAssignment.agent_id == agent_id,
            )
        )

        assignment = assignment_result.scalar_one_or_none()

        if assignment is None:
            return None

        # ---------------------------------------------------------
        # 2. Vérifier que le projet existe et est publié
        # ---------------------------------------------------------
        project_result = await self.session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.status == ProjectStatus.PUBLISHED,
            )
        )

        project = project_result.scalar_one_or_none()

        if project is None:
            return None

        # ---------------------------------------------------------
        # 3. Récupérer le fichier
        #
        # IMPORTANT :
        # le FileNode appartient au propriétaire du projet,
        # pas à l'agent.
        # ---------------------------------------------------------
        file_result = await self.session.execute(
            select(FileNode).where(
                FileNode.id == file_id,
                FileNode.user_id == project.created_by,
                FileNode.type == FileNodeType.FILE,
            )
        )

        file_node = file_result.scalar_one_or_none()

        if file_node is None:
            return None

        # ---------------------------------------------------------
        # 4. CAS A :
        # fichier directement attaché au projet
        # ---------------------------------------------------------
        attachments_config = (project.global_config or {}).get("attachments", {})

        attachments_enabled = (
            isinstance(attachments_config, dict) and attachments_config.get("enabled") is True
        )

        if (
            attachments_enabled
            and project.project_folder_id is not None
            and file_node.parent_id == project.project_folder_id
        ):
            return file_node

        # ---------------------------------------------------------
        # 5. CAS B :
        # fichier de zone attribué à CET agent
        # ---------------------------------------------------------
        zone_result = await self.session.execute(
            select(ProjectAgentAssignmentZone.id).where(
                ProjectAgentAssignmentZone.assignment_id == assignment.id,
                ProjectAgentAssignmentZone.file_node_id == file_node.id,
            )
        )

        zone_assignment_id = zone_result.scalar_one_or_none()

        if zone_assignment_id is not None:
            return file_node

        # ---------------------------------------------------------
        # 6. Aucun droit d'accès
        # ---------------------------------------------------------
        return None
