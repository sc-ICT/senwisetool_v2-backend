from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.form_builder.project_definition import ProjectDefinition
from app.models.form_builder.project_question import (
    ProjectQuestion,
)
from app.models.form_builder.project_question_dependency import (
    ProjectQuestionDependency,
)
from app.models.form_builder.question_version import QuestionVersion
from app.schemas.form_builder.project_question_dependency import (
    ProjectQuestionDependencyCreate,
)

CHOICE_TYPES = {
    "SINGLE_CHOICE",
    "MULTIPLE_CHOICE",
    "DROPDOWN",
    "AUTOCOMPLETE",
    "LIKERT_SCALE",
}


def validate_dependency_value(
    *,
    source_question: ProjectQuestion,
    operator: str,
    value: str,
) -> None:
    question_type = source_question.question_version.question_type.value

    options = source_question.question_version.options

    option_values = {option.value for option in options}

    if operator in {
        "EQUALS",
        "NOT_EQUALS",
    }:
        if question_type in CHOICE_TYPES:
            if value not in option_values:
                raise ValueError(
                    "La valeur choisie ne correspond " "à aucune option de la question source."
                )

        return

    if operator in {
        "IN",
        "NOT_IN",
    }:
        if question_type not in {
            "MULTIPLE_CHOICE",
            "DROPDOWN",
            "AUTOCOMPLETE",
            "SINGLE_CHOICE",
            "LIKERT_SCALE",
        }:
            raise ValueError(
                "Cet opérateur ne peut pas être utilisé " "avec ce type de question source."
            )

        values = [item.strip() for item in value.split(",") if item.strip()]

        if not values:
            raise ValueError("Au moins une valeur doit être fournie.")

        invalid_values = [item for item in values if item not in option_values]

        if invalid_values:
            raise ValueError(
                "Une ou plusieurs valeurs ne correspondent "
                "pas aux options de la question source."
            )

        return

    raise ValueError("Opérateur de dépendance non supporté.")


class ProjectQuestionDependencyService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def _get_project_question(
        self,
        *,
        project_id: int,
        section_id: int,
        project_question_id: int,
        user_id: int,
    ) -> ProjectQuestion | None:
        project_result = await self.session.execute(
            select(ProjectDefinition).where(
                ProjectDefinition.id == project_id,
                ProjectDefinition.created_by == user_id,
            )
        )

        project = project_result.scalar_one_or_none()

        if project is None:
            return None

        result = await self.session.execute(
            select(ProjectQuestion).where(
                ProjectQuestion.id == project_question_id,
                ProjectQuestion.project_id == project_id,
                ProjectQuestion.section_id == section_id,
            )
        )

        return result.scalar_one_or_none()

    async def _get_question_with_version(
        self,
        *,
        project_id: int,
        project_question_id: int,
        user_id: int,
    ) -> ProjectQuestion | None:
        project_result = await self.session.execute(
            select(ProjectDefinition).where(
                ProjectDefinition.id == project_id,
                ProjectDefinition.created_by == user_id,
            )
        )

        project = project_result.scalar_one_or_none()

        if project is None:
            return None

        result = await self.session.execute(
            select(ProjectQuestion)
            .options(
                selectinload(
                    ProjectQuestion.question_version,
                ).selectinload(
                    QuestionVersion.options,
                ),
            )
            .where(
                ProjectQuestion.id == project_question_id,
                ProjectQuestion.project_id == project_id,
            )
        )

        return result.scalars().first()

    async def list(
        self,
        *,
        project_id: int,
        section_id: int,
        target_question_id: int,
        user_id: int,
    ) -> list[ProjectQuestionDependency]:
        target_question = await self._get_project_question(
            project_question_id=target_question_id,
            project_id=project_id,
            section_id=section_id,
            user_id=user_id,
        )

        if target_question is None:
            raise ValueError("Question cible introuvable.")

        result = await self.session.execute(
            select(ProjectQuestionDependency)
            .where(
                ProjectQuestionDependency.target_question_id == target_question_id,
            )
            .order_by(
                ProjectQuestionDependency.id.asc(),
            )
        )

        return list(result.scalars().all())

    async def create(
        self,
        *,
        project_id: int,
        section_id: int,
        target_question_id: int,
        user_id: int,
        data: ProjectQuestionDependencyCreate,
    ) -> ProjectQuestionDependency:
        target_question = await self._get_project_question(
            project_question_id=target_question_id,
            project_id=project_id,
            section_id=section_id,
            user_id=user_id,
        )

        if target_question is None:
            raise ValueError("Question cible introuvable.")

        source_question = await self._get_question_with_version(
            project_id=project_id,
            project_question_id=data.source_question_id,
            user_id=user_id,
        )

        if source_question is None:
            raise ValueError("Question source introuvable.")

        if source_question.id == target_question.id:
            raise ValueError("Une question ne peut pas dépendre d'elle-même.")

        validate_dependency_value(
            source_question=source_question, operator=data.operator, value=data.value
        )

        existing = await self.session.execute(
            select(ProjectQuestionDependency).where(
                ProjectQuestionDependency.target_question_id == target_question_id,
                ProjectQuestionDependency.source_question_id == data.source_question_id,
            )
        )

        if existing.scalar_one_or_none() is not None:
            raise ValueError("Cette dépendance existe déjà.")

        dependency = ProjectQuestionDependency(
            target_question_id=(target_question_id),
            source_question_id=(data.source_question_id),
            operator=data.operator,
            value=data.value,
        )

        self.session.add(dependency)

        await self.session.flush()

        return dependency

    async def delete(
        self,
        *,
        project_id: int,
        section_id: int,
        target_question_id: int,
        dependency_id: int,
        user_id: int,
    ) -> None:
        target_question = await self._get_project_question(
            project_question_id=target_question_id,
            project_id=project_id,
            section_id=section_id,
            user_id=user_id,
        )

        if target_question is None:
            raise ValueError("Question cible introuvable.")

        result = await self.session.execute(
            select(ProjectQuestionDependency).where(
                ProjectQuestionDependency.id == dependency_id,
                ProjectQuestionDependency.target_question_id == target_question_id,
            )
        )

        dependency = result.scalar_one_or_none()

        if dependency is None:
            raise ValueError("Dépendance introuvable.")

        await self.session.delete(dependency)

        await self.session.flush()
