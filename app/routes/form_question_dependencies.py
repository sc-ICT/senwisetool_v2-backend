from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    CurrentUser,
    get_form_question_dependency_service,
)
from app.models.user import User
from app.schemas.common import (
    ApiResponse,
    ok,
)
from app.schemas.form_builder.form_question_dependency import (
    FormQuestionDependencyCreate,
    FormQuestionDependencyResponse,
)
from app.services.form_builder.form_question_dependency import (
    FormQuestionDependencyService,
)

router = APIRouter(
    prefix=(
        "/forms/{form_id}"
        "/sections/{section_id}"
        "/questions/{target_question_id}"
        "/dependencies"
    ),
    tags=["Form Question Dependencies"],
)


@router.get(
    "",
    response_model=ApiResponse[list[FormQuestionDependencyResponse]],
)
async def list_dependencies(
    form_id: int,
    section_id: int,
    target_question_id: int,
    service: FormQuestionDependencyService = Depends(
        get_form_question_dependency_service,
    ),
    user: User = CurrentUser,
):
    try:
        items = await service.list(
            form_id=form_id,
            section_id=section_id,
            target_question_id=target_question_id,
            user_id=user.id,
        )

        return ok(
            message="Dépendances récupérées avec succès.",
            data=[FormQuestionDependencyResponse.model_validate(item) for item in items],
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "",
    response_model=ApiResponse[FormQuestionDependencyResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_dependency(
    form_id: int,
    section_id: int,
    target_question_id: int,
    data: FormQuestionDependencyCreate,
    service: FormQuestionDependencyService = Depends(
        get_form_question_dependency_service,
    ),
    user: User = CurrentUser,
):
    try:
        dependency = await service.create(
            form_id=form_id,
            section_id=section_id,
            target_question_id=target_question_id,
            user_id=user.id,
            data=data,
        )

        return ok(
            message="Dépendance créée avec succès.",
            data=FormQuestionDependencyResponse.model_validate(dependency),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.put(
    "/{dependency_id}",
    response_model=ApiResponse[FormQuestionDependencyResponse],
)
async def update_dependency(
    form_id: int,
    section_id: int,
    target_question_id: int,
    dependency_id: int,
    data: FormQuestionDependencyCreate,
    service: FormQuestionDependencyService = Depends(
        get_form_question_dependency_service,
    ),
    user: User = CurrentUser,
):
    try:
        dependency = await service.update(
            form_id=form_id,
            section_id=section_id,
            target_question_id=target_question_id,
            dependency_id=dependency_id,
            user_id=user.id,
            data=data,
        )

        return ok(
            message="Dépendance modifiée avec succès.",
            data=FormQuestionDependencyResponse.model_validate(
                dependency,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{dependency_id}",
    response_model=ApiResponse[None],
)
async def delete_dependency(
    form_id: int,
    section_id: int,
    target_question_id: int,
    dependency_id: int,
    service: FormQuestionDependencyService = Depends(
        get_form_question_dependency_service,
    ),
    user: User = CurrentUser,
):
    try:
        await service.delete(
            form_id=form_id,
            section_id=section_id,
            target_question_id=target_question_id,
            dependency_id=dependency_id,
            user_id=user.id,
        )

        return ok(
            message="Dépendance supprimée avec succès.",
            data=None,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
