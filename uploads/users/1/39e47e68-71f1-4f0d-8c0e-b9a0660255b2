from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    CurrentUser,
    get_question_bank_service,
)
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.form_builder.question_definition import (
    QuestionCreateRequest,
    QuestionDefinitionDetailResponse,
    QuestionDefinitionListItemResponse,
    QuestionDefinitionListResponse,
    QuestionDefinitionResponse,
    QuestionDefinitionUpdate,
    QuestionDuplicateRequest,
    QuestionVersionListResponse,
)
from app.schemas.form_builder.question_version import (
    QuestionVersionCreate,
    QuestionVersionResponse,
)
from app.services.form_builder.question_bank import (
    QuestionBankService,
)

router = APIRouter(
    prefix="/question-bank",
    tags=["Question Bank"],
)


@router.post(
    "/", response_model=ApiResponse[QuestionDefinitionResponse], status_code=status.HTTP_201_CREATED
)
async def create_question(
    payload: QuestionCreateRequest,
    service: QuestionBankService = Depends(
        get_question_bank_service,
    ),
    user: User = CurrentUser,
):
    try:
        question = await service.create_question(
            user_id=user.id,
            data=payload.definition,
            version_data=payload.version,
        )

        return ok(
            message="Question créée avec succès.",
            data=QuestionDefinitionResponse.model_validate(
                question,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/", response_model=ApiResponse[QuestionDefinitionListResponse])
async def list_questions(
    service: QuestionBankService = Depends(
        get_question_bank_service,
    ),
    user: User = CurrentUser,
):
    items = await service.list_questions(
        user_id=user.id,
    )

    response_items = []

    for item in items:
        versions = sorted(
            item.versions,
            key=lambda version: version.version,
        )

        current_version = versions[-1] if versions else None

        response_items.append(
            QuestionDefinitionListItemResponse(
                id=item.id,
                code=item.code,
                name=item.name,
                description=item.description,
                status=item.status,
                created_by=item.created_by,
                current_version=(current_version.version if current_version else None),
                question_type=(current_version.question_type if current_version else None),
            )
        )

    return ok(
        message="Banque de questions récupérée avec succès.",
        data=QuestionDefinitionListResponse(
            items=response_items,
            count=len(response_items),
        ),
    )


@router.post(
    "/{question_id}/versions",
    response_model=ApiResponse[QuestionVersionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_question_version(
    question_id: int,
    data: QuestionVersionCreate,
    service: QuestionBankService = Depends(
        get_question_bank_service,
    ),
    user: User = CurrentUser,
):
    try:
        version = await service.create_version(
            question_id=question_id,
            user_id=user.id,
            data=data,
        )

        return ok(
            message="Nouvelle version créée avec succès.",
            data=QuestionVersionResponse.model_validate(
                version,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/{question_id}", response_model=ApiResponse[QuestionDefinitionDetailResponse])
async def get_question(
    question_id: int,
    service: QuestionBankService = Depends(
        get_question_bank_service,
    ),
    user: User = CurrentUser,
):
    question = await service.get_question(question_id=question_id, user_id=user.id)

    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question introuvable.",
        )

    return ok(
        message="Question récupérée avec succès.",
        data=QuestionDefinitionDetailResponse.model_validate(
            question,
        ),
    )


@router.get("/{question_id}/versions", response_model=ApiResponse[QuestionVersionListResponse])
async def list_question_versions(
    question_id: int,
    service: QuestionBankService = Depends(
        get_question_bank_service,
    ),
    user: User = CurrentUser,
):
    versions = await service.list_versions(question_id=question_id, user_id=user.id)

    return ok(
        message="Versions récupérées avec succès.",
        data=QuestionVersionListResponse(
            items=[
                QuestionVersionResponse.model_validate(
                    version,
                )
                for version in versions
            ],
            count=len(versions),
        ),
    )


@router.patch(
    "/{question_id}",
    response_model=ApiResponse[QuestionDefinitionResponse],
)
async def update_question(
    question_id: int,
    data: QuestionDefinitionUpdate,
    service: QuestionBankService = Depends(
        get_question_bank_service,
    ),
    user: User = CurrentUser,
):
    try:
        question = await service.update_question(
            question_id=question_id, user_id=user.id, data=data
        )

        return ok(
            message="Question mise à jour avec succès.",
            data=QuestionDefinitionResponse.model_validate(
                question,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{question_id}/archive",
    response_model=ApiResponse[QuestionDefinitionResponse],
)
async def archive_question(
    question_id: int,
    service: QuestionBankService = Depends(
        get_question_bank_service,
    ),
    user: User = CurrentUser,
):
    try:
        question = await service.archive_question(question_id=question_id, user_id=user.id)

        return ok(
            message="Question archivée avec succès.",
            data=QuestionDefinitionResponse.model_validate(
                question,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{question_id}/duplicate",
    response_model=ApiResponse[QuestionDefinitionDetailResponse],
    status_code=status.HTTP_201_CREATED,
)
async def duplicate_question(
    question_id: int,
    data: QuestionDuplicateRequest,
    service: QuestionBankService = Depends(
        get_question_bank_service,
    ),
    user: User = CurrentUser,
):
    try:
        question = await service.duplicate_question(
            question_id=question_id,
            user_id=user.id,
            new_code=data.code,
            new_name=data.name,
            description=data.description,
        )

        detailed_question = await service.get_question(question_id=question.id, user_id=user.id)

        if detailed_question is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question dupliquée introuvable.",
            )

        return ok(
            message="Question dupliquée avec succès.",
            data=QuestionDefinitionDetailResponse.model_validate(
                detailed_question,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
