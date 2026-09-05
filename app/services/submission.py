from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.form_builder.form_definition import FormDefinition
from app.models.form_builder.project import Project
from app.models.project_agent_assignment import ProjectAgentAssignment
from app.models.submission import Submission
from app.models.submission_answer import SubmissionAnswer
from app.schemas.submission import (
    SubmissionAnswerCreate,
    SubmissionCreate,
    SubmissionSyncError,
    SubmissionSyncItemResult,
)


class SubmissionService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def _get_existing_submission(
        self,
        *,
        local_id: str,
    ) -> Submission | None:
        result = await self.session.execute(
            select(Submission).where(
                Submission.local_id == local_id,
            )
        )

        return result.scalar_one_or_none()

    async def _validate_project_access(
        self,
        *,
        project_id: int,
        agent_id: int,
    ) -> Project:
        assignment_result = await self.session.execute(
            select(ProjectAgentAssignment.id).where(
                ProjectAgentAssignment.project_id == project_id,
                ProjectAgentAssignment.agent_id == agent_id,
            )
        )

        assignment_id = assignment_result.scalar_one_or_none()

        if assignment_id is None:
            raise ValueError(
                "L'agent n'est pas affecté à ce projet.",
            )

        project_result = await self.session.execute(
            select(Project).where(
                Project.id == project_id,
            )
        )

        project = project_result.scalar_one_or_none()

        if project is None:
            raise ValueError(
                "Projet introuvable.",
            )

        return project

    async def _get_form(
        self,
        *,
        form_id: int,
        project_id: int,
    ) -> FormDefinition:
        result = await self.session.execute(
            select(FormDefinition).where(
                FormDefinition.id == form_id,
                FormDefinition.project_id == project_id,
            )
        )

        form = result.scalar_one_or_none()

        if form is None:
            raise ValueError(
                "Le formulaire n'existe pas ou n'appartient pas à ce projet.",
            )

        return form

    async def _validate_answers(
        self,
        *,
        form_id: int,
        answers: dict[str, SubmissionAnswerCreate],
    ) -> None:
        from app.models.form_builder.form_question import FormQuestion
        from app.models.form_builder.question_definition import QuestionDefinition

        result = await self.session.execute(
            select(
                FormQuestion.id,
                QuestionDefinition.code,
            )
            .join(
                QuestionDefinition,
                QuestionDefinition.id == FormQuestion.question_definition_id,
            )
            .where(
                FormQuestion.form_id == form_id,
            )
        )

        rows = result.all()

        questions_by_id = {question_id: question_code for question_id, question_code in rows}

        for answer in answers.values():
            expected_code = questions_by_id.get(
                answer.question_id,
            )

            if expected_code is None:
                raise ValueError(
                    f"La question {answer.question_id} " "n'appartient pas au formulaire.",
                )

            if expected_code != answer.question_code:
                raise ValueError(
                    f"Le code de la question {answer.question_id} " "est invalide.",
                )

    async def create_submission(
        self,
        *,
        data: SubmissionCreate,
        agent: Agent,
    ) -> tuple[Submission, bool]:
        # --------------------------------------------------------------
        # 1. Vérifier si l'enquête existe déjà
        # --------------------------------------------------------------

        existing = await self._get_existing_submission(
            local_id=data.local_id,
        )

        if existing is not None:
            if existing.agent_id != agent.id:
                raise ValueError(
                    "Cette enquête locale existe déjà et appartient à un autre agent.",
                )

            return existing, True

        # --------------------------------------------------------------
        # 2. Vérifier le projet
        # --------------------------------------------------------------

        await self._validate_project_access(
            project_id=data.project_id,
            agent_id=agent.id,
        )

        # --------------------------------------------------------------
        # 3. Vérifier le formulaire
        # --------------------------------------------------------------

        form = await self._get_form(
            form_id=data.form_id,
            project_id=data.project_id,
        )

        # --------------------------------------------------------------
        # 4. Vérifications métier
        # --------------------------------------------------------------

        if data.status != "COMPLETED":
            raise ValueError(
                "Seules les enquêtes terminées peuvent être synchronisées.",
            )

        if not data.consent_accepted:
            raise ValueError(
                "Le consentement doit être accepté.",
            )

        if data.completed_at is None:
            raise ValueError(
                "La date de fin de l'enquête est obligatoire.",
            )

        if data.answered_questions > data.total_questions:
            raise ValueError(
                "Le nombre de réponses ne peut pas dépasser le nombre de questions.",
            )

        if data.answered_questions != len(data.answers):
            raise ValueError(
                "Le nombre de réponses déclaré ne correspond pas aux réponses envoyées.",
            )

        # --------------------------------------------------------------
        # 5. Vérifier les questions
        # --------------------------------------------------------------

        await self._validate_answers(
            form_id=form.id,
            answers=data.answers,
        )

        # --------------------------------------------------------------
        # 6. Créer la submission
        # --------------------------------------------------------------

        submission = Submission(
            local_id=data.local_id,
            agent_id=agent.id,
            project_id=data.project_id,
            form_id=data.form_id,
            form_code=form.code,
            form_name=form.name,
            name=data.name,
            status="COMPLETED",
            total_questions=data.total_questions,
            answered_questions=data.answered_questions,
            consent_accepted=data.consent_accepted,
            consent_accepted_at=data.consent_accepted_at,
            submission_metadata=data.metadata,
            created_at_mobile=data.created_at,
            started_at=data.started_at,
            completed_at=data.completed_at,
            updated_at_mobile=data.updated_at,
        )

        self.session.add(submission)

        await self.session.flush()

        # --------------------------------------------------------------
        # 7. Créer les réponses
        # --------------------------------------------------------------

        for answer in data.answers.values():
            submission_answer = SubmissionAnswer(
                submission_id=submission.id,
                question_id=answer.question_id,
                question_code=answer.question_code,
                value=answer.value,
                answered_at=answer.answered_at,
            )

            self.session.add(submission_answer)

        await self.session.flush()

        return submission, False

    async def sync_many(
        self,
        *,
        submissions: list[SubmissionCreate],
        agent: Agent,
    ) -> tuple[
        list[SubmissionSyncItemResult],
        list[SubmissionSyncError],
    ]:
        items: list[SubmissionSyncItemResult] = []

        errors: list[SubmissionSyncError] = []

        for data in submissions:
            try:
                submission, already_synced = await self.create_submission(
                    data=data,
                    agent=agent,
                )

                items.append(
                    SubmissionSyncItemResult(
                        local_id=data.local_id,
                        server_id=submission.id,
                        status=("ALREADY_SYNCED" if already_synced else "SYNCED"),
                    )
                )

            except ValueError as exc:
                errors.append(
                    SubmissionSyncError(
                        local_id=data.local_id,
                        message=str(exc),
                    )
                )

        return items, errors
