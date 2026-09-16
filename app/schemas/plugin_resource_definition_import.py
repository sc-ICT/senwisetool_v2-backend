from __future__ import annotations

from pydantic import BaseModel

from app.models.enums import PluginResourceScope


class PluginResourceDefinitionImportItem(BaseModel):
    worksheet: str
    resource_reference: str
    schema_reference: str
    data_reference: str | None = None
    relation_reference: str | None = None
    resource_id: int
    key: str
    name: str
    scope: PluginResourceScope
    fields_count: int
    records_count: int
    relations_count: int


class PluginResourceDefinitionImportResponse(BaseModel):
    plugin_id: int
    sheets: int
    resources_created: int
    schemas_created: int
    fields_created: int
    records_imported: int
    relations_created: int
    resources: list[PluginResourceDefinitionImportItem]
