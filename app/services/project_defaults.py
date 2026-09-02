from copy import deepcopy
from typing import Any

DEFAULT_PROJECT_GLOBAL_CONFIG: dict[str, Any] = {
    "collection": {
        "require_all_questions": False,
    },
    "geolocation": {
        "enabled": False,
    },
    "mapping": {
        "enabled": False,
        "basemap": "standard",
    },
    "agent_monitoring": {
        "enabled": False,
    },
    "anti_fraud": {
        "enabled": False,
    },
    "offline": {
        "enabled": True,
    },
    "media": {
        "allow_photo": True,
        "allow_video": False,
        "allow_audio": False,
    },
    "attachments": {
        "enabled": False,
    },
}


def normalize_project_global_config(
    config: dict[str, Any] | None,
) -> dict[str, Any]:
    normalized = deepcopy(
        DEFAULT_PROJECT_GLOBAL_CONFIG,
    )

    if not config:
        return normalized

    config = deepcopy(config)

    # ------------------------------------------------------------------
    # Compatibilité avec l'ancien nom de propriété.
    #
    # Ancien format :
    #     collection.require_all_forms
    #
    # Nouveau format :
    #     collection.require_all_questions
    # ------------------------------------------------------------------
    collection = config.get("collection")

    if isinstance(collection, dict):
        if "require_all_questions" not in collection and "require_all_forms" in collection:
            collection["require_all_questions"] = collection["require_all_forms"]

        collection.pop(
            "require_all_forms",
            None,
        )

    # ------------------------------------------------------------------
    # Fusion avec les valeurs par défaut.
    # ------------------------------------------------------------------
    for section_name, section_values in config.items():

        if not isinstance(section_values, dict):
            normalized[section_name] = section_values
            continue

        if section_name not in normalized:
            normalized[section_name] = deepcopy(
                section_values,
            )
            continue

        normalized[section_name].update(
            section_values,
        )

    return normalized


def merge_project_global_config(
    current: dict[str, Any] | None,
    patch: dict[str, Any],
) -> dict[str, Any]:
    merged = deepcopy(current if isinstance(current, dict) else DEFAULT_PROJECT_GLOBAL_CONFIG)

    for section_name, section_values in patch.items():

        if not isinstance(section_values, dict):
            merged[section_name] = section_values
            continue

        current_section = merged.get(
            section_name,
        )

        if not isinstance(current_section, dict):
            merged[section_name] = deepcopy(
                section_values,
            )
            continue

        current_section.update(
            section_values,
        )

    return normalize_project_global_config(
        merged,
    )
