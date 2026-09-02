from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.enums import AgentStatus
from app.schemas.agent import (
    AgentBulkCreate,
    AgentCreate,
    AgentUpdate,
)


class AgentService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    # ========================================================================
    # GET
    # ========================================================================

    async def get(
        self,
        *,
        agent_id: int,
        user_id: int,
    ) -> Agent | None:
        """
        Récupère un agent appartenant à l'utilisateur connecté.

        L'agent doit correspondre à la fois à :
        - son ID
        - l'utilisateur propriétaire
        """

        result = await self.session.execute(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.user_id == user_id,
            )
        )

        return result.scalar_one_or_none()

    # ========================================================================
    # LIST
    # ========================================================================

    async def list(
        self,
        *,
        user_id: int,
    ) -> list[Agent]:
        """
        Retourne tous les agents appartenant à l'utilisateur connecté.
        """

        result = await self.session.execute(
            select(Agent)
            .where(
                Agent.user_id == user_id,
            )
            .order_by(
                Agent.created_at.desc(),
            )
        )

        return list(result.scalars().all())

    # ========================================================================
    # CREATE
    # ========================================================================

    async def create(
        self,
        *,
        user_id: int,
        data: AgentCreate,
    ) -> Agent:
        """
        Crée un agent.

        Retourne :
            agent
        """

        full_name = data.full_name.strip()

        if not full_name:
            raise ValueError(
                "Le nom complet de l'agent est obligatoire.",
            )

        # --------------------------------------------------------------------
        # Création de l'agent
        # --------------------------------------------------------------------

        agent = Agent(
            full_name=full_name,
            role=data.role,
            status=AgentStatus.ACTIVE,
            user_id=user_id,
        )

        self.session.add(agent)

        # flush permet :
        # - d'envoyer l'INSERT à la DB
        # - de récupérer agent.id
        # - sans faire de commit
        #
        # Le commit reste géré par get_db().
        await self.session.flush()

        return agent

    # ========================================================================
    # CREATE MANY
    # ========================================================================

    async def create_many(
        self,
        *,
        user_id: int,
        data: AgentBulkCreate,
    ) -> list[Agent]:
        """
        Crée plusieurs agents appartenant au même utilisateur.

        Tous les agents sont créés dans la même transaction.

        Si une erreur survient avant le commit,
        get_db() effectuera automatiquement le rollback.
        """

        created_agents: list[Agent] = []

        for agent_data in data.agents:
            agent = await self.create(
                user_id=user_id,
                data=agent_data,
            )

            created_agents.append(agent)

        return created_agents

    # ========================================================================
    # UPDATE
    # ========================================================================

    async def update(
        self,
        *,
        agent_id: int,
        user_id: int,
        data: AgentUpdate,
    ) -> Agent:
        """
        Modifie un agent appartenant à l'utilisateur connecté.
        """

        agent = await self.get(
            agent_id=agent_id,
            user_id=user_id,
        )

        if agent is None:
            raise ValueError(
                "Agent introuvable.",
            )

        # --------------------------------------------------------------------
        # Nom
        # --------------------------------------------------------------------

        if data.full_name is not None:
            full_name = data.full_name.strip()

            if not full_name:
                raise ValueError(
                    "Le nom complet de l'agent est obligatoire.",
                )

            agent.full_name = full_name

        # --------------------------------------------------------------------
        # Rôle
        # --------------------------------------------------------------------

        if data.role is not None:
            agent.role = data.role

        # --------------------------------------------------------------------
        # Statut
        # --------------------------------------------------------------------

        if data.status is not None:
            agent.status = data.status

        # Persiste les modifications dans la session
        await self.session.flush()

        # Recharge les attributs générés/modifiés par la base
        # notamment updated_at
        await self.session.refresh(agent)

        return agent

    # ========================================================================
    # DELETE
    # ========================================================================

    async def delete(
        self,
        *,
        agent_id: int,
        user_id: int,
    ) -> None:
        """
        Supprime définitivement un agent appartenant
        à l'utilisateur connecté.
        """

        agent = await self.get(
            agent_id=agent_id,
            user_id=user_id,
        )

        if agent is None:
            raise ValueError(
                "Agent introuvable.",
            )

        await self.session.delete(agent)

        await self.session.flush()

    async def delete_many(
        self,
        *,
        user_id: int,
        agent_ids: list[int],
    ) -> None:
        """
        Supprime plusieurs agents appartenant à l'utilisateur connecté.

        Tous les IDs doivent correspondre à des agents appartenant
        à l'utilisateur courant.

        La suppression est effectuée dans la même transaction.
        """

        # --------------------------------------------------------------------
        # Suppression des doublons tout en conservant l'ordre
        # --------------------------------------------------------------------

        unique_agent_ids = list(dict.fromkeys(agent_ids))

        # --------------------------------------------------------------------
        # Récupération des agents appartenant à l'utilisateur courant
        # --------------------------------------------------------------------

        result = await self.session.execute(
            select(Agent).where(
                Agent.id.in_(unique_agent_ids),
                Agent.user_id == user_id,
            )
        )

        agents = list(result.scalars().all())

        # --------------------------------------------------------------------
        # Vérification
        # --------------------------------------------------------------------
        #
        # Si un seul ID ne correspond pas à un agent appartenant
        # à l'utilisateur courant, on refuse toute l'opération.
        #

        if len(agents) != len(unique_agent_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Un ou plusieurs agents sont introuvables.",
            )

        # --------------------------------------------------------------------
        # Suppression
        # --------------------------------------------------------------------

        for agent in agents:
            await self.session.delete(agent)

        # --------------------------------------------------------------------
        # Flush
        # --------------------------------------------------------------------
        #
        # Le commit reste géré par la session DB globale.
        #

        await self.session.flush()
