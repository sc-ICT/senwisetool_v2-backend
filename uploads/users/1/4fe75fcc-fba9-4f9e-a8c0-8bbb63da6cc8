import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.enums import UserStatus
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
from app.schemas.common import ApiResponse, ok
from app.services.email import EmailService

logger = logging.getLogger(__name__)

MAX_LOGIN_ATTEMPTS = 5

# ─── Utilitaires mot de passe ─────────────────────────────────────────────────


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12),
    ).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ─── Utilitaires tokens JWT ───────────────────────────────────────────────────


def create_token(payload: dict, expires_delta: timedelta) -> str:
    data = payload.copy()
    data["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: int) -> str:
    return create_token(
        {"sub": str(user_id), "type": "access"},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int) -> str:
    return create_token(
        {"sub": str(user_id), "type": "refresh"},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


# ─── Utilitaires hash tokens opaques (reset, refresh stocké en base) ──────────
# SHA-256 et non bcrypt : les tokens sont déjà des valeurs aléatoires longues,
# bcrypt est inutile ici et limité à 72 octets.


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_token(plain: str, hashed: str) -> bool:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest() == hashed


# ─── Service ──────────────────────────────────────────────────────────────────


class AuthService:
    """
    Toutes les méthodes retournent soit ApiResponse, soit un tuple
    (ApiResponse, access_token, refresh_token) — le router gère les cookies.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Inscription ───────────────────────────────────────────────────────────

    async def register(self, data: RegisterRequest) -> ApiResponse[UserOut]:
        try:
            # Vérification email déjà utilisé
            result = await self.db.execute(select(User).where(User.email == data.email))
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Un compte avec cet e-mail existe déjà.",
                )

            verification_token = secrets.token_urlsafe(32)
            user = User(
                email=data.email,
                name=data.name,
                password=hash_password(data.password),
                email_verification_token=verification_token,
                email_verification_expires=datetime.now(timezone.utc) + timedelta(hours=24),
            )
            self.db.add(user)
            await self.db.flush()
            await self.db.refresh(user)

            # Envoi de l'email — si échec, le compte est rollbacké via get_db()
            try:
                await EmailService.send_verification(
                    email=data.email,
                    name=data.name,
                    token=verification_token,
                )
            except Exception as exc:
                logger.error(
                    "Échec envoi email de vérification pour %s : %s",
                    data.email,
                    exc,
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Compte créé mais l'envoi de l'e-mail a échoué. Réessayez ou contactez le support.",
                )

            return ok(
                "Compte créé. Vérifiez votre e-mail pour activer votre compte.",
                UserOut.model_validate(user),
            )

        except HTTPException:
            raise

        except IntegrityError:
            # Race condition : deux inscriptions simultanées avec le même email
            logger.warning("IntegrityError à l'inscription pour %s", data.email)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Un compte avec cet e-mail existe déjà.",
            )

        except Exception:
            logger.exception("Erreur inattendue lors de l'inscription pour %s", data.email)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Une erreur interne est survenue.",
            )

    # ── Vérification email ────────────────────────────────────────────────────

    async def verify_email(self, data: VerifyEmailRequest) -> ApiResponse[None]:
        try:
            result = await self.db.execute(
                select(User).where(User.email_verification_token == data.token)
            )
            user = result.scalar_one_or_none()

            if not user or not user.email_verification_expires:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token de vérification invalide.",
                )

            if user.email_verification_expires < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token de vérification expiré. Demandez un nouveau lien.",
                )

            if user.email_verified:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cet e-mail est déjà vérifié.",
                )

            user.email_verified = True
            user.email_verified_at = datetime.now(timezone.utc)
            user.email_verification_token = None
            user.email_verification_expires = None
            user.status = UserStatus.ACTIVE  # type: ignore[assignment]
            await self.db.flush()
            await self.db.refresh(user)

            return ok("E-mail vérifié. Vous pouvez maintenant vous connecter.")

        except HTTPException:
            raise

        except Exception:
            logger.exception("Erreur lors de la vérification email, token=%s", data.token)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Une erreur interne est survenue.",
            )

    # ── Connexion ─────────────────────────────────────────────────────────────

    async def login(self, data: LoginRequest) -> tuple[ApiResponse[LoginResponse], str, str]:
        """Retourne (response, access_token, refresh_token)."""
        try:
            result = await self.db.execute(select(User).where(User.email == data.email))
            user = result.scalar_one_or_none()

            # Message générique volontaire : ne pas révéler si l'email existe
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Identifiants invalides.",
                )

            if user.login_attempts >= MAX_LOGIN_ATTEMPTS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Compte bloqué après {MAX_LOGIN_ATTEMPTS} tentatives. "
                    "Réinitialisez votre mot de passe.",
                )

            if not verify_password(data.password, user.password):
                user.login_attempts += 1
                await self.db.flush()
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Identifiants invalides.",
                )

            if not user.email_verified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Vérifiez votre e-mail avant de vous connecter.",
                )

            if user.status.value != "ACTIVE":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Compte inactif ou suspendu. Contactez le support.",
                )

            access_token = create_access_token(user.id)
            refresh_token = create_refresh_token(user.id)

            user.refresh_token = hash_token(refresh_token)
            user.refresh_token_expires = datetime.now(timezone.utc) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
            user.login_attempts = 0
            user.last_login_at = datetime.now(timezone.utc)
            await self.db.flush()
            await self.db.refresh(user)

            response = ok("Connexion réussie", LoginResponse(user=UserOut.model_validate(user)))
            return response, access_token, refresh_token

        except HTTPException:
            raise

        except Exception:
            logger.exception("Erreur lors de la connexion pour %s", data.email)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Une erreur interne est survenue.",
            )

    # ── Renouvellement du token ───────────────────────────────────────────────

    async def refresh(self, refresh_token: str) -> tuple[ApiResponse[None], str, str]:
        """Retourne (response, new_access_token, new_refresh_token)."""
        try:
            payload = jwt.decode(
                refresh_token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
            )
            user_id: str | None = payload.get("sub")
            token_type: str | None = payload.get("type")

            if not user_id or token_type != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token invalide.",
                )

        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide ou expiré.",
            )

        try:
            result = await self.db.execute(select(User).where(User.id == int(user_id)))
            user = result.scalar_one_or_none()

            if not user or not user.refresh_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session expirée.",
                )

            if not verify_token(refresh_token, user.refresh_token):
                # Possible vol de token — on invalide la session
                logger.warning("Refresh token invalide pour user_id=%s (possible vol)", user_id)
                user.refresh_token = None
                user.refresh_token_expires = None
                await self.db.flush()
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token invalide.",
                )

            if user.refresh_token_expires and user.refresh_token_expires < datetime.now(
                timezone.utc
            ):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Session expirée.",
                )

            new_access = create_access_token(user.id)
            new_refresh = create_refresh_token(user.id)

            # Rotation du refresh token — l'ancien est immédiatement invalidé
            user.refresh_token = hash_token(new_refresh)
            user.refresh_token_expires = datetime.now(timezone.utc) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
            await self.db.flush()

            return ok("Token renouvelé"), new_access, new_refresh

        except HTTPException:
            raise

        except Exception:
            logger.exception("Erreur lors du refresh pour user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Une erreur interne est survenue.",
            )

    # ── Déconnexion ───────────────────────────────────────────────────────────

    async def logout(self, user: User) -> ApiResponse[None]:
        try:
            user.refresh_token = None
            user.refresh_token_expires = None
            await self.db.flush()
            return ok("Déconnexion réussie.")

        except Exception:
            logger.exception("Erreur lors de la déconnexion pour user_id=%s", user.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Une erreur interne est survenue.",
            )

    # ── Mot de passe oublié ───────────────────────────────────────────────────

    async def forgot_password(self, data: ForgotPasswordRequest) -> ApiResponse[None]:
        """
        Réponse identique que l'email existe ou non (sécurité anti-énumération).
        """
        _GENERIC = "Si cet e-mail est enregistré, un lien de réinitialisation a été envoyé."
        try:
            result = await self.db.execute(select(User).where(User.email == data.email))
            user = result.scalar_one_or_none()

            if not user:
                return ok(_GENERIC)

            token = secrets.token_urlsafe(32)
            user.reset_password_token = token
            user.reset_password_expires = datetime.now(timezone.utc) + timedelta(hours=1)
            await self.db.flush()

            try:
                await EmailService.send_reset_password(
                    email=data.email,
                    name=user.name,
                    token=token,
                )
            except Exception as exc:
                logger.error(
                    "Échec envoi email reset pour %s : %s",
                    data.email,
                    exc,
                    exc_info=True,
                )
                # On ne révèle pas l'échec (anti-énumération)

            return ok(_GENERIC)

        except HTTPException:
            raise

        except Exception:
            logger.exception("Erreur forgot_password pour %s", data.email)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Une erreur interne est survenue.",
            )

    # ── Réinitialisation du mot de passe ─────────────────────────────────────

    async def reset_password(self, data: ResetPasswordRequest) -> ApiResponse[None]:
        try:
            result = await self.db.execute(
                select(User).where(User.reset_password_token == data.token)
            )
            user = result.scalar_one_or_none()

            if not user or not user.reset_password_expires:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token de réinitialisation invalide.",
                )

            if user.reset_password_expires < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Token de réinitialisation expiré. Refaites la demande.",
                )

            user.password = hash_password(data.new_password)
            user.reset_password_token = None
            user.reset_password_expires = None
            user.login_attempts = 0
            # Invalider toutes les sessions actives
            user.refresh_token = None
            user.refresh_token_expires = None
            await self.db.flush()

            return ok("Mot de passe réinitialisé. Vous pouvez maintenant vous connecter.")

        except HTTPException:
            raise

        except Exception:
            logger.exception("Erreur reset_password, token=%s", data.token)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Une erreur interne est survenue.",
            )

    # ── Changement de mot de passe (utilisateur connecté) ────────────────────

    async def change_password(self, user: User, data: ChangePasswordRequest) -> ApiResponse[None]:
        try:
            if not verify_password(data.current_password, user.password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Mot de passe actuel incorrect.",
                )

            if data.current_password == data.new_password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Le nouveau mot de passe doit être différent de l'actuel.",
                )

            user.password = hash_password(data.new_password)
            # Invalider toutes les autres sessions (sauf la courante si souhaité)
            user.refresh_token = None
            user.refresh_token_expires = None
            await self.db.flush()
            await self.db.refresh(user)

            return ok("Mot de passe modifié avec succès.")

        except HTTPException:
            raise

        except Exception:
            logger.exception("Erreur change_password pour user_id=%s", user.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Une erreur interne est survenue.",
            )

    # ── Profil courant ────────────────────────────────────────────────────────

    async def me(self, user: User) -> ApiResponse[UserOut]:
        return ok("Profil récupéré.", UserOut.model_validate(user))
