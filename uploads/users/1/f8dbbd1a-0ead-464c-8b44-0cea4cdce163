import time
from datetime import timedelta

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import CurrentUser, get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UserOut,
    VerifyEmailRequest,
)
from app.schemas.common import ApiResponse
from app.services.auth import AuthService

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
