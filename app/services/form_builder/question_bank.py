from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.form_builder.enums import (
    QuestionDefinitionStatus,
)
from app.models.form_builder.question_definition import (
    QuestionDefinition,
)
from app.models.form_builder.question_option import (
    QuestionOption,
)
from app.models.form_builder.question_version import (
    QuestionVersion,
)
from app.schemas.form_builder.question_definition import (
    QuestionDefinitionCreate,
    QuestionDefinitionUpdate,
)
from app.schemas.form_builder.question_version import (
    QuestionVersionCreate,
    QuestionVersionResponse,
)


class QuestionBankService:
    """
    Service métier de la banque de questions.

    Ce service ne fait pas directement de HTTP.
    Il travaille avec les modèles SQLAlchemy et les schemas
    Pydantic.
    """

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def create_question(
        self,
        *,
        user_id: int,
        data: QuestionDefinitionCreate,
        version_data: QuestionVersionCreate,
    ) -> QuestionDefinition:
        """
        Crée une question avec sa première version.

        Structure créée :

            QuestionDefinition
                    │
                    └── QuestionVersion v1
                            └── options
        """

        code = data.code.strip()

        if not code:
            raise ValueError("Le code de la question est obligatoire.")

        name = data.name.strip()

        if not name:
            raise ValueError("Le nom de la question est obligatoire.")

        # ---------------------------------------------------------
        # Vérifier que le code n'existe pas déjà
        # ---------------------------------------------------------

        existing_result = await self.session.execute(
            select(QuestionDefinition.id).where(
                QuestionDefinition.code == code,
            )
        )

        if existing_result.scalar_one_or_none() is not None:
            raise ValueError(f"Une question avec le code « {code} » existe déjà.")

        # ---------------------------------------------------------
        # Créer la définition
        # ---------------------------------------------------------

        question = QuestionDefinition(
            code=code,
            name=name,
            description=data.description,
            status=QuestionDefinitionStatus.ACTIVE,
            created_by=user_id,
        )

        self.session.add(question)

        await self.session.flush()

        # ---------------------------------------------------------
        # Créer la première version
        # ---------------------------------------------------------

        version = QuestionVersion(
            question_definition_id=question.id,
            version=1,
            label=version_data.label.strip(),
            help_text=version_data.help_text,
            question_type=version_data.question_type,
            base_config=version_data.base_config,
            created_by=user_id,
        )

        self.session.add(version)

        await self.session.flush()

        # ---------------------------------------------------------
        # Créer les options
        # ---------------------------------------------------------

        for option_data in version_data.options:
            option = QuestionOption(
                question_version_id=version.id,
                value=option_data.value.strip(),
                label=option_data.label.strip(),
                position=option_data.position,
                option_metadata=option_data.option_metadata,
            )

            self.session.add(option)

        await self.session.flush()

        return question

    async def get_question(
        self,
        *,
        question_id: int,
        user_id: int,
    ) -> QuestionDefinition | None:
        statement = (
            select(QuestionDefinition)
            .options(
                selectinload(QuestionDefinition.versions).selectinload(QuestionVersion.options)
            )
            .where(
                QuestionDefinition.id == question_id,
                QuestionDefinition.created_by == user_id,
            )
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def list_questions(
        self,
        *,
        user_id: int,
        include_archived: bool = False,
    ) -> list[QuestionDefinition]:
        statement = (
            select(QuestionDefinition)
            .options(
                selectinload(
                    QuestionDefinition.versions,
                )
            )
            .where(
                QuestionDefinition.created_by == user_id,
            )
            .order_by(
                QuestionDefinition.name.asc(),
            )
        )

        if not include_archived:
            statement = statement.where(
                QuestionDefinition.status == QuestionDefinitionStatus.ACTIVE,
            )

        result = await self.session.execute(
            statement,
        )

        return list(result.scalars().all())

    async def create_version(
        self,
        *,
        question_id: int,
        user_id: int,
        data: QuestionVersionCreate,
    ) -> QuestionVersionResponse:
        result = await self.session.execute(
            select(QuestionDefinition).where(
                QuestionDefinition.id == question_id,
                QuestionDefinition.created_by == user_id,
            )
        )

        question = result.scalar_one_or_none()

        if question is None:
            raise ValueError("Question introuvable.")

        result = await self.session.execute(
            select(QuestionVersion.version)
            .where(QuestionVersion.question_definition_id == question_id)
            .order_by(QuestionVersion.version.desc())
            .limit(1)
        )

        latest_version = result.scalar_one_or_none()

        next_version = 1 if latest_version is None else latest_version + 1

        label = data.label.strip()

        if not label:
            raise ValueError("Le libellé de la version est obligatoire.")

        version = QuestionVersion(
            question_definition_id=question_id,
            version=next_version,
            label=label,
            help_text=data.help_text,
            question_type=data.question_type,
            base_config=data.base_config,
            created_by=user_id,
        )

        self.session.add(version)

        await self.session.flush()

        for option_data in data.options:
            option = QuestionOption(
                question_version_id=version.id,
                value=option_data.value.strip(),
                label=option_data.label.strip(),
                position=option_data.position,
                option_metadata=option_data.option_metadata,
            )

            self.session.add(option)

        await self.session.flush()

        result = await self.session.execute(
            select(QuestionVersion)
            .options(
                selectinload(
                    QuestionVersion.options,
                )
            )
            .where(
                QuestionVersion.id == version.id,
            )
        )

        created_version = result.scalar_one()

        return QuestionVersionResponse.model_validate(
            created_version,
        )

    async def list_versions(
        self,
        *,
        question_id: int,
        user_id: int,
    ) -> list[QuestionVersion]:
        """
        Retourne toutes les versions d'une question
        dans l'ordre croissant.
        """

        question_result = await self.session.execute(
            select(QuestionDefinition.id).where(
                QuestionDefinition.id == question_id,
                QuestionDefinition.created_by == user_id,
            )
        )

        if question_result.scalar_one_or_none() is None:
            raise ValueError("Question introuvable.")

        result = await self.session.execute(
            select(QuestionVersion)
            .where(
                QuestionVersion.question_definition_id == question_id,
            )
            .options(
                selectinload(
                    QuestionVersion.options,
                ),
            )
            .order_by(
                QuestionVersion.version.asc(),
            )
        )

        return list(result.scalars().all())

    async def archive_question(
        self,
        *,
        question_id: int,
        user_id: int,
    ) -> QuestionDefinition:
        """
        Archive une question de la banque.

        L'archivage ne supprime ni la question,
        ni ses versions, ni ses options.
        """

        result = await self.session.execute(
            select(QuestionDefinition).where(
                QuestionDefinition.id == question_id,
                QuestionDefinition.created_by == user_id,
            )
        )

        question = result.scalar_one_or_none()

        if question is None:
            raise ValueError("Question introuvable.")

        if question.status == QuestionDefinitionStatus.ARCHIVED:
            return question

        question.status = QuestionDefinitionStatus.ARCHIVED

        await self.session.flush()

        return question

    async def duplicate_question(
        self,
        *,
        question_id: int,
        user_id: int,
        new_code: str,
        new_name: str,
        description: str | None = None,
    ) -> QuestionDefinition:
        """
        Duplique une question existante.

        La nouvelle question est indépendante :
        - nouveau code ;
        - nouvelle définition ;
        - nouvelle version 1 ;
        - nouvelles options.
        """

        source_result = await self.session.execute(
            select(QuestionDefinition)
            .options(
                selectinload(
                    QuestionDefinition.versions,
                ).selectinload(
                    QuestionVersion.options,
                )
            )
            .where(
                QuestionDefinition.id == question_id,
                QuestionDefinition.created_by == user_id,
            )
        )

        source_question = source_result.scalar_one_or_none()

        if source_question is None:
            raise ValueError("Question source introuvable.")

        code = new_code.strip()

        if not code:
            raise ValueError("Le nouveau code est obligatoire.")

        name = new_name.strip()

        if not name:
            raise ValueError("Le nouveau nom est obligatoire.")

        existing_result = await self.session.execute(
            select(QuestionDefinition.id).where(
                QuestionDefinition.code == code,
            )
        )

        if existing_result.scalar_one_or_none() is not None:
            raise ValueError(f"Une question avec le code « {code} » existe déjà.")

        source_versions = sorted(
            source_question.versions,
            key=lambda version: version.version,
        )

        if not source_versions:
            raise ValueError("La question source ne possède aucune version.")

        latest_version = source_versions[-1]

        duplicated_question = QuestionDefinition(
            code=code,
            name=name,
            description=(description if description is not None else source_question.description),
            status=QuestionDefinitionStatus.ACTIVE,
            created_by=user_id,
        )

        self.session.add(
            duplicated_question,
        )

        await self.session.flush()

        duplicated_version = QuestionVersion(
            question_definition_id=(duplicated_question.id),
            version=1,
            label=latest_version.label,
            help_text=latest_version.help_text,
            question_type=latest_version.question_type,
            base_config=dict(latest_version.base_config),
            created_by=user_id,
        )

        self.session.add(
            duplicated_version,
        )

        await self.session.flush()

        for source_option in latest_version.options:
            duplicated_option = QuestionOption(
                question_version_id=(duplicated_version.id),
                value=source_option.value,
                label=source_option.label,
                position=source_option.position,
                option_metadata=dict(source_option.option_metadata),
            )

            self.session.add(
                duplicated_option,
            )

        await self.session.flush()

        return duplicated_question

    async def update_question(
        self,
        *,
        question_id: int,
        user_id: int,
        data: QuestionDefinitionUpdate,
    ) -> QuestionDefinition:
        """
        Modifie les métadonnées d'une question de la banque.

        Le code et le type ne sont pas modifiés ici.
        """

        result = await self.session.execute(
            select(QuestionDefinition).where(
                QuestionDefinition.id == question_id,
                QuestionDefinition.created_by == user_id,
            )
        )

        question = result.scalar_one_or_none()

        if question is None:
            raise ValueError("Question introuvable.")

        if data.name is not None:
            name = data.name.strip()

            if not name:
                raise ValueError("Le nom de la question est obligatoire.")

            question.name = name

        if data.description is not None:
            question.description = data.description.strip() or None

        if data.status is not None:
            question.status = data.status

        await self.session.flush()

        return question
