from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)

from app.dependencies import (
    CurrentUser,
    get_form_import_service,
)
from app.models.user import User
from app.schemas.common import ApiResponse, ok
from app.schemas.form_builder.form_import import (
    FormImportResult,
)
from app.services.form_builder.form_import import (
    FormImportService,
)

router = APIRouter(
    prefix="/projects/{project_id}/form-import",
    tags=["Form Import"],
)


@router.post(
    "/validate",
    response_model=ApiResponse[FormImportResult],
)
async def validate_form_import(
    project_id: int,
    file: UploadFile = File(...),
    service: FormImportService = Depends(
        get_form_import_service,
    ),
    user: User = CurrentUser,
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est obligatoire.",
        )

    filename = file.filename.lower()

    if not filename.endswith((".xlsx", ".xlsm")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("Le fichier doit être un classeur Excel " "(.xlsx ou .xlsm)."),
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est vide.",
        )

    try:
        _, result = await service.build_plan(
            project_id=project_id,
            user_id=user.id,
            file_bytes=file_bytes,
        )

        return ok(
            message=result.message,
            data=result,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/execute",
    response_model=ApiResponse[FormImportResult],
)
async def execute_form_import(
    project_id: int,
    file: UploadFile = File(...),
    service: FormImportService = Depends(
        get_form_import_service,
    ),
    user: User = CurrentUser,
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est obligatoire.",
        )

    filename = file.filename.lower()

    if not filename.endswith(
        (".xlsx", ".xlsm"),
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("Le fichier doit être un classeur Excel " "(.xlsx ou .xlsm)."),
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le fichier est vide.",
        )

    try:

        plan, validation_result = await service.build_plan(
            project_id=project_id,
            user_id=user.id,
            file_bytes=file_bytes,
        )

        # --------------------------------------------------------
        # IMPORTANT :
        # aucune écriture si la validation échoue.
        # --------------------------------------------------------

        if plan is None:

            return ok(
                message=validation_result.message,
                data=validation_result,
            )

        # --------------------------------------------------------
        # Exécution
        # --------------------------------------------------------

        result = await service.execute_plan(
            plan=plan,
            project_id=project_id,
            user_id=user.id,
        )

        return ok(
            message=result.message,
            data=result,
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
