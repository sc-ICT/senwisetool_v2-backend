from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal, get_db
from app.models.agent import Agent
from app.models.enums import AgentStatus
from app.models.user import User
from app.services.agent import AgentService
from app.services.archive import ArchiveService
from app.services.file_system import FileSystemService
from app.services.form_builder.form_definition import FormDefinitionService
from app.services.form_builder.form_import import FormImportService
from app.services.form_builder.form_question import FormQuestionService
from app.services.form_builder.form_question_dependency import (
    FormQuestionDependencyService,
)
from app.services.form_builder.form_section import FormSectionService
from app.services.form_builder.question_bank import (
    QuestionBankService,
)
from app.services.form_builder.question_group import QuestionGroupService
from app.services.mobile_project import MobileProjectService
from app.services.project import ProjectService
from app.services.project_agent_assignment import ProjectAgentAssignmentService
from app.services.storage.local import LocalStorageService
from app.services.submission import SubmissionService


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Session DB par requête."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    access_token: str | None = Cookie(default=None),
) -> User:
    """
    Lit le token depuis le cookie 'access_token'.
    Protège tous les endpoints qui en dépendent.
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Non authentifié",
        )

    try:
        payload = jwt.decode(
            access_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")

        if user_id is None or token_type != "access":
            raise HTTPException(status_code=401, detail="Token invalide")

    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")

    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Vérifiez votre adresse e-mail")

    if user.status.value != "ACTIVE":
        raise HTTPException(status_code=403, detail="Compte inactif ou suspendu")

    return user


CurrentUser = Depends(get_current_user)


mobile_bearer_scheme = HTTPBearer(auto_error=False)


def get_file_storage() -> LocalStorageService:
    return LocalStorageService(
        Path(settings.UPLOAD_DIR),
    )


def get_file_system_service(
    session: AsyncSession = Depends(get_db),
    storage: LocalStorageService = Depends(get_file_storage),
) -> FileSystemService:
    return FileSystemService(
        session=session,
        storage=storage,
    )


def get_archive_service(
    storage: LocalStorageService = Depends(
        get_file_storage,
    ),
) -> ArchiveService:
    return ArchiveService(
        storage=storage,
    )


def get_question_bank_service(
    session: AsyncSession = Depends(get_db),
) -> QuestionBankService:
    return QuestionBankService(
        session=session,
    )


def get_question_group_service(
    session: AsyncSession = Depends(get_db),
) -> QuestionGroupService:
    return QuestionGroupService(
        session=session,
    )


def get_form_definition_service(
    session: AsyncSession = Depends(get_db),
    file_system: FileSystemService = Depends(
        get_file_system_service,
    ),
) -> FormDefinitionService:
    return FormDefinitionService(
        session=session,
        file_system=file_system,
    )


def get_form_section_service(
    session: AsyncSession = Depends(get_db),
) -> FormSectionService:
    return FormSectionService(
        session=session,
    )


def get_form_question_service(
    session: AsyncSession = Depends(get_db),
) -> FormQuestionService:
    return FormQuestionService(
        session=session,
    )


def get_form_question_dependency_service(
    session: AsyncSession = Depends(get_db),
) -> FormQuestionDependencyService:
    return FormQuestionDependencyService(
        session,
    )


def get_form_import_service(
    session: AsyncSession = Depends(get_db),
) -> FormImportService:
    return FormImportService(
        session=session,
    )


def get_project_service(
    session: AsyncSession = Depends(get_db),
    file_system: FileSystemService = Depends(
        get_file_system_service,
    ),
) -> ProjectService:
    return ProjectService(
        session=session,
        file_system=file_system,
    )


def get_agent_service(
    session: AsyncSession = Depends(get_db),
) -> AgentService:
    return AgentService(
        session=session,
    )


def get_project_agent_assignment_service(
    session: AsyncSession = Depends(get_db),
    file_system: FileSystemService = Depends(
        get_file_system_service,
    ),
) -> ProjectAgentAssignmentService:
    return ProjectAgentAssignmentService(
        session=session,
        file_system=file_system,
    )


def get_mobile_project_service(
    session: AsyncSession = Depends(get_db),
    file_system_service: FileSystemService = Depends(
        get_file_system_service,
    ),
) -> MobileProjectService:
    return MobileProjectService(
        session=session,
        file_system_service=file_system_service,
    )


def get_submission_service(
    session: AsyncSession = Depends(get_db),
) -> SubmissionService:
    return SubmissionService(
        session=session,
    )


async def get_current_agent(
    credentials: HTTPAuthorizationCredentials | None = Depends(mobile_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    """
    Authentifie un agent via son JWT mobile.
    """

    # 1. Vérifier la présence du token
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification mobile requise",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # 2. Décoder et vérifier le JWT
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token mobile invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Vérifier le type de token
    if payload.get("type") != "mobile":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token mobile requis",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. Récupérer l'ID de l'agent
    subject = payload.get("sub")

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant agent absent du token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        agent_id = int(subject)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant agent invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 5. Récupérer l'agent
    result = await db.execute(select(Agent).where(Agent.id == agent_id))

    agent = result.scalar_one_or_none()

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent introuvable",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 6. Vérifier le statut de l'agent
    if agent.status != AgentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Le compte agent n'est pas actif",
        )

    # 7. Vérifier que le token est toujours celui enregistré
    if not agent.token or agent.token != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token mobile invalide ou révoqué",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return agent


CurrentAgent = Depends(get_current_agent)

# async def get_current_agent(
#     db: AsyncSession = Depends(get_db),
#     credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
# ) -> UserMobile:
#     """
#     Guard pour les endpoints mobiles.
#     Lit le token depuis le header Authorization: Bearer <token>
#     """
#     if not credentials:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Token manquant",
#             headers={"WWW-Authenticate": "Bearer"},
#         )

#     try:
#         payload = jwt.decode(
#             credentials.credentials,
#             settings.SECRET_KEY,
#             algorithms=[settings.ALGORITHM],
#         )
#         agent_id: str | None = payload.get("sub")
#         token_type: str | None = payload.get("type")

#         if agent_id is None or token_type != "mobile":
#             raise HTTPException(status_code=401, detail="Token invalide")

#     except JWTError:
#         raise HTTPException(status_code=401, detail="Token invalide ou expiré")

#     result = await db.execute(select(UserMobile).where(UserMobile.id == int(agent_id)))
#     agent = result.scalar_one_or_none()

#     if not agent:
#         raise HTTPException(status_code=401, detail="Agent introuvable")

#     if agent.status.value != "ACTIVE":
#         raise HTTPException(status_code=403, detail="Compte agent inactif")

#     return agent


# CurrentAgent = Depends(get_current_agent)
