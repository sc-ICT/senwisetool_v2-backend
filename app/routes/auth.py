import time
from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import CurrentAgent, CurrentUser, get_db
from app.models.agent import Agent
from app.models.enums import AgentRole, AgentStatus, UserStatus
from app.models.user import User
from app.schemas.agent import AgentResponse
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MobileLoginRequest,
    MobileLoginResponse,
    MobileMeResponse,
    MobileUserResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UserOut,
    VerifyEmailRequest,
)
from app.schemas.common import ApiResponse
from app.services.auth import AuthService, create_mobile_token, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])

# Durées des cookies
ACCESS_COOKIE_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Injecte les tokens dans des cookies HttpOnly sécurisés."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_COOKIE_MAX_AGE,
        httponly=True,  # inaccessible au JavaScript
        secure=settings.is_production,  # HTTPS uniquement en production
        samesite="lax",  # protection CSRF
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/auth/refresh",  # limité à l'endpoint refresh uniquement
    )
    # Cookie NON-httpOnly : ne contient QUE la date d'expiration de l'access
    # token (un timestamp epoch, aucune donnée sensible). Il permet au client
    # de programmer un refresh proactif avant expiration, sans jamais avoir
    # besoin de lire ou décoder le token lui-même (qui reste httpOnly).
    access_expires_at = int(time.time()) + ACCESS_COOKIE_MAX_AGE
    response.set_cookie(
        key="access_token_expires_at",
        value=str(access_expires_at),
        max_age=ACCESS_COOKIE_MAX_AGE,
        httponly=False,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    """Supprime les cookies d'authentification."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/auth/refresh")


@router.post("/register", response_model=ApiResponse[UserOut], status_code=201)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Créer un compte administrateur."""
    return await AuthService(db).register(data)


@router.post("/verify-email", response_model=ApiResponse[None])
async def verify_email(data: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """Vérifier l'adresse e-mail via le token reçu."""
    return await AuthService(db).verify_email(data)


@router.post("/login", response_model=ApiResponse[LoginResponse])
async def login(
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Se connecter.
    Les tokens sont injectés dans des cookies HttpOnly — jamais exposés au JavaScript.
    """
    result, access_token, refresh_token = await AuthService(db).login(data)
    set_auth_cookies(response, access_token, refresh_token)
    return result


@router.post("/refresh", response_model=ApiResponse[None])
async def refresh(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str | None = Cookie(default=None),
):
    """Renouveler l'access token via le cookie refresh_token."""
    if not refresh_token:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Refresh token manquant")

    result, new_access, new_refresh = await AuthService(db).refresh(refresh_token)
    set_auth_cookies(response, new_access, new_refresh)
    return result


@router.post("/logout", response_model=ApiResponse[None])
async def logout(
    response: Response,
    user: User = CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Se déconnecter — supprime les cookies."""
    result = await AuthService(db).logout(user)
    clear_auth_cookies(response)
    return result


@router.get("/me", response_model=ApiResponse[UserOut])
async def me(user: User = CurrentUser, db: AsyncSession = Depends(get_db)):
    """Récupérer le profil de l'utilisateur connecté."""
    return await AuthService(db).me(user)


@router.post("/forgot-password", response_model=ApiResponse[None])
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Demander un lien de réinitialisation de mot de passe."""
    return await AuthService(db).forgot_password(data)


@router.post("/reset-password", response_model=ApiResponse[None])
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Réinitialiser le mot de passe."""
    return await AuthService(db).reset_password(data)


@router.patch("/change-password", response_model=ApiResponse[None])
async def change_password(
    data: ChangePasswordRequest,
    user: User = CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Changer son mot de passe."""
    return await AuthService(db).change_password(user, data)


# Mobile login endpoint
@router.post(
    "/mobile/login",
    response_model=MobileLoginResponse,
)
async def mobile_login(
    data: MobileLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    # 1. Rechercher le User par email
    result = await db.execute(select(User).where(User.email == data.email))

    user = result.scalar_one_or_none()
    print(f"===== password reçu : {data} ========")

    # 2. Vérifier que le User existe
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    # 3. Vérifier le statut du User
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Le compte utilisateur n'est pas actif",
        )

    # 4. Vérifier le mot de passe
    if not verify_password(
        data.password,
        user.password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    # 5. Rechercher l'Agent appartenant à ce User
    result = await db.execute(
        select(Agent).where(
            Agent.user_id == user.id,
            Agent.full_name == data.full_name,
        )
    )

    agent = result.scalar_one_or_none()

    # 6. Créer l'Agent s'il n'existe pas
    if agent is None:
        agent = Agent(
            full_name=data.full_name,
            role=AgentRole.COLLECTOR,
            status=AgentStatus.ACTIVE,
            user_id=user.id,
        )

        db.add(agent)

        # Nécessaire pour obtenir agent.id
        await db.flush()

    # 7. Générer le nouveau JWT mobile
    token = create_mobile_token(agent.id)

    # 8. Remplacer l'ancien token
    agent.token = token

    await db.commit()

    # Recharger explicitement l'agent depuis la base.
    # Cela garantit que les champs générés/modifiés par PostgreSQL,
    # notamment updated_at, sont disponibles avant la sérialisation Pydantic.
    await db.refresh(agent)

    # 9. Retourner les informations nécessaires au mobile
    return MobileLoginResponse(
        access_token=token,
        token_type="bearer",
        agent=AgentResponse.model_validate(agent),
        user=MobileUserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
        ),
    )


@router.get(
    "/mobile/me",
    response_model=MobileMeResponse,
)
async def mobile_me(
    agent: Agent = CurrentAgent,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == agent.user_id))

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur propriétaire de l'agent introuvable",
        )

    return MobileMeResponse(
        agent=AgentResponse.model_validate(agent),
        user=MobileUserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
        ),
    )


@router.post(
    "/mobile/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def mobile_logout(
    agent: Agent = CurrentAgent,
    db: AsyncSession = Depends(get_db),
):
    """
    Révoque le token mobile actuellement utilisé par l'agent.
    """

    agent.token = None

    await db.commit()

    return None


agent: Agent = CurrentAgent
