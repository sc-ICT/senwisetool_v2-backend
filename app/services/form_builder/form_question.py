from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.form_builder.form_definition import (
    FormDefinition,
)
from app.models.form_builder.form_question import (
    FormQuestion,
)
from app.models.form_builder.form_section import (
    FormSection,
)
from app.models.form_builder.question_definition import (
    QuestionDefinition,
)
from app.models.form_builder.question_version import (
    QuestionVersion,
)
from app.schemas.form_builder.form_question import (
    FormQuestionCreate,
    FormQuestionUpdate,
)
from app.schemas.form_builder.form_question_config import (
    FormQuestionConfig,
)

CHOICE_SINGLE_TYPES = {
    "SINGLE_CHOICE",
    "DROPDOWN",
    "AUTOCOMPLETE",
    "LIKERT_SCALE",
}

CHOICE_MULTI_TYPES = {
    "MULTIPLE_CHOICE",
}


def validate_form_question_config(
    *,
    config: FormQuestionConfig,
    question_type: str,
    option_values: Sequence[str],
) -> None:
    validation = config.validation

    # ---------------------------------------------------------
    # Valeurs numériques
    # ---------------------------------------------------------

    if (
        validation.min_value is not None
        and validation.max_value is not None
        and validation.min_value > validation.max_value
    ):
        raise ValueError("La valeur minimale ne peut pas être supérieure " "à la valeur maximale.")

    # ---------------------------------------------------------
    # Longueurs
    # ---------------------------------------------------------

    if (
        validation.min_length is not None
        and validation.max_length is not None
        and validation.min_length > validation.max_length
    ):
        raise ValueError(
            "La longueur minimale ne peut pas être supérieure " "à la longueur maximale."
        )

    default_value = validation.default_value

    # Pas de valeur par défaut
    if default_value is None:
        return

    available_values = set(option_values)

    # ---------------------------------------------------------
    # Questions à choix unique
    # ---------------------------------------------------------

    if question_type in CHOICE_SINGLE_TYPES:
        if not isinstance(
            default_value,
            str,
        ):
            raise ValueError(
                "La valeur par défaut doit être une chaîne " "pour ce type de question."
            )

        if default_value not in available_values:
            raise ValueError("La valeur par défaut ne correspond pas " "à une option disponible.")

        return

    # ---------------------------------------------------------
    # Questions à choix multiple
    # ---------------------------------------------------------

    if question_type in CHOICE_MULTI_TYPES:
        if not isinstance(
            default_value,
            list,
        ):
            raise ValueError(
                "La valeur par défaut doit être une liste " "pour une question à choix multiple."
            )

        if len(default_value) != len(set(default_value)):
            raise ValueError("Les valeurs par défaut ne peuvent pas " "contenir de doublons.")

        invalid_values = [value for value in default_value if value not in available_values]

        if invalid_values:
            raise ValueError(
                "Une ou plusieurs valeurs par défaut "
                "ne correspondent pas aux options disponibles."
            )

        return

    # ---------------------------------------------------------
    # Autres types
    # ---------------------------------------------------------

    if default_value is not None:
        raise ValueError("Ce type de question n'accepte pas de valeur " "par défaut.")


class FormQuestionService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def _get_form(
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

    async def _get_section(
        self,
        *,
        form_id: int,
        section_id: int,
    ) -> FormSection | None:
        result = await self.session.execute(
            select(FormSection).where(
                FormSection.id == section_id,
                FormSection.form_id == form_id,
            )
        )

        return result.scalar_one_or_none()

    async def _get_question(
        self,
        *,
        question_id: int,
        user_id: int,
    ) -> QuestionDefinition | None:
        result = await self.session.execute(
            select(QuestionDefinition).where(
                QuestionDefinition.id == question_id,
                QuestionDefinition.created_by == user_id,
            )
        )

        return result.scalar_one_or_none()

    async def _get_version(
        self,
        *,
        question_id: int,
        version_id: int,
    ) -> QuestionVersion | None:
        result = await self.session.execute(
            select(QuestionVersion)
            .options(
                selectinload(
                    QuestionVersion.options,
                )
            )
            .where(
                QuestionVersion.id == version_id,
                QuestionVersion.question_definition_id == question_id,
            )
        )

        return result.scalars().first()

    async def create(
        self,
        *,
        form_id: int,
        section_id: int,
        user_id: int,
        data: FormQuestionCreate,
    ) -> FormQuestion:
        form = await self._get_form(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        section = await self._get_section(
            form_id=form_id,
            section_id=section_id,
        )

        if section is None:
            raise ValueError("Section introuvable.")

        question = await self._get_question(
            question_id=data.question_definition_id,
            user_id=user_id,
        )

        if question is None:
            raise ValueError("Question introuvable.")

        version = await self._get_version(
            question_id=data.question_definition_id,
            version_id=data.question_version_id,
        )

        if version is None:
            raise ValueError("Version de question introuvable " "ou incompatible avec la question.")

        question_type = version.question_type.value

        option_values = [option.value for option in version.options]

        validate_form_question_config(
            config=data.config,
            question_type=question_type,
            option_values=option_values,
        )

        # Éviter d'ajouter deux fois exactement
        # la même version dans la même section.
        existing = await self.session.execute(
            select(FormQuestion).where(
                FormQuestion.form_id == form_id,
                FormQuestion.section_id == section_id,
                FormQuestion.question_definition_id == data.question_definition_id,
            )
        )

        if existing.scalar_one_or_none() is not None:
            raise ValueError("Cette question est " "déjà présente dans cette section.")

        result = await self.session.execute(
            select(
                func.coalesce(
                    func.max(
                        FormQuestion.position,
                    ),
                    -1,
                )
            ).where(
                FormQuestion.section_id == section_id,
            )
        )

        max_position = result.scalar_one()

        form_question = FormQuestion(
            form_id=form_id,
            section_id=section_id,
            question_definition_id=(data.question_definition_id),
            question_version_id=(data.question_version_id),
            position=max_position + 1,
            config=data.config.model_dump(),
        )

        self.session.add(
            form_question,
        )

        await self.session.flush()

        return form_question

    async def list(
        self,
        *,
        form_id: int,
        section_id: int,
        user_id: int,
    ) -> list[FormQuestion]:
        form = await self._get_form(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        section = await self._get_section(
            form_id=form_id,
            section_id=section_id,
        )

        if section is None:
            raise ValueError("Section introuvable.")

        result = await self.session.execute(
            select(FormQuestion)
            .options(
                selectinload(
                    FormQuestion.question_definition,
                ),
                selectinload(
                    FormQuestion.question_version,
                ).selectinload(
                    QuestionVersion.options,
                ),
            )
            .where(
                FormQuestion.form_id == form_id,
                FormQuestion.section_id == section_id,
            )
            .order_by(
                FormQuestion.position.asc(),
            )
        )

        return list(
            result.scalars().all(),
        )

    async def get(
        self,
        *,
        form_id: int,
        section_id: int,
        form_question_id: int,
        user_id: int,
    ) -> FormQuestion | None:
        form = await self._get_form(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            return None

        result = await self.session.execute(
            select(FormQuestion)
            .options(
                selectinload(
                    FormQuestion.question_definition,
                ),
                selectinload(
                    FormQuestion.question_version,
                ).selectinload(
                    QuestionVersion.options,
                ),
            )
            .where(
                FormQuestion.id == form_question_id,
                FormQuestion.form_id == form_id,
                FormQuestion.section_id == section_id,
            )
        )

        return result.scalars().first()

    async def update(
        self,
        *,
        form_id: int,
        section_id: int,
        form_question_id: int,
        user_id: int,
        data: FormQuestionUpdate,
    ) -> FormQuestion:
        form = await self._get_form(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        section = await self._get_section(
            form_id=form_id,
            section_id=section_id,
        )

        if section is None:
            raise ValueError("Section introuvable.")

        statement = (
            select(FormQuestion)
            .options(
                selectinload(
                    FormQuestion.question_definition,
                ),
                selectinload(
                    FormQuestion.question_version,
                ).selectinload(
                    QuestionVersion.options,
                ),
            )
            .where(
                FormQuestion.id == form_question_id,
                FormQuestion.form_id == form_id,
                FormQuestion.section_id == section_id,
            )
            .limit(1)
        )

        form_question = (await self.session.execute(statement)).scalars().first()

        if form_question is None:
            raise ValueError("Question du formulaire introuvable.")

        question_type = form_question.question_version.question_type.value

        option_values = [option.value for option in (form_question.question_version.options)]

        if data.config is not None:
            validate_form_question_config(
                config=data.config,
                question_type=question_type,
                option_values=option_values,
            )

            form_question.config = data.config.model_dump()

        await self.session.flush()

        return form_question

    async def delete(
        self,
        *,
        form_id: int,
        section_id: int,
        form_question_id: int,
        user_id: int,
    ) -> None:
        form = await self._get_form(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        section = await self._get_section(
            form_id=form_id,
            section_id=section_id,
        )

        if section is None:
            raise ValueError("Section introuvable.")

        result = await self.session.execute(
            select(FormQuestion).where(
                FormQuestion.id == form_question_id,
                FormQuestion.form_id == form_id,
                FormQuestion.section_id == section_id,
            )
        )

        form_question = result.scalar_one_or_none()

        if form_question is None:
            raise ValueError("Question du formulaire introuvable.")

        await self.session.delete(
            form_question,
        )

        await self.session.flush()

    async def reorder(
        self,
        *,
        form_id: int,
        section_id: int,
        user_id: int,
        ordered_question_ids: list[int],
    ) -> list[FormQuestion]:
        form = await self._get_form(
            form_id=form_id,
            user_id=user_id,
        )

        if form is None:
            raise ValueError("Formulaire introuvable.")

        section = await self._get_section(
            form_id=form_id,
            section_id=section_id,
        )

        if section is None:
            raise ValueError("Section introuvable.")

        result = await self.session.execute(
            select(FormQuestion)
            .options(
                selectinload(
                    FormQuestion.question_definition,
                ),
                selectinload(
                    FormQuestion.question_version,
                ).selectinload(
                    QuestionVersion.options,
                ),
            )
            .where(
                FormQuestion.form_id == form_id,
                FormQuestion.section_id == section_id,
            )
            .order_by(
                FormQuestion.position.asc(),
            )
        )

        questions = list(result.scalars().all())

        existing_ids = {question.id for question in questions}

        requested_ids = set(ordered_question_ids)

        if existing_ids != requested_ids:
            raise ValueError(
                "La liste des questions à réordonner "
                "ne correspond pas aux questions de la section."
            )

        question_by_id = {question.id: question for question in questions}

        for position, question_id in enumerate(ordered_question_ids):
            question_by_id[question_id].position = position

        await self.session.flush()

        return sorted(
            questions,
            key=lambda question: question.position,
        )
