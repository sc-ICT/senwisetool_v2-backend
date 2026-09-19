from __future__ import annotations

from copy import deepcopy
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plugin import (
    Plugin,
    PluginResource,
    PluginResourceField,
)
from app.models.plugin_program import PluginProgram
from app.models.plugin_project_template import (
    PluginProjectTemplate,
)
from app.models.plugin_resource_relation import (
    PluginResourceRelation,
)
from app.models.user import User
from app.schemas.plugin_project_template import (
    PluginProjectTemplateCreate,
    PluginProjectTemplateUpdate,
)


class PluginProjectTemplateService:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    # ============================================================
    # INTERNAL
    # ============================================================

    async def _get_plugin(
        self,
        plugin_id: int,
    ) -> Plugin:
        result = await self.session.execute(
            select(Plugin).where(
                Plugin.id == plugin_id,
            )
        )

        plugin = result.scalar_one_or_none()

        if plugin is None:
            raise ValueError("Plugin introuvable.")

        return plugin

    async def _get_template(
        self,
        plugin_id: int,
        template_id: int,
    ) -> PluginProjectTemplate | None:
        result = await self.session.execute(
            select(PluginProjectTemplate).where(
                PluginProjectTemplate.id == template_id,
                PluginProjectTemplate.plugin_id == plugin_id,
            )
        )

        return result.scalar_one_or_none()

    async def _validate_creator(
        self,
        creator: User,
    ) -> int:
        """
        Vérifie que l'utilisateur courant possède bien un ID
        persistant avant toute création.
        """

        if creator.id is None:
            raise ValueError(
                "Impossible d'identifier l'administrateur " "qui crée le modèle de projet."
            )

        result = await self.session.execute(
            select(User.id).where(
                User.id == creator.id,
            )
        )

        user_id = result.scalar_one_or_none()

        if user_id is None:
            raise ValueError("L'administrateur créateur est introuvable.")

        return user_id

    async def _validate_resources(
        self,
        plugin_id: int,
        bindings: list[Any],
    ) -> None:
        """
        Vérifie :

        1. que toutes les ressources appartiennent au plugin ;
        2. que les configurations QUESTION sont cohérentes ;
        3. que les champs utilisés comme question existent ;
        4. que les relations utilisées dans la hiérarchie existent ;
        5. que les relations forment bien une chaîne depuis
           la ressource source.
        """

        if not bindings:
            return

        normalized_bindings: list[dict[str, Any]] = []

        for binding in bindings:
            if hasattr(binding, "model_dump"):
                item = binding.model_dump(
                    mode="json",
                )
            elif isinstance(binding, dict):
                item = binding
            else:
                raise ValueError("Une liaison de ressource est invalide.")

            normalized_bindings.append(item)

        resource_ids: set[int] = set()

        for item in normalized_bindings:
            resource_id = item.get(
                "resource_id",
            )

            if (
                not isinstance(
                    resource_id,
                    int,
                )
                or resource_id <= 0
            ):
                raise ValueError(
                    "Le resource_id d'une liaison de ressource " "doit être un entier positif."
                )

            resource_ids.add(
                resource_id,
            )

            # Une ressource QUESTION peut également utiliser une autre
            # ressource comme source dynamique de ses options de réponse.
            if item.get("usage") == "QUESTION":
                configuration = item.get("configuration")
                if isinstance(configuration, dict):
                    response = configuration.get("response")
                    if isinstance(response, dict) and response.get("options_source") == "RESOURCE":
                        resource_options = response.get("resource_options")
                        if isinstance(resource_options, dict):
                            options_resource_id = resource_options.get("resource_id")
                            if isinstance(options_resource_id, int) and options_resource_id > 0:
                                resource_ids.add(options_resource_id)

        # ------------------------------------------------------------------
        # RESOURCES
        # ------------------------------------------------------------------

        resources_result = await self.session.execute(
            select(PluginResource).where(
                PluginResource.plugin_id == plugin_id,
                PluginResource.id.in_(
                    resource_ids,
                ),
            )
        )

        resources = {resource.id: resource for resource in resources_result.scalars().all()}

        if set(resources.keys()) != resource_ids:
            raise ValueError("Une ou plusieurs ressources n'appartiennent " "pas à ce plugin.")

        # ------------------------------------------------------------------
        # FIELDS
        # ------------------------------------------------------------------

        fields_result = await self.session.execute(
            select(
                PluginResourceField,
            ).where(
                PluginResourceField.resource_id.in_(
                    resource_ids,
                ),
                PluginResourceField.is_active.is_(
                    True,
                ),
            )
        )

        fields_by_resource: dict[
            int,
            set[str],
        ] = {}

        for field in fields_result.scalars().all():
            fields_by_resource.setdefault(
                field.resource_id,
                set(),
            ).add(
                field.key,
            )

        # ------------------------------------------------------------------
        # RELATIONS USED BY QUESTION STRUCTURES
        # ------------------------------------------------------------------

        relation_ids: set[int] = set()

        for item in normalized_bindings:
            if item.get("usage") != "QUESTION":
                continue

            configuration = item.get(
                "configuration",
            )

            if not isinstance(
                configuration,
                dict,
            ):
                raise ValueError("La configuration d'une ressource QUESTION " "est invalide.")

            display = configuration.get(
                "display",
                {},
            )

            if not isinstance(
                display,
                dict,
            ):
                raise ValueError(
                    "La configuration display d'une ressource " "QUESTION est invalide."
                )

            question_field_key = display.get(
                "question_field_key",
            )

            resource_id = item["resource_id"]

            if (
                not isinstance(
                    question_field_key,
                    str,
                )
                or not question_field_key
            ):
                raise ValueError(
                    f"La ressource {resource_id} utilisée comme "
                    "QUESTION doit définir le champ contenant la question."
                )

            if question_field_key not in fields_by_resource.get(
                resource_id,
                set(),
            ):
                raise ValueError(
                    f"Le champ '{question_field_key}' "
                    f"n'existe pas dans la ressource {resource_id}."
                )

            optional_field_keys = [
                display.get(
                    "question_key_field_key",
                ),
                display.get(
                    "title_field_key",
                ),
            ]

            for field_key in optional_field_keys:
                if field_key is not None and field_key not in fields_by_resource.get(
                    resource_id,
                    set(),
                ):
                    raise ValueError(
                        f"Le champ '{field_key}' " f"n'existe pas dans la ressource {resource_id}."
                    )

            hierarchy = display.get(
                "hierarchy",
                [],
            )

            if not isinstance(
                hierarchy,
                list,
            ):
                raise ValueError("La hiérarchie d'une ressource QUESTION " "doit être une liste.")

            current_resource_id = resource_id

            expected_position = 0

            for level in hierarchy:
                if not isinstance(
                    level,
                    dict,
                ):
                    raise ValueError("Un niveau de hiérarchie est invalide.")

                position = level.get(
                    "position",
                )

                if position != expected_position:
                    raise ValueError(
                        "Les positions de la hiérarchie doivent " "être continues et commencer à 0."
                    )

                expected_position += 1

                relation_id = level.get(
                    "relation_id",
                )

                target_resource_id = level.get(
                    "resource_id",
                )

                source_field_key = level.get(
                    "source_field_key",
                )

                target_field_key = level.get(
                    "target_field_key",
                )

                if not isinstance(
                    relation_id,
                    int,
                ):
                    raise ValueError(
                        "Chaque niveau de hiérarchie doit " "posséder un relation_id valide."
                    )

                if not isinstance(
                    target_resource_id,
                    int,
                ):
                    raise ValueError(
                        "Chaque niveau de hiérarchie doit " "posséder un resource_id valide."
                    )

                if not isinstance(
                    source_field_key,
                    str,
                ):
                    raise ValueError(
                        "Chaque niveau de hiérarchie doit " "posséder un source_field_key valide."
                    )

                if not isinstance(
                    target_field_key,
                    str,
                ):
                    raise ValueError(
                        "Chaque niveau de hiérarchie doit " "posséder un target_field_key valide."
                    )

                relation_ids.add(
                    relation_id,
                )

                relation_result = await self.session.execute(
                    select(
                        PluginResourceRelation,
                    ).where(
                        PluginResourceRelation.id == relation_id,
                        PluginResourceRelation.is_active.is_(
                            True,
                        ),
                    )
                )

                relation = relation_result.scalar_one_or_none()

                if relation is None:
                    raise ValueError(
                        f"La relation {relation_id} " "utilisée par la hiérarchie est introuvable."
                    )

                # ----------------------------------------------------------
                # La relation doit partir de la ressource courante.
                # ----------------------------------------------------------

                if relation.source_resource_id != current_resource_id:
                    raise ValueError(
                        f"La relation {relation_id} ne peut pas être "
                        f"utilisée depuis la ressource {current_resource_id}."
                    )

                # ----------------------------------------------------------
                # Les champs déclarés dans la configuration doivent
                # correspondre à ceux de la relation réelle.
                # ----------------------------------------------------------

                if relation.source_field_key != source_field_key:
                    raise ValueError(
                        f"Le champ source de la relation {relation_id} "
                        "ne correspond pas à la configuration."
                    )

                if relation.target_field_key != target_field_key:
                    raise ValueError(
                        f"Le champ cible de la relation {relation_id} "
                        "ne correspond pas à la configuration."
                    )

                if relation.target_resource_id != target_resource_id:
                    raise ValueError(
                        f"La ressource cible de la relation {relation_id} "
                        "ne correspond pas à la configuration."
                    )

                # ----------------------------------------------------------
                # La ressource suivante devient la ressource courante
                # pour le niveau suivant.
                # ----------------------------------------------------------

                current_resource_id = relation.target_resource_id

        # ------------------------------------------------------------------
        # RESPONSE CONFIGURATION
        # ------------------------------------------------------------------

        for item in normalized_bindings:
            if item.get("usage") != "QUESTION":
                continue

            configuration = item.get(
                "configuration",
            )

            if not isinstance(
                configuration,
                dict,
            ):
                continue

            response = configuration.get(
                "response",
                {},
            )

            if not isinstance(
                response,
                dict,
            ):
                continue

            mode = response.get(
                "mode",
            )

            types = response.get(
                "types",
                [],
            )

            if (
                mode == "FIXED"
                and len(
                    types,
                )
                != 1
            ):
                raise ValueError(
                    "Une ressource QUESTION en mode FIXED "
                    "doit définir exactement un type de réponse."
                )

            if mode == "ALLOWED" and not types:
                raise ValueError(
                    "Une ressource QUESTION en mode ALLOWED "
                    "doit définir au moins un type de réponse."
                )

            if mode == "DEFERRED" and types:
                raise ValueError(
                    "Une ressource QUESTION en mode DEFERRED "
                    "ne doit pas définir de types de réponse."
                )

            options_source = response.get("options_source", "MANUAL")

            if options_source == "RESOURCE":
                resource_options = response.get("resource_options")

                if not isinstance(resource_options, dict):
                    raise ValueError(
                        "La source d'options RESOURCE doit définir "
                        "une ressource, un champ valeur et un champ libellé."
                    )

                options_resource_id = resource_options.get("resource_id")
                value_field_key = resource_options.get("value_field_key")
                label_field_key = resource_options.get("label_field_key")

                if options_resource_id not in resources:
                    raise ValueError(
                        "La ressource utilisée comme source des options "
                        "n'appartient pas à ce plugin."
                    )

                source_fields = fields_by_resource.get(options_resource_id, set())

                if value_field_key not in source_fields:
                    raise ValueError(
                        f"Le champ valeur '{value_field_key}' n'existe pas "
                        f"dans la ressource {options_resource_id}."
                    )

                if label_field_key not in source_fields:
                    raise ValueError(
                        f"Le champ libellé '{label_field_key}' n'existe pas "
                        f"dans la ressource {options_resource_id}."
                    )

            elif options_source not in (None, "MANUAL"):
                raise ValueError("La source des options de réponse est invalide.")

        # ------------------------------------------------------------------
        # STATISTICS
        # ------------------------------------------------------------------

        for item in normalized_bindings:
            if item.get("usage") != "QUESTION":
                continue

            configuration = item.get(
                "configuration",
            )

            if not isinstance(
                configuration,
                dict,
            ):
                continue

            statistics = configuration.get(
                "statistics",
                {},
            )

            if not isinstance(
                statistics,
                dict,
            ):
                continue

            if not statistics.get(
                "enabled",
                False,
            ):
                continue

            global_enabled = statistics.get(
                "global",
                True,
            )

            hierarchy_levels = statistics.get(
                "hierarchy_levels",
                [],
            )

            if not global_enabled and not hierarchy_levels:
                raise ValueError(
                    "Les statistiques doivent être activées "
                    "au moins au niveau global ou sur un niveau "
                    "de la hiérarchie."
                )

            measures = statistics.get(
                "measures",
                [],
            )

            if not measures:
                raise ValueError("Au moins un indicateur statistique " "doit être sélectionné.")

            hierarchy_length = len(
                configuration.get(
                    "display",
                    {},
                ).get(
                    "hierarchy",
                    [],
                )
            )

            for level in hierarchy_levels:
                if (
                    not isinstance(
                        level,
                        int,
                    )
                    or level < 0
                    or level >= hierarchy_length
                ):
                    raise ValueError(
                        "Un niveau statistique référence " "un niveau de hiérarchie inexistant."
                    )

    async def _validate_program(
        self,
        plugin_id: int,
        program_id: int | None,
    ) -> None:
        """
        Vérifie que le programme choisi appartient bien au plugin.

        None est autorisé : cela signifie que le modèle crée
        des projets indépendants de tout programme.
        """

        if program_id is None:
            return

        result = await self.session.execute(
            select(PluginProgram.id).where(
                PluginProgram.id == program_id,
                PluginProgram.plugin_id == plugin_id,
                PluginProgram.is_active.is_(True),
            )
        )

        if result.scalar_one_or_none() is None:
            raise ValueError(
                "Le programme sélectionné n'appartient pas " "à ce plugin ou est inactif."
            )

    # ============================================================
    # LIST
    # ============================================================

    async def list(
        self,
        *,
        plugin_id: int,
        include_inactive: bool = False,
    ) -> list[PluginProjectTemplate]:
        await self._get_plugin(plugin_id)

        statement = (
            select(PluginProjectTemplate)
            .where(
                PluginProjectTemplate.plugin_id == plugin_id,
            )
            .order_by(
                PluginProjectTemplate.position.asc(),
                PluginProjectTemplate.id.asc(),
            )
        )

        if not include_inactive:
            statement = statement.where(
                PluginProjectTemplate.is_active.is_(True),
            )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    # ============================================================
    # GET
    # ============================================================

    async def get(
        self,
        *,
        plugin_id: int,
        template_id: int,
    ) -> PluginProjectTemplate | None:
        await self._get_plugin(plugin_id)

        return await self._get_template(
            plugin_id=plugin_id,
            template_id=template_id,
        )

    # ============================================================
    # CREATE
    # ============================================================

    async def create(
        self,
        *,
        plugin_id: int,
        creator: User,
        data: PluginProjectTemplateCreate,
    ) -> PluginProjectTemplate:
        await self._get_plugin(plugin_id)

        created_by = await self._validate_creator(creator)

        await self._validate_resources(
            plugin_id,
            data.resource_bindings,
        )

        await self._validate_program(
            plugin_id,
            data.program_id,
        )

        key = data.key.strip()
        name = data.name.strip()
        project_type = data.project_type.strip()

        if not key:
            raise ValueError("La clé du modèle de projet est obligatoire.")

        if not name:
            raise ValueError("Le nom du modèle de projet est obligatoire.")

        if not project_type:
            raise ValueError("Le type du projet est obligatoire.")

        existing_result = await self.session.execute(
            select(PluginProjectTemplate.id).where(
                PluginProjectTemplate.plugin_id == plugin_id,
                PluginProjectTemplate.key == key,
            )
        )

        if existing_result.scalar_one_or_none() is not None:
            raise ValueError("Un modèle de projet avec cette clé " "existe déjà dans ce plugin.")

        item = PluginProjectTemplate(
            plugin_id=plugin_id,
            # ----------------------------------------------------
            # PROGRAMME
            # ----------------------------------------------------
            program_id=data.program_id,
            key=key,
            name=name,
            description=(data.description.strip() if data.description else None),
            project_type=project_type,
            icon=(data.icon.strip() if data.icon else None),
            position=data.position,
            is_active=True,
            allow_user_use=data.allow_user_use,
            allow_user_customization=(data.allow_user_customization),
            configuration=deepcopy(data.configuration),
            rules=deepcopy(data.rules),
            resource_bindings=deepcopy(data.resource_bindings),
            metrics=deepcopy(data.metrics),
            created_by=created_by,
        )

        self.session.add(item)

        await self.session.flush()

        await self.session.refresh(item)

        return item

    # ============================================================
    # UPDATE
    # ============================================================

    async def update(
        self,
        *,
        plugin_id: int,
        template_id: int,
        data: PluginProjectTemplateUpdate,
    ) -> PluginProjectTemplate:
        item = await self._get_template(
            plugin_id=plugin_id,
            template_id=template_id,
        )

        if item is None:
            raise ValueError("Modèle de projet introuvable.")

        payload = data.model_dump(
            exclude_unset=True,
        )

        # --------------------------------------------------------
        # KEY
        # --------------------------------------------------------

        if "key" in payload:
            key = payload["key"]

            if not isinstance(key, str):
                raise ValueError("La clé du modèle de projet est invalide.")

            key = key.strip()

            if not key:
                raise ValueError("La clé du modèle de projet est obligatoire.")

            duplicate_result = await self.session.execute(
                select(PluginProjectTemplate.id).where(
                    PluginProjectTemplate.plugin_id == plugin_id,
                    PluginProjectTemplate.key == key,
                    PluginProjectTemplate.id != template_id,
                )
            )

            if duplicate_result.scalar_one_or_none() is not None:
                raise ValueError("Un autre modèle de projet utilise déjà " "cette clé.")

            payload["key"] = key

        # --------------------------------------------------------
        # NAME
        # --------------------------------------------------------

        if "name" in payload:
            if not isinstance(
                payload["name"],
                str,
            ):
                raise ValueError("Le nom du modèle de projet est invalide.")

            payload["name"] = payload["name"].strip()

            if not payload["name"]:
                raise ValueError("Le nom du modèle de projet est obligatoire.")

        # --------------------------------------------------------
        # PROJECT TYPE
        # --------------------------------------------------------

        if "project_type" in payload:
            if not isinstance(
                payload["project_type"],
                str,
            ):
                raise ValueError("Le type du projet est invalide.")

            payload["project_type"] = payload["project_type"].strip()

            if not payload["project_type"]:
                raise ValueError("Le type du projet est obligatoire.")

        # --------------------------------------------------------
        # ICON
        # --------------------------------------------------------

        if "icon" in payload:
            icon = payload["icon"]

            if icon is not None:
                if not isinstance(
                    icon,
                    str,
                ):
                    raise ValueError("L'icône du projet est invalide.")

                payload["icon"] = icon.strip() or None

        # --------------------------------------------------------
        # DESCRIPTION
        # --------------------------------------------------------

        if "description" in payload:
            description = payload["description"]

            if description is not None:
                if not isinstance(
                    description,
                    str,
                ):
                    raise ValueError("La description du projet est invalide.")

                payload["description"] = description.strip() or None

        # --------------------------------------------------------
        # PROGRAM
        # --------------------------------------------------------

        if "program_id" in payload:
            await self._validate_program(
                plugin_id,
                payload["program_id"],
            )

        # --------------------------------------------------------
        # RESOURCES
        # --------------------------------------------------------

        if "resource_bindings" in payload:
            await self._validate_resources(
                plugin_id,
                payload["resource_bindings"] or [],
            )

        # --------------------------------------------------------
        # APPLY
        # --------------------------------------------------------

        for field, value in payload.items():
            setattr(
                item,
                field,
                deepcopy(value),
            )

        await self.session.flush()

        await self.session.refresh(item)

        return item

    # ============================================================
    # DELETE
    # ============================================================

    async def delete(
        self,
        *,
        plugin_id: int,
        template_id: int,
    ) -> None:
        item = await self._get_template(
            plugin_id=plugin_id,
            template_id=template_id,
        )

        if item is None:
            raise ValueError("Modèle de projet introuvable.")

        await self.session.delete(item)

        await self.session.flush()
