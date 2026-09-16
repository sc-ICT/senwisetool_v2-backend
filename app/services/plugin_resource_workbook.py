from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

REFERENCE_PATTERN = re.compile(
    r"^_(RESOURCE|SCHEMA|RELATION|DATA)_\(\s*([A-Z]{1,3}\d+)\s*:\s*([A-Z]{1,3}\d+)\s*\)$",
    re.IGNORECASE,
)


class WorkbookImportError(ValueError):
    """Erreur de structure du workbook d'import."""


@dataclass(frozen=True)
class WorkbookReference:
    kind: str
    start_cell: str
    end_cell: str


@dataclass
class ParsedWorkbookSection:
    kind: str
    worksheet: str
    start_cell: str
    end_cell: str
    headers: list[str]
    rows: list[dict[str, Any]]
    start_row: int
    end_row: int


@dataclass
class ParsedWorkbookSheet:
    worksheet: str
    resource: ParsedWorkbookSection
    schema: ParsedWorkbookSection
    relation: ParsedWorkbookSection
    data: ParsedWorkbookSection


class PluginResourceWorkbookParser:
    """
    Parse le template Excel de configuration complète des ressources.

    La première ligne de chaque feuille contient les références :

        _RESOURCE_(A5:E6)
        _SCHEMA_(A10:M20)
        _RELATION_(A52:E55)
        _DATA_(A31:J46)

    Les coordonnées sont entièrement dynamiques.
    """

    REQUIRED_SECTIONS = {
        "RESOURCE",
        "SCHEMA",
        "RELATION",
        "DATA",
    }

    def parse(
        self,
        workbook,
    ) -> list[ParsedWorkbookSheet]:
        if not workbook.worksheets:
            raise WorkbookImportError("Le fichier Excel ne contient aucune feuille.")

        result: list[ParsedWorkbookSheet] = []

        for worksheet in workbook.worksheets:
            result.append(
                self._parse_worksheet(
                    worksheet,
                )
            )

        return result

    # ======================================================================
    # SHEET
    # ======================================================================

    def _parse_worksheet(
        self,
        worksheet: Worksheet,
    ) -> ParsedWorkbookSheet:
        references = self._read_references(
            worksheet,
        )

        missing = self.REQUIRED_SECTIONS - set(references)

        if missing:
            raise WorkbookImportError(
                f"Feuille « {worksheet.title} » : "
                f"référence(s) manquante(s) : "
                f"{', '.join(sorted(missing))}."
            )

        sections = {
            kind: self._read_section(
                worksheet=worksheet,
                reference=reference,
            )
            for kind, reference in references.items()
        }

        return ParsedWorkbookSheet(
            worksheet=worksheet.title,
            resource=sections["RESOURCE"],
            schema=sections["SCHEMA"],
            relation=sections["RELATION"],
            data=sections["DATA"],
        )

    # ======================================================================
    # REFERENCES
    # ======================================================================

    def _read_references(
        self,
        worksheet: Worksheet,
    ) -> dict[str, WorkbookReference]:
        references: dict[str, WorkbookReference] = {}

        for cell in worksheet[1]:
            value = cell.value

            if value is None:
                continue

            text = str(value).strip()

            if not text:
                continue

            match = REFERENCE_PATTERN.match(
                text,
            )

            if not match:
                continue

            kind = match.group(1).upper()
            start_cell = match.group(2).upper()
            end_cell = match.group(3).upper()

            if kind in references:
                raise WorkbookImportError(
                    f"Feuille « {worksheet.title} » : "
                    f"la référence _{kind}_ est déclarée plusieurs fois."
                )

            references[kind] = WorkbookReference(
                kind=kind,
                start_cell=start_cell,
                end_cell=end_cell,
            )

        return references

    # ======================================================================
    # SECTION
    # ======================================================================

    def _read_section(
        self,
        *,
        worksheet: Worksheet,
        reference: WorkbookReference,
    ) -> ParsedWorkbookSection:
        start_row = worksheet[reference.start_cell].row
        end_row = worksheet[reference.end_cell].row

        start_column = worksheet[reference.start_cell].column
        end_column = worksheet[reference.end_cell].column

        if start_row > end_row:
            raise WorkbookImportError(
                f"Feuille « {worksheet.title} » : "
                f"plage invalide pour _{reference.kind}_ : "
                f"{reference.start_cell}:{reference.end_cell}."
            )

        if start_column > end_column:
            raise WorkbookImportError(
                f"Feuille « {worksheet.title} » : "
                f"plage invalide pour _{reference.kind}_ : "
                f"{reference.start_cell}:{reference.end_cell}."
            )

        values = []

        for row in worksheet.iter_rows(
            min_row=start_row,
            max_row=end_row,
            min_col=start_column,
            max_col=end_column,
            values_only=True,
        ):
            values.append(
                [
                    self._normalize_value(
                        value,
                    )
                    for value in row
                ]
            )

        if not values:
            raise WorkbookImportError(
                f"Feuille « {worksheet.title} » : " f"la section _{reference.kind}_ est vide."
            )

        headers = [
            self._normalize_header(
                value,
            )
            for value in values[0]
        ]

        self._validate_headers(
            worksheet=worksheet,
            kind=reference.kind,
            headers=headers,
        )

        rows: list[dict[str, Any]] = []

        for row_values in values[1:]:
            if self._row_is_empty(
                row_values,
            ):
                continue

            row_data: dict[str, Any] = {}

            for index, header in enumerate(headers):
                if not header:
                    continue

                value = row_values[index] if index < len(row_values) else None

                row_data[header] = value

            rows.append(
                row_data,
            )

        return ParsedWorkbookSection(
            kind=reference.kind,
            worksheet=worksheet.title,
            start_cell=reference.start_cell,
            end_cell=reference.end_cell,
            headers=headers,
            rows=rows,
            start_row=start_row,
            end_row=end_row,
        )

    # ======================================================================
    # VALIDATION
    # ======================================================================

    @staticmethod
    def _validate_headers(
        *,
        worksheet: Worksheet,
        kind: str,
        headers: list[str],
    ) -> None:
        seen: set[str] = set()

        for header in headers:
            if not header:
                raise WorkbookImportError(
                    f"Feuille « {worksheet.title} » : "
                    f"la section _{kind}_ contient une colonne sans en-tête."
                )

            normalized = header.strip()

            if normalized in seen:
                raise WorkbookImportError(
                    f"Feuille « {worksheet.title} » : "
                    f"la colonne « {normalized} » est dupliquée "
                    f"dans la section _{kind}_."
                )

            seen.add(normalized)

    # ======================================================================
    # NORMALIZATION
    # ======================================================================

    @staticmethod
    def _normalize_header(
        value: Any,
    ) -> str:
        if value is None:
            return ""

        return str(value).strip()

    @classmethod
    def _normalize_value(
        cls,
        value: Any,
    ) -> Any:
        if value is None:
            return None

        if isinstance(
            value,
            datetime,
        ):
            return value

        if isinstance(
            value,
            date,
        ):
            return value

        if isinstance(
            value,
            bool,
        ):
            return value

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
        row: list[Any],
    ) -> bool:
        for value in row:
            if value is None:
                continue

            if isinstance(value, str) and not value.strip():
                continue

            return False

        return True

    # ======================================================================
    # JSON / BOOLEAN HELPERS
    # ======================================================================

    @staticmethod
    def parse_boolean(
        value: Any,
        *,
        field_name: str,
    ) -> bool:
        if isinstance(
            value,
            bool,
        ):
            return value

        if isinstance(
            value,
            (int, float),
        ):
            if value == 1:
                return True

            if value == 0:
                return False

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
                "y",
            }:
                return True

            if normalized in {
                "false",
                "0",
                "no",
                "non",
                "n",
            }:
                return False

        raise WorkbookImportError(
            f"La valeur « {value} » du champ " f"« {field_name} » doit être TRUE ou FALSE."
        )

    @staticmethod
    def parse_json(
        value: Any,
        *,
        field_name: str,
    ) -> Any:
        if value is None:
            return None

        if isinstance(
            value,
            (list, dict, int, float, bool),
        ):
            return value

        if not isinstance(
            value,
            str,
        ):
            return value

        text = value.strip()

        if not text:
            return None

        try:
            return json.loads(
                text,
            )
        except json.JSONDecodeError as exc:
            raise WorkbookImportError(
                f"La valeur du champ « {field_name} » " "doit contenir un JSON valide."
            ) from exc
