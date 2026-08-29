from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.form_builder.enums import QuestionGroupStatus
from app.models.form_builder.question_definition import (
    QuestionDefinition,
)
from app.models.form_builder.question_group import QuestionGroup
from app.schemas.form_builder.question_group import (
    QuestionGroupCreate,
    QuestionGroupUpdate,
)


class QuestionGroupService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_by_name(
        self,
        *,
        user_id: int,
        name: str,
    ) -> QuestionGroup | None:
        """
        Recherche un groupe appartenant à l'utilisateur
        par son nom.
        """

        normalized_name = name.strip()

        if not normalized_name:
            raise ValueError("Le nom du groupe est obligatoire.")

        result = await self.session.execute(
            select(QuestionGroup).where(
                QuestionGroup.created_by == user_id,
                QuestionGroup.name == normalized_name,
            )
        )

        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: int,
        data: QuestionGroupCreate,
    ) -> QuestionGroup:
        name = data.name.strip()

        if not name:
            raise ValueError("Le nom du groupe est obligatoire.")

        group = QuestionGroup(
            name=name,
            description=(
                data.description.strip() if data.description and data.description.strip() else None
            ),
            created_by=user_id,
        )

        self.session.add(group)

        await self.session.flush()

        return group

    async def list(
        self,
        *,
        user_id: int,
        include_archived: bool = False,
    ) -> list[QuestionGroup]:
        statement = (
            select(QuestionGroup)
            .where(
                QuestionGroup.created_by == user_id,
            )
            .order_by(
                QuestionGroup.name.asc(),
            )
        )

        if not include_archived:
            statement = statement.where(
                QuestionGroup.status == QuestionGroupStatus.ACTIVE,
            )

        result = await self.session.execute(
            statement,
        )

        return list(result.scalars().all())

    async def get(
        self,
        *,
        group_id: int,
        user_id: int,
    ) -> QuestionGroup | None:
        result = await self.session.execute(
            select(QuestionGroup)
            .options(
                selectinload(
                    QuestionGroup.questions,
                )
            )
            .where(
                QuestionGroup.id == group_id,
                QuestionGroup.created_by == user_id,
            )
        )

        return result.scalar_one_or_none()

    async def update(
        self,
        *,
        group_id: int,
        user_id: int,
        data: QuestionGroupUpdate,
    ) -> QuestionGroup:
        group = await self.get(
            group_id=group_id,
            user_id=user_id,
        )

        if group is None:
            raise ValueError("Groupe introuvable.")

        if data.name is not None:
            name = data.name.strip()

            if not name:
                raise ValueError("Le nom du groupe est obligatoire.")

            group.name = name

        if data.description is not None:
            group.description = data.description.strip() or None

        if data.status is not None:
            group.status = data.status

        await self.session.flush()

        return group

    async def archive(
        self,
        *,
        group_id: int,
        user_id: int,
    ) -> QuestionGroup:
        group = await self.get(
            group_id=group_id,
            user_id=user_id,
        )

        if group is None:
            raise ValueError("Groupe introuvable.")

        group.status = QuestionGroupStatus.ARCHIVED

        await self.session.flush()

        return group

    async def add_question(
        self,
        *,
        group_id: int,
        question_id: int,
        user_id: int,
    ) -> QuestionGroup:
        group = await self.get(
            group_id=group_id,
            user_id=user_id,
        )

        if group is None:
            raise ValueError("Groupe introuvable.")

        result = await self.session.execute(
            select(QuestionDefinition).where(
                QuestionDefinition.id == question_id,
                QuestionDefinition.created_by == user_id,
            )
        )

        question = result.scalar_one_or_none()

        if question is None:
            raise ValueError("Question introuvable.")

        if question not in group.questions:
            group.questions.append(question)

        await self.session.flush()

        return group

    async def remove_question(
        self,
        *,
        group_id: int,
        question_id: int,
        user_id: int,
    ) -> QuestionGroup:
        group = await self.get(
            group_id=group_id,
            user_id=user_id,
        )

        if group is None:
            raise ValueError("Groupe introuvable.")

        question = next(
            (question for question in group.questions if question.id == question_id),
            None,
        )

        if question is None:
            raise ValueError("Cette question ne fait pas partie du groupe.")

        group.questions.remove(question)

        await self.session.flush()

        return group
