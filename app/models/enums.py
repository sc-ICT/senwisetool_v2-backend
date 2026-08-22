import enum


class UserRole(str, enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    SUPERVISOR = "SUPERVISOR"
    LEADER = "LEADER"


class UserStatus(str, enum.Enum):
    PENDING = "PENDING"  # compte créé, email non vérifié
    ACTIVE = "ACTIVE"  # compte actif
    SUSPENDED = "SUSPENDED"  # suspendu par un admin
    DEACTIVATED = "DEACTIVATED"


class FileNodeType(str, enum.Enum):
    FOLDER = "FOLDER"
    FILE = "FILE"


# class FormStatus(str, enum.Enum):
#     DRAFT = "DRAFT"  # en cours de construction
#     PUBLISHED = "PUBLISHED"  # publié, prêt à être déployé
#     ARCHIVED = "ARCHIVED"  # archivé, plus modifiable
#     DELETED = "DELETED"  # supprimé (soft delete)


# class ItemStatus(str, enum.Enum):
#     """Statut pour les sections et questions dans un formulaire."""

#     AVAILABLE = "AVAILABLE"
#     HIDDEN = "HIDDEN"
#     DELETED = "DELETED"


# class AgentFormStatus(str, enum.Enum):
#     PENDING_APPROVAL = "PENDING_APPROVAL"  # agent a demandé, admin pas encore répondu
#     PENDING_DOWNLOAD = "PENDING_DOWNLOAD"  # approuvé, pas encore téléchargé
#     DOWNLOADED = "DOWNLOADED"  # téléchargé sur le mobile
#     REJECTED = "REJECTED"  # refusé par l'admin


# class SubmissionStatus(str, enum.Enum):
#     DRAFT = "DRAFT"  # collecte en cours sur le mobile
#     COMPLETED = "COMPLETED"  # terminée localement
#     PENDING_SYNC = "PENDING_SYNC"  # en cours d'envoi
#     SYNCED = "SYNCED"  # reçue et confirmée par le serveur
#     SYNC_ERROR = "SYNC_ERROR"  # erreur lors de l'envoi


# class QuestionType(str, enum.Enum):
#     # Texte
#     TEXT = "TEXT"
#     LONG_TEXT = "LONG_TEXT"
#     EMAIL = "EMAIL"
#     PHONE = "PHONE"
#     URL = "URL"
#     ADDRESS = "ADDRESS"
#     # Numérique
#     NUMBER = "NUMBER"
#     DECIMAL = "DECIMAL"
#     INTERVAL = "INTERVAL"
#     SLIDER = "SLIDER"
#     # Choix
#     SINGLE_CHOICE = "SINGLE_CHOICE"
#     MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
#     DROPDOWN = "DROPDOWN"
#     RANKING = "RANKING"
#     RATING = "RATING"
#     LIKERT_SCALE = "LIKERT_SCALE"
#     TABLE = "TABLE"
#     MATRIX = "MATRIX"
#     # Date & heure
#     DATE = "DATE"
#     TIME = "TIME"
#     DATETIME = "DATETIME"
#     # Géolocalisation
#     POINT = "POINT"
#     LINE = "LINE"
#     POLYGON = "POLYGON"
#     ZONE = "ZONE"
#     # Médias
#     PHOTO = "PHOTO"
#     VIDEO = "VIDEO"
#     AUDIO = "AUDIO"
#     FILE = "FILE"
#     SIGNATURE = "SIGNATURE"
#     QR_CODE = "QR_CODE"
#     BARCODE = "BARCODE"
#     # Logique & affichage
#     CALCULATION = "CALCULATION"
#     HIDDEN = "HIDDEN"
#     NOTE = "NOTE"
#     CONSENT = "CONSENT"
#     EXTERNAL_XML = "EXTERNAL_XML"


# class MapType(str, enum.Enum):
#     """Fond de carte pour les questions géolocalisation."""

#     STANDARD = "STANDARD"
#     SATELLITE = "SATELLITE"
