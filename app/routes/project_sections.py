from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import (
    CurrentUser,
    get_project_section_service,
)
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.form_builder.project_section import (
    ProjectSectionCreate,
    ProjectSectionListResponse,
    ProjectSectionReorder,
    ProjectSectionResponse,
    ProjectSectionUpdate,
)
from app.services.form_builder.project_section import (
    ProjectSectionService,
)

router = APIRouter(
    prefix="/projects/{project_id}/sections",
    tags=["Project Sections"],
)


@router.post(
    "",
    response_model=ApiResponse[ProjectSectionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_project_section(
    project_id: int,
    data: ProjectSectionCreate,
    service: ProjectSectionService = Depends(
        get_project_section_service,
    ),
    user: User = CurrentUser,
):
    try:
        section = await service.create(
            project_id=project_id,
            user_id=user.id,
            data=data,
        )

        return ok(
            message="Section créée avec succès.",
            data=ProjectSectionResponse.model_validate(
                section,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("", response_model=ApiResponse[ProjectSectionListResponse])
async def list_project_sections(
    project_id: int,
    service: ProjectSectionService = Depends(
        get_project_section_service,
    ),
    user: User = CurrentUser,
):
    try:
        sections = await service.list(
            project_id=project_id,
            user_id=user.id,
        )

        return ok(
            message="Sections récupérées avec succès.",
            data=ProjectSectionListResponse(
                items=[
                    ProjectSectionResponse.model_validate(
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


@router.patch("/reorder", response_model=ApiResponse[ProjectSectionListResponse])
async def reorder_project_sections(
    project_id: int,
    data: ProjectSectionReorder,
    service: ProjectSectionService = Depends(
        get_project_section_service,
    ),
    user: User = CurrentUser,
):
    try:
        sections = await service.reorder(
            project_id=project_id,
            user_id=user.id,
            ordered_section_ids=data.ordered_section_ids,
        )

        return ok(
            message="Sections réordonnées avec succès.",
            data=ProjectSectionListResponse(
                items=[
                    ProjectSectionResponse.model_validate(
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


@router.patch("/{section_id}", response_model=ApiResponse[ProjectSectionResponse])
async def update_project_section(
    project_id: int,
    section_id: int,
    data: ProjectSectionUpdate,
    service: ProjectSectionService = Depends(
        get_project_section_service,
    ),
    user: User = CurrentUser,
):
    try:
        section = await service.update(
            project_id=project_id,
            section_id=section_id,
            user_id=user.id,
            data=data,
        )

        return ok(
            message="Section modifiée avec succès.",
            data=ProjectSectionResponse.model_validate(
                section,
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.delete("/{section_id}", response_model=ApiResponse[None])
async def delete_project_section(
    project_id: int,
    section_id: int,
    service: ProjectSectionService = Depends(
        get_project_section_service,
    ),
    user: User = CurrentUser,
):
    try:
        await service.delete(
            project_id=project_id,
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
