from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import CurrentUser, get_agent_service, get_current_user
from app.models.user import User
from app.schemas.agent import (
    AgentBulkCreate,
    AgentBulkCreatedResponse,
    AgentBulkDelete,
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
)
from app.schemas.common import ApiResponse
from app.services.agent import AgentService

router = APIRouter(
    prefix="/agents",
    tags=["Agents"],
)


# =============================================================================
# LIST
# =============================================================================


@router.get(
    "",
    response_model=ApiResponse[AgentListResponse],
)
async def list_agents(
    current_user: User = CurrentUser,
    service: AgentService = Depends(get_agent_service),
) -> ApiResponse[AgentListResponse]:
    """
    Retourne la liste des agents appartenant à l'utilisateur connecté.
    """

    agents = await service.list(
        user_id=current_user.id,
    )

    return ApiResponse(
        success=True,
        message="Agents récupérés avec succès.",
        data=AgentListResponse(
            items=[AgentResponse.model_validate(agent) for agent in agents],
            count=len(agents),
        ),
    )


# =============================================================================
# GET ONE
# =============================================================================


@router.get(
    "/{agent_id}",
    response_model=ApiResponse[AgentResponse],
)
async def get_agent(
    agent_id: int,
    current_user: User = CurrentUser,
    service: AgentService = Depends(get_agent_service),
) -> ApiResponse[AgentResponse]:
    """
    Retourne un agent appartenant à l'utilisateur connecté.
    """

    agent = await service.get(
        agent_id=agent_id,
        user_id=current_user.id,
    )

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent introuvable.",
        )

    return ApiResponse(
        success=True,
        message="Agent récupéré avec succès.",
        data=AgentResponse.model_validate(agent),
    )


# =============================================================================
# CREATE ONE
# =============================================================================


@router.post(
    "",
    response_model=ApiResponse[AgentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_agent(
    data: AgentCreate,
    current_user: User = CurrentUser,
    service: AgentService = Depends(get_agent_service),
) -> ApiResponse[AgentResponse]:
    """
    Crée un agent appartenant à l'utilisateur connecté.
    """

    try:
        agent = await service.create(
            user_id=current_user.id,
            data=data,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ApiResponse(
        success=True,
        message="Agent créé avec succès.",
        data=AgentResponse.model_validate(agent),
    )


# =============================================================================
# CREATE MANY
# =============================================================================


@router.post(
    "/bulk",
    response_model=ApiResponse[AgentBulkCreatedResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_agents_bulk(
    data: AgentBulkCreate,
    current_user: User = CurrentUser,
    service: AgentService = Depends(get_agent_service),
) -> ApiResponse[AgentBulkCreatedResponse]:
    """
    Crée plusieurs agents appartenant à l'utilisateur connecté.

    Tous les agents sont créés dans la même transaction.
    """

    try:
        created_agents = await service.create_many(
            user_id=current_user.id,
            data=data,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    items = [AgentResponse.model_validate(agent) for agent in created_agents]

    return ApiResponse(
        success=True,
        message=f"{len(items)} agent(s) créé(s) avec succès.",
        data=AgentBulkCreatedResponse(
            items=items,
            count=len(items),
        ),
    )


# =============================================================================
# UPDATE
# =============================================================================


@router.patch(
    "/{agent_id}",
    response_model=ApiResponse[AgentResponse],
)
async def update_agent(
    agent_id: int,
    data: AgentUpdate,
    current_user: User = CurrentUser,
    service: AgentService = Depends(get_agent_service),
) -> ApiResponse[AgentResponse]:
    """
    Modifie un agent appartenant à l'utilisateur connecté.
    """

    try:
        agent = await service.update(
            agent_id=agent_id,
            user_id=current_user.id,
            data=data,
        )

    except ValueError as exc:
        if str(exc) == "Agent introuvable.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return ApiResponse(
        success=True,
        message="Agent modifié avec succès.",
        data=AgentResponse.model_validate(agent),
    )


# =============================================================================
# DELETE
# =============================================================================


@router.delete(
    "/bulk",
    response_model=ApiResponse[None],
)
async def delete_agents_bulk(
    data: AgentBulkDelete,
    dataService: AgentService = Depends(
        get_agent_service,
    ),
    current_user: User = Depends(
        get_current_user,
    ),
):
    await dataService.delete_many(
        user_id=current_user.id,
        agent_ids=data.agent_ids,
    )

    return ApiResponse(
        success=True,
        message="Agents supprimés avec succès.",
        data=None,
    )


@router.delete(
    "/{agent_id}",
    response_model=ApiResponse[None],
)
async def delete_agent(
    agent_id: int,
    current_user: User = CurrentUser,
    service: AgentService = Depends(get_agent_service),
) -> ApiResponse[None]:
    """
    Supprime définitivement un agent appartenant
    à l'utilisateur connecté.
    """

    try:
        await service.delete(
            agent_id=agent_id,
            user_id=current_user.id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return ApiResponse(
        success=True,
        message="Agent supprimé avec succès.",
        data=None,
    )
