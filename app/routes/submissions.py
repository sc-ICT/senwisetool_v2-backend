from fastapi import APIRouter, Depends

from app.dependencies import (
    CurrentAgent,
    get_submission_service,
)
from app.models.agent import Agent
from app.schemas.common import ApiResponse
from app.schemas.submission import (
    SubmissionSyncRequest,
    SubmissionSyncResponse,
)
from app.services.submission import SubmissionService

router = APIRouter(
    prefix="/mobile/submissions",
    tags=["Mobile Submissions"],
)


@router.post(
    "/sync",
    response_model=ApiResponse[SubmissionSyncResponse],
)
async def sync_submissions(
    data: SubmissionSyncRequest,
    service: SubmissionService = Depends(
        get_submission_service,
    ),
    agent: Agent = CurrentAgent,
) -> ApiResponse[SubmissionSyncResponse]:

    items, errors = await service.sync_many(
        submissions=data.submissions,
        agent=agent,
    )

    synced = sum(1 for item in items if item.status == "SYNCED")

    already_synced = sum(1 for item in items if item.status == "ALREADY_SYNCED")

    failed = len(errors)

    return ApiResponse(
        success=True,
        message=("Synchronisation des enquêtes terminée."),
        data=SubmissionSyncResponse(
            total=len(data.submissions),
            synced=synced,
            already_synced=already_synced,
            failed=failed,
            items=items,
            errors=errors,
        ),
    )
