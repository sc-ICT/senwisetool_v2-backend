from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    CurrentUser,
    get_form_question_service,
)
from app.models.form_builder.form_question import (
    FormQuestion,
)
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.form_builder.form_question import (
    FormQuestionCreate,
    FormQuestionListResponse,
    FormQuestionOptionResponse,
    FormQuestionReorder,
    FormQuestionResponse,
    FormQuestionUpdate,
)
from app.services.form_builder.form_question import (
    FormQuestionService,
)


def build_form_question_response(
    question: FormQuestion,
) -> FormQuestionResponse:
    return FormQuestionResponse(
        id=question.id,
        form_id=question.form_id,
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
            FormQuestionOptionResponse(
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
    prefix="/forms/{form_id}/sections/{section_id}/questions",
    tags=["Form Questions"],
)


@router.post(
    "",
    response_model=ApiResponse[FormQuestionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_form_question(
    form_id: int,
    section_id: int,
    data: FormQuestionCreate,
    service: FormQuestionService = Depends(
        get_form_question_service,
    ),
    user: User = CurrentUser,
):
    try:
        form_question = await service.create(
            form_id=form_id,
            section_id=section_id,
            user_id=user.id,
            data=data,
        )

        form_question = await service.get(
            form_id=form_id,
            section_id=section_id,
            form_question_id=form_question.id,
            user_id=user.id,
        )

        if form_question is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=("La question a été créée, " "mais sa récupération a échoué."),
            )

        return ok(
            message="Question ajoutée au formulaire.",
            data=build_form_question_response(form_question),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=ApiResponse[FormQuestionListResponse],
)
async def list_form_questions(
    form_id: int,
    section_id: int,
    service: FormQuestionService = Depends(
        get_form_question_service,
    ),
    user: User = CurrentUser,
):
    try:
        questions = await service.list(
            form_id=form_id,
            section_id=section_id,
            user_id=user.id,
        )

        items = [build_form_question_response(question) for question in questions]

        return ok(
            message="Questions récupérées avec succès.",
            data=FormQuestionListResponse(
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
    response_model=ApiResponse[FormQuestionListResponse],
)
async def reorder_form_questions(
    form_id: int,
    section_id: int,
    data: FormQuestionReorder,
    service: FormQuestionService = Depends(
        get_form_question_service,
    ),
    user: User = CurrentUser,
):
    try:
        questions = await service.reorder(
            form_id=form_id,
            section_id=section_id,
            user_id=user.id,
            ordered_question_ids=(data.ordered_question_ids),
        )

        return ok(
            message="Questions réordonnées avec succès.",
            data=FormQuestionListResponse(
                items=[build_form_question_response(question) for question in questions],
                count=len(questions),
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{form_question_id}",
    response_model=ApiResponse[FormQuestionResponse],
)
async def update_form_question(
    form_id: int,
    section_id: int,
    form_question_id: int,
    data: FormQuestionUpdate,
    service: FormQuestionService = Depends(
        get_form_question_service,
    ),
    user: User = CurrentUser,
):
    try:
        form_question = await service.update(
            form_id=form_id,
            section_id=section_id,
            form_question_id=form_question_id,
            user_id=user.id,
            data=data,
        )

        return ok(
            message="Question du formulaire modifiée.",
            data=build_form_question_response(form_question),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{form_question_id}",
    response_model=ApiResponse[None],
)
async def delete_form_question(
    form_id: int,
    section_id: int,
    form_question_id: int,
    service: FormQuestionService = Depends(
        get_form_question_service,
    ),
    user: User = CurrentUser,
):
    try:
        await service.delete(
            form_id=form_id,
            section_id=section_id,
            form_question_id=form_question_id,
            user_id=user.id,
        )

        return ok(
            message="Question retirée du formulaire.",
            data=None,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
