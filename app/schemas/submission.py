from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# ============================================================================
# ANSWER
# ============================================================================


class SubmissionAnswerCreate(BaseModel):
    question_id: int = Field(
        gt=0,
    )

    question_code: str = Field(
        min_length=1,
        max_length=100,
    )

    value: Any = None

    answered_at: datetime


# ============================================================================
# SUBMISSION
# ============================================================================


class SubmissionCreate(BaseModel):
    local_id: str = Field(
        min_length=1,
        max_length=255,
    )

    project_id: int = Field(
        gt=0,
    )

    form_id: int = Field(
        gt=0,
    )

    form_code: str = Field(
        min_length=1,
        max_length=100,
    )

    form_name: str = Field(
        min_length=1,
        max_length=255,
    )

    name: str = Field(
        min_length=1,
        max_length=255,
    )

    status: Literal["COMPLETED"]

    total_questions: int = Field(
        ge=0,
    )

    answered_questions: int = Field(
        ge=0,
    )

    answers: dict[str, SubmissionAnswerCreate]

    consent_accepted: bool

    consent_accepted_at: datetime | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    created_at: datetime

    started_at: datetime | None = None

    completed_at: datetime

    updated_at: datetime


# ============================================================================
# REQUEST
# ============================================================================


class SubmissionSyncRequest(BaseModel):
    submissions: list[SubmissionCreate] = Field(
        min_length=1,
        max_length=100,
    )


# ============================================================================
# RESPONSE
# ============================================================================


class SubmissionSyncItemResult(BaseModel):
    local_id: str
    server_id: int
    status: Literal["SYNCED", "ALREADY_SYNCED"]


class SubmissionSyncError(BaseModel):
    local_id: str
    message: str


class SubmissionSyncResponse(BaseModel):
    total: int
    synced: int
    already_synced: int
    failed: int

    items: list[SubmissionSyncItemResult]

    errors: list[SubmissionSyncError]
