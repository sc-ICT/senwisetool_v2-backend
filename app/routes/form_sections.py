from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    CurrentUser,
    get_form_section_service,
)
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.form_builder.form_section import (
    FormSectionCreate,
    FormSectionListResponse,
    FormSectionReorder,
    FormSectionResponse,
    FormSectionUpdate,
)
from app.services.form_builder.form_section import (
    FormSectionService,
)

router = APIRouter(
    prefix="/forms/{form_id}/sections",
    tags=["Form Sections"],
)


@router.post(
    "",
    response_model=ApiResponse[FormSectionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_form_section(
    form_id: int,
    data: FormSectionCreate,
    service: FormSectionService = Depends(
        get_form_section_service,
    ),
    user: User = CurrentUser,
):
    try:
        section = await service.create(
            form_id=form_id,
            user_id=user.id,
            data=data,
        )

        return ok(
            message="Section créée avec succès.",
            data=FormSectionResponse.model_validate(
                section,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("", response_model=ApiResponse[FormSectionListResponse])
async def list_form_sections(
    form_id: int,
    service: FormSectionService = Depends(
        get_form_section_service,
    ),
    user: User = CurrentUser,
):
    try:
        sections = await service.list(
            form_id=form_id,
            user_id=user.id,
        )

        return ok(
            message="Sections récupérées avec succès.",
            data=FormSectionListResponse(
                items=[
                    FormSectionResponse.model_validate(
                        section,
                    )
                    for section in sections
                ],
                count=len(sections),
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch("/reorder", response_model=ApiResponse[FormSectionListResponse])
async def reorder_form_sections(
    form_id: int,
    data: FormSectionReorder,
    service: FormSectionService = Depends(
        get_form_section_service,
    ),
    user: User = CurrentUser,
):
    try:
        sections = await service.reorder(
            form_id=form_id,
            user_id=user.id,
            ordered_section_ids=data.ordered_section_ids,
        )

        return ok(
            message="Sections réordonnées avec succès.",
            data=FormSectionListResponse(
                items=[
                    FormSectionResponse.model_validate(
                        section,
                    )
                    for section in sections
                ],
                count=len(sections),
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch("/{section_id}", response_model=ApiResponse[FormSectionResponse])
async def update_form_section(
    form_id: int,
    section_id: int,
    data: FormSectionUpdate,
    service: FormSectionService = Depends(
        get_form_section_service,
    ),
    user: User = CurrentUser,
):
    try:
        section = await service.update(
            form_id=form_id,
            section_id=section_id,
            user_id=user.id,
            data=data,
        )

        return ok(
            message="Section modifiée avec succès.",
            data=FormSectionResponse.model_validate(
                section,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete("/{section_id}", response_model=ApiResponse[None])
async def delete_form_section(
    form_id: int,
    section_id: int,
    service: FormSectionService = Depends(
        get_form_section_service,
    ),
    user: User = CurrentUser,
):
    try:
        await service.delete(
            form_id=form_id,
            section_id=section_id,
            user_id=user.id,
        )

        return ok(
            message="Section supprimée avec succès.",
            data=None,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
