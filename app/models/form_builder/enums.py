from __future__ import annotations

from enum import Enum


class QuestionDefinitionStatus(str, Enum):
    """
    Statut global d'une question dans la banque.
    """

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class QuestionGroupStatus(str, Enum):
    """
    Statut global d'un groupe de questions dans la banque.
    """

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class QuestionType(str, Enum):
    """
    Types de questions supportés par le moteur.

    Cette liste constitue le socle initial.
    Nous pourrons l'étendre sans changer
    l'architecture générale.
    """

    # ============================================================
    # Texte
    # ============================================================

    TEXT = "TEXT"
    LONG_TEXT = "LONG_TEXT"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    URL = "URL"
    ADDRESS = "ADDRESS"

    # ============================================================
    # Numérique
    # ============================================================

    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    PERCENTAGE = "PERCENTAGE"
    CURRENCY = "CURRENCY"

    # ============================================================
    # Choix
    # ============================================================

    SINGLE_CHOICE = "SINGLE_CHOICE"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    DROPDOWN = "DROPDOWN"
    AUTOCOMPLETE = "AUTOCOMPLETE"
    RATING = "RATING"
    LIKERT_SCALE = "LIKERT_SCALE"
    RANKING = "RANKING"

    # ============================================================
    # Date / heure
    # ============================================================

    DATE = "DATE"
    TIME = "TIME"
    DATETIME = "DATETIME"
    DURATION = "DURATION"

    # ============================================================
    # Géolocalisation
    # ============================================================

    POINT = "POINT"
    LINE = "LINE"
    POLYGON = "POLYGON"
    AREA = "AREA"

    # ============================================================
    # Médias
    # ============================================================

    PHOTO = "PHOTO"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    FILE = "FILE"
    SIGNATURE = "SIGNATURE"

    # ============================================================
    # Identification / scan
    # ============================================================

    QR_CODE = "QR_CODE"
    BARCODE = "BARCODE"

    # ============================================================
    # Métier / logique
    # ============================================================

    ENTITY_SELECT = "ENTITY_SELECT"
    ENTITY_SEARCH = "ENTITY_SEARCH"
    CALCULATION = "CALCULATION"

    # ============================================================
    # Présentation / information
    # ============================================================

    NOTE = "NOTE"
    CONSENT = "CONSENT"
    HIDDEN = "HIDDEN"


class ProjectStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"
