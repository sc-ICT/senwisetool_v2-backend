from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    CurrentUser,
    get_project_question_service,
)
from app.models.form_builder.project_question import (
    ProjectQuestion,
)
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.form_builder.project_question import (
    ProjectQuestionCreate,
    ProjectQuestionListResponse,
    ProjectQuestionOptionResponse,
    ProjectQuestionReorder,
    ProjectQuestionResponse,
    ProjectQuestionUpdate,
)
from app.services.form_builder.project_question import (
    ProjectQuestionService,
)


def build_project_question_response(
    question: ProjectQuestion,
) -> ProjectQuestionResponse:
    return ProjectQuestionResponse(
        id=question.id,
        project_id=question.project_id,
        section_id=question.section_id,
        question_definition_id=(question.question_definition_id),
        question_version_id=(question.question_version_id),
        position=question.position,
        config=question.config,
        question_code=(question.question_definition.code),
        question_name=(question.question_definition.name),
        version_number=(question.question_version.version),
        version_label=(question.question_version.label),
        question_type=(question.question_version.question_type.value),
        options=[
            ProjectQuestionOptionResponse(
                id=option.id,
                value=option.value,
                label=option.label,
                position=option.position,
                option_metadata=option.option_metadata,
            )
            for option in sorted(
                question.question_version.options,
                key=lambda option: option.position,
            )
        ],
    )


router = APIRouter(
    prefix="/projects/{project_id}/sections/{section_id}/questions",
    tags=["Project Questions"],
)


@router.post(
    "",
    response_model=ApiResponse[ProjectQuestionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_project_question(
    project_id: int,
    section_id: int,
    data: ProjectQuestionCreate,
    service: ProjectQuestionService = Depends(
        get_project_question_service,
    ),
    user: User = CurrentUser,
):
    try:
        project_question = await service.create(
            project_id=project_id,
            section_id=section_id,
            user_id=user.id,
            data=data,
        )

        project_question = await service.get(
            project_id=project_id,
            section_id=section_id,
            project_question_id=project_question.id,
            user_id=user.id,
        )

        if project_question is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=("La question a été créée, " "mais sa récupération a échoué."),
            )

        return ok(
            message="Question ajoutée au projet.",
            data=build_project_question_response(project_question),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=ApiResponse[ProjectQuestionListResponse],
)
async def list_project_questions(
    project_id: int,
    section_id: int,
    service: ProjectQuestionService = Depends(
        get_project_question_service,
    ),
    user: User = CurrentUser,
):
    try:
        questions = await service.list(
            project_id=project_id,
            section_id=section_id,
            user_id=user.id,
        )

        items = [build_project_question_response(question) for question in questions]

        return ok(
            message="Questions récupérées avec succès.",
            data=ProjectQuestionListResponse(
                items=items,
                count=len(items),
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "/reorder",
    response_model=ApiResponse[ProjectQuestionListResponse],
)
async def reorder_project_questions(
    project_id: int,
    section_id: int,
    data: ProjectQuestionReorder,
    service: ProjectQuestionService = Depends(
        get_project_question_service,
    ),
    user: User = CurrentUser,
):
    try:
        questions = await service.reorder(
            project_id=project_id,
            section_id=section_id,
            user_id=user.id,
            ordered_question_ids=(data.ordered_question_ids),
        )

        return ok(
            message="Questions réordonnées avec succès.",
            data=ProjectQuestionListResponse(
                items=[build_project_question_response(question) for question in questions],
                count=len(questions),
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{project_question_id}",
    response_model=ApiResponse[ProjectQuestionResponse],
)
async def update_project_question(
    project_id: int,
    section_id: int,
    project_question_id: int,
    data: ProjectQuestionUpdate,
    service: ProjectQuestionService = Depends(
        get_project_question_service,
    ),
    user: User = CurrentUser,
):
    try:
        project_question = await service.update(
            project_id=project_id,
            section_id=section_id,
            project_question_id=project_question_id,
            user_id=user.id,
            data=data,
        )

        return ok(
            message="Question du projet modifiée.",
            data=build_project_question_response(project_question),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{project_question_id}",
    response_model=ApiResponse[None],
)
async def delete_project_question(
    project_id: int,
    section_id: int,
    project_question_id: int,
    service: ProjectQuestionService = Depends(
        get_project_question_service,
    ),
    user: User = CurrentUser,
):
    try:
        await service.delete(
            project_id=project_id,
            section_id=section_id,
            project_question_id=project_question_id,
            user_id=user.id,
        )

        return ok(
            message="Question retirée du projet.",
            data=None,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
