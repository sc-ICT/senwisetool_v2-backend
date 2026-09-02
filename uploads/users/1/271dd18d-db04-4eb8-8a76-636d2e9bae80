from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    CurrentUser,
    get_question_group_service,
)
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.form_builder.question_group import (
    QuestionGroupCreate,
    QuestionGroupDetailResponse,
    QuestionGroupListResponse,
    QuestionGroupQuestionResponse,
    QuestionGroupResponse,
    QuestionGroupUpdate,
)
from app.services.form_builder.question_group import (
    QuestionGroupService,
)

router = APIRouter(
    prefix="/question-groups",
    tags=["Question Groups"],
)


@router.post(
    "",
    response_model=ApiResponse[QuestionGroupResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_question_group(
    data: QuestionGroupCreate,
    service: QuestionGroupService = Depends(
        get_question_group_service,
    ),
    user: User = CurrentUser,
):
    try:
        group = await service.create(
            user_id=user.id,
            data=data,
        )

        return ok(
            message="Groupe créé avec succès.",
            data=QuestionGroupResponse.model_validate(
                group,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=ApiResponse[QuestionGroupListResponse],
)
async def list_question_groups(
    include_archived: bool = False,
    service: QuestionGroupService = Depends(
        get_question_group_service,
    ),
    user: User = CurrentUser,
):
    groups = await service.list(
        user_id=user.id,
        include_archived=include_archived,
    )

    return ok(
        message="Groupes récupérés avec succès.",
        data=QuestionGroupListResponse(
            items=[
                QuestionGroupResponse(
                    id=group.id,
                    name=group.name,
                    description=group.description,
                    status=group.status,
                    created_by=group.created_by,
                    question_ids=[question.id for question in group.questions],
                )
                for group in groups
            ],
            count=len(groups),
        ),
    )


@router.get("/{group_id}", response_model=ApiResponse[QuestionGroupDetailResponse])
async def get_question_group(
    group_id: int,
    service: QuestionGroupService = Depends(
        get_question_group_service,
    ),
    user: User = CurrentUser,
):
    group = await service.get(
        group_id=group_id,
        user_id=user.id,
    )

    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Groupe introuvable.",
        )

    return ok(
        message="Groupe récupéré avec succès.",
        data=QuestionGroupDetailResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            status=group.status,
            created_by=group.created_by,
            questions=[
                QuestionGroupQuestionResponse(
                    id=question.id,
                    code=question.code,
                    name=question.name,
                    status=question.status.value,
                )
                for question in group.questions
            ],
        ),
    )


@router.patch(
    "/{group_id}",
    response_model=ApiResponse[QuestionGroupResponse],
)
async def update_question_group(
    group_id: int,
    data: QuestionGroupUpdate,
    service: QuestionGroupService = Depends(
        get_question_group_service,
    ),
    user: User = CurrentUser,
):
    try:
        group = await service.update(
            group_id=group_id,
            user_id=user.id,
            data=data,
        )

        return ok(
            message="Groupe modifié avec succès.",
            data=QuestionGroupResponse.model_validate(
                group,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{group_id}/archive",
    response_model=ApiResponse[QuestionGroupResponse],
)
async def archive_question_group(
    group_id: int,
    service: QuestionGroupService = Depends(
        get_question_group_service,
    ),
    user: User = CurrentUser,
):
    try:
        group = await service.archive(
            group_id=group_id,
            user_id=user.id,
        )

        return ok(
            message="Groupe archivé avec succès.",
            data=QuestionGroupResponse.model_validate(
                group,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{group_id}/questions/{question_id}",
    response_model=ApiResponse[QuestionGroupDetailResponse],
)
async def add_question_to_group(
    group_id: int,
    question_id: int,
    service: QuestionGroupService = Depends(
        get_question_group_service,
    ),
    user: User = CurrentUser,
):
    try:
        group = await service.add_question(
            group_id=group_id,
            question_id=question_id,
            user_id=user.id,
        )

        return ok(
            message="Question ajoutée au groupe.",
            data=QuestionGroupDetailResponse(
                id=group.id,
                name=group.name,
                description=group.description,
                status=group.status,
                created_by=group.created_by,
                questions=[
                    QuestionGroupQuestionResponse(
                        id=question.id,
                        code=question.code,
                        name=question.name,
                        status=question.status.value,
                    )
                    for question in group.questions
                ],
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{group_id}/questions/{question_id}",
    response_model=ApiResponse[QuestionGroupDetailResponse],
)
async def remove_question_from_group(
    group_id: int,
    question_id: int,
    service: QuestionGroupService = Depends(
        get_question_group_service,
    ),
    user: User = CurrentUser,
):
    try:
        group = await service.remove_question(
            group_id=group_id,
            question_id=question_id,
            user_id=user.id,
        )

        return ok(
            message="Question retirée du groupe.",
            data=QuestionGroupDetailResponse(
                id=group.id,
                name=group.name,
                description=group.description,
                status=group.status,
                created_by=group.created_by,
                questions=[
                    QuestionGroupQuestionResponse(
                        id=question.id,
                        code=question.code,
                        name=question.name,
                        status=question.status.value,
                    )
                    for question in group.questions
                ],
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
