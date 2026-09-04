from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import UserRole, UserStatus
from app.schemas.agent import AgentResponse


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if not any(c.isdigit() for c in v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


# ─── Réponses ─────────────────────────────────────────────────────────────────


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    email: str
    name: str
    role: UserRole
    status: UserStatus
    email_verified: bool
    created_at: datetime
    updated_at: datetime


class LoginResponse(BaseModel):
    """Les tokens sont dans les cookies — on retourne seulement les infos utilisateur."""

    user: UserOut


class MobileLoginRequest(BaseModel):
    full_name: str = Field(
        min_length=2,
        max_length=255,
    )
    email: EmailStr
    password: str = Field(
        min_length=1,
    )


class MobileUserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr


class MobileLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

    agent: AgentResponse
    user: MobileUserResponse


class MobileMeResponse(BaseModel):
    agent: AgentResponse
    user: MobileUserResponse
