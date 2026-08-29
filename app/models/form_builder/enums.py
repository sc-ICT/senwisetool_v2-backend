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


class DependencyConditionOperator(str, Enum):
    """
    Opérateurs utilisables dans les conditions de dépendance.
    """

    # ============================================================
    # Comparaisons générales
    # ============================================================

    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"

    # ============================================================
    # Texte
    # ============================================================

    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"

    STARTS_WITH = "STARTS_WITH"
    NOT_STARTS_WITH = "NOT_STARTS_WITH"

    ENDS_WITH = "ENDS_WITH"
    NOT_ENDS_WITH = "NOT_ENDS_WITH"

    MATCHES_REGEX = "MATCHES_REGEX"

    # ============================================================
    # Numérique
    # ============================================================

    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_OR_EQUALS = "GREATER_THAN_OR_EQUALS"

    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUALS = "LESS_THAN_OR_EQUALS"

    BETWEEN = "BETWEEN"
    NOT_BETWEEN = "NOT_BETWEEN"

    # ============================================================
    # Collections / choix
    # ============================================================

    IN = "IN"
    NOT_IN = "NOT_IN"

    CONTAINS_ANY = "CONTAINS_ANY"
    CONTAINS_ALL = "CONTAINS_ALL"
    CONTAINS_NONE = "CONTAINS_NONE"

    # ============================================================
    # État
    # ============================================================

    IS_EMPTY = "IS_EMPTY"
    IS_NOT_EMPTY = "IS_NOT_EMPTY"

    # ============================================================
    # Booléen
    # ============================================================

    IS_TRUE = "IS_TRUE"
    IS_FALSE = "IS_FALSE"


class DependencyLogicalOperator(str, Enum):
    """
    Opérateur logique utilisé pour combiner plusieurs conditions.
    """

    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class DependencyTargetType(str, Enum):
    """
    Type d'élément sur lequel une règle peut agir.
    """

    QUESTION = "QUESTION"
    SECTION = "SECTION"


class DependencyActionType(str, Enum):
    """
    Actions qu'une règle peut appliquer à sa cible.

    Cette liste constitue le socle du moteur.
    Les configurations spécifiques seront ajoutées ensuite.
    """

    # Présentation
    SHOW = "SHOW"
    HIDE = "HIDE"

    # Saisie
    ENABLE = "ENABLE"
    DISABLE = "DISABLE"
    REQUIRE = "REQUIRE"
    OPTIONAL = "OPTIONAL"
    READONLY = "READONLY"
    EDITABLE = "EDITABLE"

    # Valeur
    CLEAR_VALUE = "CLEAR_VALUE"
    SET_VALUE = "SET_VALUE"
    COPY_VALUE = "COPY_VALUE"

    # Options
    FILTER_OPTIONS = "FILTER_OPTIONS"

    # Répétition
    REPEAT_SECTION = "REPEAT_SECTION"
