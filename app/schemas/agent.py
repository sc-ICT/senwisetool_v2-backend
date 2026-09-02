from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AgentRole, AgentStatus

# ============================================================================
# Création
# ============================================================================


class AgentCreate(BaseModel):
    full_name: str = Field(
        min_length=2,
        max_length=255,
    )

    role: AgentRole

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 2:
            raise ValueError("Le nom complet doit contenir au moins 2 caractères.")

        return value


class AgentBulkCreate(BaseModel):
    agents: list[AgentCreate] = Field(
        min_length=1,
        max_length=100,
    )


class AgentBulkDelete(BaseModel):
    agent_ids: list[int] = Field(
        min_length=1,
        max_length=100,
    )


# ============================================================================
# Modification
# ============================================================================


class AgentUpdate(BaseModel):
    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
    )

    role: AgentRole | None = None

    status: AgentStatus | None = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if len(value) < 2:
            raise ValueError("Le nom complet doit contenir au moins 2 caractères.")

        return value


# ============================================================================
# Réponse
# ============================================================================


class AgentResponse(BaseModel):
    id: int
    full_name: str
    role: AgentRole
    status: AgentStatus
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


class AgentListResponse(BaseModel):
    items: list[AgentResponse]
    count: int


class AgentBulkCreatedResponse(BaseModel):
    items: list[AgentResponse]
    count: int
