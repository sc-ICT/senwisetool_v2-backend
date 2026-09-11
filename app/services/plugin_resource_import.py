from __future__ import annotations

from typing import Any, BinaryIO

from openpyxl import load_workbook

from app.models.enums import PluginResourceScope
from app.models.plugin_resource_data import PluginResourceRecord
from app.schemas.plugin_resource import (
    PluginResourceImportError,
    PluginResourceImportResponse,
)
from app.services.plugin_resource import PluginResourceService


class PluginResourceImportService:

    MAX_ROWS = 10_000

    def __init__(
        self,
        resource_service: PluginResourceService,
    ) -> None:
        self.resource_service = resource_service

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

        # --------------------------------------------------------------------
        # Autorisations
        # --------------------------------------------------------------------

        if resource.scope == PluginResourceScope.GLOBAL and not is_admin:
            raise ValueError(
                "Seul un administrateur peut importer " "des données dans une ressource GLOBAL.",
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
            raise ValueError(
                "Impossible de lire le fichier Excel.",
            ) from exc

        try:

            if not workbook.worksheets:
                raise ValueError(
                    "Le fichier Excel ne contient aucune feuille.",
                )

            worksheet = workbook.worksheets[0]

            rows = worksheet.iter_rows(
                values_only=True,
            )

            try:
                header_row = next(
                    rows,
                )
            except StopIteration:
                raise ValueError(
                    "Le fichier Excel est vide.",
                )

            headers = self._normalize_headers(
                header_row,
            )

            schema = await self._get_import_schema(
                resource_id=resource_id,
                user_id=user_id,
                is_admin=is_admin,
            )

            fields = [
                field
                for field in schema.get(
                    "fields",
                    [],
                )
                if field.get(
                    "is_active",
                    True,
                )
            ]

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

                if self._row_is_empty(
                    raw_row,
                ):
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

            # ----------------------------------------------------------------
            # IMPORTANT :
            #
            # Une seule erreur = aucune insertion.
            # ----------------------------------------------------------------

            if errors:

                return PluginResourceImportResponse(
                    resource_id=resource_id,
                    imported=0,
                    rejected=len(valid_rows) + len(errors),
                    errors=errors,
                )

            # ----------------------------------------------------------------
            # Insertion atomique
            # ----------------------------------------------------------------

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

    # ========================================================================
    # SCHEMA
    # ========================================================================

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

        # GLOBAL
        if resource.scope == PluginResourceScope.GLOBAL:

            return self.resource_service._resource_schema(
                resource,
            )

        # USER
        #
        # Admin importe des données communes.
        if is_admin:

            return self.resource_service._resource_schema(
                resource,
            )

        # User importe ses propres données.
        return await self.resource_service.get_effective_schema(
            resource_id=resource_id,
            user_id=user_id,
        )

    # ========================================================================
    # HEADERS
    # ========================================================================

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

        # Retirer les colonnes vides à droite.
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
                        message=(f"La colonne « {header} » est dupliquée."),
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

        required_fields = {
            field["key"]
            for field in fields
            if field.get(
                "required",
                False,
            )
        }

        provided_fields = {header for header in headers if header}

        missing = required_fields - provided_fields

        for field in sorted(
            missing,
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

    # ========================================================================
    # CELL
    # ========================================================================

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

    # ========================================================================
    # OWNER
    # ========================================================================

    @staticmethod
    def _resolve_owner_id(
        *,
        resource_scope: PluginResourceScope,
        user_id: int,
        is_admin: bool,
    ) -> int | None:

        if resource_scope == PluginResourceScope.GLOBAL:

            if not is_admin:
                raise ValueError(
                    "Seul un administrateur peut importer " "une ressource GLOBAL.",
                )

            return None

        # USER
        #
        # Admin → données communes.
        if is_admin:
            return None

        # User → données personnelles.
        return user_id

    # ========================================================================
    # ERROR FIELD
    # ========================================================================

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
