from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, BinaryIO

from openpyxl import load_workbook
from openpyxl.utils.cell import range_boundaries
from sqlalchemy import select

from app.models.enums import (
    PluginFieldType,
    PluginResourceScope,
)
from app.models.plugin_resource_relation import PluginResourceRelation
from app.schemas.plugin_resource import (
    PluginResourceCreate,
    PluginResourceFieldCreate,
    PluginResourceRecordCreate,
    PluginResourceRelationCreate,
)
from app.schemas.plugin_resource_definition_import import (
    PluginResourceDefinitionImportItem,
    PluginResourceDefinitionImportResponse,
)
from app.services.plugin_resource import PluginResourceService


class PluginResourceDefinitionImportError(ValueError):
    """
    Erreur de validation de l'import Excel des définitions
    de ressources et de leurs schemas.
    """


@dataclass(frozen=True)
class ParsedResourceDefinition:
    """
    Représentation interne entièrement validée d'une ressource
    et de son schema avant toute écriture en base.
    """

    worksheet: str

    resource_reference: str
    schema_reference: str

    resource_start_row: int
    resource_end_row: int
    resource_start_column: int
    resource_end_column: int

    schema_start_row: int
    schema_end_row: int
    schema_start_column: int
    schema_end_column: int

    data_reference: str | None
    data_start_row: int | None
    data_end_row: int | None
    data_start_column: int | None
    data_end_column: int | None

    data_rows: tuple[dict[str, Any], ...]

    relation_reference: str | None
    relations: tuple[dict[str, Any], ...]

    resource: PluginResourceCreate


class PluginResourceDefinitionImportService:
    """
    Import Excel des définitions de ressources + schemas.

    Format supporté :

        Ligne 1 :

            _RESOURCE_(A5:E6)
            _SCHEMA_(A10:M20)

        Section RESOURCE :

            name | key | description | scope | user_schema_customization
            ...

        Section SCHEMA :

            key | label | description | field_type | required | ...
            ...

    ---------------------------------------------------------------
    REGLE D'ATOMICITE
    ---------------------------------------------------------------

    La phase de parsing et de validation n'effectue AUCUNE écriture
    en base.

    Toutes les feuilles sont entièrement validées avant le premier
    appel à PluginResourceService.create().

    ---------------------------------------------------------------
    CE SERVICE NE GERE PAS
    ---------------------------------------------------------------

        - les relations ;
        - l'ancien import Workbook ;
        - les schemas utilisateur.

    Il gère :

        RESOURCE + SCHEMA + DATA

    DATA est optionnel. Lorsqu'il est présent, toutes les lignes DATA
    sont validées avant toute écriture en base.
    """

    MAX_SHEETS = 100

    # Une feuille = une ressource.
    MAX_RESOURCE_DATA_ROWS = 1

    RESOURCE_REFERENCE_PATTERN = re.compile(
        r"^_RESOURCE_\(\s*([A-Z]{1,3}\d+)\s*:\s*([A-Z]{1,3}\d+)\s*\)$",
        re.IGNORECASE,
    )

    SCHEMA_REFERENCE_PATTERN = re.compile(
        r"^_SCHEMA_\(\s*([A-Z]{1,3}\d+)\s*:\s*([A-Z]{1,3}\d+)\s*\)$",
        re.IGNORECASE,
    )

    DATA_REFERENCE_PATTERN = re.compile(
        r"^_DATA_\(\s*([A-Z]{1,3}\d+)\s*:\s*([A-Z]{1,3}\d+)\s*\)$",
        re.IGNORECASE,
    )

    RELATION_REFERENCE_PATTERN = re.compile(
        r"^_RELATION_\(\s*([A-Z]{1,3}\d+)\s*:\s*([A-Z]{1,3}\d+)\s*\)$",
        re.IGNORECASE,
    )

    # ========================================================================
    # RESOURCE HEADERS
    # ========================================================================

    RESOURCE_HEADER_ALIASES: dict[str, str] = {
        "name": "name",
        "key": "key",
        "description": "description",
        "scope": "scope",
        "user_schema_customization": "allow_user_schema_override",
        "allow_user_schema_override": "allow_user_schema_override",
        "position": "position",
        "icon": "icon",
        "is_active": "is_active",
    }

    RESOURCE_REQUIRED_HEADERS = {
        "name",
        "key",
        "scope",
    }

    # ========================================================================
    # SCHEMA HEADERS
    # ========================================================================

    SCHEMA_HEADER_ALIASES: dict[str, str] = {
        "key": "key",
        "label": "label",
        "description": "description",
        "field_type": "field_type",
        "required": "required",
        "min_length": "min_length",
        "max_length": "max_length",
        "min_value": "min_value",
        "max_value": "max_value",
        "pattern": "pattern",
        "options": "options",
        "default_value": "default_value",
        "position": "position",
        "is_active": "is_active",
    }

    SCHEMA_REQUIRED_HEADERS = {
        "key",
        "label",
        "field_type",
    }

    # ========================================================================
    # RELATION HEADERS
    # ========================================================================

    RELATION_HEADER_ALIASES: dict[str, str] = {
        "source_field_key": "source_field_key",
        "target_resource_key": "target_resource_key",
        "target_field_key": "target_field_key",
        "label": "label",
        "is_active": "is_active",
    }

    RELATION_REQUIRED_HEADERS = {
        "source_field_key",
        "target_resource_key",
        "target_field_key",
    }

    # ========================================================================
    # CONSTRUCTOR
    # ========================================================================

    def __init__(
        self,
        resource_service: PluginResourceService,
    ) -> None:
        self.resource_service = resource_service

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    async def import_resources(
        self,
        *,
        plugin_id: int,
        file: BinaryIO,
        admin_user_id: int,
    ) -> PluginResourceDefinitionImportResponse:
        """
        Importe toutes les ressources + schemas du workbook.

        IMPORTANT :

        Toute la validation est terminée avant la première écriture
        dans la base.
        """

        # --------------------------------------------------------------------
        # Plugin
        # --------------------------------------------------------------------

        plugin = await self.resource_service._get_plugin(
            plugin_id=plugin_id,
        )

        self.resource_service._ensure_plugin_editable(
            plugin,
        )

        # --------------------------------------------------------------------
        # Workbook
        # --------------------------------------------------------------------

        try:

            workbook = load_workbook(
                file,
                read_only=True,
                data_only=True,
            )

        except Exception as exc:

            raise PluginResourceDefinitionImportError(
                "Impossible de lire le fichier Excel. "
                "Vérifiez qu'il s'agit d'un fichier .xlsx valide.",
            ) from exc

        try:

            if not workbook.worksheets:

                raise PluginResourceDefinitionImportError(
                    "Le fichier Excel ne contient aucune feuille.",
                )

            if len(workbook.worksheets) > self.MAX_SHEETS:

                raise PluginResourceDefinitionImportError(
                    "Le fichier contient trop de feuilles. "
                    f"Maximum autorisé : {self.MAX_SHEETS}.",
                )

            # ----------------------------------------------------------------
            # Ressources existantes
            #
            # Lecture uniquement.
            # ----------------------------------------------------------------

            existing_resources = await self.resource_service.list(
                plugin_id=plugin_id,
            )

            existing_resource_keys = {
                str(resource.key).strip()
                for resource in existing_resources
                if resource.key is not None
            }

            existing_resources_by_key: dict[str, Any] = {
                str(resource.key).strip(): resource
                for resource in existing_resources
                if resource.key is not None
            }

            # ----------------------------------------------------------------
            # PRE-FLIGHT
            # ----------------------------------------------------------------

            parsed_resources: list[ParsedResourceDefinition] = []

            errors: list[str] = []

            workbook_resource_keys: dict[
                str,
                str,
            ] = {}

            for worksheet in workbook.worksheets:

                try:

                    parsed = self._parse_sheet(
                        worksheet,
                    )

                    parsed_resources.append(
                        parsed,
                    )

                    resource_key = parsed.resource.key.strip()

                    # --------------------------------------------------------
                    # Unicité dans le workbook
                    # --------------------------------------------------------

                    previous_sheet = workbook_resource_keys.get(
                        resource_key,
                    )

                    if previous_sheet is not None:

                        errors.append(
                            f"Feuille « {worksheet.title} » : "
                            f"la clé de ressource « {resource_key} » "
                            f"est déjà utilisée par la feuille "
                            f"« {previous_sheet} ».",
                        )

                    else:

                        workbook_resource_keys[resource_key] = worksheet.title

                    # --------------------------------------------------------
                    # Unicité avec la BD
                    # --------------------------------------------------------

                    if resource_key in existing_resource_keys:

                        errors.append(
                            f"Feuille « {worksheet.title} » : "
                            f"la clé de ressource « {resource_key} » "
                            "existe déjà dans ce plugin.",
                        )

                except PluginResourceDefinitionImportError as exc:

                    errors.append(
                        str(exc),
                    )
                    
            # ----------------------------------------------------------------
            # VALIDATION GLOBALE DES RELATIONS
            # ----------------------------------------------------------------

            if parsed_resources:
                relation_errors = await self._validate_relations_preflight(
                    plugin_id=plugin_id,
                    parsed_resources=parsed_resources,
                    existing_resources_by_key=existing_resources_by_key,
                )

                errors.extend(relation_errors)

            # ----------------------------------------------------------------
            # Il faut absolument avoir au moins une ressource valide.
            # ----------------------------------------------------------------

            if not parsed_resources and not errors:

                errors.append(
                    "Aucune ressource exploitable n'a été trouvée.",
                )

            # ----------------------------------------------------------------
            # AUCUNE ECRITURE SI UNE ERREUR EXISTE
            # ----------------------------------------------------------------

            if errors:

                raise PluginResourceDefinitionImportError(
                    self._format_errors(
                        errors,
                    ),
                )

            # =================================================================
            # PHASE D'ECRITURE
            # =================================================================

            created_resources: list[PluginResourceDefinitionImportItem] = []

            creation_order = self._get_resource_creation_order(
                parsed_resources=parsed_resources,
            )

            created_by_key: dict[str, Any] = {}

            for parsed in creation_order:

                resource = await self.resource_service.create(
                    plugin_id=plugin_id,
                    data=parsed.resource,
                )

                created_by_key[resource.key.strip()] = resource

                records_imported = 0

                for row in parsed.data_rows:
                    await self.resource_service.create_record(
                        resource_id=resource.id,
                        data=PluginResourceRecordCreate(
                            data=dict(row),
                            is_active=True,
                        ),
                        user_id=admin_user_id,
                        is_admin=True,
                    )
                    records_imported += 1

                created_resources.append(
                    PluginResourceDefinitionImportItem(
                        worksheet=parsed.worksheet,
                        resource_reference=parsed.resource_reference,
                        schema_reference=parsed.schema_reference,
                        data_reference=parsed.data_reference,
                        relation_reference=parsed.relation_reference,
                        resource_id=resource.id,
                        key=resource.key,
                        name=resource.name,
                        scope=resource.scope,
                        fields_count=len(parsed.resource.fields),
                        records_count=records_imported,
                        relations_count=len(parsed.relations),
                    ),
                )

            for parsed in creation_order:

                source_resource = created_by_key[parsed.resource.key.strip()]

                for relation in parsed.relations:
                    target_key = relation["target_resource_key"]

                    if target_key in created_by_key:
                        target_resource_id = created_by_key[target_key].id
                    else:
                        target_resource_id = existing_resources_by_key[target_key].id

                    await self.resource_service.create_relation(
                        resource_id=source_resource.id,
                        data=PluginResourceRelationCreate(
                            source_field_key=relation["source_field_key"],
                            target_resource_id=target_resource_id,
                            target_field_key=relation["target_field_key"],
                            label=relation["label"],
                            is_active=relation["is_active"],
                        ),
                    )

            return PluginResourceDefinitionImportResponse(
                plugin_id=plugin_id,
                sheets=len(parsed_resources),
                resources_created=len(created_resources),
                schemas_created=len(created_resources),
                fields_created=sum(len(parsed.resource.fields) for parsed in parsed_resources),
                records_imported=sum(len(parsed.data_rows) for parsed in parsed_resources),
                relations_created=sum(len(parsed.relations) for parsed in parsed_resources),
                resources=created_resources,
            )

        finally:

            workbook.close()

    # ========================================================================
    # PARSE SHEET
    # ========================================================================

    def _parse_sheet(
        self,
        worksheet,
    ) -> ParsedResourceDefinition:

        # --------------------------------------------------------------------
        # Les deux références doivent obligatoirement exister.
        # --------------------------------------------------------------------

        references = self._find_references(
            worksheet,
        )

        resource_reference = references["resource"]

        schema_reference = references["schema"]
        data_reference = references["data"]

        if resource_reference is None:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet.title} » : "
                "aucune référence _RESOURCE_(...) n'a été trouvée "
                "sur la première ligne.",
            )

        if schema_reference is None:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet.title} » : "
                "aucune référence _SCHEMA_(...) n'a été trouvée "
                "sur la première ligne.",
            )

        # --------------------------------------------------------------------
        # Bornes RESOURCE
        # --------------------------------------------------------------------

        resource_bounds = self._parse_reference_bounds(
            worksheet_name=worksheet.title,
            reference=resource_reference,
            reference_type="RESOURCE",
        )

        # --------------------------------------------------------------------
        # Bornes SCHEMA
        # --------------------------------------------------------------------

        schema_bounds = self._parse_reference_bounds(
            worksheet_name=worksheet.title,
            reference=schema_reference,
            reference_type="SCHEMA",
        )

        (
            resource_start_column,
            resource_start_row,
            resource_end_column,
            resource_end_row,
        ) = resource_bounds

        (
            schema_start_column,
            schema_start_row,
            schema_end_column,
            schema_end_row,
        ) = schema_bounds

        data_start_column = None
        data_start_row = None
        data_end_column = None
        data_end_row = None

        relation_start_column = None
        relation_start_row = None
        relation_end_column = None
        relation_end_row = None

        relation_reference = references["relation"]

        if relation_reference is not None:
            (
                relation_start_column,
                relation_start_row,
                relation_end_column,
                relation_end_row,
            ) = self._parse_reference_bounds(
                worksheet_name=worksheet.title,
                reference=relation_reference,
                reference_type="RELATION",
            )

        if data_reference is not None:
            (
                data_start_column,
                data_start_row,
                data_end_column,
                data_end_row,
            ) = self._parse_reference_bounds(
                worksheet_name=worksheet.title,
                reference=data_reference,
                reference_type="DATA",
            )

        # --------------------------------------------------------------------
        # Les plages ne doivent pas se chevaucher.
        # --------------------------------------------------------------------

        ranges = [
            (
                "RESOURCE",
                resource_start_row,
                resource_end_row,
                resource_start_column,
                resource_end_column,
            ),
            (
                "SCHEMA",
                schema_start_row,
                schema_end_row,
                schema_start_column,
                schema_end_column,
            ),
        ]

        if data_reference is not None:
            # ensure parsed bounds are present (typing: avoid Optional[int] in the tuple)
            assert (
                data_start_row is not None
                and data_end_row is not None
                and data_start_column is not None
                and data_end_column is not None
            )
            ranges.append(
                ("DATA", data_start_row, data_end_row, data_start_column, data_end_column)
            )

        if relation_reference is not None:
            assert (
                relation_start_row is not None
                and relation_end_row is not None
                and relation_start_column is not None
                and relation_end_column is not None
            )
            ranges.append(
                (
                    "RELATION",
                    relation_start_row,
                    relation_end_row,
                    relation_start_column,
                    relation_end_column,
                )
            )

        for index, (name_a, start_row_a, end_row_a, start_col_a, end_col_a) in enumerate(ranges):
            for name_b, start_row_b, end_row_b, start_col_b, end_col_b in ranges[index + 1 :]:
                if self._ranges_overlap(
                    start_row_a,
                    end_row_a,
                    start_col_a,
                    end_col_a,
                    start_row_b,
                    end_row_b,
                    start_col_b,
                    end_col_b,
                ):
                    raise PluginResourceDefinitionImportError(
                        f"Feuille « {worksheet.title} » : "
                        f"les plages {name_a} et {name_b} se chevauchent.",
                    )

        # --------------------------------------------------------------------
        # Extraction RESOURCE
        # --------------------------------------------------------------------

        resource_data = self._extract_range(
            worksheet=worksheet,
            start_row=resource_start_row,
            end_row=resource_end_row,
            start_column=resource_start_column,
            end_column=resource_end_column,
        )

        resource = self._parse_resource_section(
            worksheet_name=worksheet.title,
            values=resource_data,
        )

        # --------------------------------------------------------------------
        # Extraction SCHEMA
        # --------------------------------------------------------------------

        schema_data = self._extract_range(
            worksheet=worksheet,
            start_row=schema_start_row,
            end_row=schema_end_row,
            start_column=schema_start_column,
            end_column=schema_end_column,
        )

        fields = self._parse_schema_section(
            worksheet_name=worksheet.title,
            values=schema_data,
        )

        # --------------------------------------------------------------------
        # Extraction + validation DATA.
        # --------------------------------------------------------------------

        data_rows: tuple[dict[str, Any], ...] = ()

        if data_reference is not None:
            assert (
                data_start_row is not None
                and data_end_row is not None
                and data_start_column is not None
                and data_end_column is not None
            )

            data_section = self._extract_range(
                worksheet=worksheet,
                start_row=data_start_row,
                end_row=data_end_row,
                start_column=data_start_column,
                end_column=data_end_column,
            )

            data_rows = tuple(
                self._parse_data_section(
                    worksheet_name=worksheet.title,
                    values=data_section,
                    fields=fields,
                    first_row_number=data_start_row,
                )
            )

        # --------------------------------------------------------------------
        # Extraction RELATION (optionnelle).
        # --------------------------------------------------------------------

        relations: tuple[dict[str, Any], ...] = ()

        if relation_reference is not None:
            assert (
                relation_start_row is not None
                and relation_end_row is not None
                and relation_start_column is not None
                and relation_end_column is not None
            )

            relation_section = self._extract_range(
                worksheet=worksheet,
                start_row=relation_start_row,
                end_row=relation_end_row,
                start_column=relation_start_column,
                end_column=relation_end_column,
            )

            relations = tuple(
                self._parse_relation_section(
                    worksheet_name=worksheet.title,
                    values=relation_section,
                    fields=fields,
                )
            )

        # --------------------------------------------------------------------
        # Construction finale.
        # --------------------------------------------------------------------

        resource = resource.model_copy(
            update={
                "fields": fields,
            },
        )

        return ParsedResourceDefinition(
            worksheet=worksheet.title,
            resource_reference=resource_reference,
            schema_reference=schema_reference,
            resource_start_row=resource_start_row,
            resource_end_row=resource_end_row,
            resource_start_column=resource_start_column,
            resource_end_column=resource_end_column,
            schema_start_row=schema_start_row,
            schema_end_row=schema_end_row,
            schema_start_column=schema_start_column,
            schema_end_column=schema_end_column,
            data_reference=data_reference,
            data_start_row=data_start_row,
            data_end_row=data_end_row,
            data_start_column=data_start_column,
            data_end_column=data_end_column,
            data_rows=data_rows,
            relation_reference=relation_reference,
            relations=relations,
            resource=resource,
        )

    # ========================================================================
    # DATA SECTION
    # ========================================================================

    def _parse_data_section(
        self,
        *,
        worksheet_name: str,
        values: list[list[Any]],
        fields: list[PluginResourceFieldCreate],
        first_row_number: int,
    ) -> list[dict[str, Any]]:
        """
        Valide intégralement la section DATA sans écrire en base.

        La première ligne contient les clés des champs. Toutes les lignes
        suivantes sont validées par la même validation métier que
        create_record().
        """
        if len(values) < 1:
            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : " "la section DATA est vide.",
            )

        headers = self._normalize_data_headers(
            worksheet_name=worksheet_name,
            values=values[0],
        )

        active_fields = [field for field in fields if field.is_active]
        schema_keys = {field.key for field in active_fields}
        data_keys = set(headers)

        unknown = data_keys - schema_keys
        if unknown:
            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : "
                "la section DATA contient des champs inconnus : "
                f"{', '.join(sorted(unknown))}.",
            )

        missing = schema_keys - data_keys
        if missing:
            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : "
                "la section DATA ne contient pas tous les champs "
                f"actifs du schema : {', '.join(sorted(missing))}.",
            )

        schema = {
            "version": 1,
            "fields": [field.model_dump(mode="json") for field in fields],
        }

        validated_rows: list[dict[str, Any]] = []

        for offset, row in enumerate(values[1:], start=1):
            excel_row = first_row_number + offset

            if self._row_is_empty(row):
                continue

            raw_data: dict[str, Any] = {}

            for index, header in enumerate(headers):
                value = row[index] if index < len(row) else None
                raw_data[header] = self._normalize_data_value(value)

            try:
                normalized = self.resource_service.validate_record(
                    schema=schema,
                    data=raw_data,
                )
            except ValueError as exc:
                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} », " f"ligne DATA {excel_row} : {exc}",
                ) from exc

            validated_rows.append(normalized)

        return validated_rows

    def _normalize_data_headers(
        self,
        *,
        worksheet_name: str,
        values: list[Any],
    ) -> list[str]:
        headers: list[str] = []
        seen: set[str] = set()

        for value in values:
            if value is None or not str(value).strip():
                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} » : "
                    "la section DATA contient une colonne sans en-tête.",
                )

            header = str(value).strip()

            if header in seen:
                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} » : "
                    f"la colonne DATA « {header} » est dupliquée.",
                )

            seen.add(header)
            headers.append(header)

        if not headers:
            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : " "la section DATA ne contient aucun en-tête.",
            )

        return headers

    @staticmethod
    def _normalize_data_value(value: Any) -> Any:
        """
        Les types ne sont volontairement pas convertis ici.

        La validation métier existante reste l'autorité :
        NUMBER/DECIMAL acceptent les nombres Excel et les chaînes
        numériques, BOOLEAN accepte booléens et représentations textuelles,
        DATE/DATETIME acceptent les valeurs datetime/date d'Excel.
        """
        if isinstance(value, str):
            value = value.strip()
            return value or None

        return value

    # ========================================================================
    # RELATION SECTION
    # ========================================================================

    def _parse_relation_section(
        self,
        *,
        worksheet_name: str,
        values: list[list[Any]],
        fields: list[PluginResourceFieldCreate],
    ) -> list[dict[str, Any]]:
        if not values:
            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : la section RELATION est vide.",
            )

        headers = self._normalize_relation_headers(
            worksheet_name=worksheet_name,
            values=values[0],
        )

        field_keys = {field.key for field in fields if field.is_active}

        relations: list[dict[str, Any]] = []

        for offset, row in enumerate(values[1:], start=1):
            if self._row_is_empty(row):
                continue

            raw = {
                header: self._normalize_data_value(row[index] if index < len(row) else None)
                for index, header in enumerate(headers)
            }

            for required in self.RELATION_REQUIRED_HEADERS:
                if self._is_empty(raw.get(required)):
                    raise PluginResourceDefinitionImportError(
                        f"Feuille « {worksheet_name} », ligne RELATION "
                        f"{offset + 1} : « {required} » est obligatoire.",
                    )

            source_field_key = str(raw["source_field_key"]).strip()
            target_resource_key = str(raw["target_resource_key"]).strip()
            target_field_key = str(raw["target_field_key"]).strip()

            if source_field_key not in field_keys:
                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} », ligne RELATION "
                    f"{offset + 1} : le champ source « {source_field_key} » "
                    "n'existe pas dans le schema.",
                )

            relations.append(
                {
                    "source_field_key": source_field_key,
                    "target_resource_key": target_resource_key,
                    "target_field_key": target_field_key,
                    "label": (
                        None if self._is_empty(raw.get("label")) else str(raw["label"]).strip()
                    ),
                    "is_active": self._parse_import_bool(
                        raw.get("is_active"),
                        worksheet_name=worksheet_name,
                        context=f"ligne RELATION {offset + 1}",
                        default=True,
                    ),
                }
            )

        return relations

    def _normalize_relation_headers(
        self,
        *,
        worksheet_name: str,
        values: list[Any],
    ) -> list[str]:
        headers: list[str] = []
        seen: set[str] = set()

        for value in values:
            if value is None or not str(value).strip():
                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} » : "
                    "la section RELATION contient une colonne sans en-tête.",
                )

            header = str(value).strip().lower()

            if header not in self.RELATION_HEADER_ALIASES:
                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} » : " f"en-tête RELATION inconnu « {value} ».",
                )

            normalized = self.RELATION_HEADER_ALIASES[header]

            if normalized in seen:
                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} » : "
                    f"l'en-tête RELATION « {value} » est dupliqué.",
                )

            seen.add(normalized)
            headers.append(normalized)

        missing = self.RELATION_REQUIRED_HEADERS - set(headers)

        if missing:
            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : "
                "en-têtes RELATION obligatoires manquants : "
                f"{', '.join(sorted(missing))}.",
            )

        return headers

    @staticmethod
    def _parse_import_bool(
        value: Any,
        *,
        worksheet_name: str,
        context: str,
        default: bool,
    ) -> bool:
        if value is None:
            return default

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)

        text = str(value).strip().lower()

        if text in {"true", "1", "yes", "y", "oui", "vrai"}:
            return True
        if text in {"false", "0", "no", "n", "non", "faux"}:
            return False

        raise PluginResourceDefinitionImportError(
            f"Feuille « {worksheet_name} », {context} : "
            f"« {value} » n'est pas une valeur booléenne valide.",
        )

    async def _validate_relations_preflight(
        self,
        *,
        plugin_id: int,
        parsed_resources: list[ParsedResourceDefinition],
        existing_resources_by_key: dict[str, Any],
    ) -> list[str]:
        errors: list[str] = []

        workbook_by_key = {parsed.resource.key.strip(): parsed for parsed in parsed_resources}

        signatures: set[tuple[str, str, str, str]] = set()

        for parsed in parsed_resources:
            for relation in parsed.relations:
                target_key = relation["target_resource_key"]

                target_parsed = workbook_by_key.get(target_key)
                target_existing = existing_resources_by_key.get(target_key)

                if target_parsed is None and target_existing is None:
                    errors.append(
                        f"Feuille « {parsed.worksheet} » : la ressource cible "
                        f"« {target_key} » n'existe ni dans le fichier ni dans le plugin.",
                    )
                    continue

                source_field = next(
                    (
                        field
                        for field in parsed.resource.fields
                        if field.is_active and field.key == relation["source_field_key"]
                    ),
                    None,
                )

                if source_field is None:
                    errors.append(
                        f"Feuille « {parsed.worksheet} » : le champ source "
                        f"« {relation['source_field_key']} » n'existe pas ou est inactif.",
                    )
                    continue

                if target_parsed is not None:
                    target_fields = target_parsed.resource.fields
                else:
                    assert target_existing is not None
                    target_fields = target_existing.fields

                target_field = next(
                    (
                        field
                        for field in target_fields
                        if field.is_active and field.key == relation["target_field_key"]
                    ),
                    None,
                )

                if target_field is None:
                    errors.append(
                        f"Feuille « {parsed.worksheet} » : le champ cible "
                        f"« {relation['target_field_key']} » n'existe pas dans "
                        f"« {target_key} » ou est inactif.",
                    )
                    continue

                source_type = self._field_type_value(source_field)
                target_type = self._field_type_value(target_field)

                if source_type != target_type:
                    errors.append(
                        f"Feuille « {parsed.worksheet} » : les types des champs "
                        f"de relation doivent être identiques. "
                        f"Source={source_type}, cible={target_type}.",
                    )

                if source_type in {"SINGLE_CHOICE", "MULTIPLE_CHOICE"}:
                    errors.append(
                        f"Feuille « {parsed.worksheet} » : les champs de type "
                        "choix ne peuvent pas être utilisés comme clé de relation.",
                    )

                if parsed.resource.key.strip() == target_key:
                    errors.append(
                        f"Feuille « {parsed.worksheet} » : une ressource ne peut "
                        "pas être liée à elle-même.",
                    )

                signature = (
                    parsed.resource.key.strip(),
                    relation["source_field_key"],
                    target_key,
                    relation["target_field_key"],
                )

                if signature in signatures:
                    errors.append(
                        f"Feuille « {parsed.worksheet} » : la relation "
                        "est définie plusieurs fois dans le workbook.",
                    )
                signatures.add(signature)

                # Si la cible est déjà en BD, vérifier immédiatement les
                # valeurs uniques comme create_relation().
                if target_existing is not None:
                    target_records = await self.resource_service._get_all_records(
                        resource_id=target_existing.id,
                    )

                    seen_values: set[str] = set()

                    for record in target_records:
                        value = (record.data or {}).get(target_field.key)

                        if self._is_empty(value):
                            continue

                        key = self._relation_value_key(value)

                        if key in seen_values:
                            errors.append(
                                f"Feuille « {parsed.worksheet} » : le champ cible "
                                f"« {target_field.key} » de « {target_key} » "
                                "contient déjà des valeurs dupliquées.",
                            )
                            break

                        seen_values.add(key)

                else:
                    # La cible sera créée dans le workbook. Vérifier les DATA
                    # déjà validées de cette cible.
                    assert target_parsed is not None
                    seen_values: set[str] = set()

                    for record in target_parsed.data_rows:
                        value = record.get(target_field.key)

                        if self._is_empty(value):
                            continue

                        key = self._relation_value_key(value)

                        if key in seen_values:
                            errors.append(
                                f"Feuille « {parsed.worksheet} » : le champ cible "
                                f"« {target_field.key} » de « {target_key} » "
                                "contient des valeurs dupliquées dans DATA.",
                            )
                            break

                        seen_values.add(key)

                # Une relation dont la source est nouvelle ne peut pas déjà
                # exister en BD. On vérifie néanmoins le cas défensivement.
                source_existing = existing_resources_by_key.get(parsed.resource.key.strip())

                if source_existing is not None:
                    result = await self.resource_service.session.execute(
                        select(PluginResourceRelation).where(
                            PluginResourceRelation.source_resource_id == source_existing.id,
                            PluginResourceRelation.source_field_key == relation["source_field_key"],
                            PluginResourceRelation.target_resource_id
                            == (target_existing.id if target_existing is not None else -1),
                            PluginResourceRelation.target_field_key == relation["target_field_key"],
                        )
                    )

                    if result.scalar_one_or_none() is not None:
                        errors.append(
                            f"Feuille « {parsed.worksheet} » : cette relation "
                            "existe déjà dans le plugin.",
                        )

        return errors

    @staticmethod
    def _field_type_value(field: Any) -> str:
        value = field.field_type
        return value.value if hasattr(value, "value") else str(value)

    @staticmethod
    def _relation_value_key(value: Any) -> str:
        if isinstance(value, bool):
            return f"bool:{value}"
        if isinstance(value, (int, float)):
            return f"number:{value}"
        if isinstance(value, (date, datetime)):
            return f"date:{value.isoformat()}"
        return f"string:{str(value).strip()}"

    def _get_resource_creation_order(
        self,
        *,
        parsed_resources: list[ParsedResourceDefinition],
    ) -> list[ParsedResourceDefinition]:
        by_key = {parsed.resource.key.strip(): parsed for parsed in parsed_resources}

        dependencies = {
            key: {
                relation["target_resource_key"]
                for relation in parsed.relations
                if relation["target_resource_key"] in by_key
            }
            for key, parsed in by_key.items()
        }

        ordered: list[ParsedResourceDefinition] = []
        remaining = set(by_key)

        while remaining:
            ready = sorted(key for key in remaining if not (dependencies[key] & remaining))

            if not ready:
                raise PluginResourceDefinitionImportError(
                    "Impossible de déterminer l'ordre de création : "
                    "un cycle de dépendances entre ressources a été détecté : "
                    + ", ".join(sorted(remaining)),
                )

            for key in ready:
                ordered.append(by_key[key])
                remaining.remove(key)

        return ordered

    # ========================================================================
    # REFERENCES
    # ========================================================================

    def _find_references(
        self,
        worksheet,
    ) -> dict[str, str | None]:

        resource_reference: str | None = None
        schema_reference: str | None = None
        data_reference: str | None = None
        relation_reference: str | None = None

        for cell in worksheet[1]:

            if cell.value is None:
                continue

            text = str(
                cell.value,
            ).strip()

            if not text:
                continue

            upper = text.upper()

            # ----------------------------------------------------------------
            # RESOURCE
            # ----------------------------------------------------------------

            if upper.startswith("_RESOURCE_"):

                match = self.RESOURCE_REFERENCE_PATTERN.fullmatch(
                    text,
                )

                if match is None:

                    raise PluginResourceDefinitionImportError(
                        f"Feuille « {worksheet.title} » : "
                        f"la référence RESOURCE « {text} » est invalide. "
                        "Format attendu : _RESOURCE_(A5:E6).",
                    )

                if resource_reference is not None:

                    raise PluginResourceDefinitionImportError(
                        f"Feuille « {worksheet.title} » : "
                        "plusieurs références RESOURCE ont été trouvées "
                        "sur la première ligne.",
                    )

                resource_reference = text

            # ----------------------------------------------------------------
            # SCHEMA
            # ----------------------------------------------------------------

            if upper.startswith("_SCHEMA_"):

                match = self.SCHEMA_REFERENCE_PATTERN.fullmatch(
                    text,
                )

                if match is None:

                    raise PluginResourceDefinitionImportError(
                        f"Feuille « {worksheet.title} » : "
                        f"la référence SCHEMA « {text} » est invalide. "
                        "Format attendu : _SCHEMA_(A10:M20).",
                    )

                if schema_reference is not None:

                    raise PluginResourceDefinitionImportError(
                        f"Feuille « {worksheet.title} » : "
                        "plusieurs références SCHEMA ont été trouvées "
                        "sur la première ligne.",
                    )

                schema_reference = text

            # ----------------------------------------------------------------
            # DATA
            # ----------------------------------------------------------------

            if upper.startswith("_DATA_"):

                match = self.DATA_REFERENCE_PATTERN.fullmatch(
                    text,
                )

                if match is None:

                    raise PluginResourceDefinitionImportError(
                        f"Feuille « {worksheet.title} » : "
                        f"la référence DATA « {text} » est invalide. "
                        "Format attendu : _DATA_(A31:I36).",
                    )

                if data_reference is not None:

                    raise PluginResourceDefinitionImportError(
                        f"Feuille « {worksheet.title} » : "
                        "plusieurs références DATA ont été trouvées "
                        "sur la première ligne.",
                    )

                data_reference = text

            if upper.startswith("_RELATION_"):

                match = self.RELATION_REFERENCE_PATTERN.fullmatch(text)

                if match is None:
                    raise PluginResourceDefinitionImportError(
                        f"Feuille « {worksheet.title} » : "
                        f"la référence RELATION « {text} » est invalide. "
                        "Format attendu : _RELATION_(A52:E53).",
                    )

                if relation_reference is not None:
                    raise PluginResourceDefinitionImportError(
                        f"Feuille « {worksheet.title} » : "
                        "plusieurs références RELATION ont été trouvées "
                        "sur la première ligne.",
                    )

                relation_reference = text

        return {
            "resource": resource_reference,
            "schema": schema_reference,
            "data": data_reference,
            "relation": relation_reference,
        }

    # ========================================================================
    # REFERENCE BOUNDS
    # ========================================================================

    @staticmethod
    def _parse_reference_bounds(
        *,
        worksheet_name: str,
        reference: str,
        reference_type: str,
    ) -> tuple[int, int, int, int]:

        if reference_type == "RESOURCE":
            pattern = PluginResourceDefinitionImportService.RESOURCE_REFERENCE_PATTERN
        elif reference_type == "SCHEMA":
            pattern = PluginResourceDefinitionImportService.SCHEMA_REFERENCE_PATTERN
        elif reference_type == "DATA":
            pattern = PluginResourceDefinitionImportService.DATA_REFERENCE_PATTERN
        elif reference_type == "RELATION":
            pattern = PluginResourceDefinitionImportService.RELATION_REFERENCE_PATTERN
        else:
            raise PluginResourceDefinitionImportError(
                f"Type de référence inconnu : {reference_type}.",
            )

        match = pattern.fullmatch(
            reference,
        )

        if match is None:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : "
                f"référence {reference_type} invalide : "
                f"« {reference} ».",
            )

        start_cell = match.group(1).upper()
        end_cell = match.group(2).upper()

        try:

            (
                start_column,
                start_row,
                end_column,
                end_row,
            ) = range_boundaries(
                f"{start_cell}:{end_cell}",
            )

        except Exception as exc:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : "
                f"la plage {reference_type} "
                f"« {reference} » est invalide.",
            ) from exc

        if start_column is None or end_column is None or start_row is None or end_row is None:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : "
                f"la plage {reference_type} "
                f"« {reference} » est invalide.",
            )

        if start_column > end_column or start_row > end_row:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : "
                f"la plage {reference_type} "
                f"« {reference} » est inversée.",
            )

        return (
            start_column,
            start_row,
            end_column,
            end_row,
        )

    # ========================================================================
    # RANGE EXTRACTION
    # ========================================================================

    @staticmethod
    def _extract_range(
        *,
        worksheet,
        start_row: int,
        end_row: int,
        start_column: int,
        end_column: int,
    ) -> list[list[Any]]:

        values: list[list[Any]] = []

        for row in worksheet.iter_rows(
            min_row=start_row,
            max_row=end_row,
            min_col=start_column,
            max_col=end_column,
            values_only=True,
        ):

            values.append(
                [
                    PluginResourceDefinitionImportService._normalize_value(
                        value,
                    )
                    for value in row
                ]
            )

        return values

    # ========================================================================
    # RESOURCE SECTION
    # ========================================================================

    def _parse_resource_section(
        self,
        *,
        worksheet_name: str,
        values: list[list[Any]],
    ) -> PluginResourceCreate:

        if len(values) < 2:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : "
                "la section RESOURCE doit contenir "
                "une ligne d'en-têtes et une ligne de données.",
            )

        headers = self._normalize_resource_headers(
            worksheet_name=worksheet_name,
            values=values[0],
        )

        data_rows = [row for row in values[1:] if not self._row_is_empty(row)]

        if not data_rows:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : " "la section RESOURCE ne contient aucune donnée.",
            )

        if len(data_rows) > self.MAX_RESOURCE_DATA_ROWS:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : "
                "une feuille ne peut définir qu'une seule ressource. "
                f"{len(data_rows)} lignes de données ont été trouvées.",
            )

        row = data_rows[0]

        raw_data: dict[str, Any] = {}

        for index, header in enumerate(headers):

            value = row[index] if index < len(row) else None

            raw_data[header] = value

        return self._build_resource_create(
            worksheet_name=worksheet_name,
            raw_data=raw_data,
        )

    # ========================================================================
    # RESOURCE HEADERS
    # ========================================================================

    def _normalize_resource_headers(
        self,
        *,
        worksheet_name: str,
        values: list[Any],
    ) -> list[str]:

        headers: list[str] = []
        seen: set[str] = set()

        for value in values:

            if value is None or not str(value).strip():

                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} » : "
                    "la section RESOURCE contient "
                    "une colonne sans en-tête.",
                )

            header = (
                str(
                    value,
                )
                .strip()
                .lower()
            )

            if header not in self.RESOURCE_HEADER_ALIASES:

                allowed = ", ".join(
                    sorted(
                        self.RESOURCE_HEADER_ALIASES.keys(),
                    )
                )

                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} » : "
                    f"colonne RESOURCE inconnue « {value} ». "
                    f"Colonnes autorisées : {allowed}.",
                )

            canonical = self.RESOURCE_HEADER_ALIASES[header]

            if canonical in seen:

                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} » : "
                    f"la colonne RESOURCE « {value} » est dupliquée.",
                )

            seen.add(
                canonical,
            )

            headers.append(
                canonical,
            )

        missing = self.RESOURCE_REQUIRED_HEADERS - seen

        if missing:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : "
                "colonne(s) RESOURCE obligatoire(s) manquante(s) : "
                f"{', '.join(sorted(missing))}.",
            )

        return headers

    # ========================================================================
    # RESOURCE MODEL
    # ========================================================================

    def _build_resource_create(
        self,
        *,
        worksheet_name: str,
        raw_data: dict[str, Any],
    ) -> PluginResourceCreate:

        normalized = dict(
            raw_data,
        )

        # --------------------------------------------------------------------
        # name
        # --------------------------------------------------------------------

        normalized["name"] = self._require_string(
            worksheet_name=worksheet_name,
            field_name="name",
            value=normalized.get("name"),
        )

        # --------------------------------------------------------------------
        # key
        # --------------------------------------------------------------------

        normalized["key"] = self._require_string(
            worksheet_name=worksheet_name,
            field_name="key",
            value=normalized.get("key"),
        )

        # --------------------------------------------------------------------
        # description
        # --------------------------------------------------------------------

        if "description" in normalized:

            normalized["description"] = self._optional_string(
                worksheet_name=worksheet_name,
                field_name="description",
                value=normalized.get("description"),
            )

        # --------------------------------------------------------------------
        # scope
        # --------------------------------------------------------------------

        normalized["scope"] = self._parse_scope(
            worksheet_name=worksheet_name,
            value=normalized.get("scope"),
        )

        # --------------------------------------------------------------------
        # user schema customization
        # --------------------------------------------------------------------

        normalized["allow_user_schema_override"] = self._parse_boolean(
            worksheet_name=worksheet_name,
            field_name="user_schema_customization",
            value=normalized.get(
                "allow_user_schema_override",
            ),
            default=False,
        )

        # --------------------------------------------------------------------
        # position
        # --------------------------------------------------------------------

        normalized["position"] = self._parse_non_negative_int(
            worksheet_name=worksheet_name,
            field_name="position",
            value=normalized.get("position"),
            default=0,
        )

        # --------------------------------------------------------------------
        # icon
        # --------------------------------------------------------------------

        if "icon" in normalized:

            normalized["icon"] = self._optional_string(
                worksheet_name=worksheet_name,
                field_name="icon",
                value=normalized.get("icon"),
            )

        # --------------------------------------------------------------------
        # is_active
        # --------------------------------------------------------------------

        normalized["is_active"] = self._parse_boolean(
            worksheet_name=worksheet_name,
            field_name="is_active",
            value=normalized.get("is_active"),
            default=True,
        )

        # --------------------------------------------------------------------
        # Règle métier Resource existante
        # --------------------------------------------------------------------

        if (
            normalized["scope"] == PluginResourceScope.GLOBAL
            and normalized["allow_user_schema_override"]
        ):

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : "
                "une ressource GLOBAL ne peut pas autoriser "
                "la personnalisation du schema utilisateur.",
            )

        # --------------------------------------------------------------------
        # Validation officielle PluginResourceCreate.
        #
        # Les fields sont ajoutés ensuite.
        # --------------------------------------------------------------------

        normalized["fields"] = []

        try:

            return PluginResourceCreate.model_validate(
                normalized,
            )

        except Exception as exc:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : "
                "la définition RESOURCE est invalide : "
                f"{self._pydantic_error_message(exc)}",
            ) from exc

    # ========================================================================
    # SCHEMA SECTION
    # ========================================================================

    def _parse_schema_section(
        self,
        *,
        worksheet_name: str,
        values: list[list[Any]],
    ) -> list[PluginResourceFieldCreate]:

        if len(values) < 2:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : "
                "la section SCHEMA doit contenir "
                "une ligne d'en-têtes et au moins un champ.",
            )

        headers = self._normalize_schema_headers(
            worksheet_name=worksheet_name,
            values=values[0],
        )

        data_rows = [row for row in values[1:] if not self._row_is_empty(row)]

        if not data_rows:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : " "la section SCHEMA ne contient aucun champ.",
            )

        fields: list[PluginResourceFieldCreate] = []

        for row_index, row in enumerate(
            data_rows,
            start=2,
        ):

            try:

                raw_field: dict[str, Any] = {}

                for index, header in enumerate(headers):

                    value = row[index] if index < len(row) else None

                    raw_field[header] = value

                field = self._build_field_create(
                    worksheet_name=worksheet_name,
                    row_number=row_index,
                    raw_data=raw_field,
                )

                fields.append(
                    field,
                )

            except PluginResourceDefinitionImportError:
                raise

            except Exception as exc:

                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} », "
                    f"ligne SCHEMA {row_index} : "
                    f"champ invalide : {exc}",
                ) from exc

        # --------------------------------------------------------------------
        # Validation officielle du système :
        #
        #   - clé unique
        #   - min/max
        #   - options pour choix
        #   - pattern
        # --------------------------------------------------------------------

        try:

            self.resource_service._validate_fields_collection(
                fields,
            )

        except ValueError as exc:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : " f"schema invalide : {exc}",
            ) from exc

        # --------------------------------------------------------------------
        # Validation des defaults.
        #
        # PluginResourceService.add_field() valide les defaults lors d'une
        # création individuelle. Comme ici nous passons par create(),
        # nous devons reproduire explicitement cette vérification pendant
        # le pre-flight.
        # --------------------------------------------------------------------

        for field in fields:

            if field.default_value is None:
                continue

            try:

                self.resource_service._validate_value(
                    field=field.model_dump(
                        mode="json",
                    ),
                    value=field.default_value,
                )

            except ValueError as exc:

                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} » : "
                    f"le default_value du champ "
                    f"« {field.key} » est invalide : {exc}",
                ) from exc

        return fields

    # ========================================================================
    # SCHEMA HEADERS
    # ========================================================================

    def _normalize_schema_headers(
        self,
        *,
        worksheet_name: str,
        values: list[Any],
    ) -> list[str]:

        headers: list[str] = []
        seen: set[str] = set()

        for value in values:

            if value is None or not str(value).strip():

                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} » : "
                    "la section SCHEMA contient "
                    "une colonne sans en-tête.",
                )

            header = (
                str(
                    value,
                )
                .strip()
                .lower()
            )

            if header not in self.SCHEMA_HEADER_ALIASES:

                allowed = ", ".join(
                    sorted(
                        self.SCHEMA_HEADER_ALIASES.keys(),
                    )
                )

                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} » : "
                    f"colonne SCHEMA inconnue « {value} ». "
                    f"Colonnes autorisées : {allowed}.",
                )

            canonical = self.SCHEMA_HEADER_ALIASES[header]

            if canonical in seen:

                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} » : "
                    f"la colonne SCHEMA « {value} » est dupliquée.",
                )

            seen.add(
                canonical,
            )

            headers.append(
                canonical,
            )

        missing = self.SCHEMA_REQUIRED_HEADERS - seen

        if missing:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : "
                "colonne(s) SCHEMA obligatoire(s) manquante(s) : "
                f"{', '.join(sorted(missing))}.",
            )

        return headers

    # ========================================================================
    # FIELD CREATE
    # ========================================================================

    def _build_field_create(
        self,
        *,
        worksheet_name: str,
        row_number: int,
        raw_data: dict[str, Any],
    ) -> PluginResourceFieldCreate:

        data = dict(
            raw_data,
        )

        # --------------------------------------------------------------------
        # key
        # --------------------------------------------------------------------

        data["key"] = self._require_string(
            worksheet_name=worksheet_name,
            field_name=f"schema.key (ligne {row_number})",
            value=data.get("key"),
        )

        # --------------------------------------------------------------------
        # label
        # --------------------------------------------------------------------

        data["label"] = self._require_string(
            worksheet_name=worksheet_name,
            field_name=f"schema.label (ligne {row_number})",
            value=data.get("label"),
        )

        # --------------------------------------------------------------------
        # description
        # --------------------------------------------------------------------

        if "description" in data:

            data["description"] = self._optional_string(
                worksheet_name=worksheet_name,
                field_name=f"schema.description (ligne {row_number})",
                value=data.get("description"),
            )

        # --------------------------------------------------------------------
        # field_type
        # --------------------------------------------------------------------

        data["field_type"] = self._parse_field_type(
            worksheet_name=worksheet_name,
            row_number=row_number,
            value=data.get("field_type"),
        )

        # --------------------------------------------------------------------
        # required
        # --------------------------------------------------------------------

        data["required"] = self._parse_boolean(
            worksheet_name=worksheet_name,
            field_name=f"schema.required (ligne {row_number})",
            value=data.get("required"),
            default=False,
        )

        # --------------------------------------------------------------------
        # min_length
        # --------------------------------------------------------------------

        data["min_length"] = self._parse_optional_non_negative_int(
            worksheet_name=worksheet_name,
            field_name=f"schema.min_length (ligne {row_number})",
            value=data.get("min_length"),
        )

        # --------------------------------------------------------------------
        # max_length
        # --------------------------------------------------------------------

        data["max_length"] = self._parse_optional_non_negative_int(
            worksheet_name=worksheet_name,
            field_name=f"schema.max_length (ligne {row_number})",
            value=data.get("max_length"),
        )

        # --------------------------------------------------------------------
        # min_value
        # --------------------------------------------------------------------

        data["min_value"] = self._parse_optional_number(
            worksheet_name=worksheet_name,
            field_name=f"schema.min_value (ligne {row_number})",
            value=data.get("min_value"),
        )

        # --------------------------------------------------------------------
        # max_value
        # --------------------------------------------------------------------

        data["max_value"] = self._parse_optional_number(
            worksheet_name=worksheet_name,
            field_name=f"schema.max_value (ligne {row_number})",
            value=data.get("max_value"),
        )

        # --------------------------------------------------------------------
        # pattern
        # --------------------------------------------------------------------

        if "pattern" in data:

            data["pattern"] = self._optional_string(
                worksheet_name=worksheet_name,
                field_name=f"schema.pattern (ligne {row_number})",
                value=data.get("pattern"),
            )

        # --------------------------------------------------------------------
        # options
        # --------------------------------------------------------------------

        data["options"] = self._parse_options(
            worksheet_name=worksheet_name,
            row_number=row_number,
            value=data.get("options"),
        )

        # --------------------------------------------------------------------
        # default_value
        # --------------------------------------------------------------------

        data["default_value"] = self._parse_default_value(
            worksheet_name=worksheet_name,
            row_number=row_number,
            value=data.get("default_value"),
        )

        # --------------------------------------------------------------------
        # position
        # --------------------------------------------------------------------

        data["position"] = self._parse_non_negative_int(
            worksheet_name=worksheet_name,
            field_name=f"schema.position (ligne {row_number})",
            value=data.get("position"),
            default=row_number - 2,
        )

        # --------------------------------------------------------------------
        # is_active
        # --------------------------------------------------------------------

        data["is_active"] = self._parse_boolean(
            worksheet_name=worksheet_name,
            field_name=f"schema.is_active (ligne {row_number})",
            value=data.get("is_active"),
            default=True,
        )

        # --------------------------------------------------------------------
        # Validation Pydantic officielle.
        # --------------------------------------------------------------------

        try:

            field = PluginResourceFieldCreate.model_validate(
                data,
            )

        except Exception as exc:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} », "
                f"ligne SCHEMA {row_number} : "
                f"{self._pydantic_error_message(exc)}",
            ) from exc

        # --------------------------------------------------------------------
        # Validation métier du champ.
        # --------------------------------------------------------------------

        try:

            self.resource_service._validate_field(
                field,
            )

        except ValueError as exc:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} », "
                f"ligne SCHEMA {row_number} : "
                f"champ « {field.key} » invalide : {exc}",
            ) from exc

        return field

    # ========================================================================
    # FIELD TYPE
    # ========================================================================

    def _parse_field_type(
        self,
        *,
        worksheet_name: str,
        row_number: int,
        value: Any,
    ) -> PluginFieldType:

        if value is None:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} », "
                f"ligne SCHEMA {row_number} : "
                "field_type est obligatoire.",
            )

        if isinstance(
            value,
            PluginFieldType,
        ):

            return value

        if not isinstance(
            value,
            str,
        ):

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} », "
                f"ligne SCHEMA {row_number} : "
                "field_type doit être une chaîne.",
            )

        normalized = value.strip().upper()

        try:

            return PluginFieldType(
                normalized,
            )

        except ValueError as exc:

            allowed = ", ".join(item.value for item in PluginFieldType)

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} », "
                f"ligne SCHEMA {row_number} : "
                f"field_type « {value} » invalide. "
                f"Valeurs autorisées : {allowed}.",
            ) from exc

    # ========================================================================
    # OPTIONS
    # ========================================================================

    def _parse_options(
        self,
        *,
        worksheet_name: str,
        row_number: int,
        value: Any,
    ) -> list[Any]:

        if value is None:

            return []

        if isinstance(
            value,
            list,
        ):

            return value

        if isinstance(
            value,
            tuple,
        ):

            return list(
                value,
            )

        if not isinstance(
            value,
            str,
        ):

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} », "
                f"ligne SCHEMA {row_number} : "
                "options doit contenir un tableau JSON.",
            )

        text = value.strip()

        if not text:

            return []

        try:

            parsed = json.loads(
                text,
            )

        except json.JSONDecodeError as exc:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} », "
                f"ligne SCHEMA {row_number} : "
                "options contient un JSON invalide.",
            ) from exc

        if not isinstance(
            parsed,
            list,
        ):

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} », "
                f"ligne SCHEMA {row_number} : "
                "options doit être un tableau JSON.",
            )

        return parsed

    # ========================================================================
    # DEFAULT VALUE
    # ========================================================================

    def _parse_default_value(
        self,
        *,
        worksheet_name: str,
        row_number: int,
        value: Any,
    ) -> Any:

        if value is None:
            return None

        if not isinstance(
            value,
            str,
        ):

            return value

        text = value.strip()

        if not text:
            return None

        # --------------------------------------------------------------------
        # Les types simples restent des chaînes.
        #
        # Pour les valeurs complexes, on accepte le JSON :
        #
        #     ["A", "B"]
        #     {"x": 1}
        #
        # Cela permet notamment les defaults MULTIPLE_CHOICE.
        # --------------------------------------------------------------------

        if text.startswith(
            (
                "[",
                "{",
            )
        ):

            try:

                return json.loads(
                    text,
                )

            except json.JSONDecodeError as exc:

                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} », "
                    f"ligne SCHEMA {row_number} : "
                    "default_value contient un JSON invalide.",
                ) from exc

        return value

    # ========================================================================
    # BOOLEAN
    # ========================================================================

    def _parse_boolean(
        self,
        *,
        worksheet_name: str,
        field_name: str,
        value: Any,
        default: bool,
    ) -> bool:

        if value is None:
            return default

        if isinstance(
            value,
            bool,
        ):

            return value

        if isinstance(
            value,
            int,
        ) and value in (
            0,
            1,
        ):

            return bool(
                value,
            )

        if isinstance(
            value,
            float,
        ) and value in (
            0.0,
            1.0,
        ):

            return bool(
                int(value),
            )

        if isinstance(
            value,
            str,
        ):

            normalized = value.strip().lower()

            if normalized in {
                "true",
                "1",
                "yes",
                "oui",
                "vrai",
            }:

                return True

            if normalized in {
                "false",
                "0",
                "no",
                "non",
                "faux",
            }:

                return False

        raise PluginResourceDefinitionImportError(
            f"Le champ « {field_name} » de la feuille "
            f"« {worksheet_name} » doit être un booléen.",
        )

    # ========================================================================
    # SCOPE
    # ========================================================================

    def _parse_scope(
        self,
        *,
        worksheet_name: str,
        value: Any,
    ) -> PluginResourceScope:

        if value is None:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : " "scope est obligatoire.",
            )

        if not isinstance(
            value,
            str,
        ):

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : " "scope doit être GLOBAL ou USER.",
            )

        normalized = value.strip().upper()

        try:

            return PluginResourceScope(
                normalized,
            )

        except ValueError as exc:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : "
                f"scope « {value} » invalide. "
                "Valeurs autorisées : GLOBAL, USER.",
            ) from exc

    # ========================================================================
    # STRING
    # ========================================================================

    @staticmethod
    def _require_string(
        *,
        worksheet_name: str,
        field_name: str,
        value: Any,
    ) -> str:

        if value is None:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : " f"« {field_name} » est obligatoire.",
            )

        if not isinstance(
            value,
            str,
        ):

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : " f"« {field_name} » doit être une chaîne.",
            )

        value = value.strip()

        if not value:

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : " f"« {field_name} » est obligatoire.",
            )

        return value

    @staticmethod
    def _optional_string(
        *,
        worksheet_name: str,
        field_name: str,
        value: Any,
    ) -> str | None:

        if value is None:
            return None

        if not isinstance(
            value,
            str,
        ):

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : " f"« {field_name} » doit être une chaîne.",
            )

        value = value.strip()

        return value or None

    # ========================================================================
    # INTEGER
    # ========================================================================

    def _parse_non_negative_int(
        self,
        *,
        worksheet_name: str,
        field_name: str,
        value: Any,
        default: int = 0,
    ) -> int:

        if value is None:
            return default

        if isinstance(
            value,
            bool,
        ):

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : " f"« {field_name} » doit être un entier >= 0.",
            )

        if isinstance(
            value,
            int,
        ):

            if value < 0:

                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} » : " f"« {field_name} » doit être >= 0.",
                )

            return value

        if isinstance(
            value,
            float,
        ):

            if not value.is_integer() or value < 0:

                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} » : "
                    f"« {field_name} » doit être un entier >= 0.",
                )

            return int(
                value,
            )

        if isinstance(
            value,
            str,
        ):

            text = value.strip()

            if not text:
                return default

            if not re.fullmatch(
                r"\d+",
                text,
            ):

                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} » : "
                    f"« {field_name} » doit être un entier >= 0.",
                )

            return int(
                text,
            )

        raise PluginResourceDefinitionImportError(
            f"Feuille « {worksheet_name} » : " f"« {field_name} » doit être un entier >= 0.",
        )

    def _parse_optional_non_negative_int(
        self,
        *,
        worksheet_name: str,
        field_name: str,
        value: Any,
    ) -> int | None:

        if value is None:
            return None

        return self._parse_non_negative_int(
            worksheet_name=worksheet_name,
            field_name=field_name,
            value=value,
            default=0,
        )

    # ========================================================================
    # NUMBER
    # ========================================================================

    def _parse_optional_number(
        self,
        *,
        worksheet_name: str,
        field_name: str,
        value: Any,
    ) -> float | None:

        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):

            raise PluginResourceDefinitionImportError(
                f"Feuille « {worksheet_name} » : " f"« {field_name} » doit être numérique.",
            )

        if isinstance(
            value,
            (
                int,
                float,
            ),
        ):

            return float(
                value,
            )

        if isinstance(
            value,
            str,
        ):

            text = value.strip()

            if not text:
                return None

            try:

                return float(
                    text,
                )

            except ValueError as exc:

                raise PluginResourceDefinitionImportError(
                    f"Feuille « {worksheet_name} » : " f"« {field_name} » doit être numérique.",
                ) from exc

        raise PluginResourceDefinitionImportError(
            f"Feuille « {worksheet_name} » : " f"« {field_name} » doit être numérique.",
        )

    # ========================================================================
    # GENERIC HELPERS
    # ========================================================================

    @staticmethod
    def _normalize_value(
        value: Any,
    ) -> Any:

        if isinstance(
            value,
            str,
        ):

            value = value.strip()

            return value or None

        return value

    @staticmethod
    def _row_is_empty(
        row: list[Any],
    ) -> bool:

        return all(
            value is None
            or (
                isinstance(
                    value,
                    str,
                )
                and not value.strip()
            )
            for value in row
        )

    @staticmethod
    def _is_empty(value: Any) -> bool:
        return (
            value is None
            or (
                isinstance(value, str)
                and not value.strip()
            )
        )
        
    @staticmethod
    def _ranges_overlap(
        start_row_a: int,
        end_row_a: int,
        start_column_a: int,
        end_column_a: int,
        start_row_b: int,
        end_row_b: int,
        start_column_b: int,
        end_column_b: int,
    ) -> bool:

        rows_overlap = start_row_a <= end_row_b and start_row_b <= end_row_a

        columns_overlap = start_column_a <= end_column_b and start_column_b <= end_column_a

        return rows_overlap and columns_overlap

    # ========================================================================
    # PYDANTIC ERROR
    # ========================================================================

    @staticmethod
    def _pydantic_error_message(
        exc: Exception,
    ) -> str:

        errors_method = getattr(
            exc,
            "errors",
            None,
        )

        if not callable(
            errors_method,
        ):

            return str(
                exc,
            )

        parts: list[str] = []

        try:
            errors = errors_method()
        except TypeError:
            return str(
                exc,
            )

        if not isinstance(
            errors,
            (list, tuple),
        ):
            return str(
                exc,
            )

        for error in errors:

            if not isinstance(
                error,
                dict,
            ):
                parts.append(
                    str(
                        error,
                    )
                )
                continue

            loc = error.get(
                "loc",
                [],
            )

            if isinstance(
                loc,
                str,
            ):
                loc_items = [loc]
            else:
                try:
                    loc_items = list(
                        loc,
                    )
                except TypeError:
                    loc_items = []

            location = " → ".join(str(item) for item in loc_items)

            message = str(
                error.get(
                    "msg",
                    "Valeur invalide",
                )
            )

            if location:

                parts.append(
                    f"{location} : {message}",
                )

            else:

                parts.append(
                    message,
                )

        return "; ".join(
            parts,
        ) or str(
            exc,
        )

    # ========================================================================
    # ERROR FORMAT
    # ========================================================================

    @staticmethod
    def _format_errors(
        errors: list[str],
    ) -> str:

        lines = [
            "Le fichier Excel contient des erreurs. "
            "Aucune ressource ni aucun schema n'a été créé.",
        ]

        lines.extend(f"- {error}" for error in errors)

        return "\n".join(
            lines,
        )
