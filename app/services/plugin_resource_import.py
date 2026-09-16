from __future__ import annotations

from datetime import date, datetime
from typing import Any, BinaryIO

from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.enums import PluginFieldType, PluginResourceScope
from app.models.plugin import PluginResource
from app.models.plugin_resource_data import PluginResourceRecord
from app.schemas.plugin_resource import (
    PluginResourceCreate,
    PluginResourceFieldCreate,
    PluginResourceImportError,
    PluginResourceImportResponse,
    PluginResourceRelationCreate,
    PluginResourceUpdate,
    PluginResourceWorkbookImportResponse,
)
from app.services.plugin_resource import PluginResourceService
from app.services.plugin_resource_workbook import (
    ParsedWorkbookSheet,
    PluginResourceWorkbookParser,
    WorkbookImportError,
)


class PluginResourceImportService:

    MAX_ROWS = 10_000
    MAX_SHEETS = 100

    def __init__(
        self,
        resource_service: PluginResourceService,
    ) -> None:
        self.resource_service = resource_service
        self.workbook_parser = PluginResourceWorkbookParser()

    # ======================================================================
    # ANCIEN IMPORT — UNE RESSOURCE
    # ======================================================================

    async def import_excel(
        self,
        *,
        resource_id: int,
        file: BinaryIO,
        user_id: int,
        is_admin: bool,
    ) -> PluginResourceImportResponse:

        resource = await self.resource_service._get_resource_or_fail(
            resource_id=resource_id,
        )

        if not resource.fields:
            raise ValueError(
                "Impossible d'importer des données : " "la ressource ne possède encore aucun champ."
            )

        if resource.scope == PluginResourceScope.GLOBAL and not is_admin:
            raise ValueError(
                "Seul un administrateur peut importer " "des données dans une ressource GLOBAL."
            )

        try:
            workbook = load_workbook(
                file,
                read_only=True,
                data_only=True,
            )
        except Exception as exc:
            raise ValueError(
                "Impossible de lire le fichier Excel.",
            ) from exc

        try:
            if not workbook.worksheets:
                raise ValueError("Le fichier Excel ne contient aucune feuille.")

            worksheet = workbook.worksheets[0]

            rows = worksheet.iter_rows(
                values_only=True,
            )

            try:
                header_row = next(rows)
            except StopIteration as exc:
                raise ValueError("Le fichier Excel est vide.") from exc

            headers = self._normalize_headers(
                header_row,
            )

            schema = await self._get_import_schema(
                resource_id=resource_id,
                user_id=user_id,
                is_admin=is_admin,
            )

            fields = [field for field in schema.get("fields", []) if field.get("is_active", True)]

            field_map = {field["key"]: field for field in fields}

            header_errors = self._validate_headers(
                headers=headers,
                fields=fields,
            )

            if header_errors:
                return PluginResourceImportResponse(
                    resource_id=resource_id,
                    imported=0,
                    rejected=0,
                    errors=header_errors,
                )

            valid_rows: list[dict[str, Any]] = []
            errors: list[PluginResourceImportError] = []

            excel_row_number = 1

            for raw_row in rows:
                excel_row_number += 1

                if self._row_is_empty(raw_row):
                    continue

                if excel_row_number > self.MAX_ROWS + 1:
                    errors.append(
                        PluginResourceImportError(
                            row=excel_row_number,
                            message=(
                                f"Le fichier dépasse la limite de " f"{self.MAX_ROWS} lignes."
                            ),
                        )
                    )
                    break

                data: dict[str, Any] = {}

                for index, header in enumerate(headers):
                    if not header:
                        continue

                    value = raw_row[index] if index < len(raw_row) else None

                    value = self._normalize_cell_value(
                        value,
                    )

                    if value is None:
                        continue

                    data[header] = value

                try:
                    normalized = self.resource_service.validate_record(
                        schema=schema,
                        data=data,
                    )

                    await self.resource_service._validate_record_relations(
                        resource=resource,
                        data=normalized,
                        user_id=user_id,
                        owner_id=self._resolve_owner_id(
                            resource_scope=resource.scope,
                            user_id=user_id,
                            is_admin=is_admin,
                        ),
                        is_admin=is_admin,
                        pending_records=valid_rows,
                    )

                    valid_rows.append(
                        normalized,
                    )

                except ValueError as exc:
                    field_name = self._extract_field_from_error(
                        message=str(exc),
                        field_map=field_map,
                    )

                    errors.append(
                        PluginResourceImportError(
                            row=excel_row_number,
                            field=field_name,
                            message=str(exc),
                        )
                    )

            if errors:
                return PluginResourceImportResponse(
                    resource_id=resource_id,
                    imported=0,
                    rejected=len(valid_rows) + len(errors),
                    errors=errors,
                )

            owner_id = self._resolve_owner_id(
                resource_scope=resource.scope,
                user_id=user_id,
                is_admin=is_admin,
            )

            records: list[PluginResourceRecord] = []

            for normalized in valid_rows:
                record = PluginResourceRecord(
                    resource_id=resource_id,
                    user_id=owner_id,
                    data=normalized,
                    is_active=True,
                )

                self.resource_service.session.add(
                    record,
                )

                records.append(
                    record,
                )

            await self.resource_service.session.flush()

            return PluginResourceImportResponse(
                resource_id=resource_id,
                imported=len(records),
                rejected=0,
                errors=[],
            )

        finally:
            workbook.close()

    # ======================================================================
    # VALIDATION GLOBALE DES CLES DE RESSOURCES
    # ======================================================================

    async def _validate_workbook_resource_keys(
        self,
        *,
        plugin_id: int,
        sheets: list[ParsedWorkbookSheet],
    ) -> None:
        """
        Vérifie l'unicité des clés de ressources avant toute création.

        Règles :

        1. Chaque feuille doit définir exactement une ressource.
        2. Chaque ressource doit avoir une clé non vide.
        3. Deux feuilles du même workbook ne peuvent pas utiliser la même clé.
        4. Une clé du workbook ne peut pas déjà être utilisée par une ressource
        existante du même plugin.

        Cette validation est exécutée avant `_import_resources()` afin d'éviter
        de créer une partie du workbook puis de découvrir une collision plus loin.
        """

        existing_resources = await self.resource_service.list(
            plugin_id=plugin_id,
        )

        existing_keys = {str(resource.key).strip() for resource in existing_resources}

        workbook_keys: dict[str, str] = {}

        for sheet in sheets:

            # --------------------------------------------------------------
            # Une feuille doit avoir une définition RESOURCE.
            # --------------------------------------------------------------

            resource_rows = sheet.resource.rows

            if len(resource_rows) != 1:
                raise ValueError(
                    f"Feuille « {sheet.worksheet} » : "
                    "la section _RESOURCE_ doit contenir exactement "
                    "une ligne de données."
                )

            raw = resource_rows[0]

            key = str(raw.get("key") or "").strip()

            # --------------------------------------------------------------
            # Clé obligatoire.
            # --------------------------------------------------------------

            if not key:
                raise ValueError(
                    f"Feuille « {sheet.worksheet} » : " "la clé de la ressource est obligatoire."
                )

            # --------------------------------------------------------------
            # Collision avec une autre feuille du même workbook.
            # --------------------------------------------------------------

            previous_sheet = workbook_keys.get(
                key,
            )

            if previous_sheet is not None:
                raise ValueError(
                    f"Clé de ressource dupliquée dans le fichier Excel : "
                    f"« {key} ». "
                    f"Elle est utilisée dans les feuilles "
                    f"« {previous_sheet} » et "
                    f"« {sheet.worksheet} »."
                )

            workbook_keys[key] = sheet.worksheet

            # --------------------------------------------------------------
            # Collision avec une ressource déjà présente en BD.
            # --------------------------------------------------------------

            if key in existing_keys:
                raise ValueError(
                    f"La clé de ressource « {key} » est déjà utilisée "
                    "par une ressource existante de ce plugin."
                )

    # ======================================================================
    # VALIDATION GLOBALE DES RELATIONS
    # ======================================================================

    async def _validate_workbook_relations(
        self,
        *,
        sheets: list[ParsedWorkbookSheet],
        resource_map: dict[str, Any],
    ) -> None:

        for sheet in sheets:

            if len(sheet.resource.rows) != 1:
                raise ValueError(
                    f"Feuille « {sheet.worksheet} » : "
                    "la section _RESOURCE_ doit contenir exactement "
                    "une ligne de données."
                )

            source_key = str(
                sheet.resource.rows[0].get("key") or "",
            ).strip()

            source_resource = resource_map.get(
                source_key,
            )

            if source_resource is None:
                raise ValueError(
                    f"Feuille « {sheet.worksheet} » : "
                    f"la ressource « {source_key} » n'existe pas."
                )

            # ==============================================================
            # RELATION FACULTATIVE
            #
            # Une section RELATION vide est parfaitement valide.
            # ==============================================================

            if not sheet.relation.rows:
                continue

            # ==============================================================
            # Index des champs SOURCE
            # ==============================================================

            source_fields = {
                str(field.key).strip(): field for field in source_resource.fields if field.is_active
            }

            for row_index, row in enumerate(
                sheet.relation.rows,
                start=1,
            ):

                source_field_key = str(
                    row.get("source_field_key") or "",
                ).strip()

                target_resource_key = str(
                    row.get("target_resource_key") or "",
                ).strip()

                target_field_key = str(
                    row.get("target_field_key") or "",
                ).strip()

                label_value = row.get(
                    "label",
                )

                is_active_value = row.get(
                    "is_active",
                    True,
                )

                # ==========================================================
                # LIGNE VIDE
                # ==========================================================

                if (
                    not source_field_key
                    and not target_resource_key
                    and not target_field_key
                    and label_value is None
                ):
                    continue

                # ==========================================================
                # CHAMPS OBLIGATOIRES
                # ==========================================================

                missing: list[str] = []

                if not source_field_key:
                    missing.append(
                        "source_field_key",
                    )

                if not target_resource_key:
                    missing.append(
                        "target_resource_key",
                    )

                if not target_field_key:
                    missing.append(
                        "target_field_key",
                    )

                if missing:
                    raise ValueError(
                        f"Feuille « {sheet.worksheet} », "
                        f"section RELATION, ligne {row_index} : "
                        "relation incomplète. "
                        f"Champs manquants : {', '.join(missing)}."
                    )

                # ==========================================================
                # SOURCE RESOURCE
                #
                # Elle correspond toujours à la RESOURCE de la feuille.
                # ==========================================================

                source_resource = resource_map.get(
                    source_key,
                )

                if source_resource is None:
                    raise ValueError(
                        f"Feuille « {sheet.worksheet} », "
                        f"section RELATION, ligne {row_index} : "
                        f"ressource source « {source_key} » introuvable."
                    )

                # ==========================================================
                # SOURCE FIELD
                # ==========================================================

                source_field = source_fields.get(
                    source_field_key,
                )

                if source_field is None:

                    available = ", ".join(
                        sorted(source_fields.keys()),
                    )

                    raise ValueError(
                        f"Feuille « {sheet.worksheet} », "
                        f"section RELATION, ligne {row_index} : "
                        f"le champ source « {source_field_key} » "
                        f"n'existe pas dans la ressource "
                        f"« {source_key} ». "
                        f"Champs disponibles : "
                        f"{available or 'aucun'}."
                    )

                # ==========================================================
                # TARGET RESOURCE
                #
                # resource_map contient :
                #
                # - les ressources déjà présentes en BD ;
                # - toutes les ressources provenant du workbook.
                #
                # Elles ont toutes été créées AVANT cette phase.
                # ==========================================================

                target_resource = resource_map.get(
                    target_resource_key,
                )

                if target_resource is None:
                    raise ValueError(
                        f"Feuille « {sheet.worksheet} », "
                        f"section RELATION, ligne {row_index} : "
                        f"la ressource cible « {target_resource_key} » "
                        "n'existe pas."
                    )

                # ==========================================================
                # SELF RELATION
                # ==========================================================

                if source_resource.id == target_resource.id:
                    raise ValueError(
                        f"Feuille « {sheet.worksheet} », "
                        f"section RELATION, ligne {row_index} : "
                        f"la ressource « {source_key} » "
                        "ne peut pas être liée à elle-même."
                    )

                # ==========================================================
                # TARGET FIELD
                # ==========================================================

                target_fields = {
                    str(field.key).strip(): field
                    for field in target_resource.fields
                    if field.is_active
                }

                target_field = target_fields.get(
                    target_field_key,
                )

                if target_field is None:

                    available = ", ".join(
                        sorted(target_fields.keys()),
                    )

                    raise ValueError(
                        f"Feuille « {sheet.worksheet} », "
                        f"section RELATION, ligne {row_index} : "
                        f"le champ cible « {target_field_key} » "
                        f"n'existe pas dans la ressource "
                        f"« {target_resource_key} ». "
                        f"Champs disponibles : "
                        f"{available or 'aucun'}."
                    )

                # ==========================================================
                # TYPE SOURCE / TARGET
                # ==========================================================

                source_type = (
                    source_field.field_type.value
                    if hasattr(
                        source_field.field_type,
                        "value",
                    )
                    else source_field.field_type
                )

                target_type = (
                    target_field.field_type.value
                    if hasattr(
                        target_field.field_type,
                        "value",
                    )
                    else target_field.field_type
                )

                if source_type != target_type:
                    raise ValueError(
                        f"Feuille « {sheet.worksheet} », "
                        f"section RELATION, ligne {row_index} : "
                        "les types des champs source et cible "
                        "doivent être identiques. "
                        f"Source={source_type}, "
                        f"cible={target_type}."
                    )

                # ==========================================================
                # CHAMPS CHOICE INTERDITS
                # ==========================================================

                if source_type in {
                    "SINGLE_CHOICE",
                    "MULTIPLE_CHOICE",
                }:
                    raise ValueError(
                        f"Feuille « {sheet.worksheet} », "
                        f"section RELATION, ligne {row_index} : "
                        "les champs de type choix ne peuvent pas "
                        "être utilisés comme clé de relation."
                    )

    # ======================================================================
    # RESOURCES
    # ======================================================================

    async def _import_resources(
        self,
        *,
        plugin_id: int,
        sheets: list[ParsedWorkbookSheet],
    ) -> dict[str, Any]:

        resource_map: dict[str, Any] = {}

        created = 0

        for sheet in sheets:

            rows = sheet.resource.rows

            if len(rows) != 1:
                raise ValueError(
                    f"Feuille « {sheet.worksheet} » : "
                    "la section _RESOURCE_ doit contenir exactement "
                    "une ligne de données."
                )

            raw = rows[0]

            data = self._resource_create_from_row(
                raw,
            )

            key = data.key.strip()

            if not key:
                raise ValueError(
                    f"Feuille « {sheet.worksheet} » : " "la clé de la ressource est obligatoire."
                )

            # --------------------------------------------------------------
            # Sécurité supplémentaire.
            #
            # Normalement cette situation a déjà été détectée par
            # `_validate_workbook_resource_keys()`.
            # --------------------------------------------------------------

            if key in resource_map:
                raise ValueError(f"Clé de ressource dupliquée : « {key} ».")

            # --------------------------------------------------------------
            # Aucune ressource existante ne doit être réutilisée ici.
            #
            # Toutes les clés ont déjà été vérifiées avant cette phase.
            # --------------------------------------------------------------

            resource = await self.resource_service.create(
                plugin_id=plugin_id,
                data=data,
            )

            resource_map[key] = resource

            created += 1

        resource_map["_created"] = created
        resource_map["_updated"] = 0
        resource_map["_schemas_created"] = 0
        resource_map["_schemas_updated"] = 0

        return resource_map

    @staticmethod
    def _resource_create_from_row(
        row: dict[str, Any],
    ) -> PluginResourceCreate:

        return PluginResourceCreate(
            key=str(row.get("key") or "").strip(),
            name=str(row.get("name") or "").strip(),
            description=(
                str(row["description"]).strip() if row.get("description") is not None else None
            ),
            scope=PluginResourceScope(str(row.get("scope") or "").strip().upper()),
            allow_user_schema_override=(
                PluginResourceWorkbookParser.parse_boolean(
                    row.get("user_schema_customization", False),
                    field_name="user_schema_customization",
                )
            ),
            position=int(row.get("position") or 0),
            icon=(str(row["icon"]).strip() if row.get("icon") is not None else None),
            is_active=(
                PluginResourceWorkbookParser.parse_boolean(
                    row.get("is_active", True),
                    field_name="is_active",
                )
            ),
            fields=[],
        )

    async def _reload_resource_map(
        self,
        *,
        plugin_id: int,
    ) -> dict[str, Any]:

        result = await self.resource_service.session.execute(
            select(PluginResource)
            .where(
                PluginResource.plugin_id == plugin_id,
            )
            .options(
                selectinload(
                    PluginResource.fields,
                ),
            )
            .execution_options(
                populate_existing=True,
            )
        )

        resources = list(
            result.scalars().unique().all(),
        )

        resource_map: dict[str, Any] = {}

        for resource in resources:
            key = str(
                resource.key or "",
            ).strip()

            if not key:
                continue

            resource_map[key] = resource

        return resource_map

    # ======================================================================
    # SCHEMAS
    # ======================================================================

    async def _import_schemas(
        self,
        *,
        sheets: list[ParsedWorkbookSheet],
        resource_map: dict[str, Any],
    ) -> None:

        from app.schemas.plugin_resource import (
            PluginResourceFieldUpdate,
        )

        for sheet in sheets:

            if len(sheet.resource.rows) != 1:
                raise ValueError(
                    f"Feuille « {sheet.worksheet} » : "
                    "la section _RESOURCE_ doit contenir exactement "
                    "une ligne de données."
                )

            resource_row = sheet.resource.rows[0]

            resource_key = str(
                resource_row.get("key") or "",
            ).strip()

            resource = resource_map.get(
                resource_key,
            )

            if resource is None:
                raise ValueError(
                    f"Feuille « {sheet.worksheet} » : " f"ressource « {resource_key} » introuvable."
                )

            # ==============================================================
            # IMPORTANT
            #
            # La ressource vient d'être créée lors de la phase précédente.
            # On construit une copie locale des champs actuellement connus.
            # ==============================================================

            existing_fields = {str(field.key).strip(): field for field in resource.fields}

            for row in sheet.schema.rows:

                field_data = self._field_create_from_row(
                    row,
                )

                field_key = str(
                    field_data.key or "",
                ).strip()

                if not field_key:
                    raise ValueError(
                        f"Feuille « {sheet.worksheet} », "
                        "section SCHEMA : "
                        "la clé du champ est obligatoire."
                    )

                # ==========================================================
                # DOUBLON DANS LE SCHEMA DU FICHIER
                # ==========================================================

                if field_key in existing_fields:
                    existing = existing_fields[field_key]

                    update_data = PluginResourceFieldUpdate(
                        key=field_data.key,
                        label=field_data.label,
                        description=field_data.description,
                        field_type=field_data.field_type,
                        required=field_data.required,
                        min_length=field_data.min_length,
                        max_length=field_data.max_length,
                        min_value=field_data.min_value,
                        max_value=field_data.max_value,
                        pattern=field_data.pattern,
                        options=field_data.options,
                        default_value=field_data.default_value,
                        position=field_data.position,
                        is_active=field_data.is_active,
                    )

                    await self.resource_service.update_field(
                        resource_id=resource.id,
                        field_id=existing.id,
                        data=update_data,
                    )

                    continue

                # ==========================================================
                # NOUVEAU CHAMP
                # ==========================================================

                await self.resource_service.add_field(
                    resource_id=resource.id,
                    data=field_data,
                )

                # ----------------------------------------------------------
                # IMPORTANT :
                #
                # Le champ existe maintenant en BD.
                # On l'ajoute à notre map locale pour que la même section
                # ne puisse pas créer deux fois la même clé.
                #
                # On n'a pas besoin de fabriquer ici un objet SQLAlchemy :
                # le prochain reload global remettra tout proprement.
                # ----------------------------------------------------------

                existing_fields[field_key] = True

    @staticmethod
    def _field_create_from_row(
        row: dict[str, Any],
    ) -> PluginResourceFieldCreate:

        options = PluginResourceWorkbookParser.parse_json(
            row.get("options"),
            field_name="options",
        )

        if options is None:
            options = []

        if not isinstance(
            options,
            list,
        ):
            raise ValueError("La colonne « options » doit contenir une liste JSON.")

        field_type_raw = row.get("field_type")
        field_type = (
            PluginFieldType(field_type_raw) if field_type_raw is not None else PluginFieldType.TEXT
        )

        return PluginResourceFieldCreate(
            key=str(row.get("key") or "").strip(),
            label=str(row.get("label") or "").strip(),
            description=(
                str(row["description"]).strip() if row.get("description") is not None else None
            ),
            field_type=field_type,
            required=PluginResourceWorkbookParser.parse_boolean(
                row.get("required", False),
                field_name="required",
            ),
            min_length=(int(row["min_length"]) if row.get("min_length") is not None else None),
            max_length=(int(row["max_length"]) if row.get("max_length") is not None else None),
            min_value=(float(row["min_value"]) if row.get("min_value") is not None else None),
            max_value=(float(row["max_value"]) if row.get("max_value") is not None else None),
            pattern=(str(row["pattern"]) if row.get("pattern") is not None else None),
            options=options,
            default_value=row.get("default_value"),
            position=int(row.get("position") or 0),
            is_active=PluginResourceWorkbookParser.parse_boolean(
                row.get("is_active", True),
                field_name="is_active",
            ),
        )

    # ======================================================================
    # RELATIONS
    # ======================================================================

    async def _import_relations(
        self,
        *,
        sheets: list[ParsedWorkbookSheet],
        resource_map: dict[str, Any],
    ) -> dict[str, int]:

        created = 0
        existing_count = 0

        # ==============================================================
        # IMPORTANT
        #
        # L'ordre des feuilles Excel est conservé.
        #
        # MAIS toutes les ressources ont déjà été créées avant cette phase.
        # ==============================================================

        for sheet in sheets:

            source_key = str(
                sheet.resource.rows[0].get("key") or "",
            ).strip()

            source_resource = resource_map.get(
                source_key,
            )

            if source_resource is None:
                raise ValueError(
                    f"Feuille « {sheet.worksheet} » : " f"ressource « {source_key} » introuvable."
                )

            # ==========================================================
            # RELATION FACULTATIVE
            # ==========================================================

            if not sheet.relation.rows:
                continue

            for row in sheet.relation.rows:

                source_field_key = str(
                    row.get("source_field_key") or "",
                ).strip()

                target_resource_key = str(
                    row.get("target_resource_key") or "",
                ).strip()

                target_field_key = str(
                    row.get("target_field_key") or "",
                ).strip()

                label_value = row.get(
                    "label",
                )

                is_active_value = row.get(
                    "is_active",
                    True,
                )

                # ----------------------------------------------------------
                # Ligne vide du template.
                # ----------------------------------------------------------

                if (
                    not source_field_key
                    and not target_resource_key
                    and not target_field_key
                    and label_value is None
                ):
                    continue

                target_resource = resource_map.get(
                    target_resource_key,
                )

                if target_resource is None:
                    raise ValueError(
                        f"Feuille « {sheet.worksheet} » : "
                        f"ressource cible « {target_resource_key} » "
                        "introuvable."
                    )

                existing = await self._find_relation(
                    source_resource_id=source_resource.id,
                    source_field_key=source_field_key,
                    target_resource_id=target_resource.id,
                    target_field_key=target_field_key,
                )

                if existing is not None:

                    existing.label = str(label_value).strip() if label_value is not None else None

                    existing.is_active = PluginResourceWorkbookParser.parse_boolean(
                        is_active_value,
                        field_name="is_active",
                    )

                    existing_count += 1

                    continue

                relation_data = PluginResourceRelationCreate(
                    source_field_key=source_field_key,
                    target_resource_id=target_resource.id,
                    target_field_key=target_field_key,
                    label=(str(label_value).strip() if label_value is not None else None),
                    is_active=(
                        PluginResourceWorkbookParser.parse_boolean(
                            is_active_value,
                            field_name="is_active",
                        )
                    ),
                )

                await self.resource_service.create_relation(
                    resource_id=source_resource.id,
                    data=relation_data,
                )

                created += 1

        return {
            "created": created,
            "existing": existing_count,
        }

    async def _find_relation(
        self,
        *,
        source_resource_id: int,
        source_field_key: str,
        target_resource_id: int,
        target_field_key: str,
    ):
        from sqlalchemy import select

        from app.models.plugin_resource_relation import (
            PluginResourceRelation,
        )

        result = await self.resource_service.session.execute(
            select(PluginResourceRelation).where(
                PluginResourceRelation.source_resource_id == source_resource_id,
                PluginResourceRelation.source_field_key == source_field_key,
                PluginResourceRelation.target_resource_id == target_resource_id,
                PluginResourceRelation.target_field_key == target_field_key,
            )
        )

        return result.scalar_one_or_none()

    # ======================================================================
    # DATA
    # ======================================================================

    async def _import_data(
        self,
        *,
        sheets: list[ParsedWorkbookSheet],
        resource_map: dict[str, Any],
        user_id: int,
        is_admin: bool,
    ) -> dict[str, int]:

        imported = 0

        # Les ressources cibles des relations doivent être chargées
        # avant les ressources qui les référencent.
        ordered_sheets = self._order_data_sheets(
            sheets=sheets,
            resource_map=resource_map,
        )

        for sheet in ordered_sheets:
            resource_key = str(sheet.resource.rows[0].get("key") or "").strip()

            resource = resource_map.get(
                resource_key,
            )

            if resource is None:
                raise ValueError(
                    f"Feuille « {sheet.worksheet} » : " f"ressource « {resource_key} » introuvable."
                )

            for index, row in enumerate(
                sheet.data.rows,
                start=2,
            ):
                try:
                    from app.schemas.plugin_resource import (
                        PluginResourceRecordCreate,
                    )

                    await self.resource_service.create_record(
                        resource_id=resource.id,
                        data=PluginResourceRecordCreate(
                            data=row,
                            is_active=True,
                        ),
                        user_id=user_id,
                        is_admin=is_admin,
                    )

                    imported += 1

                except ValueError as exc:
                    raise ValueError(
                        f"Feuille « {sheet.worksheet} », "
                        f"section DATA, ligne {sheet.data.start_row + index - 1} : "
                        f"{exc}"
                    ) from exc

        return {
            "imported": imported,
        }

    def _order_data_sheets(
        self,
        *,
        sheets: list[ParsedWorkbookSheet],
        resource_map: dict[str, Any],
    ) -> list[ParsedWorkbookSheet]:

        resource_keys = {
            str(sheet.resource.rows[0].get("key") or "").strip(): sheet for sheet in sheets
        }

        dependencies: dict[str, set[str]] = {key: set() for key in resource_keys}

        for sheet in sheets:
            source_key = str(sheet.resource.rows[0].get("key") or "").strip()

            for relation in sheet.relation.rows:
                target_key = str(relation.get("target_resource_key") or "").strip()

                if target_key in resource_keys:
                    dependencies[source_key].add(
                        target_key,
                    )

        ordered: list[str] = []
        remaining = set(resource_keys)

        while remaining:
            ready = sorted(key for key in remaining if not (dependencies[key] & remaining))

            if not ready:
                # Cycle de relations.
                # Dans ce cas, le moteur actuel exige qu'une référence
                # existe déjà. On arrête explicitement plutôt que d'insérer
                # des données invalides.
                cycle = ", ".join(
                    sorted(remaining),
                )

                raise ValueError(
                    "Impossible de déterminer l'ordre d'import des données "
                    f"à cause d'une dépendance circulaire entre les ressources : "
                    f"{cycle}."
                )

            ordered.extend(
                ready,
            )

            remaining -= set(ready)

        return [resource_keys[key] for key in ordered]

    # ======================================================================
    # OLD IMPORT HELPERS
    # ======================================================================

    async def _get_import_schema(
        self,
        *,
        resource_id: int,
        user_id: int,
        is_admin: bool,
    ) -> dict[str, Any]:

        resource = await self.resource_service._get_resource_or_fail(
            resource_id=resource_id,
        )

        if resource.scope == PluginResourceScope.GLOBAL:
            return self.resource_service._resource_schema(
                resource,
            )

        if is_admin:
            return self.resource_service._resource_schema(
                resource,
            )

        return await self.resource_service.get_effective_schema(
            resource_id=resource_id,
            user_id=user_id,
        )

    @staticmethod
    def _normalize_headers(
        row: tuple[Any, ...],
    ) -> list[str]:

        headers: list[str] = []

        for value in row:
            if value is None:
                headers.append("")
                continue

            headers.append(
                str(value).strip(),
            )

        while headers and not headers[-1]:
            headers.pop()

        return headers

    @staticmethod
    def _validate_headers(
        *,
        headers: list[str],
        fields: list[dict[str, Any]],
    ) -> list[PluginResourceImportError]:

        errors: list[PluginResourceImportError] = []

        seen: set[str] = set()

        for header in headers:
            if not header:
                errors.append(
                    PluginResourceImportError(
                        row=1,
                        message="Une colonne Excel possède un en-tête vide.",
                    )
                )
                continue

            if header in seen:
                errors.append(
                    PluginResourceImportError(
                        row=1,
                        column=header,
                        field=header,
                        message=f"La colonne « {header} » est dupliquée.",
                    )
                )

            seen.add(header)

        field_map = {field["key"]: field for field in fields}

        for header in headers:
            if header and header not in field_map:
                errors.append(
                    PluginResourceImportError(
                        row=1,
                        column=header,
                        field=header,
                        message=(
                            f"La colonne « {header} » n'existe pas "
                            "dans le schema de la ressource."
                        ),
                    )
                )

        required_fields = {field["key"] for field in fields if field.get("required", False)}

        provided_fields = {header for header in headers if header}

        for field in sorted(
            required_fields - provided_fields,
        ):
            errors.append(
                PluginResourceImportError(
                    row=1,
                    field=field,
                    message=(
                        f"La colonne obligatoire « {field} » " "est absente du fichier Excel."
                    ),
                )
            )

        return errors

    @staticmethod
    def _normalize_cell_value(
        value: Any,
    ) -> Any:

        if value is None:
            return None

        if isinstance(
            value,
            str,
        ):
            value = value.strip()

            if not value:
                return None

            return value

        return value

    @staticmethod
    def _row_is_empty(
        row: tuple[Any, ...],
    ) -> bool:

        for value in row:
            if value is None:
                continue

            if (
                isinstance(
                    value,
                    str,
                )
                and not value.strip()
            ):
                continue

            return False

        return True

    @staticmethod
    def _resolve_owner_id(
        *,
        resource_scope: PluginResourceScope,
        user_id: int,
        is_admin: bool,
    ) -> int | None:

        if resource_scope == PluginResourceScope.GLOBAL:
            if not is_admin:
                raise ValueError("Seul un administrateur peut importer " "une ressource GLOBAL.")

            return None

        if is_admin:
            return None

        return user_id

    @staticmethod
    def _extract_field_from_error(
        *,
        message: str,
        field_map: dict[str, Any],
    ) -> str | None:

        for key in field_map:
            if f"« {field_map[key].get('label', key)} »" in message:
                return key

            if key in message:
                return key

        return None
